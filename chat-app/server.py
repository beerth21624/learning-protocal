import socket
import json
import hashlib
import threading

MAX_CONNECTIONS = 5
clients = []
clients_lock = threading.Lock()

def create_message(body):
    header = {
        "length": len(body),
        "type": "chat"
    }
    header_json = json.dumps(header)
    checksum = hashlib.md5((header_json + body).encode()).hexdigest()
    return f"{header_json}|{body}|{checksum}"

def parse_message(message):
    header_json, body, checksum = message.split("|")
    header = json.loads(header_json)
    calculated_checksum = hashlib.md5((header_json + body).encode()).hexdigest()
    if calculated_checksum != checksum:
        raise ValueError("Checksum mismatch")
    return header, body

def broadcast(message, sender_socket):
    with clients_lock:
        for client in clients:
            if client != sender_socket:
                try:
                    client.send(message.encode())
                except:
                    remove_client(client)

def remove_client(client_socket):
    with clients_lock:
        if client_socket in clients:
            clients.remove(client_socket)
            client_socket.close()

def handle_client(client_socket, client_address):
    print(f"New connection from {client_address}")
    with clients_lock:
        if len(clients) >= MAX_CONNECTIONS:
            print(f"Maximum connections reached. Rejecting {client_address}")
            client_socket.send(create_message("Server is full. Try again later.").encode())
            client_socket.close()
            return
        clients.append(client_socket)

    while True:
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                break

            header, body = parse_message(message)
            print(f"Received from {client_address}: {body}")

            broadcast_message = create_message(f"Client {client_address}: {body}")
            broadcast(broadcast_message, client_socket)
        except ValueError as e:
            print(f"Error with client {client_address}: {e}")
            break
        except Exception as e:
            print(f"Unexpected error with client {client_address}: {e}")
            break

    print(f"Connection from {client_address} closed")
    remove_client(client_socket)

def start_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, client_address = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

if __name__ == "__main__":
    HOST = 'localhost' 
    PORT = 12000
    start_server(HOST, PORT)