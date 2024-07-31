import socket
import json
import threading
import hashlib
import time

class TradingClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.connected = False

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Connected to server at {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.connected = False

    def reconnect(self):
        print("Attempting to reconnect...")
        for _ in range(3):  # Try to reconnect 3 times
            self.connect()
            if self.connected:
                return True
            time.sleep(2)  # Wait for 2 seconds before trying again
        return False

    def send_message(self, message):
        if not self.connected:
            if not self.reconnect():
                print("Failed to reconnect. Please try again later.")
                return False

        data = self.create_message(message['type'], self.username, message.get('content', {}))
        message_length = len(data).to_bytes(4, byteorder='big')
        try:
            self.socket.send(message_length + data.encode())
            return True
        except BrokenPipeError:
            print("Connection lost. Attempting to reconnect...")
            self.connected = False
            return self.send_message(message)  # Recursive call after reconnection attempt
        except Exception as e:
            print(f"Error sending message: {e}")
            self.connected = False
            return False

    def receive_message(self):
        if not self.connected:
            if not self.reconnect():
                print("Failed to reconnect. Please try again later.")
                return None

        try:
            message_length = int.from_bytes(self.socket.recv(4), byteorder='big')
            message_data = self.socket.recv(message_length).decode()
            return self.parse_message(message_data)
        except ConnectionResetError:
            print("Connection reset by server. Attempting to reconnect...")
            self.connected = False
            if self.reconnect():
                return self.receive_message()  # Recursive call after reconnection
            return None
        except Exception as e:
            print(f"Error receiving message: {e}")
            self.connected = False
            return None

    @staticmethod
    def create_message(msg_type, user, content):
        header = json.dumps({'type': msg_type, 'user': user})
        body = json.dumps(content)
        combined = f"{header}\n{body}"
        checksum = hashlib.md5(combined.encode()).hexdigest()
        return f"{header}\n{body}\n{checksum}"

    @staticmethod
    def parse_message(data):
        try:
            # Try to parse as JSON first
            parsed_data = json.loads(data)
            return {'header': {'type': 'RESPONSE'}, 'body': parsed_data}
        except json.JSONDecodeError:
            # If it's not JSON, try to split it into parts
            parts = data.split('\n', 2)
            if len(parts) == 3:
                header, body, received_checksum = parts
                try:
                    header = json.loads(header)
                    body = json.loads(body)
                    combined = f"{json.dumps(header)}\n{json.dumps(body)}"
                    calculated_checksum = hashlib.md5(combined.encode()).hexdigest()
                    
                    if calculated_checksum != received_checksum:
                        print("Warning: Checksum mismatch")
                    
                    return {'header': header, 'body': body}
                except json.JSONDecodeError:
                    pass  # If parsing fails, fall through to the default case
            
            # If all else fails, wrap the raw data in a JSON structure
            return {
                'header': {'type': 'UNKNOWN'},
                'body': {'message': data.strip() if data.strip() else 'Empty response'}
            }

    def register(self, username):
        if self.send_message({'type': 'REGISTER', 'user': username}):
            response = self.receive_message()
            if response:
                print(response['body'].get('message', 'Unknown response'))
                if response['body'].get('status') == 'SUCCESS':
                    self.username = username

    def login(self, username):
        if self.send_message({'type': 'LOGIN', 'user': username}):
            response = self.receive_message()
            if response:
                print(response['body'].get('message', 'Unknown response'))
                if response['body'].get('status') == 'SUCCESS':
                    self.username = username

    def logout(self):
        if self.send_message({'type': 'LOGOUT', 'user': self.username}):
            response = self.receive_message()
            if response:
                print(response['body'].get('message', 'Unknown response'))
                self.username = None

    def get_balance(self):
        if self.send_message({'type': 'BALANCE', 'user': self.username}):
            response = self.receive_message()
            if response:
                if response['body'].get('status') == 'SUCCESS':
                    print("Your balance:")
                    for currency, amount in response['body'].get('balance', {}).items():
                        print(f"{currency}: {amount}")
                else:
                    print(response['body'].get('message', 'Unknown response'))

    def place_order(self, order_type, crypto, amount, price):
        content = {
            'order_type': order_type,
            'crypto': crypto,
            'amount': float(amount),
            'price': float(price)
        }
        if self.send_message({'type': 'ORDER', 'user': self.username, 'content': content}):
            response = self.receive_message()
            if response:
                print(response['body'].get('message', 'Unknown response'))

    def get_market_data(self):
        if self.send_message({'type': 'MARKET_DATA', 'user': self.username}):
            response = self.receive_message()
            if response:
                if response['body'].get('status') == 'SUCCESS':
                    print("Current market data:")
                    for crypto, price in response['body'].get('market_data', {}).items():
                        print(f"{crypto}: ${price:.2f}")
                else:
                    print(response['body'].get('message', 'Unknown response'))

def main():
    client = TradingClient('localhost', 5001)
    client.connect()

    while True:
        command = input("Enter command (register/login/logout/balance/buy/sell/market/exit): ").lower()

        if command == 'exit':
            break
        elif command == 'register':
            username = input("Enter username: ")
            client.register(username)
        elif command == 'login':
            username = input("Enter username: ")
            client.login(username)
        elif command == 'logout':
            client.logout()
        elif command == 'balance':
            client.get_balance()
        elif command in ['buy', 'sell']:
            crypto = input("Enter crypto (A/B/C): ").upper()
            amount = input("Enter amount: ")
            price = input("Enter price: ")
            client.place_order(command.upper(), crypto, amount, price)
        elif command == 'market':
            client.get_market_data()
        else:
            print("Invalid command. Please try again.")

    if client.socket:
        client.socket.close()

if __name__ == "__main__":
    main()