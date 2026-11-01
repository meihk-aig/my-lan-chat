import const_val as c
import socket as sk
import threading as thd


class ChatManager:
    def __init__(self, tcp_port, host):
        self.max_length = 1024 * 1024

        self.tcp_port = tcp_port
        self.host = host
        self.connections = {}
        self.active_chat = None

        self.lock = thd.Lock()

        self.stop_event = thd.Event()

        self.listen_socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
        self.listen_socket.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEADDR, True)

        self.listen_socket.bind(("", tcp_port))
        self.listen_socket.listen()
        self.listen_socket.settimeout(2)

        self.listener_thread = thd.Thread(target=self.accept, daemon=True)
        self.listener_thread.start()

    def accept(self):
        while not self.stop_event.is_set():
            try:
                conn, addr = self.listen_socket.accept()
            except sk.timeout:
                continue

            with self.host.peers_lock:
                peers = [
                    name
                    for name, info in self.host.peers.items()
                    if info.get("ip") == addr[0]
                ]

            if len(peers) != 1:
                conn.close()
                continue

            self.register_connection(peers[0], conn)

    def register_connection(self, peer_name, conn):
        with self.lock:
            if peer_name in self.connections:
                conn.close()
                return

            self.connections[peer_name] = conn

        recv_thread = thd.Thread(
            target=self.recieve_loop, args=(peer_name, conn), daemon=True
        )
        recv_thread.start()

    def connect_to_peer(self, peer_name):
        with self.lock:
            if peer_name in self.connections:
                return True

        with self.host.peers_lock:
            info = self.host.peers.get(peer_name)

        if info is None:
            print(f"[*] {peer_name} not found.")
            return False

        conn = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
        conn.settimeout(5)

        addr = (info["ip"], info["port"])
        try:
            conn.connect(addr)
        except:
            conn.close()
            return False

        conn.settimeout(None)
        self.register_connection(peer_name, conn)

        with self.lock:
            return self.connections.get(peer_name) is conn

    def close_connection(self, peer_name):
        with self.lock:
            conn = self.connections.pop(peer_name, None)

        if conn:
            conn.close()

    def start_chat(self, peer_name):
        if not self.connect_to_peer(peer_name):
            print(f"[*] Cannot connect to {peer_name}")
            return False

        with self.lock:
            self.active_chat = peer_name

        with self.host.unread_lock:
            messages = self.host.unread.pop(peer_name, [])

            for message in messages:
                print(f"[{peer_name}] {message}")

        return True

    def leave_chat(self):
        with self.lock:
            self.active_chat = None

    def recv_exact(self, conn, size):
        data = bytearray()

        while len(data) < size:
            chunk = conn.recv(size - len(data))

            if not chunk:
                return None
            data.extend(chunk)

        return bytes(data)

    def recv_message(self, conn):
        header = self.recv_exact(conn, c.HEADER)
        if header is None:
            return None

        length = int(header.decode(c.FORMAT).strip())

        if not (0 <= length <= self.max_length):
            return None

        payload = self.recv_exact(conn, length)
        if payload is None:
            return None

        return payload.decode(c.FORMAT)

    def send_message(self, peer_name, message):
        with self.lock:
            conn = self.connections.get(peer_name)

        if conn is None:
            return False

        try:
            payload = message.encode(c.FORMAT)
            header = str(len(payload)).ljust(c.HEADER).encode(c.FORMAT)

            conn.sendall(header + payload)

            return True
        except:
            self.close_connection(peer_name)
            return False

    def recieve_loop(self, peer_name, conn):
        try:
            while not self.stop_event.is_set():
                message = self.recv_message(conn)

                if message is None:
                    break

                with self.lock:
                    active = self.active_chat == peer_name

                    if not active:
                        with self.host.unread_lock:
                            unread = self.host.unread.setdefault(peer_name, [])
                            unread.append(message)
                            count = len(unread)

                if active:
                    print(f"[{peer_name}] {message}")
                else:
                    print(f"[*] New message from {peer_name} ({count} unread)")
        except:
            with self.lock:
                if self.connections.get(peer_name) is conn:
                    self.connections.pop(peer_name)

            conn.close()
