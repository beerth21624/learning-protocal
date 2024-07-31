
# client.py
import socket

def send_request(host, port, method, path, body=None):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        request = f"{method} {path} HTTP/1.1\r\nHost: {host}\r\n"
        if body:
            request += f"Content-Length: {len(body)}\r\n"
        request += "\r\n"
        if body:
            request += body
        
        s.sendall(request.encode())
        response = s.recv(1024).decode()
        return response

if __name__ == "__main__":
    print(send_request('localhost', 8080, 'GET', '/'))
    print(send_request('localhost', 8080, 'POST', '/', 'Hello, Server!'))