# Chat project - revised

Files:
- `peer.py`: Peer state and shared unread storage.
- `broadcast.py`: UDP presence broadcaster compatible with the `Broadcaster(host, bcast, tcp_port)` API.
- `chat_manager.py`: TCP chat, active session routing, unread handling, callbacks.

## Required `const_val.py`
This project expects your existing `const_val.py` to define:
- `PORT`: UDP discovery port
- `HEADER`: fixed header length for TCP message framing (e.g. 64)
- `FORMAT`: text encoding (e.g. `"utf-8"`)

## Example integration

```python
from peer import Peer
from broadcast import Broadcaster
from chat_manager import ChatManager

host = Peer("Alice")

def show_message(peer_name, message):
    # If using a GUI toolkit, schedule this callback on the UI/main thread.
    print(f"{peer_name}: {message}")

def unread_changed(peer_name, count):
    print(f"{peer_name} unread: {count}")

chat = ChatManager(
    tcp_port=5000,
    host=host,
    on_message=show_message,
    on_unread_changed=unread_changed,
)

broadcaster = Broadcaster(host, "255.255.255.255", 5000)
chat.start_listening()
broadcaster.start_listening()
broadcaster.start_broadcasting()

# Open a chat:
# chat.start_chat("Bob")
# chat.send_message("Bob", "Hello")
# chat.leave_chat()
# chat.close()
# broadcaster.end_process()
```

## Important protocol note
`chat_manager.py` uses a fixed-size header (`HEADER` bytes) containing the UTF-8 byte length of the message, followed by that many payload bytes. Both ends must use this exact framing in `_send_framed` and `_recv_message`. Do not mix it with the old implementation that sends raw message bytes only.

`/send <file>` is listed in the original help text but file-transfer framing is not implemented in this ChatManager; text framing should not be reused for binary file transfers without adding a separate message-type protocol.

Peer identification in the current discovery architecture uses IP address. Multiple peers sharing one IP cannot be reliably distinguished until a peer-name handshake is added to TCP.
