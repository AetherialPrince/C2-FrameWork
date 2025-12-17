import os

CHUNK_SIZE = 262144  # 256 KB


def box_runtime(message: str):
    """Display a message in a box."""
    print("\n" + "=" * 60)
    print(message.center(60))
    print("=" * 60 + "\n")


def choose_file_to_send(base_dir):
    """Let user choose a file to send."""
    files = [
        f for f in os.listdir(base_dir)
        if os.path.isfile(os.path.join(base_dir, f))
    ]
    
    if not files:
        print(f"[!] No files in {base_dir}/")
        return None
    
    print("[*] Available files:")
    for i, f in enumerate(files, 1):
        print(f"  {i}) {f}")
    
    try:
        choice = input("Select file number: ").strip()
        idx = int(choice) - 1
        
        if 0 <= idx < len(files):
            return files[idx]
        
        print("[!] Invalid selection")
        return None
    except:
        print("[!] Invalid input")
        return None


def recv_line(sock):
    """Receive a line from socket."""
    data = b""
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("Socket closed")
        if chunk == b"\n":
            break
        data += chunk
    return data.decode("utf-8", errors="ignore").strip()


def recv_exact(sock, size: int) -> bytes:
    """Receive exact number of bytes from socket."""
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(min(CHUNK_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError("Connection closed during recv_exact")
        data.extend(chunk)
    return bytes(data)