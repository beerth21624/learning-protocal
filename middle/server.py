import socket
import threading

def handle_client(client_socket, client_address):
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                break
            print(f"ข้อความจาก {client_address}: {message}")
            broadcast(f"{client_address}: {message}", client_socket)
        except:
            break
    clients.remove(client_socket)
    client_socket.close()

def broadcast(message, sender_socket):
    for client in clients:
        if client != sender_socket:
            try:
                client.send(message.encode('utf-8'))
            except:
                client.close()
                clients.remove(client)

def accept_connections():
    while True:
        client_socket, client_address = server_socket.accept()
        print(f"เชื่อมต่อใหม่จาก {client_address}")
        clients.append(client_socket)
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('', 8082))
server_socket.listen(5)

clients = []

print("เซิร์ฟเวอร์กำลังทำงาน... กำลังรอการเชื่อมต่อ")
accept_thread = threading.Thread(target=accept_connections)
accept_thread.start()
accept_thread.join()

server_socket.close()