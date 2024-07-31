import socket
import threading

class ChatClient:
    def __init__(self, host, port, username):
        self.host = host
        self.port = port
        self.username = username
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        self.client_socket.connect((self.host, self.port))
        self.send_message('JOIN', self.username, '')
        
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.start()
        
        self.send_messages()

    def send_messages(self):
        while True:
            content = input()
            if content.lower() == 'quit':
                self.send_message('LEAVE', self.username, '')
                break
            self.send_message('MESSAGE', self.username, content)
        
        self.client_socket.close()

    def receive_messages(self):
        while True:
            try:
                message = self.receive_message()
                if not message:
                    break
                print(f"{message['user']}: {message['content']}")
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def send_message(self, msg_type, user, content):
        message = f"TYPE: {msg_type}\nUSER: {user}\nLENGTH: {len(content)}\n\n{content}"
        self.client_socket.send(message.encode())

    def receive_message(self):
        headers = self.client_socket.recv(1024).decode().strip().split('\n')
        message = {}
        for header in headers:
            if ': ' in header:
                key, value = header.split(': ', 1)
                message[key.lower()] = value
        
        if 'length' in message:
            content_length = int(message['length'])
            message['content'] = self.client_socket.recv(content_length).decode()
        
        return message
    
client = ChatClient('localhost', 5000, 'YourUsername')
client.start()