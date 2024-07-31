from socket import *

serverName = '127.0.0.1'  # หรือใช้ '127.0.0.1' ก็ได้
serverPort = 8082

clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, serverPort))

sentence = input('พิมพ์ประโยคตัวพิมพ์เล็ก: ')
clientSocket.send(sentence.encode())

modifiedSentence = clientSocket.recv(1024).decode()
print('จากเซิร์ฟเวอร์:', modifiedSentence)

clientSocket.close()