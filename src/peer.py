import threading as thd


class Peer:
    def __init__(self, peer_name):
        self.name = peer_name
        self.peers = {}
        self.state = "online"
        self.peers_lock = thd.Lock()
        self.unread = {}


def print_help_message():
    print("[*] Available commands: ")
    print(
        "    /list                     Show online users with number, name, IP and status"
    )
    print(
        "    /chat <name|number>       Open a chat with the selected user (TCP connection)"
    )
    print("    <any text>                Send a message to the current chat partner")
    print("    /send <file>              Send a file to the current chat partner")
    print("    /leave                    Close the current chat")
    print("    /status <online|away>     Change your status (sent via UDP)")
    print("    /help                     Show all commands")
    print("    /quit                     Exit the program")
