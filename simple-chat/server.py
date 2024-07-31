# server.py
import socket
import threading

class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # {client_socket: username}

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server started on {self.host}:{self.port}")
        
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
                
                if message['type'] == 'JOIN':
                    self.clients[client_socket] = message['user']
                    self.broadcast(f"{message['user']} has joined the chat.")
                elif message['type'] == 'LEAVE':
                    self.broadcast(f"{message['user']} has left the chat.")
                    del self.clients[client_socket]
                    break
                elif message['type'] == 'MESSAGE':
                    self.broadcast(f"{message['user']}: {message['content']}")
            except Exception as e:
                print(f"Error handling client: {e}")
                break
        
        client_socket.close()

    def receive_message(self, client_socket):
        try:
            headers = client_socket.recv(1024).decode().strip().split('\n')
            message = {}
            for header in headers:
                if ': ' in header:
                    key, value = header.split(': ', 1)
                    message[key.lower()] = value
            
            if 'length' in message:
                content_length = int(message['length'])
                message['content'] = client_socket.recv(content_length).decode()
            
            return message
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None

    def broadcast(self, message):
        for client_socket in self.clients:
            self.send_message(client_socket, 'MESSAGE', 'Server', message)

    def send_message(self, client_socket, msg_type, user, content):
        message = f"TYPE: {msg_type}\nUSER: {user}\nLENGTH: {len(content)}\n\n{content}"
        client_socket.send(message.encode())
if __name__ == "__main__":
    # For server
    server = ChatServer('localhost', 5000)
    server.start()
    