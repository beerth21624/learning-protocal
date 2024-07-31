import socket
import json
from terminaltables import AsciiTable
from colorama import Fore, Back, Style, init

init(autoreset=True)  # Initialize colorama

class CTSClient:
    def __init__(self, host='localhost', port=6002):
        self.host = host
        self.port = port
        self.socket = None
        self.logged_in = False
        self.username = None

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))

    def send_request(self, method, resource, body=None):
        if not self.socket:
            self.connect()

        request = f"CTSP/1.0 {method} {resource}\n"
        if body:
            request += f"Content-Length: {len(body)}\n\n{body}"
        else:
            request += "\n"

        self.socket.send(request.encode())
        response = self.socket.recv(1024).decode()

        # Parse the response
        lines = response.split('\n')
        status_line = lines[0].split()
        status_code = int(status_line[1])
        body = lines[-1]

        return status_code, body

    def register(self, username, password):
        status_code, body = self.send_request('REGISTER', '/auth', json.dumps({
            'username': username,
            'password': password
        }))
        return status_code, body

    def login(self, username, password):
        status_code, body = self.send_request('LOGIN', '/auth', json.dumps({
            'username': username,
            'password': password
        }))
        if status_code == 200:
            self.logged_in = True
            self.username = username
        return status_code, body

    def logout(self):
        if self.logged_in:
            status_code, body = self.send_request('LOGOUT', '/auth')
            if status_code == 200:
                self.logged_in = False
                self.username = None
            return status_code, body
        return 400, "Not logged in"

    def get_prices(self):
        status, prices = self.send_request('GET_PRICES', '/market')
        if status == 200:
            return json.loads(prices)
        return None

    def trade(self, trade_type, coin, amount):
        return self.send_request(trade_type, '/trade', json.dumps({
            'coin': coin,
            'amount': float(amount)
        }))

    def get_portfolio(self):
        status, portfolio = self.send_request('GET_PORTFOLIO', '/portfolio')
        if status == 200:
            return json.loads(portfolio)
        return None

    def get_history(self):
        status, history = self.send_request('GET_HISTORY', '/history')
        if status == 200:
            return json.loads(history)
        return None

    def get_report(self):
        status, report = self.send_request('GET_REPORT', '/report')
        if status == 200:
            return json.loads(report)
        return None
    def get_leaderboard(self):
        status, leaderboard = self.send_request('GET_LEADERBOARD', '/leaderboard')
        if status == 200:
            return json.loads(leaderboard)
        return None

def print_menu():
    menu = [
        ['Crypto Trading Simulator'],
        ['1. Register', '6. Buy'],
        ['2. Login', '7. Sell'],
        ['3. Logout', '8. View Portfolio'],
        ['4. Get Prices', '9. View Trade History'],
        ['5. View Dashboard', '10. View Leaderboard'],
        ['0. Exit']
    ]
    table = AsciiTable(menu)
    table.inner_heading_row_border = False
    print(f"\n{Fore.CYAN}{table.table}{Style.RESET_ALL}")

def format_currency(value):
    return f"${value:.2f}"

def print_prices(prices):
    if prices:
        data = [['Coin', 'Price']]
        for coin, price in prices.items():
            data.append([coin, format_currency(price)])
        table = AsciiTable(data)
        print(f"\n{Fore.GREEN}Current Prices:{Style.RESET_ALL}")
        print(table.table)
    else:
        print(f"{Fore.RED}Unable to fetch prices.{Style.RESET_ALL}")

def print_portfolio(portfolio):
    if portfolio:
        data = [['Coin', 'Amount']]
        for coin, amount in portfolio.items():
            data.append([coin, amount])
        table = AsciiTable(data)
        print(f"\n{Fore.GREEN}Your Portfolio:{Style.RESET_ALL}")
        print(table.table)
    else:
        print(f"{Fore.RED}Unable to fetch portfolio.{Style.RESET_ALL}")

def print_history(history):
    if history:
        data = [['Type', 'Coin', 'Amount', 'Price', 'Time']]
        for trade in history:
            data.append([
                trade['type'],
                trade['coin'],
                trade['amount'],
                format_currency(trade['price']),
                trade['timestamp']
            ])
        table = AsciiTable(data)
        print(f"\n{Fore.GREEN}Trade History:{Style.RESET_ALL}")
        print(table.table)
    else:
        print(f"{Fore.RED}Unable to fetch trade history.{Style.RESET_ALL}")

def print_report(report):
    if report:
        print(f"\n{Fore.GREEN}Financial Report:{Style.RESET_ALL}")
        print(f"Balance: {format_currency(report['balance'])}")
        print(f"Total Value: {format_currency(report['total_value'])}")
        print(f"Profit/Loss: {format_currency(report['profit_loss'])}")
        print("\nPortfolio:")
        for coin, amount in report['portfolio'].items():
            print(f"  {coin}: {amount}")
    else:
        print(f"{Fore.RED}Unable to fetch report.{Style.RESET_ALL}")

def print_dashboard(client):
    prices = client.get_prices()
    portfolio = client.get_portfolio()
    report = client.get_report()

    print(f"\n{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.CYAN}{'Dashboard':^40}")
    print(f"{Fore.CYAN}{'=' * 40}{Style.RESET_ALL}")

    print_prices(prices)
    print_portfolio(portfolio)
    print_report(report)

def print_leaderboard(leaderboard):
    if leaderboard:
        data = [['Rank', 'Username', 'Total Value', 'Profit/Loss']]
        for i, user in enumerate(leaderboard, 1):
            data.append([
                i,
                user['username'],
                format_currency(user['total_value']),
                format_currency(user['profit_loss'])
            ])
        table = AsciiTable(data)
        print(f"\n{Fore.GREEN}Leaderboard:{Style.RESET_ALL}")
        print(table.table)
    else:
        print(f"{Fore.RED}Unable to fetch leaderboard.{Style.RESET_ALL}")

def main():
    client = CTSClient()

    while True:
        print_menu()
        choice = input(f"{Fore.YELLOW}Enter your choice: {Style.RESET_ALL}")

        if choice == '1':
            username = input("Enter username: ")
            password = input("Enter password: ")
            status, message = client.register(username, password)
            print(f"{Fore.GREEN if status == 200 else Fore.RED}Status: {status}, Message: {message}{Style.RESET_ALL}")

        elif choice == '2':
            username = input("Enter username: ")
            password = input("Enter password: ")
            status, message = client.login(username, password)
            print(f"{Fore.GREEN if status == 200 else Fore.RED}Status: {status}, Message: {message}{Style.RESET_ALL}")

        elif choice == '3':
            status, message = client.logout()
            print(f"{Fore.GREEN if status == 200 else Fore.RED}Status: {status}, Message: {message}{Style.RESET_ALL}")

        elif choice == '4':
            prices = client.get_prices()
            print_prices(prices)

        elif choice == '5':
            print_dashboard(client)

        elif choice in ['6', '7']:
            trade_type = 'BUY' if choice == '6' else 'SELL'
            coin = input("Enter coin (AA/BB/CC): ").upper()
            amount = input("Enter amount: ")
            status, message = client.trade(trade_type, coin, amount)
            print(f"{Fore.GREEN if status == 200 else Fore.RED}Status: {status}, Message: {message}{Style.RESET_ALL}")

        elif choice == '8':
            portfolio = client.get_portfolio()
            print_portfolio(portfolio)

        elif choice == '9':
            history = client.get_history()
            print_history(history)

        elif choice == '0':
            print(f"{Fore.CYAN}Thank you for using Crypto Trading Simulator. Goodbye!{Style.RESET_ALL}")
            break

        elif choice == '10':
            leaderboard = client.get_leaderboard()
            print_leaderboard(leaderboard)

        elif choice == '0':
            print(f"{Fore.CYAN}Thank you for using Crypto Trading Simulator. Goodbye!{Style.RESET_ALL}")
            break

        else:
            print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")


if __name__ == "__main__":
    main()