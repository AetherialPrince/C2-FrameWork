
import os,sys,random,subprocess,threading,time,datetime
GUI_AVAILABLE = False

def install_deps():
    """Auto-install required dependencies"""
    try:
        subprocess.run(['which', 'apt-get'], capture_output=True, check=True)
    except:
        return False
    
    try:
        import tkinter
    except ImportError:
        try:
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'python3-tk'], 
                         capture_output=True, check=True)
        except:
            pass
    
    return True

try:
    import tkinter as tk
    from tkinter import messagebox
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

class PrankMaster:
    def __init__(self):
        self.pranks = [self.popup_madness, self.fake_update, self.desktop_icons]
        self.running = True
        self.cleanup_files = []
    
    def popup_madness(self):
        if not GUI_AVAILABLE:
            return
            
        messages = [
            ("SYSTEM ALERT", "Your computer has been infected with cuteness!"),
            ("COFFEE REQUIRED", "Critical coffee levels detected!"),
            ("AI ACTIVATED", "Your computer is now self-aware!"),
            ("CRITICAL WARNING", "Too much productivity detected!"),
            ("DOWNLOADING", "Downloading more RAM..."),
            ("UPDATING", "Upgrading to Windows 95..."),
            ("LOVE DETECTED", "Your computer loves you!"),
            ("GAME TIME", "Installing games instead of work..."),
            ("PIZZA ALERT", "System hungry! Please insert pizza!"),
            ("PANIC MODE", "Remain calm! (But actually panic)"),
        ]
        
        def create_popup():
            if not self.running:
                return
            try:
                title, msg = random.choice(messages)
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo(title, msg)
                root.destroy()
            except:
                pass
        
        # Create lots of popups
        for i in range(40):
            if not self.running:
                break
            threading.Thread(target=create_popup, daemon=True).start()
            time.sleep(random.uniform(0.2, 0.8))
    
    def fake_update(self):
        """YES - This creates the BIG fake update screen"""
        if not GUI_AVAILABLE:
            return
            
        try:
            root = tk.Tk()
            root.title("CRITICAL SYSTEM UPDATE")
            root.attributes('-fullscreen', True)  # FULLSCREEN
            root.configure(bg='#000033')
            
            # Big header
            header = tk.Label(root, text="SYSTEM UPDATE IN PROGRESS", 
                            font=('Courier', 32, 'bold'), fg='white', bg='#000033')
            header.pack(pady=50)
            
            # Progress bar display
            progress_text = tk.Label(root, text="[                    ] 0%", 
                                   font=('Monospace', 24), fg='#00ff00', bg='#000033')
            progress_text.pack(pady=20)
            
            # Status messages
            status = tk.Label(root, text="Initializing update...", 
                            font=('Arial', 16), fg='cyan', bg='#000033')
            status.pack(pady=10)
            
            # Fake file list
            file_box = tk.Text(root, height=8, width=60, 
                             font=('Monospace', 12), bg='#111144', fg='white')
            file_box.pack(pady=20)
            file_box.insert('1.0', "Preparing update...\n")
            file_box.config(state='disabled')
            
            def update_progress():
                status_messages = [
                    "Downloading security patches...",
                    "Installing system updates...",
                    "Verifying package integrity...",
                    "Updating kernel modules...",
                    "Patching system libraries...",
                    "Optimizing performance...",
                    "Cleaning temporary files...",
                    "Finalizing installation..."
                ]
                
                for i in range(1, 101):
                    if not self.running:
                        break
                    
                    # Update progress bar
                    filled = i // 5
                    empty = 20 - filled
                    bar = "[" + "#" * filled + " " * empty + "]"
                    progress_text.config(text=f"{bar} {i}%")
                    
                    # Update status every 10%
                    if i % 10 == 0:
                        status.config(text=random.choice(status_messages))
                    
                    # Add to file list every 15%
                    if i % 15 == 0:
                        file_box.config(state='normal')
                        file_box.insert('end', f"update-package-{i}.bin ... OK\n")
                        file_box.see('end')
                        file_box.config(state='disabled')
                    
                    root.update()
                    time.sleep(0.05)  # Smooth progress
                
                # Final message before closing
                status.config(text="Update complete! Rebooting system...", fg='yellow')
                progress_text.config(text="[####################] 100%", fg='green')
                root.update()
                time.sleep(3)
                root.destroy()
            
            threading.Thread(target=update_progress, daemon=True).start()
            root.mainloop()
        except Exception as e:
            print(f"Update screen error: {e}")
    
    def desktop_icons(self):
        desktop = os.path.expanduser("~/Desktop")
        if not os.path.exists(desktop):
            return
            
        files = [
            ("README_NOW.txt", "Your computer misses you! Spend more time together!"),
            ("SYSTEM_WARNING.log", f"System anomaly detected at {datetime.now()}"),
            ("SECRET_MSG.txt", "You found the secret! This was just a prank."),
            ("URGENT_FILE.exe.txt", "Warning: This is NOT actually an executable!"),
            ("DO_NOT_OPEN.txt", "You opened it! Curiosity satisfied."),
        ]
        
        for name, content in files:
            path = os.path.join(desktop, name)
            try:
                with open(path, 'w') as f:
                    f.write(content)
                self.cleanup_files.append(path)
            except:
                pass
    
    def cleanup(self):
        self.running = False
        time.sleep(1)
        
        for path in self.cleanup_files:
            try:
                os.remove(path)
            except:
                pass

def main():
    # STRICT Linux check
    if sys.platform != "linux":
        print("ERROR: This script is for Linux systems only.")
        sys.exit(1)
    
    print("Linux Prankware - Starting harmless pranks...")
    
    # Auto-install if needed
    if len(sys.argv) > 1 and sys.argv[1] != "--no-install":
        install_deps()
    
    # Re-check GUI after potential install
    global GUI_AVAILABLE
    try:
        import tkinter as tk
        from tkinter import messagebox
        GUI_AVAILABLE = True
    except ImportError:
        GUI_AVAILABLE = False
        print("Warning: GUI not available. Some pranks disabled.")
    
    prank = PrankMaster()
    
    try:
        print("Pranks will run for 60 seconds...")
        print("Look for the BIG update screen and popups!")
        
        # Start all pranks
        threads = []
        for func in prank.pranks:
            if func in [prank.popup_madness, prank.fake_update] and not GUI_AVAILABLE:
                continue
            t = threading.Thread(target=func)
            t.daemon = True
            t.start()
            threads.append(t)
            time.sleep(0.5)
        
        # Countdown
        for remaining in range(120, 0, -1):
            if not prank.running:
                break
            print(f"\rTime remaining: {remaining:02d} seconds ", end='', flush=True)
            time.sleep(1)
        print()
        
    except KeyboardInterrupt:
        print("\n\nStopping early...")
    finally:
        prank.cleanup()
        
        # Final message
        if GUI_AVAILABLE:
            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo("Prank Complete", 
                                  "Just a harmless prank!\n\n"
                                  "All changes have been reverted.\n"
                                  "Have a great day!")
                root.destroy()
            except:
                pass
        
        print("All cleaned up! Thanks for playing.")

if __name__ == "__main__":
    main()