import asyncio
import json
import random
from datetime import datetime
from typing import Dict, List, Any

class CTSServer:
    def __init__(self, host: str = 'localhost', port: int = 6001):
        self.host = host
        self.port = port
        self.clients: Dict[str, asyncio.StreamWriter] = {}
        self.prices: Dict[str, float] = {'AA': 100.0, 'BB': 200.0, 'CC': 300.0}
        self.users: Dict[str, Dict[str, Any]] = {
            'beer': {
                'password': '1234',
                'portfolio': {'AA': 10, 'BB': 20, 'CC': 30},
                'balance': 5000
            },
        }
        self.transactions: List[Dict[str, Any]] = []

    async def start(self):
        server = await asyncio.start_server(
            self._handle_client, self.host, self.port)
        
        print(f"Server listening on {self.host}:{self.port}")
        
        asyncio.create_task(self._update_prices())
        
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        client_id = f"{writer.get_extra_info('peername')}"
        self.clients[client_id] = writer
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                message = data.decode()
                response = await self._process_request(client_id, message)
                writer.write(response.encode())
                await writer.drain()
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            del self.clients[client_id]
            writer.close()
            await writer.wait_closed()

    async def _process_request(self, client_id: str, data: str) -> str:
        try:
            lines = data.split('\n')
            request_line = lines[0].split()
            method, resource = request_line[1], request_line[2]
            body = lines[-1] if len(lines) > 1 else ''

            request_handlers = {
                ('REGISTER', '/auth'): self._register_user,
                ('LOGIN', '/auth'): self._login_user,
                ('LOGOUT', '/auth'): self._logout_user,
                ('GET_PRICES', '/market'): self._get_prices,
                ('BUY', '/trade'): self._process_buy,
                ('SELL', '/trade'): self._process_sell,
                ('GET_PORTFOLIO', '/portfolio'): self._get_portfolio,
                ('GET_HISTORY', '/history'): self._get_history,
                ('GET_REPORT', '/report'): self._get_report
            }

            handler = request_handlers.get((method, resource))
            if handler:
                return await handler(client_id, json.loads(body) if body else None)
            else:
                return self._create_response(400, "Bad Request")
        except Exception as e:
            return self._create_response(500, f"Internal Server Error: {str(e)}")

    async def _register_user(self, client_id: str, user_data: Dict[str, str]) -> str:
        username = user_data['username']
        if username in self.users:
            return self._create_response(400, "Username already exists")
        self.users[username] = {
            'password': user_data['password'],
            'portfolio': {'AA': 0, 'BB': 0, 'CC': 0},
            'balance': 10000  # Starting balance
        }
        return self._create_response(200, "User registered successfully")

    async def _login_user(self, client_id: str, login_data: Dict[str, str]) -> str:
        username = login_data['username']
        password = login_data['password']
        if username in self.users and self.users[username]['password'] == password:
            self.clients[client_id].username = username
            return self._create_response(200, "Login successful")
        return self._create_response(401, "Invalid credentials")

    async def _logout_user(self, client_id: str, _: None) -> str:
        if hasattr(self.clients[client_id], 'username'):
            del self.clients[client_id].username
            return self._create_response(200, "Logout successful")
        return self._create_response(400, "No user logged in")

    async def _get_prices(self, client_id: str, _: None) -> str:
        return self._create_response(200, json.dumps(self.prices))

    async def _process_buy(self, client_id: str, trade_data: Dict[str, Any]) -> str:
        return await self._process_trade(client_id, trade_data, 'buy')

    async def _process_sell(self, client_id: str, trade_data: Dict[str, Any]) -> str:
        return await self._process_trade(client_id, trade_data, 'sell')

    async def _process_trade(self, client_id: str, trade_data: Dict[str, Any], trade_type: str) -> str:
        if not hasattr(self.clients[client_id], 'username'):
            return self._create_response(401, "User not logged in")
        
        username = self.clients[client_id].username
        coin = trade_data['coin']
        amount = trade_data['amount']
        price = self.prices[coin]
        total_cost = amount * price
        
        user = self.users[username]
        if trade_type == 'buy':
            if user['balance'] < total_cost:
                return self._create_response(400, "Insufficient funds")
            user['balance'] -= total_cost
            user['portfolio'][coin] += amount
        else:  # sell
            if user['portfolio'][coin] < amount:
                return self._create_response(400, "Insufficient coins")
            user['balance'] += total_cost
            user['portfolio'][coin] -= amount
        
        await self._record_transaction(username, trade_type, coin, amount, price)
        
        return self._create_response(200, f"{trade_type.capitalize()} order processed for {amount} {coin} at {price}")

    async def _record_transaction(self, username: str, trade_type: str, coin: str, amount: float, price: float):
        transaction = {
            'username': username,
            'type': trade_type,
            'coin': coin,
            'amount': amount,
            'price': price,
            'timestamp': datetime.now().isoformat()
        }
        self.transactions.append(transaction)
        await self._notify_clients('NEW_TRANSACTION', transaction)

    async def _get_portfolio(self, client_id: str, _: None) -> str:
        if not hasattr(self.clients[client_id], 'username'):
            return self._create_response(401, "User not logged in")
        username = self.clients[client_id].username
        return self._create_response(200, json.dumps(self.users[username]['portfolio']))

    async def _get_history(self, client_id: str, _: None) -> str:
        if not hasattr(self.clients[client_id], 'username'):
            return self._create_response(401, "User not logged in")
        username = self.clients[client_id].username
        user_transactions = [t for t in self.transactions if t['username'] == username]
        return self._create_response(200, json.dumps(user_transactions))

    async def _get_report(self, client_id: str, _: None) -> str:
        if not hasattr(self.clients[client_id], 'username'):
            return self._create_response(401, "User not logged in")
        username = self.clients[client_id].username
        user = self.users[username]
        total_value = user['balance'] + sum(user['portfolio'][coin] * self.prices[coin] for coin in self.prices)
        report = {
            'balance': user['balance'],
            'portfolio': user['portfolio'],
            'total_value': total_value,
            'profit_loss': total_value - 10000  # Assuming starting balance was 10000
        }
        return self._create_response(200, json.dumps(report))

    async def _update_prices(self):
        while True:
            await asyncio.sleep(1)  # Update prices every second
            old_prices = self.prices.copy()
            for coin in self.prices:
                self.prices[coin] *= (1 + (random.random() - 0.5) * 0.02)  # Random price fluctuation ±1%
            if self.prices != old_prices:
                await self._notify_clients('PRICE_UPDATE', self.prices)

    async def _notify_clients(self, notification_type: str, data: Any):
        message = json.dumps({
            'type': notification_type,
            'data': data
        })
        for client in self.clients.values():
            try:
                client.write(self._create_response(200, message).encode())
                await client.drain()
            except Exception as e:
                print(f"Error notifying client: {e}")

    @staticmethod
    def _create_response(status_code: int, body: str) -> str:
        status_phrase = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 500: "Internal Server Error"}
        headers = f"CTSP/1.0 {status_code} {status_phrase.get(status_code, '')}\n"
        headers += f"Content-Length: {len(body)}\n"
        return f"{headers}\n{body}"

if __name__ == "__main__":
    server = CTSServer()
    asyncio.run(server.start())