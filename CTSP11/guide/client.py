import socket
import json
import hashlib

class CTSPClient:
    def __init__(self, host: str = 'localhost', port: int = 6789):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.player_id = None
        self.sequence_number = 0

    def connect(self):
        self.socket.connect((self.host, self.port))

    def send_request(self, command: str, payload: dict) -> dict:
        payload_json = json.dumps(payload)
        checksum = self._calculate_checksum(payload_json)
        
        headers = f"CTSP/1.0 {command}\n"
        headers += f"Sequence: {self.sequence_number}\n"
        if self.player_id:
            headers += f"Player-ID: {self.player_id}\n"
        headers += f"Content-Length: {len(payload_json)}\n"
        headers += f"Checksum: {checksum}\n"
        
        request = f"{headers}\n{payload_json}"
        self.socket.send(request.encode('utf-8'))
        
        response = self.socket.recv(4096).decode('utf-8')
        return self._parse_response(response)

    def enter(self, username: str, password: str) -> dict:
        payload = {"username": username, "password": password}
        response = self.send_request("ENTER", payload)
        if response['status'] == 200:
            self.player_id = response['body']['player_id']
        return response

    def exit(self) -> dict:
        return self.send_request("EXIT", {})

    def scan(self, coins: List[str]) -> dict:
        return self.send_request("SCAN", {"coins": coins})

    def buy(self, coin: str, amount: float) -> dict:
        return self.send_request("BUY", {"coin": coin, "amount": amount})

    def sell(self, coin: str, amount: float) -> dict:
        return self.send_request("SELL", {"coin": coin, "amount": amount})

    def check(self, check_type: str) -> dict:
        return self.send_request("CHECK", {"type": check_type})

    def rank(self) -> dict:
        return self.send_request("RANK", {})

    def ping(self) -> dict:
        return self.send_request("PING", {})

    @staticmethod
    def _calculate_checksum(payload: str) -> str:
        return hashlib.md5(payload.encode('utf-8')).hexdigest()[:16]

    def _parse_response(self, response: str) -> dict:
        lines = response.split('\n')
        headers = {}
        for line in lines[1:]:
            if line.strip() == '':
                break
            key, value = line.split(': ')
            headers[key] = value
        
        body = json.loads(lines[-1])
        
        return {
            "command": lines[0].split()[1],
            "status": int(headers['Status'].split()[0]),
            "player_id": headers.get('Player-ID'),
            "sequence": int(headers.get('Sequence', 0)),
            "body": body
        }

    def close(self):
        self.socket.close()

if __name__ == "__main__":
    client = CTSPClient()
    client.connect()
    
    # Example usage
    print(client.enter("Satoshi", "bitcoin123"))
    print(client.scan(["BTC", "ETH", "DOGE"]))
    print(client.buy("BTC", 0.1))
    print(client.check("portfolio"))
    print(client.rank())
    print(client.exit())
    
    client.close()