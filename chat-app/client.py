import socket
import json
import hashlib
import threading

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

def receive_messages(client_socket):
    while True:
        try:
            response = client_socket.recv(1024).decode()
            if not response:
                break
            header, body = parse_message(response)
            print(f"\nServer: {body}")
            print("You: ", end="", flush=True)
        except Exception as e:
            print(f"\nError receiving message: {e}")
            break
    print("\nDisconnected from server")

def start_client(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, port))
        print(f"Connected to server at {host}:{port}")

        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
        receive_thread.start()

        while True:
            message = input("You: ")
            if message.lower() == 'quit':
                break
            
            full_message = create_message(message)
            client_socket.send(full_message.encode())

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    HOST = 'localhost'  # หรือ IP ของ server ถ้าเชื่อมต่อจากเครื่องอื่น
    PORT = 12000
    start_client(HOST, PORT)