from socket import *
from threading import Thread
import sys, select
import datetime
import json

# acquire server (host and port) and (number of failed attempts) from command line parameter
if len(sys.argv) != 3:
    print("\n===== Error usage, python3 TCPServer3.py server_port number_of_consecutive_failed_attempts ======\n")
    exit(0)
serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])
serverAddress = (serverHost, serverPort)
numFailAttempts = int(sys.argv[2])

if (numFailAttempts < 1 or numFailAttempts > 5):
    print(f"Invalid number of allowed failed consecutive attempt: {numFailAttempts}")
    exit(0)

# define socket for the server side and bind address
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(serverAddress)

# Dictionaries of clients
clients = {}        # Contains all active clients
clientsUDP = {}     # Contains all clients UDP
numTrialUser = {}   # Contains all number of trial of users
blockedUser = {}    # Contains all blocked user

# Dictionaries of groups
groups = {}         # For joined members
memberGroups = {}   # For added members (including creator)

class ClientThread(Thread):
    def __init__(self, clientAddress, clientSocket):
        Thread.__init__(self)
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientAlive = False
        
        # print("=== New connection created for: ", clientAddress)
        self.clientAlive = True
        
    def run(self):
        while self.clientAlive:
            data = self.clientSocket.recv(1024)
            if not data:
                self.clientAlive = False
                # print("=== the user disconnected - ", self.clientAddress)
                break

            message = json.loads(data.decode())

            if message['type'] == 'login':
                self.process_login()
            elif message['type'] == 'command':
                message = "Enter one of the following commands (/msgto, /activeuser, /creategroup, /joingroup, /groupmsg, /p2pvideo, /logout): "
                self.clientSocket.send(message.encode())

                self.process_command()
            else:
                print("[recv] " + json.dumps(message))
                print("[send] Cannot understand this message")
                response = {'type': 'error', 'message': 'Cannot understand this message'}
                self.clientSocket.send(json.dumps(response).encode())
        
    def process_login(self):
        # === ATTRIBUTUTES ===
        message = "wrongUser"
        timeLogin = None
        clientUdpPort = None

        # === MAIN CODE===
        data = self.clientSocket.recv(1024)
        self.USERNAME = data.decode()

        data = self.clientSocket.recv(1024)
        PASSWORD = data.decode()

        file = open("credentials.txt", "r")
        for line in file:
            user, pw = line.split(" ")
            pw = pw.strip()

            if (self.USERNAME in clients):
                message = "Multiple accounts logged in at the same time!"
            elif self.USERNAME == user:
                # Trial should be based on username
                if self.USERNAME not in numTrialUser:
                    numTrialUser[self.USERNAME] = 0

                message = "wrongPass"
                while message == "wrongPass":
                    # FOR UNBLO mnCKING --
                    if (self.USERNAME in blockedUser):
                        currTime = datetime.datetime.strptime(datetime.datetime.now().strftime("%H:%M:%S"),"%H:%M:%S")
                                                
                        if (currTime-blockedUser[self.USERNAME]).seconds >= 10:
                            del blockedUser[self.USERNAME]
                            numTrialUser[self.USERNAME] = 0
                        else: 
                            message = "blocked"
                    elif (PASSWORD == pw):
                        message = "successful"
                        timeLogin = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
                    else:
                        # If the password is wrong
                        # FOR BLOCKING --
                        numTrialUser[self.USERNAME] += 1
                        if numTrialUser[self.USERNAME] >= numFailAttempts:
                            message = "blocked"
                            blockedTime = datetime.datetime.strptime(datetime.datetime.now().strftime("%H:%M:%S"),"%H:%M:%S")
                            blockedUser[self.USERNAME] = blockedTime

                        # Send status
                        self.clientSocket.send(message.encode())
                    
                        # Get the password
                        data = self.clientSocket.recv(1024)
                        PASSWORD = data.decode()
                break
        
        self.clientSocket.send(message.encode())
        file.close()

        # Sending to user log file
        if (message == "successful"):
            print(f"{self.USERNAME} is online")
            
            # Getting sequenceNumber
            sequenceNumber = 0
            with open("userlog.txt", "r") as file:
                content = file.read()
                sequenceNumber = content.count('\n')
                sequenceNumber += 1

            # Getting client udp port
            data = self.clientSocket.recv(1024)
            clientUdpPort = data.decode()
            clientUdpPort = int(clientUdpPort)
            
            # USERNAME = unique clientSockt
            clients[self.USERNAME] = clientSockt
            clientsUDP[self.USERNAME] = clientUdpPort

            file = open("userlog.txt", "a")
            file.write(f"{sequenceNumber}; {timeLogin}; {self.USERNAME}; {clientAddress[0]}; {clientUdpPort}\n")
            file.close()
                    
    def process_command(self):
        data = self.clientSocket.recv(1024)
        command = data.decode()
        command = command.split()

        if (command[0] == "/msgto"):
            # ATTRIBUTES
            if (len(command) < 2):
                message = "Please enter in the format of '/msgto USERNAME MESSAGE_CONTENT'\n"
                self.clientSocket.send(message.encode())
                print("Invalid length send private message")
            else:
                # Getting messageNumber
                messageNumber = 0
                with open("messagelog.txt", "r") as file:
                    content = file.read()
                    messageNumber = content.count('\n')
                    messageNumber += 1

                RECEIVER = command[1]
                chat = " ".join(command[2:])
                
                if not chat:
                    message = "Invalid chat\n"
                    self.clientSocket.send(message.encode())
                    print("Invalid chat!")
                elif (RECEIVER == self.USERNAME):
                    message = "Cannot send message to yourself\n"
                    self.clientSocket.send(message.encode())
                    print(f"{self.USERNAME} sending a message to themselves")
                elif (RECEIVER in clients):
                    timeSent = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
                   
                    file = open("messagelog.txt", "a")
                    file.write(f"{messageNumber}; {timeSent}; {RECEIVER}; {chat}\n")
                    file.close()

                    message = f"message sent at {timeSent}.\n"
                    self.clientSocket.send(message.encode())

                    # Send it to the client destination
                    message = f"{timeSent}, {RECEIVER}: {chat}\n"
                    receiver_socket = clients[RECEIVER]
                    receiver_socket.send(message.encode())

                    print(f"{self.USERNAME} message to {RECEIVER} “{chat}” at {timeSent}.")
                else:
                    message = "Invalid user destination\n"
                    self.clientSocket.send(message.encode())
                    print("Invalid user destination!")

        elif (command[0] == "/activeuser"):
            print(f"{self.USERNAME} issued /activeuser command")
            # Get all active users
            activeUsers = []
            for user in clients.keys():
                if (user != self.USERNAME):
                    activeUsers.append(user)
            if not activeUsers:
                print(f"Return messages:\nNo other active user")
                message = "No other active user\n"
            else:
                # Get all the details
                with open("userlog.txt", "r") as file:
                    lines = file.readlines()
                    
                    userDetails = []
                    for line in lines:
                        userDetails.append(line.strip().split(";"))
                    
                    print("Return active user list:")
                    for detail in userDetails:
                        if detail[2].strip() in activeUsers:
                            print(f"{detail[2].strip()}; {detail[3].strip()}; {detail[4].strip()}; active since {detail[1].strip()}.")
                            message = f"{detail[2].strip()}, {detail[3].strip()}, {detail[4].strip()}, active since {detail[1].strip()}.\n"
            self.clientSocket.send(message.encode())

        elif (command[0] == "/creategroup"):
            if (len(command) < 3):
                message = "Please enter in the format of '/creategroup groupname username1 username2 ..'\n"
                self.clientSocket.send(message.encode())
                print("Invalid length argument to create group")
            else:
                # Get groupName and members
                groupName = command[1]
                members = command[2:]
                if not members:
                    message = "Please enter at least one more active users.\n"
                    self.clientSocket.send(message.encode())
                    print("Group chat room is not created. Please enter at least one more active users.")
                elif any(member not in clients for member in members):
                    message = "Invalid username! Please enter a valid username.\n"
                    self.clientSocket.send(message.encode())
                    print("Invalid username! The user may be offline or not exist")
                elif groupName in groups:
                    message = f"a group chat (Name: {groupName}) already exist\n"
                    self.clientSocket.send(message.encode())
                    print("Invalid groupName!")
                elif not groupName.isalnum():
                    message = "Invalid group name! Group name must only contain letters and digits.\n"
                    self.clientSocket.send(message.encode())
                    print("Invalid group name! Group name must only contain letters and digits.")
                elif self.USERNAME in members:
                    message = "Invalid group member! The owner is already a member of the group.\n"
                    self.clientSocket.send(message.encode())
                    print("Invalid group member! The owner is already a member of the group.")
                else:
                    print(f"{self.USERNAME} issued /creategroup command")
                    
                    # Store all the members
                    group = []
                    group.append(self.USERNAME)
                    for member in members:
                        group.append(member)

                    # Store to to memberGroups
                    memberGroups[groupName] = group
                    
                    message = f"Group chat created {groupName}\n"
                    self.clientSocket.send(message.encode())

                    # Store only the owner to the real group
                    group = []
                    group.append(self.USERNAME)
                    groups[groupName] = group

                    # Create log file
                    with open(f"{groupName}_messagelog.txt", "a") as groupFile:
                        pass
                    
                    # Printing all members in memberGroups[groupName]
                    print(f"Return message:\nGroup chat room has been created, room name: {groupName}, users in this room: ", end="")
                    member = ', '.join(memberGroups[groupName])
                    print(member)
        
        elif (command[0] == "/joingroup"):
            if (len(command) < 2):
                message = "Please enter in the format of '/joingroup groupname'\n"
                self.clientSocket.send(message.encode())

                print("Invalid length argument to join group")
            else:
                groupName = command[1]
                if groupName not in groups:
                    message = f"a group chat (Name: {groupName}) doesn't exist\n"
                    self.clientSocket.send(message.encode())

                    print(f"{self.USERNAME} tries to join to a group chat that doesn’t exist!")
                # Check if the user is already in the group
                elif self.USERNAME in groups[groupName]:
                    message = "You are already in the group\n"
                    self.clientSocket.send(message.encode())

                    print(f"{self.USERNAME} tries to re-join to a group chat {groupName}")
                # Check if user is invited
                elif self.USERNAME not in memberGroups[groupName]:
                    message = f"You cannot join the group (Name: {groupName})\n"
                    self.clientSocket.send(message.encode())

                    print(f"{self.USERNAME} tries to join to a group chat {groupName}")
                else:
                    print(f"{self.USERNAME} issued /joingroup command")

                    groups[groupName].append(self.USERNAME)
                    message = f"Joined the group chat: {groupName} successfully.\n"
                    self.clientSocket.send(message.encode())

                    # Printing all members
                    print(f"Return message:\nJoin group chat room successfully, room name: {groupName}, users in this room: ", end="")
                    member = ', '.join(memberGroups[groupName])
                    print(member)
        
        elif (command[0] == "/groupmsg"):
            if (len(command) < 3):
                message = "Please enter in the format of '/groupmsg groupname message'\n"
                self.clientSocket.send(message.encode())

                print("Invalid length argument to group message")
            else:
                groupName = command[1]
                chat = " ".join(command[2:])
                if groupName not in groups:
                    message = "The group chat does not exist\n"
                    self.clientSocket.send(message.encode())

                    print(f"{self.USERNAME} tries to join to a group chat that doesn’t exist!")
                # Check if user is invited
                elif self.USERNAME not in memberGroups[groupName]:
                    message = "You are not added in this group chat.\n"
                    self.clientSocket.send(message.encode())

                    print(f"{self.USERNAME} tries to message to a group chat without being added")
                # Check if the user is already in the group
                elif self.USERNAME not in groups[groupName]:
                    message = "Please join the group before sending messages.\n"
                    self.clientSocket.send(message.encode())

                    print(f"{self.USERNAME} sent a message to a group chat, but {self.USERNAME} hasn't been joined to the group.")
                else:
                    timeSent = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")

                    # Getting messageNumber
                    with open(f"{groupName}_messagelog.txt", "r") as file:
                        content = file.read()
                        messageNumber = content.count('\n')

                    with open(f"{groupName}_messagelog.txt", "a") as file:
                        file.write(f"{messageNumber+1}; {timeSent}; {self.USERNAME}; {chat}\n")

                    # Send it to the client destination
                    for member in memberGroups[groupName]:
                        if member != self.USERNAME:
                            message = f"{timeSent}, {groupName}, {self.USERNAME}: {chat}\n"
                            receiver_socket = clients[member]
                            receiver_socket.send(message.encode())

                    message = "Group chat message sent.\n"
                    self.clientSocket.send(message.encode())

                    print(f"{self.USERNAME} issued a message in group chat {groupName}: {timeSent}; {self.USERNAME}; {chat}")
        
        elif (command[0] == "/logout"):
            # Change the array of clients (remove it)
            # Remove the client from userlog file
            if len(command) != 1:
                message = "Please enter in the format of /logout\n"
                self.clientSocket.send(message.encode())
                print("Invalid format for logout command")
            else:
                # Remove the user from userlog file
                lines = None
                with open("userlog.txt", "r") as file:
                    lines = file.readlines()

                # Find the index
                lineDel = None
                for count, line in enumerate(lines):
                    if (self.USERNAME == line.split(";")[2].strip()):
                        lineDel = count
                
                if lineDel is None or lines is None:
                    message = "An error occured!\n"
                    self.clientSocket.send(message.encode())
                    print("No username matches with the active userlog file")
                else:
                    # Remove from both userlog file and the clients list
                    lines.pop(lineDel)
                    del clients[self.USERNAME]
                    
                    # Update the userlog and the sequence number
                    with open("userlog.txt", "w") as file:
                        for count, line in enumerate(lines):
                            count += 1
                            newLine = f"{count};{line.split(';', 1)[1]}"
                            file.writelines(newLine)
                    print(f"{self.USERNAME} has logged out")

        else:
            if (command[0] != "/p2pvideo"):
                print("Error. Invalid command!")
                message = "Error. Invalid command!\n"
                self.clientSocket.send(message.encode())

        

print("\n=== Server is running ===")
print("=== Waiting for connection request from clients...===")

while True:
    serverSocket.listen()
    clientSockt, clientAddress = serverSocket.accept()
    clientThread = ClientThread(clientAddress, clientSockt)
    clientThread.start()