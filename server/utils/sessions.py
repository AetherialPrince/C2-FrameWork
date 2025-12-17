from threading import Lock

clients = {}
lock = Lock()

def add_client(cid, sock):
    """Add a client to active sessions."""
    with lock:
        clients[cid] = sock
    print(f"[+] Client {cid} added")

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

def handle_client(sock, addr, cid, db_hooks):
    """Handle client communication with fingerprint support."""
    from .common import recv_line
    from .file_transfers import receive_file_from_client
    
    ip, port = addr[0], addr[1]
    
    try:
        # FIRST: Receive fingerprint from client
        first_line = recv_line(sock)
        
        client_id = None
        if first_line and first_line.startswith("FINGERPRINT "):
            fingerprint = first_line.split()[1]
            
            # Create minimal fingerprint data
            fp_data = {"fingerprint": fingerprint}
            
            # Register/update client and get persistent ID
            client_id = db_hooks["register_client"](fingerprint, fp_data, ip, port)
            
            # Record session opening with persistent client_id
            db_hooks["record_session_open"](client_id, ip, port)
            
            # Update sessions dict with new ID if different from temp ID
            if client_id != cid:
                with lock:
                    if cid in clients:
                        clients[client_id] = clients.pop(cid)
            
            print(f"[+] Client {client_id} (fingerprint: {fingerprint[:8]}...) connected from {ip}:{port}")
        else:
            # Legacy client or no fingerprint - use temp ID
            client_id = cid
            fp_data = {}
            db_hooks["record_session_open"](client_id, ip, port)
            print(f"[+] Client {client_id} connected from {ip}:{port} (legacy)")
        
        # Main communication loop
        while True:
            line = recv_line(sock)
            if not line:
                break
            
            # Handle FILE transfer from client
            if line.startswith("FILE "):
                try:
                    name, size, path = receive_file_from_client(sock, line)
                    db_hooks["record_transfer"](client_id, "receive", name, size)
                    print(f"[+] File received from {client_id}: {path}")
                    sock.sendall("RECVOK\n".encode())
                except Exception as e:
                    print(f"[!] File transfer error from {client_id}: {e}")
                continue
            
            # Handle RECVOK
            if line == "RECVOK":
                print(f"[{client_id}] File transfer acknowledged")
                continue
            
            # Handle any other response
            print(f"[{client_id}] {line}")
            db_hooks["record_response"](client_id, line)
            
    except ConnectionError:
        print(f"[-] Client {client_id if client_id else cid} disconnected")
    except Exception as e:
        print(f"[!] Client {client_id if client_id else cid} error: {e}")
    finally:
        if client_id:
            db_hooks["record_session_close"](client_id)
            remove_client(client_id)
        else:
            remove_client(cid)
        print(f"[-] Client {client_id if client_id else cid} disconnected")