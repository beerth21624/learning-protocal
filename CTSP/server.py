import socket
import json
import threading
import time
from datetime import datetime
import random
from typing import Dict, List, Any

class CTSServer:
    def __init__(self, host: str = 'localhost', port: int = 6002):
        self.host = host
        self.port = port
        self.server_socket  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: Dict[int, Dict[str, Any]] = {}
        self.prices: Dict[str, float] = {'AA': 100.0, 'BB': 200.0, 'CC': 300.0}
        self.users: Dict[str, Dict[str, Any]] = {
            'beer': {
                'password': '1234',
                'portfolio': {'AA': 10, 'BB': 20, 'CC': 30},
                'balance': 5000
            },
        }
        self.transactions: List[Dict[str, Any]] = []

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server listening on {self.host}:{self.port}")
        
        self._start_price_update_thread()
        
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"New connection from {addr}")
            self._start_client_thread(client_socket)

    def _start_price_update_thread(self):
        price_thread = threading.Thread(target=self._update_prices)
        price_thread.daemon = True
        price_thread.start()

    def _start_client_thread(self, client_socket):
        client_thread = threading.Thread(target=self._handle_client, args=(client_socket,))
        client_thread.start()

    def _handle_client(self, client_socket):
        client_id = id(client_socket)
        self.clients[client_id] = {'socket': client_socket, 'user': None}
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                response = self._process_request(client_id, data)
                client_socket.send(response.encode('utf-8'))
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            del self.clients[client_id]
            client_socket.close()

    def _process_request(self, client_id: int, data: str) -> str:
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
                ('GET_REPORT', '/report'): self._get_report,
                ('GET_LEADERBOARD', '/leaderboard'): self._get_leaderboard  # เพิ่มตัวจัดการคำขอสำหรับ Leaderboard
            }

            handler = request_handlers.get((method, resource))
            if handler:
                return handler(client_id, json.loads(body) if body else None)
            else:
                return self._create_response(400, "Bad Request")
        except Exception as e:
            return self._create_response(500, f"Internal Server Error: {str(e)}")

    def _get_leaderboard(self, client_id: int, _: None) -> str:
        leaderboard = []
        for username, user_data in self.users.items():
            total_value = user_data['balance'] + sum(user_data['portfolio'][coin] * self.prices[coin] for coin in self.prices)
            profit_loss = total_value - 10000  # สมมติว่าเงินเริ่มต้นคือ 10000
            leaderboard.append({
                'username': username,
                'total_value': total_value,
                'profit_loss': profit_loss
            })
            leaderboard.sort(key=lambda x: x['profit_loss'], reverse=True)
            top_10 = leaderboard[:10]
        
        return self._create_response(200, json.dumps(top_10))

    def _register_user(self, client_id: int, user_data: Dict[str, str]) -> str:
        print(user_data)
        print(self.users)
        username = user_data['username']
        if username in self.users:
            return self._create_response(400, "Username already exists")
        self.users[username] = {
            'password': user_data['password'],
            'portfolio': {'AA': 0, 'BB': 0, 'CC': 0},
            'balance': 10000  # Starting balance
        }
        return self._create_response(200, "User registered successfully")

    def _login_user(self, client_id: int, login_data: Dict[str, str]) -> str:
        username = login_data['username']
        password = login_data['password']
        if username in self.users and self.users[username]['password'] == password:
            self.clients[client_id]['user'] = username
            return self._create_response(200, "Login successful")
        return self._create_response(401, "Invalid credentials")

    def _logout_user(self, client_id: int, _: None) -> str:
        if self.clients[client_id]['user']:
            self.clients[client_id]['user'] = None
            return self._create_response(200, "Logout successful")
        return self._create_response(400, "No user logged in")

    def _get_prices(self, client_id: int, _: None) -> str:
        return self._create_response(200, json.dumps(self.prices))

    def _process_buy(self, client_id: int, trade_data: Dict[str, Any]) -> str:
        return self._process_trade(client_id, trade_data, 'buy')

    def _process_sell(self, client_id: int, trade_data: Dict[str, Any]) -> str:
        return self._process_trade(client_id, trade_data, 'sell')

    def _process_trade(self, client_id: int, trade_data: Dict[str, Any], trade_type: str) -> str:
        username = self.clients[client_id]['user']
        if not username:
            return self._create_response(401, "User not logged in")
        
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
        
        self._record_transaction(username, trade_type, coin, amount, price)
        
        return self._create_response(200, f"{trade_type.capitalize()} order processed for {amount} {coin} at {price}")

    def _record_transaction(self, username: str, trade_type: str, coin: str, amount: float, price: float):
        self.transactions.append({
            'username': username,
            'type': trade_type,
            'coin': coin,
            'amount': amount,
            'price': price,
            'timestamp': datetime.now().isoformat()
        })

    def _get_portfolio(self, client_id: int, _: None) -> str:
        username = self.clients[client_id]['user']
        if not username:
            return self._create_response(401, "User not logged in")
        return self._create_response(200, json.dumps(self.users[username]['portfolio']))

    def _get_history(self, client_id: int, _: None) -> str:
        username = self.clients[client_id]['user']
        if not username:
            return self._create_response(401, "User not logged in")
        user_transactions = [t for t in self.transactions if t['username'] == username]
        return self._create_response(200, json.dumps(user_transactions))

    def _get_report(self, client_id: int, _: None) -> str:
        username = self.clients[client_id]['user']
        if not username:
            return self._create_response(401, "User not logged in")
        user = self.users[username]
        total_value = user['balance'] + sum(user['portfolio'][coin] * self.prices[coin] for coin in self.prices)
        report = {
            'balance': user['balance'],
            'portfolio': user['portfolio'],
            'total_value': total_value,
            'profit_loss': total_value - 10000  # Assuming starting balance was 10000
        }
        return self._create_response(200, json.dumps(report))

    def _update_prices(self):
        while True:
            time.sleep(5)  # Update prices every 5 seconds
            for coin in self.prices:
                self.prices[coin] *= (1 + (random.random() - 0.5) * 0.02)  # Random price fluctuation ±1%

    @staticmethod
    def _create_response(status_code: int, body: str) -> str:
        status_phrase = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 500: "Internal Server Error"}
        headers = f"CTSP/1.0 {status_code} {status_phrase.get(status_code, '')}\n"
        headers += f"Content-Length: {len(body)}\n"
        return f"{headers}\n{body}"

if __name__ == "__main__":
    server = CTSServer()
    server.start()