import socket
import threading
import json
import time
import random
import hashlib

# Utility functions
def calculate_checksum(data):
    return hashlib.md5(data.encode()).hexdigest()

def create_message(msg_type, user, content):
    body = json.dumps({'type': msg_type, 'user': user, 'content': content})
    checksum = calculate_checksum(body)
    header = json.dumps({'length': len(body), 'checksum': checksum})
    return f"{header}\n{body}"

def parse_message(data):
    header, body = data.split('\n', 1)
    header = json.loads(header)
    body = json.loads(body)
    
    if calculate_checksum(body) != header['checksum']:
        raise ValueError("Checksum mismatch")
    
    return body

# Server
class TradingServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # {client_socket: username}
        self.balances = {}  # {username: {'A': 100, 'B': 100, 'C': 100, 'USD': 10000}}
        self.market_data = {'A': 10, 'B': 20, 'C': 30}  # Initial prices
        self.orders = []  # List of active orders

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server started on {self.host}:{self.port}")
        
        # Start market data simulation
        threading.Thread(target=self.simulate_market, daemon=True).start()
        
        while True:
            client_socket, address = self.server_socket.accept()
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()

    def handle_client(self, client_socket):
        while True:
            try:
                message = self.receive_message(client_socket)
                if not message:
                    break
                
                response = self.process_message(client_socket, message)
                self.send_message(client_socket, response)
            except Exception as e:
                print(f"Error handling client: {e}")
                break
        
        if client_socket in self.clients:
            del self.clients[client_socket]
        client_socket.close()

    def receive_message(self, client_socket):
        header_length = int.from_bytes(client_socket.recv(4), byteorder='big')
        header = client_socket.recv(header_length).decode()
        header = json.loads(header)
        
        body = client_socket.recv(header['length']).decode()
        
        try:
            return parse_message(f"{json.dumps(header)}\n{body}")
        except ValueError:
            print("Received message with invalid checksum")
            return None

    def send_message(self, client_socket, message):
        data = create_message(message['type'], message.get('user', ''), message.get('content', {}))
        header_length = len(data.split('\n')[0]).to_bytes(4, byteorder='big')
        client_socket.send(header_length + data.encode())

    def process_message(self, client_socket, message):
        msg_type = message['type']
        username = message['user']
        content = message.get('content', {})

        if msg_type == 'REGISTER':
            if username not in self.balances:
                self.balances[username] = {'A': 100, 'B': 100, 'C': 100, 'USD': 10000}
                return {'type': 'RESPONSE', 'status': 'SUCCESS', 'message': 'Registered successfully'}
            else:
                return {'type': 'RESPONSE', 'status': 'ERROR', 'message': 'Username already exists'}

        elif msg_type == 'LOGIN':
            self.clients[client_socket] = username
            return {'type': 'RESPONSE', 'status': 'SUCCESS', 'message': 'Logged in successfully'}

        elif msg_type == 'LOGOUT':
            if client_socket in self.clients:
                del self.clients[client_socket]
            return {'type': 'RESPONSE', 'status': 'SUCCESS', 'message': 'Logged out successfully'}

        elif msg_type == 'BALANCE':
            if username in self.balances:
                return {'type': 'RESPONSE', 'status': 'SUCCESS', 'content': {'balance': self.balances[username]}}
            else:
                return {'type': 'RESPONSE', 'status': 'ERROR', 'message': 'User not found'}

        elif msg_type == 'ORDER':
            order_type = content['order_type']
            crypto = content['crypto']
            amount = content['amount']
            price = content['price']

            if username not in self.balances:
                return {'type': 'RESPONSE', 'status': 'ERROR', 'message': 'User not found'}

            if order_type == 'BUY':
                if self.balances[username]['USD'] < amount * price:
                    return {'type': 'RESPONSE', 'status': 'ERROR', 'message': 'Insufficient USD balance'}
                self.balances[username]['USD'] -= amount * price
                self.balances[username][crypto] += amount
            elif order_type == 'SELL':
                if self.balances[username][crypto] < amount:
                    return {'type': 'RESPONSE', 'status': 'ERROR', 'message': f'Insufficient {crypto} balance'}
                self.balances[username]['USD'] += amount * price
                self.balances[username][crypto] -= amount

            return {'type': 'RESPONSE', 'status': 'SUCCESS', 'message': f'{order_type} order executed successfully'}

        elif msg_type == 'MARKET_DATA':
            return {'type': 'RESPONSE', 'status': 'SUCCESS', 'content': {'market_data': self.market_data}}

        else:
            return {'type': 'RESPONSE', 'status': 'ERROR', 'message': 'Invalid message type'}

    def simulate_market(self):
        while True:
            for crypto in self.market_data:
                change = random.uniform(-0.5, 0.5)
                self.market_data[crypto] *= (1 + change)
            time.sleep(5)  # Update every 5 seconds

# Usage
if __name__ == "__main__":
    server = TradingServer('localhost', 5003)
    server.start()