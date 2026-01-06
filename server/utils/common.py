# ======================== CONFIGURATION ========================
import os

CHUNK_SIZE = 262144  # 256 KB

# ======================== DISPLAY HELPERS ========================
def box_runtime(message: str):
    """Display a message in a box."""
    print("\n" + "=" * 60)
    print(message.center(60))
    print("=" * 60 + "\n")

# ======================== FILE SELECTION ========================
def _list_available_files(base_dir):
    """List available files in directory."""
    return [f for f in os.listdir(base_dir)
            if os.path.isfile(os.path.join(base_dir, f))]

def _display_file_choices(files):
    """Display file choices to user."""
    print("[*] Available files:")
    for i, f in enumerate(files, 1):
        print(f"  {i}) {f}")

def choose_file_to_send(base_dir):
    """Let user choose a file to send."""
    files = _list_available_files(base_dir)
    
    if not files:
        print(f"[!] No files in {base_dir}/")
        return None
    
    _display_file_choices(files)
    
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

# ======================== NETWORK HELPERS ========================
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