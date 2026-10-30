import socket as sk
import threading as thd
import time as tm
import const_val as c


class Broadcaster:
    def __init__(self, host, bcast, tcp_port):
        self.host = host
        self.bcast = bcast
        self.tcp_port = tcp_port
        self.stop_flag = thd.Event()

        self.receive_socket = self._make_udp_socket()
        self.broadcast_socket = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
        self.broadcast_socket.setsockopt(sk.SOL_SOCKET, sk.SO_BROADCAST, 1)

        self.receive_thread = thd.Thread(
            target=self.receive_message, daemon=True
        )
        self.broadcast_thread = thd.Thread(
            target=self.broadcast_message, daemon=True
        )

    def _make_udp_socket(self):
        conn = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
        conn.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEADDR, 1)
        conn.bind(("", c.PORT))
        conn.settimeout(1.0)
        return conn

    def receive_message(self):
        print(f"[*] Receiving presence on UDP port {c.PORT}")
        while not self.stop_flag.is_set():
            try:
                data, addr = self.receive_socket.recvfrom(4096)
            except sk.timeout:
                continue
            except OSError:
                break

            try:
                parts = data.decode(c.FORMAT).split("|")
                if len(parts) != 4 or parts[0] != "!LOL":
                    continue

                _, peer_name, port_text, peer_state = parts
                if peer_name == self.host.name:
                    continue

                peer_port = int(port_text)
                if not (1 <= peer_port <= 65535):
                    continue

                with self.host.peers_lock:
                    self.host.peers[peer_name] = {
                        "ip": addr[0],
                        "port": peer_port,
                        "last_seen": tm.time(),
                        "state": peer_state,
                    }
            except (UnicodeDecodeError, ValueError):
                # Gói UDP không đúng định dạng thì bỏ qua.
                continue

    def broadcast_message(self):
        print(f"[*] Broadcasting presence; TCP port {self.tcp_port}")
        while not self.stop_flag.is_set():
            msg = (
                f"!LOL|{self.host.name}|{self.tcp_port}|{self.host.state}"
            ).encode(c.FORMAT)
            try:
                self.broadcast_socket.sendto(msg, (self.bcast, c.PORT))
            except OSError:
                if not self.stop_flag.is_set():
                    raise
                break
            self.stop_flag.wait(3)

    def start_listening(self):
        if not self.receive_thread.is_alive():
            self.receive_thread.start()

    def start_broadcasting(self):
        if not self.broadcast_thread.is_alive():
            self.broadcast_thread.start()

    def end_process(self):
        self.stop_flag.set()
        for sock in (self.receive_socket, self.broadcast_socket):
            try:
                sock.close()
            except OSError:
                pass
