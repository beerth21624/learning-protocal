import asyncio
import json
import aioconsole
from typing import Dict, Any

class CTSClient:
    def __init__(self, host='localhost', port=6001):
        self.host = host
        self.port = port
        self.reader: asyncio.StreamReader = None
        self.writer: asyncio.StreamWriter = None
        self.logged_in = False
        self.username = None
        self.prices: Dict[str, float] = {}
        self.portfolio: Dict[str, float] = {}
        self.balance: float = 0

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        asyncio.create_task(self.listen_for_updates())

    async def send_request(self, method: str, resource: str, body: Any = None) -> Dict[str, Any]:
        if not self.writer:
            await self.connect()

        request = f"CTSP/1.0 {method} {resource}\n"
        if body:
            body_json = json.dumps(body)
            request += f"Content-Length: {len(body_json)}\n\n{body_json}"
        else:
            request += "\n"

        self.writer.write(request.encode())
        await self.writer.drain()

        response = await self.reader.read(1024)
        response_str = response.decode()

        lines = response_str.split('\n')
        status_line = lines[0].split()
        status_code = int(status_line[1])
        body = json.loads(lines[-1]) if lines[-1] else {}

        return {"status": status_code, "body": body}

    async def register(self, username: str, password: str) -> Dict[str, Any]:
        return await self.send_request('REGISTER', '/auth', {'username': username, 'password': password})

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        response = await self.send_request('LOGIN', '/auth', {'username': username, 'password': password})
        if response['status'] == 200:
            self.logged_in = True
            self.username = username
            await self.update_portfolio()
        return response

    async def logout(self) -> Dict[str, Any]:
        if self.logged_in:
            response = await self.send_request('LOGOUT', '/auth')
            if response['status'] == 200:
                self.logged_in = False
                self.username = None
                self.portfolio = {}
                self.balance = 0
            return response
        return {"status": 400, "body": "Not logged in"}

    async def get_prices(self) -> Dict[str, Any]:
        return await self.send_request('GET_PRICES', '/market')

    async def trade(self, trade_type: str, coin: str, amount: float) -> Dict[str, Any]:
        response = await self.send_request(trade_type, '/trade', {'coin': coin, 'amount': amount})
        if response['status'] == 200:
            await self.update_portfolio()
        return response

    async def get_portfolio(self) -> Dict[str, Any]:
        return await self.send_request('GET_PORTFOLIO', '/portfolio')

    async def get_history(self) -> Dict[str, Any]:
        return await self.send_request('GET_HISTORY', '/history')

    async def get_report(self) -> Dict[str, Any]:
        return await self.send_request('GET_REPORT', '/report')

    async def update_portfolio(self):
        portfolio_response = await self.get_portfolio()
        if portfolio_response['status'] == 200:
            self.portfolio = portfolio_response['body']
        report_response = await self.get_report()
        if report_response['status'] == 200:
            self.balance = report_response['body']['balance']

    async def listen_for_updates(self):
        while True:
            try:
                data = await self.reader.read(1024)
                if not data:
                    break
                message = json.loads(data.decode())
                if message['type'] == 'PRICE_UPDATE':
                    self.prices = message['data']
                    await self.display_prices()
                elif message['type'] == 'NEW_TRANSACTION':
                    print("\nNew transaction occurred. Your portfolio may have been updated.")
                    await self.update_portfolio()
                    await self.display_portfolio()
            except Exception as e:
                print(f"Error in listening for updates: {e}")
                break

    async def display_prices(self):
        print("\nCurrent Prices:")
        for coin, price in self.prices.items():
            print(f"{coin}: ${price:.2f}")

    async def display_portfolio(self):
        print("\nYour Portfolio:")
        for coin, amount in self.portfolio.items():
            print(f"{coin}: {amount}")
        print(f"Balance: ${self.balance:.2f}")

async def print_menu():
    print("\nCrypto Trading Simulator")
    print("1. Register")
    print("2. Login")
    print("3. Logout")
    print("4. Get Prices")
    print("5. Buy")
    print("6. Sell")
    print("7. View Portfolio")
    print("8. View Trade History")
    print("9. View Report")
    print("0. Exit")

async def main():
    client = CTSClient()

    while True:
        await print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == '1':
            username = await aioconsole.ainput("Enter username: ")
            password = await aioconsole.ainput("Enter password: ")
            response = await client.register(username, password)
            print(f"Status: {response['status']}, Message: {response['body']}")

        elif choice == '2':
            username = await aioconsole.ainput("Enter username: ")
            password = await aioconsole.ainput("Enter password: ")
            response = await client.login(username, password)
            print(f"Status: {response['status']}, Message: {response['body']}")

        elif choice == '3':
            response = await client.logout()
            print(f"Status: {response['status']}, Message: {response['body']}")

        elif choice == '4':
            response = await client.get_prices()
            if response['status'] == 200:
                await client.display_prices()
            else:
                print(f"Error: {response['body']}")

        elif choice in ['5', '6']:
            trade_type = 'BUY' if choice == '5' else 'SELL'
            coin = await aioconsole.ainput("Enter coin (AA/BB/CC): ").upper()
            amount = float(await aioconsole.ainput("Enter amount: "))
            response = await client.trade(trade_type, coin, amount)
            print(f"Status: {response['status']}, Message: {response['body']}")

        elif choice == '7':
            await client.display_portfolio()

        elif choice == '8':
            response = await client.get_history()
            if response['status'] == 200:
                for trade in response['body']:
                    print(f"Type: {trade['type']}, Coin: {trade['coin']}, Amount: {trade['amount']}, Price: {trade['price']}, Time: {trade['timestamp']}")
            else:
                print(f"Error: {response['body']}")

        elif choice == '9':
            response = await client.get_report()
            if response['status'] == 200:
                report = response['body']
                print(f"Balance: ${report['balance']:.2f}")
                print("Portfolio:")
                for coin, amount in report['portfolio'].items():
                    print(f"  {coin}: {amount}")
                print(f"Total Value: ${report['total_value']:.2f}")
                print(f"Profit/Loss: ${report['profit_loss']:.2f}")
            else:
                print(f"Error: {response['body']}")

        elif choice == '0':
            print("Thank you for using Crypto Trading Simulator. Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    asyncio.run(main())