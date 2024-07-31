from socket import *

serverPort = 8082  # ต้องตรงกับพอร์ตในโค้ดไคลเอ็นต์
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(1)
print('เซิร์ฟเวอร์พร้อมรับการเชื่อมต่อแล้ว')

while True:
    connectionSocket, addr = serverSocket.accept()
    sentence = connectionSocket.recv(1024).decode()
    capitalizedSentence = sentence.upper()
    connectionSocket.send(capitalizedSentence.encode())
    connectionSocket.close()