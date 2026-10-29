# import const_val as c
# import socket as sk
# import threading as thd


# class ChatManager:
#     def __init__(self, tcp_port, name, peer):
#         # Thông tin của bản thân
#         self.name = name
#         self.other = peer
#         self.tcp_port = tcp_port

#         # Socket chờ kết nối từ peer khác
#         self.listen_socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)

#         # Lưu những kết nối chat đang hoạt động
#         self.connections = {}

#         self.active_chat = None
#         self.unread = {}

#         self.listener_thread = thd.Thread(target=self.start_accepting)
#         self.listener_thread.daemon = True

#         # Bảo vệ connections nếu nhiều thread truy cập
#         self.lock = thd.Lock()

#     def start_accepting(self):
#         # bind, listen
#         self.listen_socket.bind(("", self.tcp_port))
#         # accept liên tục
#         self.listen_socket.listen()
#         while True:
#             conn, addr = self.listen_socket.accept()

#             # Mỗi kết nối mới được giao cho handler
#             peer_name = ""
#             for name, info in self.other.peers.items():
#                 if info["ip"] == addr[0]:
#                     peer_name = name

#             with self.lock:
#                 self.connections[peer_name] = conn

#             recv_thread = thd.Thread(
#                 target=self.receive_handler, args=(peer_name, conn)
#             )
#             recv_thread.daemon = True
#             recv_thread.start()

#     def start_listening(self):
#         self.listener_thread.start()

#     def start_chat(self, peer_name):
#         if peer_name not in self.other.peers:
#             print(f"[*] Cannot find the user {peer_name}")
#             return

#         if peer_name not in self.connections:
#             try:
#                 self.connect_to_peer(peer_name)
#             except:
#                 print(f"[*] Cannot connect to the user {peer_name}")
#                 with self.lock:
#                     self.active_chat = None

#         with self.lock:
#             self.active_chat = peer_name

#     def connect_to_peer(self, peer_name):
#         # Tìm IP và TCP port trong danh sách peers
#         peer_ip = self.other.peers[peer_name]["ip"]
#         peer_port = self.other.peers[peer_name]["port"]
#         peer_address = (peer_ip, peer_port)
#         # Tạo socket client
#         client_socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
#         # connect đến peer
#         client_socket.connect(peer_address)
#         # Đăng ký kết nối

#         with self.lock:
#             self.connections[peer_name] = client_socket

#     def receive_handler(self, peer_name, conn):
#         # Chỉ nhận dữ liệu
#         # Xử lý khi peer ngắt kết nối
#         while True:
#             try:
#                 msg = conn.recv(c.HEADER).decode(c.FORMAT)
#                 if not msg:
#                     break
#                 print(f"{peer_name}: {msg}")
#             except:
#                 break

#         # clean up
#         with self.lock:
#             if peer_name in self.connections:
#                 self.connections.pop(peer_name)
#             if self.active_chat == peer_name:
#                 self.active_chat = None

#         conn.close()

#     def send_message(self, peer_name, msg):
#         try:
#             # Tìm kết nối tương ứng
#             send_socket = self.connections[peer_name]
#             msg = msg.encode(c.FORMAT)
#             # Gửi message qua kết nối đó
#             send_socket.sendall(msg)
#         except:
#             self.close_connection(peer_name)

#     def close_connection(self, peer_name):
#         # Xóa kết nối và đóng socket đúng cách
#         with self.lock:
#             conn = self.connections.pop(peer_name, None)

#             if conn is None:
#                 return

#             if self.active_chat == peer_name:
#                 self.active_chat = None

#         conn.close()


import const_val as c
import socket as sk
import threading as thd


class ChatManager:
    def __init__(
        self,
        tcp_port,
        name,
        peer,
        on_message=None,
        on_unread_changed=None,
    ):
        self.name = name
        self.other = peer
        self.tcp_port = tcp_port

        # Kết nối đang hoạt động: {peer_name: socket}
        self.connections = {}

        # Người đang được mở trong giao diện chat
        self.active_chat = None

        # Tin nhắn chưa đọc: {peer_name: [message, ...]}
        self.unread = {}

        # Callback giao tiếp với UI
        self.on_message = on_message
        self.on_unread_changed = on_unread_changed

        self.lock = thd.RLock()

        self.listen_socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)
        self.listen_socket.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEADDR, 1)

        self.listener_thread = thd.Thread(
            target=self.start_accepting,
            daemon=True,
        )

    # ---------------- TCP PROTOCOL ----------------

    def _recv_exact(self, conn, size):
        """Đọc đủ số byte cần thiết, tránh thiếu dữ liệu TCP."""
        data = bytearray()

        while len(data) < size:
            chunk = conn.recv(size - len(data))

            if not chunk:
                return None

            data.extend(chunk)

        return bytes(data)

    def _recv_message(self, conn):
        """
        Đọc header chứa độ dài tin nhắn, sau đó đọc payload.
        Cả hai phía phải dùng cùng giao thức.
        """
        header = self._recv_exact(conn, c.HEADER)

        if header is None:
            return None

        try:
            length = int(header.decode(c.FORMAT).strip())
        except (ValueError, UnicodeDecodeError):
            raise ValueError("Header tin nhắn không hợp lệ")

        if length < 0:
            raise ValueError("Độ dài tin nhắn không hợp lệ")

        # Tránh cấp phát/đọc payload quá lớn.
        if length > 10 * 1024 * 1024:
            raise ValueError("Tin nhắn vượt quá giới hạn 10 MB")

        if length == 0:
            return ""

        payload = self._recv_exact(conn, length)

        if payload is None:
            return None

        return payload.decode(c.FORMAT)

    def _send_message(self, conn, msg):
        payload = msg.encode(c.FORMAT)

        header = str(len(payload)).encode(c.FORMAT)

        if len(header) > c.HEADER:
            raise ValueError("HEADER không đủ chứa độ dài tin nhắn")

        header = header.ljust(c.HEADER, b" ")

        conn.sendall(header + payload)

    # ---------------- LISTENING ----------------

    def start_accepting(self):
        self.listen_socket.bind(("", self.tcp_port))
        self.listen_socket.listen()

        while True:
            try:
                conn, addr = self.listen_socket.accept()
            except OSError:
                break

            peer_name = None

            for name, info in self.other.peers.items():
                if info["ip"] == addr[0]:
                    peer_name = name
                    break

            # Không nhận kết nối từ peer không xác định.
            if peer_name is None:
                conn.close()
                continue

            with self.lock:
                # Không ghi đè socket đang được sử dụng.
                old_conn = self.connections.get(peer_name)

                if old_conn is None:
                    self.connections[peer_name] = conn
                    accepted = True
                else:
                    accepted = False

            if not accepted:
                conn.close()
                continue

            thd.Thread(
                target=self.receive_handler,
                args=(peer_name, conn),
                daemon=True,
            ).start()

    def start_listening(self):
        if not self.listener_thread.is_alive():
            self.listener_thread.start()

    # ---------------- CHAT SESSION ----------------

    def start_chat(self, peer_name):
        """Mở phiên chat và xử lý tin nhắn chưa đọc."""

        if peer_name not in self.other.peers:
            print(f"Cannot find user: {peer_name}")
            return False

        with self.lock:
            connected = peer_name in self.connections

        if not connected:
            try:
                self.connect_to_peer(peer_name)
            except OSError as exc:
                print(f"Cannot connect to {peer_name}: {exc}")
                return False

        with self.lock:
            # Chuyển phiên chat đang mở sang peer mới.
            self.active_chat = peer_name

            # Lấy và xóa unread trong cùng một critical section.
            pending = self.unread.pop(peer_name, [])

        # Callback bên ngoài lock để tránh deadlock với UI.
        if self.on_unread_changed:
            self.on_unread_changed(peer_name, 0)

        # Hiển thị các tin nhắn đến trước khi mở chat.
        if self.on_message:
            for msg in pending:
                self.on_message(peer_name, msg)

        return True

    def leave_chat(self):
        """Đóng phiên chat hiện tại nhưng giữ kết nối TCP."""
        with self.lock:
            self.active_chat = None

    def connect_to_peer(self, peer_name):
        info = self.other.peers[peer_name]

        client_socket = sk.socket(sk.AF_INET, sk.SOCK_STREAM)

        try:
            client_socket.connect((info["ip"], info["port"]))

            with self.lock:
                existing = self.connections.get(peer_name)

                if existing is None:
                    self.connections[peer_name] = client_socket
                    accepted = True
                else:
                    accepted = False

            if not accepted:
                client_socket.close()
                return

            thd.Thread(
                target=self.receive_handler,
                args=(peer_name, client_socket),
                daemon=True,
            ).start()

        except Exception:
            client_socket.close()
            raise

    # ---------------- RECEIVE MESSAGES ----------------

    def receive_handler(self, peer_name, conn):
        try:
            while True:
                msg = self._recv_message(conn)

                if msg is None:
                    break

                # Phân loại tin nhắn trong cùng lock để
                # tránh sai lệch khi người dùng đổi phiên chat.
                with self.lock:
                    if self.active_chat == peer_name:
                        is_active = True
                    else:
                        is_active = False

                        self.unread.setdefault(peer_name, []).append(msg)

                        unread_count = len(self.unread[peer_name])

                if is_active:
                    # Đang mở chat với người gửi:
                    # hiển thị ngay, không tăng unread.
                    if self.on_message:
                        self.on_message(peer_name, msg)
                    else:
                        print(f"{peer_name}: {msg}")

                else:
                    # Không mở chat với người gửi:
                    # lưu vào unread.
                    if self.on_unread_changed:
                        self.on_unread_changed(peer_name, unread_count)

        except (OSError, ValueError, UnicodeDecodeError) as exc:
            print(f"Receive error from {peer_name}: {exc}")

        finally:
            with self.lock:
                # Chỉ xóa nếu dictionary vẫn trỏ đến
                # đúng socket mà thread này đang quản lý.
                if self.connections.get(peer_name) is conn:
                    self.connections.pop(peer_name, None)

                # Không tự ý đổi active_chat tại đây:
                # phiên UI là trạng thái riêng với kết nối.

            try:
                conn.close()
            except OSError:
                pass

    # ---------------- SEND MESSAGES ----------------

    def send_message(self, peer_name, msg):
        with self.lock:
            send_socket = self.connections.get(peer_name)

        if send_socket is None:
            print(f"No connection to {peer_name}")
            return False

        try:
            self._send_message(send_socket, msg)
            return True

        except (OSError, ValueError) as exc:
            print(f"Send error to {peer_name}: {exc}")
            self.close_connection(peer_name)
            return False

    # ---------------- UNREAD MANAGEMENT ----------------

    def get_unread(self, peer_name):
        """Lấy bản sao danh sách tin chưa đọc."""
        with self.lock:
            return list(self.unread.get(peer_name, []))

    def get_unread_count(self, peer_name=None):
        with self.lock:
            if peer_name is not None:
                return len(self.unread.get(peer_name, []))

            return sum(len(messages) for messages in self.unread.values())

    def close_connection(self, peer_name):
        with self.lock:
            conn = self.connections.pop(peer_name, None)

        if conn is not None:
            try:
                conn.shutdown(sk.SHUT_RDWR)
            except OSError:
                pass

            try:
                conn.close()
            except OSError:
                pass

    def close(self):
        """Đóng toàn bộ kết nối và socket lắng nghe."""
        with self.lock:
            connections = list(self.connections.values())
            self.connections.clear()
            self.active_chat = None

        for conn in connections:
            try:
                conn.shutdown(sk.SHUT_RDWR)
            except OSError:
                pass

            try:
                conn.close()
            except OSError:
                pass

        try:
            self.listen_socket.close()
        except OSError:
            pass
