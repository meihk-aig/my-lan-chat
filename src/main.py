from broadcast import *
import peer as p
import const_val as c
import chatting as cht

import threading as thd
import time as tm
import socket as sk
import argparse as ap

if __name__ == "__main__":
    try:
        # These are parser from the argparse module
        # Eg: Run "python .\src\main.py --name Mathhew" to start the program and set your name Matthew

        parser = ap.ArgumentParser()
        parser.add_argument("--name", required=True)
        parser.add_argument("--bcast", default="255.255.255.255")
        parser.add_argument("--tcp-port", type=int, default=5050)

        lst = parser.parse_args()

        host = p.Peer(lst.name)

        broadcaster = Broadcaster(host, lst.bcast, lst.tcp_port)
        broadcaster.start_broadcasting()
        broadcaster.start_listening()

        print("Hello")

        chat = cht.ChatManager(lst.tcp_port, lst.name, host)
        chat.start_listening()

        print("Hello")

        print("[*] Type /help for instructions")
        while True:
            command = input("> ").split()

            if len(command) == 0:
                continue

            if command[0] == "/quit":  # /quit
                broadcaster.end_process()
                print("[*] Connection closed")
                break

            elif command[0] == "/help":  # /help
                p.print_help_message()

            elif command[0] == "/list":  # /list
                current_time = tm.time()

                with host.peers_lock:
                    index = 1
                    peers_snapshot = host.peers.copy()
                    for name, info in peers_snapshot.items():
                        current_state = info["state"]

                        if current_time - info["last_seen"] > c.TIMEOUT:
                            current_state = "away"

                        print(f"    {index}. {name} ({info['ip']}) {current_state}")

                        index += 1

            elif command[0] == "/status" and len(command) == 2:  # /status
                if command[1] == "online":
                    host.state = "online"
                elif command[1] == "away":
                    host.state = "away"
                else:
                    print('[*] Your status must be "online" or "away"')
                    continue

                print(f'[*] Your status set to "{host.state}"')

    except KeyboardInterrupt:
        print("[*] Connection closed")
