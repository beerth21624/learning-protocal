import socket
import json
import hashlib
import hmac
import time
import uuid

# คีย์สำหรับ HMAC (ต้องตรงกับที่เซิร์ฟเวอร์ใช้)
hmac_key = b'secret_key_for_hmac'

def create_message(msg_type, user_id, content):
    header = {
        "protocol_version": "1.0",
        "message_type": msg_type,
        "sender_id": user_id,
        "timestamp": int(time.time()),
        "message_id": str(uuid.uuid4())
    }
    body = {
        "content": content
    }
    message = json.dumps({"header": header, "body": body})
    signature = hmac.new(hmac_key, message.encode(), hashlib.sha256).hexdigest()
    return json.dumps({"message": message, "signature": signature})

def verify_and_decode_message(encoded_message):
    message_data = json.loads(encoded_message)
    message = message_data["message"]
    signature = message_data["signature"]
    
    # ตรวจสอบ signature
    if hmac.new(hmac_key, message.encode(), hashlib.sha256).hexdigest() != signature:
        raise ValueError("Invalid message signature")
    
    decoded_message = json.loads(message)
    return decoded_message["header"], decoded_message["body"]
def send_message(client_socket, message):
    client_socket.send(message.encode())
def receive_message(client_socket):
    data = client_socket.recv(4096).decode()
    return data


def send_command(host, port, command, user_id, content):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((host, port))

        message = create_message(command, user_id, content)
        send_message(client_socket, message)

        response = receive_message(client_socket)
        header, body = verify_and_decode_message(response)
        print(body['content']['message'])
        if body['content']['status_code'] == 200:
            print(body['content']['data'])
        

if __name__ == "__main__":
    host = 'localhost'
    port = 12345  # เปลี่ยนเป็น port ที่เซิร์ฟเวอร์กำลังฟังอยู่
    user_id = 'U001'  # เปลี่ยนเป็น user_id ของคุณ

    while True:
        print("Available commands: A (AUTHENTICATION), IQ (INVENTORY_QUERY), IU (INVENTORY_UPDATE), IA (INVENTORY_ADD), WC (WEAPON_CHECKOUT), M (MONITOR), exit")
        command = input("Enter command (A, IQ, IU, IA, WC, M, exit): ")
        if command == 'A':
            command = 'AUTHENTICATION'
        elif command == 'IQ':
            command = 'INVENTORY_QUERY'
        elif command == 'IU':
            command = 'INVENTORY_UPDATE'
        elif command == 'IA':
            command = 'INVENTORY_ADD'
        elif command == 'WC':
            command = 'WEAPON_CHECKOUT'
        elif command == 'M':
            command = 'MONITOR'
        else:
            print("Invalid command")
            continue
        
        if command == 'exit':
            break

        if command == 'AUTHENTICATION':
            password = input("Enter password: ")
            content = {"password": password}
        elif command == 'INVENTORY_QUERY':
            item_id = input("Enter item ID: ")
            content = {"item_id": item_id}
        elif command == 'INVENTORY_UPDATE':
            item_id = input("Enter item ID: ")
            quantity = input("Enter quantity: ")
            content = {"item_id": item_id, "quantity": quantity}
        elif command == 'INVENTORY_ADD':
            item_id = input("Enter item ID: ")
            quantity = input("Enter quantity: ")
            content = {"item_id": item_id, "quantity": quantity}

        elif command == 'WEAPON_CHECKOUT':
            weapon_id = input("Enter weapon ID: ")
            quantity = input("Enter quantity: ")
            content = {"weapon_id": weapon_id, "quantity": quantity}
        elif command == 'MONITOR':
            content = {}
        else :
            print("Invalid command")
            continue
        send_command(host, port, command, user_id, content)
