import threading as thd


class Peer:
    def __init__(self, peer_name):
        self.name = peer_name
        self.peers = {}
        self.state = "online"
        self.peers_lock = thd.Lock()

        self.unread_lock = thd.Lock()
        self.unread = {}
