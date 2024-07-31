import socket
import json
import threading
import time
import hashlib
import random
from typing import Dict, List, Any

class CTSPServer:
    def __init__(self, host: str = 'localhost', port: int = 6789):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: Dict[str, Dict[str, Any]] = {}
        self.prices: Dict[str, float] = {'BTC': 50000.0, 'ETH': 3000.0, 'DOGE': 0.5}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.sequence_numbers: Dict[str, int] = {}

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
        player_id = None
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                lines = data.split('\n')
                headers = {}
                for line in lines[1:]:
                    if line.strip() == '':
                        break
                    key, value = line.split(': ')
                    headers[key] = value
                
                payload = lines[-1]
                
                if self._verify_checksum(payload, headers['Checksum']):
                    response = self._process_request(headers, payload)
                    if 'Player-ID' in headers:
                        player_id = headers['Player-ID']
                        self.sequence_numbers[player_id] = int(headers['Sequence']) + 1
                    client_socket.send(response.encode('utf-8'))
                else:
                    nack = self._create_response("NACK", 400, {"error": "Checksum mismatch"}, player_id)
                    client_socket.send(nack.encode('utf-8'))
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            if player_id:
                del self.clients[player_id]
            client_socket.close()

    def _process_request(self, headers: Dict[str, str], payload: str) -> str:
        command = headers['CTSP/1.0']
        player_id = headers.get('Player-ID')
        
        handlers = {
            'ENTER': self._handle_enter,
            'EXIT': self._handle_exit,
            'SCAN': self._handle_scan,
            'BUY': self._handle_buy,
            'SELL': self._handle_sell,
            'CHECK': self._handle_check,
            'RANK': self._handle_rank,
            'PING': self._handle_ping
        }
        
        handler = handlers.get(command)
        if handler:
            return handler(player_id, json.loads(payload))
        else:
            return self._create_response(command, 400, {"error": "Invalid command"}, player_id)

    def _handle_enter(self, player_id: str, data: Dict[str, str]) -> str:
        username = data['username']
        password = data['password']
        
        if username in self.users and self.users[username]['password'] == password:
            player_id = f"{username}_{int(time.time())}"
            self.clients[player_id] = {'socket': None, 'username': username}
            self.sequence_numbers[player_id] = 0
            return self._create_response("ENTER", 200, {
                "message": f"Welcome back, {username}!",
                "player_id": player_id
            }, player_id)
        else:
            return self._create_response("ENTER", 401, {"error": "Invalid credentials"}, player_id)

    def _handle_exit(self, player_id: str, data: Dict[str, Any]) -> str:
        if player_id in self.clients:
            del self.clients[player_id]
            return self._create_response("EXIT", 200, {"message": "Logout successful"}, player_id)
        return self._create_response("EXIT", 400, {"error": "Not logged in"}, player_id)

    def _handle_scan(self, player_id: str, data: Dict[str, Any]) -> str:
        return self._create_response("SCAN", 200, {"market_data": [
            {"coin": coin, "price": price, "change_24h": f"{random.uniform(-10, 10):.1f}%"}
            for coin, price in self.prices.items()
        ]}, player_id)

    def _handle_buy(self, player_id: str, data: Dict[str, Any]) -> str:
        coin = data['coin']
        amount = data['amount']
        if coin in self.prices:
            return self._create_response("BUY", 200, {
                "message": f"Congrats! You've mined {amount} {coin}!",
                "transaction": {
                    "coin": coin,
                    "amount": amount,
                    "price": self.prices[coin],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            }, player_id)
        return self._create_response("BUY", 400, {"error": "Invalid coin"}, player_id)

    def _handle_sell(self, player_id: str, data: Dict[str, Any]) -> str:
        coin = data['coin']
        amount = data['amount']
        if coin in self.prices:
            return self._create_response("SELL", 200, {
                "message": f"You've sold {amount} {coin}!",
                "transaction": {
                    "coin": coin,
                    "amount": amount,
                    "price": self.prices[coin],
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            }, player_id)
        return self._create_response("SELL", 400, {"error": "Invalid coin"}, player_id)

    def _handle_check(self, player_id: str, data: Dict[str, Any]) -> str:
        check_type = data['type']
        if check_type == 'portfolio':
            return self._create_response("CHECK", 200, {
                "portfolio": {
                    "BTC": 1.5,
                    "ETH": 10,
                    "DOGE": 1000
                },
                "balance": 25000
            }, player_id)
        return self._create_response("CHECK", 400, {"error": "Invalid check type"}, player_id)

    def _handle_rank(self, player_id: str, data: Dict[str, Any]) -> str:
        return self._create_response("RANK", 200, {
            "leaderboard": [
                {"username": "Satoshi", "total_value": 100000, "rank": 1},
                {"username": "Vitalik", "total_value": 90000, "rank": 2},
                {"username": "Elon", "total_value": 80000, "rank": 3}
            ]
        }, player_id)

    def _handle_ping(self, player_id: str, data: Dict[str, Any]) -> str:
        return self._create_response("PONG", 200, {}, player_id)

    def _update_prices(self):
        while True:
            time.sleep(5)
            for coin in self.prices:
                self.prices[coin] *= (1 + (random.random() - 0.5) * 0.02)

    @staticmethod
    def _create_response(command: str, status_code: int, body: Dict[str, Any], player_id: str = None) -> str:
        status_phrase = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 500: "Internal Server Error"}
        body_json = json.dumps(body)
        checksum = CTSPServer._calculate_checksum(body_json)
        
        headers = f"CTSP/1.0 {command}\n"
        headers += f"Status: {status_code} {status_phrase.get(status_code, '')}\n"
        if player_id:
            headers += f"Player-ID: {player_id}\n"
            headers += f"Sequence: {CTSPServer._get_next_sequence(player_id)}\n"
        headers += f"Content-Length: {len(body_json)}\n"
        headers += f"Checksum: {checksum}\n"
        
        return f"{headers}\n{body_json}"

    @staticmethod
    def _calculate_checksum(payload: str) -> str:
        return hashlib.md5(payload.encode('utf-8')).hexdigest()[:16]

    @staticmethod
    def _verify_checksum(payload: str, checksum: str) -> bool:
        return CTSPServer._calculate_checksum(payload) == checksum

    @staticmethod
    def _get_next_sequence(player_id: str) -> int:
        if player_id not in CTSPServer.sequence_numbers:
            CTSPServer.sequence_numbers[player_id] = 0
        CTSPServer.sequence_numbers[player_id] += 1
        return CTSPServer.sequence_numbers[player_id]

if __name__ == "__main__":
    server = CTSPServer()
    server.start()