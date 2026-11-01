from broadcast import *
import peer as p
import const_val as c
import chat as cht

import threading as thd
import time as tm
import socket as sk
import argparse as ap


def help_command(args):
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


def quit_command(args, broadcaster):
    if len(args) != 1:
        print('[*] Do you mean"/quit"?')
        return

    broadcaster.end_process()
    print("[*] Connection closed.")
    return c.EXIT


def status_command(args, host):
    if len(args) != 2:
        print('[*] Do you mean"/status <online|away>"?')
        return

    state = args[1]
    if state == "online":
        host.state = "online"
    elif state == "away":
        host.state = "away"
    else:
        print('[*] Your status must be "online" or "away".')
        return

    print(f'[*] Your status set to "{host.state}".')


def list_command(args, host):
    if len(args) != 1:
        print('[*] Do you mean"/list"?')
        return

    current_time = tm.time()

    with host.peers_lock:
        index = 1
        peers_snapshot = host.peers.copy()
        for name, info in peers_snapshot.items():
            current_state = info["state"]

            if current_time - info["last_seen"] > c.TIMEOUT:
                current_state = "away"

            print(f"    {index}. {name} ({info['ip']}) {current_state}.")

            index += 1


def chat_command(args, manager):
    if len(args) != 2:
        print('[*] Do you mean "/chat <name>"?')
        return

    peer_name = args[1]

    if not manager.start_chat(peer_name):
        return

    while True:
        message = input("> ").strip()

        if not message:
            continue

        if message.startswith("/leave"):
            if message == "/leave":
                manager.leave_chat()
                print(f"[*] You have left the chat with {peer_name}.")
                break
            else:
                print('[*] Do you mean "/leave"?')
                continue

        if message.startswith("/"):
            print("[*] You must leave the current chat session to use other commands.")
            continue

        manager.send_message(peer_name, message)


def send_command(args):
    pass
