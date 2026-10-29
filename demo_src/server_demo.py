import socket as sk
import threading as thd

SERVER = sk.gethostbyname(sk.gethostname())
PORT = 5050
ADDRESS = (SERVER, PORT)

HEADER = 1024
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!lol-bye"

server = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
server.bind(ADDRESS)


def handle_client(conn, addr):
    print(f"[{addr}] connected to the server.")

    connected = True
    while connected:
        msg_length = conn.recv(HEADER).decode(FORMAT)
        if msg_length:
            msg = conn.recv(HEADER).decode(FORMAT)
            print(f"[{addr}] {msg}")

            if msg == DISCONNECT_MESSAGE:
                connected = False
                print(f"[DISCONNECTION] {addr} left.")

    conn.close()


def start():
    try:
        server.listen()
        while True:
            conn, addr = server.accept()
            thread = thd.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[ACTIVE] Current active clients: {thd.active_count() - 1}")
    except KeyboardInterrupt:
        print("[SERVER] The server has closed.")
        server.close()
    finally:
        print("[SERVER] The server has closed.")
        server.close()


print("[SERVER] The server is starting...")
print("[SERVER] Waiting for connection.")
start()
