import socket as sk

SERVER = "192.168.1.8"  # This IPv4 address must be replaced by the server IP
PORT = 5050
ADDRESS = (SERVER, PORT)

HEADER = 1024
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!lol-bye"

client = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
client.connect(ADDRESS)


def send(msg):
    msg = msg.encode(FORMAT)
    length = len(msg)
    sent_length = str(length).encode(FORMAT)
    padding = HEADER - len(sent_length)
    sent_length += b" " * padding

    client.send(sent_length)
    client.send(msg)


def chat():
    try:
        print(f"[CLIENT] Connected successfully.")

        connected = True
        while connected:
            msg = input("Enter your message: ")
            send(msg)
            if msg == DISCONNECT_MESSAGE:
                client.close()
                print("[DISCONNECTION] You left the chat.")
                connected = False
    except KeyboardInterrupt:
        print(f"[SERVER] The connection has closed.")
        client.close()
    finally:
        print(f"[SERVER] The connection has closed.")
        client.close()


chat()
