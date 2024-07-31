# server.py
import socket

def handle_request(request):
    # แยกส่วนของ request
    headers, body = request.split('\r\n\r\n', 1)
    request_line = headers.split('\r\n')[0]
    method, path, _ = request_line.split()
    
    if method == 'GET':
        if path == '/':
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nHello, World!"
        else:
            response = "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nPage not found"
    elif method == 'POST':
        response = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nReceived: {body}"
    else:
        response = "HTTP/1.1 405 Method Not Allowed\r\nContent-Type: text/plain\r\n\r\nMethod not allowed"
    
    return response.encode()

def run_server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Server running on {host}:{port}")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                data = conn.recv(1024).decode()
                response = handle_request(data)
                conn.sendall(response)

if __name__ == "__main__":
    run_server('localhost', 8080)