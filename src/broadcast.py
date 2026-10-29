import const_val as c
import peer as pr
import threading as thd
import time as tm
import socket as sk


class Broadcaster:
    def __init__(self, host, bcast, tcp_port):
        self.recieve_socket = self.make_udp_socket()
        self.broadcast_socket = self.make_udp_socket()

        self.recieve_thread = thd.Thread(target=self.recieve_message, args=(host,))
        self.recieve_thread.daemon = True

        self.broadcast_thread = thd.Thread(
            target=self.broadcast_message, args=(host, bcast, tcp_port)
        )
        self.broadcast_thread.daemon = True

        self.stop_flag = thd.Event()

    def make_udp_socket(self):
        # Create an UDP socket with SOCK_DGRAM parameter
        conn = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
        # The parameters SO_REUSEADDR and True mean that the address (IP and port) can be used by others
        conn.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEADDR, True)
        # The parameters SO_BROADCAST and True make sure that this socket cannot be denied by the operating system
        conn.setsockopt(sk.SOL_SOCKET, sk.SO_BROADCAST, True)
        # Bind the socket to the address as below ("" means all the machine in the LAN)
        conn.bind(("", c.PORT))

        return conn

    def recieve_message(self, host):
        print(f"[*] Broadcasting presence on UDP port {c.PORT}")
        while True:
            # The variable data holds the message in bytes (we have to decode it), and addr holds the sender IP and PORT
            data, addr = self.recieve_socket.recvfrom(c.HEADER)
            # Decode the message
            msg = data.decode(c.FORMAT, errors="replace")
            # Split the message into parts to get the information
            info = msg.split("|")
            # Skip the broadcast of this socket
            if len(info) == 4 and info[0] == "!LOL" and info[1] == host.name:
                continue

            peer_name = info[1]
            tcp_port = int(info[2])
            peer_ip = addr[0]
            peer_state = info[3]

            # Add the information recieved to the peers dictionary which is a global variable
            with host.peers_lock:
                host.peers[peer_name] = {
                    "ip": peer_ip,
                    "port": tcp_port,
                    "last_seen": tm.time(),
                    "state": peer_state,
                }

            if self.stop_flag.is_set():
                break

    def broadcast_message(self, host, bcast, tcp_port):
        print(f"[*] Listening on TCP port {tcp_port}")
        while True:
            # Make the message and encode it to bytes
            msg = f"!LOL|{host.name}|{tcp_port}|{host.state}".encode(c.FORMAT)
            # The variable addr holds IP limits (defalt = 255.255.255.255) and the PORT that the others are listening to
            addr = (bcast, c.PORT)
            # Send the message and the adress
            self.broadcast_socket.sendto(msg, addr)
            # If the stop event happens, these two lines will terminate the process
            if self.stop_flag.is_set():
                break

            # Stop 3 second before sending another message
            tm.sleep(3)

    def start_listening(self):
        self.recieve_thread.start()

    def start_broadcasting(self):
        self.broadcast_thread.start()

    def end_process(self):
        self.stop_flag.set()
