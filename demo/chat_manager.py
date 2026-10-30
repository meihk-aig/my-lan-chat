import socket as sk
import threading as thd
import const_val as c


class ChatManager:
    MAX_MESSAGE_BYTES = 10 * 1024 * 1024

    def __init__(
        self, tcp_port, host, on_message=None, on_unread_changed=None, on_error=None
    ):
        self.tcp_port = tcp_port
        self.host = host
        self.connections = {}
        self.active_chat = None

        self.lock = thd.RLock()
        self.host.unread = getattr(self.host, "unread", {})
        self.host.unread_lock = getattr(self.host, "unread_lock", thd.RLock())

        self.on_message = on_message
        self.on_unread_changed = on_unread_changed
        self.on_error = on_error

        self.stop_event = thd.Event()

        self.listen_socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
        self.listen_socket.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEADDR, 1)
        self.listen_socket.bind(("", tcp_port))
        self.listen_socket.listen()
        self.listen_socket.settimeout(1)

        self.listener_thread = thd.Thread(target=self._accept_loop, daemon=True)

    # ---------- Start / Close ----------

    def start_listening(self):
        if not self.listener_thread.is_alive():
            self.listener_thread.start()

    def close(self):
        self.stop_event.set()
        self.listen_socket.close()

        with self.lock:
            connections = list(self.connections.values())
            self.connections.clear()
            self.active_chat = None

        for conn in connections:
            conn.close()

    # ---------- Connection ----------

    def _accept_loop(self):
        while not self.stop_event.is_set():
            try:
                conn, addr = self.listen_socket.accept()
            except sk.timeout:
                continue
            except OSError:
                break

            with self.host.peers_lock:
                peers = [
                    name
                    for name, info in self.host.peers.items()
                    if info.get("ip") == addr[0]
                ]

            if len(peers) != 1:
                conn.close()
                continue

            self._register_connection(peers[0], conn)

    def _register_connection(self, peer_name, conn):
        with self.lock:
            if peer_name in self.connections:
                conn.close()
                return

            self.connections[peer_name] = conn

        thd.Thread(
            target=self._receive_loop, args=(peer_name, conn), daemon=True
        ).start()

    def connect_to_peer(self, peer_name):
        with self.host.peers_lock:
            info = self.host.peers.get(peer_name)

        if info is None:
            raise ValueError(f"Không tìm thấy peer: {peer_name}")

        with self.lock:
            if peer_name in self.connections:
                return True

        conn = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
        conn.settimeout(5)

        try:
            conn.connect((info["ip"], int(info["port"])))
        except OSError:
            conn.close()
            raise

        conn.settimeout(None)
        self._register_connection(peer_name, conn)

        with self.lock:
            return self.connections.get(peer_name) is conn

    def start_chat(self, peer_name):
        try:
            if not self.connect_to_peer(peer_name):
                return False
        except (OSError, ValueError) as exc:
            self._report_error(f"Không thể kết nối {peer_name}: {exc}")
            return False

        with self.lock:
            self.active_chat = peer_name

        with self.host.unread_lock:
            messages = self.host.unread.pop(peer_name, [])

        self._notify_unread(peer_name, 0)

        for message in messages:
            self._notify_message(peer_name, message)

        return True

    def leave_chat(self):
        with self.lock:
            self.active_chat = None

    # ---------- Send / Receive ----------

    def _recv_exact(self, conn, size):
        data = bytearray()

        while len(data) < size:
            chunk = conn.recv(size - len(data))
            if not chunk:
                return None
            data.extend(chunk)

        return bytes(data)

    def _recv_message(self, conn):
        header = self._recv_exact(conn, c.HEADER)
        if header is None:
            return None

        length = int(header.decode(c.FORMAT).strip())

        if not 0 <= length <= self.MAX_MESSAGE_BYTES:
            raise ValueError("Độ dài tin nhắn không hợp lệ")

        payload = self._recv_exact(conn, length)
        if payload is None:
            return None

        return payload.decode(c.FORMAT)

    def _send_message(self, conn, message):
        payload = message.encode(c.FORMAT)
        header = str(len(payload)).ljust(c.HEADER).encode(c.FORMAT)

        if len(str(len(payload))) > c.HEADER:
            raise ValueError("Header không đủ lớn")

        conn.sendall(header + payload)

    def send_message(self, peer_name, message):
        with self.lock:
            conn = self.connections.get(peer_name)

        if conn is None:
            self._report_error(f"Chưa kết nối tới {peer_name}")
            return False

        try:
            self._send_message(conn, message)
            return True
        except (OSError, ValueError) as exc:
            self._report_error(f"Lỗi gửi tin: {exc}")
            self.close_connection(peer_name)
            return False

    def _receive_loop(self, peer_name, conn):
        try:
            while not self.stop_event.is_set():
                message = self._recv_message(conn)

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
                    self._notify_message(peer_name, message)
                else:
                    self._notify_unread(peer_name, count)

        except (OSError, ValueError, UnicodeDecodeError) as exc:
            if not self.stop_event.is_set():
                self._report_error(f"Lỗi nhận tin từ {peer_name}: {exc}")

        finally:
            with self.lock:
                if self.connections.get(peer_name) is conn:
                    del self.connections[peer_name]

            conn.close()

    def close_connection(self, peer_name):
        with self.lock:
            conn = self.connections.pop(peer_name, None)

        if conn:
            conn.close()

    # ---------- Unread ----------

    def get_unread(self, peer_name):
        with self.host.unread_lock:
            return list(self.host.unread.get(peer_name, []))

    def get_unread_count(self, peer_name=None):
        with self.host.unread_lock:
            if peer_name:
                return len(self.host.unread.get(peer_name, []))

            return sum(len(messages) for messages in self.host.unread.values())

    # ---------- Callbacks ----------

    def _notify_message(self, peer_name, message):
        if self.on_message:
            self.on_message(peer_name, message)
        else:
            print(f"{peer_name}: {message}")

    def _notify_unread(self, peer_name, count):
        if self.on_unread_changed:
            self.on_unread_changed(peer_name, count)

    def _report_error(self, message):
        if self.on_error:
            self.on_error(message)
        else:
            print(f"[ChatManager] {message}")
