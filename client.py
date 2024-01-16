from socket import *
import sys
import threading
import json
import os

clients = {}

# Server would be running on the same host as Client
if len(sys.argv) != 4:
    print("\n===== Error usage, python3 TCPClient3.py server_IP server_port client_udp_server_port ======\n")
    exit(0)

serverHost = sys.argv[1]
serverPort = int(sys.argv[2])
serverAddress = (serverHost, serverPort)
clientUdpPort = int(sys.argv[3])

# Define socket for the client side = used to communicate with the server
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect(serverAddress)

# 1. Authentication
print("Please login")
while True:
    message = json.dumps({'type': "login"})
    clientSocket.sendall(message.encode())

    USERNAME = input("Username: ")
    clientSocket.sendall(USERNAME.encode())

    PASSWORD = input("Password: ")
    clientSocket.sendall(PASSWORD.encode())

    data = clientSocket.recv(1024)
    status = data.decode()

    # Logged in with the same username and password
    if status == "Multiple accounts logged in at the same time!":
        print(status)

    # Case1: wrong username
    if status == "wrongUser":
        print("Invalid Username. Please try again")

    # Case2: wrong password
    while status == "wrongPass":
        # MAIN CODE --
        print("Invalid Password. Please try again")
        # Send the password
        PASSWORD = input("Password: ")
        clientSocket.sendall(PASSWORD.encode())
        
        # Update status
        data = clientSocket.recv(1024)
        status = data.decode()

    # FOR BLOCKING --
    if status == "blocked":
        print("Your account is blocked due to multiple login failures. Please try again later")
        sys.exit(0)
    
    # Case3: correct details
    if status == "successful":
        print("Welcome to Tessenger!\n")
        clientSocket.sendall(str(clientUdpPort).encode())
        break

# HANDLING Peer to peer communication
def p2p_communication(command, username, client_socket):
    if (len(command) < 3):
        print("Please enter in the format of '/p2pvideo username filename'\n")
    else:
        AUDIENCE = command[1]
        filename = command[2]

        # Check if AUDIENCE is valid
        if (AUDIENCE not in clients):
            print(f"{AUDIENCE} is offline\n")

        else:
            udp_socket = socket(AF_INET, SOCK_DGRAM)

            # Sending both the username and filename of the sender
            udp_socket.sendto(username.encode(), (serverHost, clients[AUDIENCE]))
            udp_socket.sendto(filename.encode(), (serverHost, clients[AUDIENCE]))

            with open(f'{filename}', "rb") as file:
                data = file.read(1024)
                while data:
                    udp_socket.sendto(data, (serverHost, clients[AUDIENCE]))
                    data = file.read(1024)
                udp_socket.close()
                print("Sent the file over UDP")

# HANDLING Receive and Sending at the same time
def receive_thread(client_socket):
    while True:
        data = client_socket.recv(1024)
        if not data:
            break
        message = data.decode()
        print(message)
        
        try:
            for line in message.split("\n"):
                user, IPAddress, UDPServerPort, msg = line.strip().split(", ")
                clients[user] = int(UDPServerPort)
        except:
            continue

# HANDLING Receive thread for udp
def udp_receive_thread(client_socket):
    while True:
        # Accept the data through UDP
        udp_socket = socket(AF_INET, SOCK_DGRAM)
        udp_socket.bind((serverHost, clientUdpPort))

        try:
            # Get the sender and filename
            data = str(udp_socket.recvfrom(1024)[0])
            PRESENTER = data.split("'")[1]

            data = str(udp_socket.recvfrom(1024)[0])
            filename = data.split("'")[1]

            # Download the file
            with open(f"{PRESENTER}_{filename}", "wb") as file:
                try:
                    data, addr = udp_socket.recvfrom(1024)
                    file.write(data)
                except socket.timeout:
                    break

            print(f"a file ({filename}) has been received from {PRESENTER}")

            udp_socket.close()
        except:
            continue

def send_thread(client_socket, username):
    while True:
        message = json.dumps({'type': "command"})
        clientSocket.sendall(message.encode())

        command = input()
        clientSocket.sendall(command.encode())

        if (command == "/logout"):
            print("=== You have logged out successfully ===")
            os._exit(0)
        
        command = command.split()
        if (command[0] == "/p2pvideo"):
            p2p_communication(command, username, client_socket)
            

while True:
    receive_thread = threading.Thread(target=receive_thread, args=(clientSocket,))
    udp_receive_thread = threading.Thread(target=udp_receive_thread, args=(clientSocket,))
    send_thread = threading.Thread(target=send_thread, args=(clientSocket, USERNAME))

    receive_thread.start()
    udp_receive_thread.start()
    send_thread.start()

    receive_thread.join()
    udp_receive_thread.join()
    send_thread.join()

    # close the socket
    clientSocket.close()