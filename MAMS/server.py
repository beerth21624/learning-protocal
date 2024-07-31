import socket
import json
import hashlib
import hmac
import time
import threading
import uuid

# คีย์สำหรับ HMAC (ในระบบจริงควรเก็บไว้อย่างปลอดภัย)
hmac_key = b'secret_key_for_hmac'

# Status Codes
STATUS_CODES = {
    200: "Operation Successful",
    201: "Item Created Successfully",
    202: "Request Accepted, Pending Processing",
    300: "Additional Authentication Required",
    301: "Access Denied",
    302: "Authentication Expired",
    400: "Invalid Request",
    401: "Insufficient Information",
    402: "Usage Limit Exceeded",
    403: "Weapon Unavailable",
    404: "Requested Item Not Found",
    500: "Internal System Error",
    501: "System Maintenance",
    502: "System Unresponsive",
    600: "Emergency Situation",
    601: "Temporary Lockdown",
    602: "Special Inspection in Progress",
    700: "General Notification",
    701: "Weapon Maintenance Required",
    702: "Low Inventory Level"
}


users = {
    "U001": {"password": "password123", "role": "admin"}
}

weapons = {
    "W001": {"name": "Rifle", "quantity": 100}
}

audit_log = []


def create_response(status_code, message, data=None):
    return {
        "status_code": status_code,
        "status_message": STATUS_CODES.get(status_code, "Unknown Status"),
        "message": message,
        "data": data
    }


def authenticate(user_id, password):
    user = users.get(user_id)
    if user and user["password"] == password:
        return create_response(200, "Authentication successful")
    else:
        return create_response(301, "Authentication failed")

def log_action(user_id, action):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    audit_log.append({"timestamp": timestamp, "user_id": user_id, "action": action})


def handle_inventory_query(user_id):
    log_action(user_id, "Queried inventory")
    return create_response(200, "Inventory query successful", {"inventory": weapons})

def handle_inventory_update(user_id, weapon_id, quantity):
    if weapon_id in weapons:
        weapons[weapon_id]["quantity"] = quantity
        log_action(user_id, f"Updated inventory: {weapon_id} to {quantity}")
        return create_response(200, "Inventory updated successfully")
    else:
        return create_response(404, "Weapon not found")

def handle_weapon_checkout(user_id, weapon_id, quantity):
    weapon = weapons.get(weapon_id)
    if not weapon:
        return create_response(404, "Weapon not found")
    current_quantity = weapon["quantity"]
    if current_quantity < quantity:
        return create_response(403, "Insufficient quantity")
    weapons[weapon_id]["quantity"] -= quantity
    log_action(user_id, f"Checked out {quantity} of {weapon_id}")
    return create_response(200, "Weapon checked out successfully")



# ฟังก์ชันสร้างข้อความและตรวจสอบข้อความ
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

# ฟังก์ชันการรับและส่งข้อความ
def send_message(client_socket, message):
    client_socket.send(message.encode())

def receive_message(client_socket):
    data = client_socket.recv(4096).decode()
    return data

# ฟังก์ชันการเชื่อมต่อและส่งคำสั่งไปยัง server
def send_command(client_socket, command, user_id, content):
    message = create_message(command, user_id, content)
    send_message(client_socket, message)
    response = receive_message(client_socket)
    header, body = verify_and_decode_message(response)
    return header, body

# ฟังก์ชันการทำงานของ server
def handle_client(client_socket):
    try:
        while True:
            data = receive_message(client_socket)
            if not data:
                break
            
            try:
                header, body = verify_and_decode_message(data)
                user_id = header["sender_id"]
                msg_type = header["message_type"]
                content = body["content"]

                if msg_type == 'AUTHENTICATION':
                    response = authenticate(user_id, content["password"])
                elif msg_type == 'INVENTORY_QUERY':
                    response = handle_inventory_query(user_id)
                elif msg_type == 'INVENTORY_UPDATE':
                    response = handle_inventory_update(user_id, content["weapon_id"], content["quantity"])
                elif msg_type == 'WEAPON_CHECKOUT':
                    response = handle_weapon_checkout(user_id, content["weapon_id"], content["quantity"])
                elif msg_type == 'MONITOR':
                    monitor_data = {
                        "weapon_count": len(weapons),
                        "log_count": len(audit_log)
                    }
                    response = create_response(200, "Monitor data", monitor_data)
                    response_message = create_message("RESPONSE", "SERVER", response)
                    send_message(client_socket, response_message)
                else:
                    response = create_response(400, "Unknown command")

                response_message = create_message("RESPONSE", "SERVER", response)
                send_message(client_socket, response_message)
            
            except ValueError as e:
                print(f"Error processing message: {e}")
                error_response = create_response(400, str(e))
                error_message = create_message("RESPONSE", "SERVER", error_response)
                send_message(client_socket, error_message)
    
    finally:
        client_socket.close()

# ฟังก์ชันเริ่ม server
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 12345))
    server_socket.listen(5)
    print("Server started on localhost:12345")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"New connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()

if __name__ == "__main__":
    start_server()
