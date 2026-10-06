import requests
import os
import time
import threading
import psutil
import win32gui
import win32process
from database import DatabaseManager
from handle_manager import get_roblox_pids, close_singleton_handle

class AccountManager:
    def __init__(self, on_account_update=None):
        self.db = DatabaseManager()
        self.on_account_update = on_account_update
        self.active_watch_running = False
        self.active_slots = {}  # slot_index -> pid
        self.parent_slot_id = None  # Tracks the master parent instance

    def start_watcher(self):
        """Spawns a background daemon thread to continuously monitor active Roblox PIDs and sync states."""
        if self.active_watch_running:
            return
            
        self.active_watch_running = True
        
        def _watcher_loop():
            while self.active_watch_running:
                try:
                    current_pids = get_roblox_pids()
                    
                    # Clean up slots whose PIDs have closed externally
                    slots_to_remove = []
                    for slot_id, pid in self.active_slots.items():
                        if pid not in current_pids:
                            slots_to_remove.append(slot_id)
                    
                    for slot_id in slots_to_remove:
                        print(f"[WATCHER] Slot #{slot_id} (PID {self.active_slots[slot_id]}) has closed.")
                        del self.active_slots[slot_id]
                        if slot_id == self.parent_slot_id:
                            self.parent_slot_id = None
                        if self.on_account_update:
                            self.on_account_update()
                            
                except Exception as e:
                    print(f"[WATCHER] Error in monitoring loop: {e}")
                    
                time.sleep(2)

        threading.Thread(target=_watcher_loop, daemon=True).start()

    def fetch_active_instances(self):
        """Fetches stored accounts from database and checks their live execution & focus states."""
        accounts = self.db.get_all_accounts()
        current_pids = get_roblox_pids()
        
        focused_pid = None
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, focused_pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            pass

        instances = []
        for acc in accounts:
            slot_id = acc["slot_index"]
            pid = self.active_slots.get(slot_id, 0)
            
            is_running = pid in current_pids if pid != 0 else False
            if not is_running and slot_id in self.active_slots:
                del self.active_slots[slot_id]
                if slot_id == self.parent_slot_id:
                    self.parent_slot_id = None
                pid = 0

            if is_running:
                is_active = True
                if pid == focused_pid:
                    state = "Active: Focus"
                else:
                    state = "Active: Idle"
            else:
                is_active = False
                state = "Closed"
                pid = 0

            instances.append({
                "slot_index": slot_id,
                "username": acc["username"],
                "display_name": acc["display_name"],
                "custom_label": acc.get("custom_label", ""),
                "is_active": is_active,
                "state": state,
                "pid": pid
            })
            
        return instances

    def link_manual_account(self, slot_id: int, raw_cookie: str, custom_label: str = ""):
        cookie = raw_cookie.strip()
        cookies = {".ROBLOSECURITY": cookie}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        try:
            response = requests.get(
                "https://users.roblox.com/v1/users/authenticated",
                cookies=cookies,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                user_data = response.json()
                username = user_data.get("name")
                display_name = user_data.get("displayName")

                self.db.save_account(
                    slot_index=slot_id,
                    username=username,
                    display_name=display_name,
                    cookie=cookie,
                    custom_label=custom_label
                )
                
                if self.on_account_update:
                    self.on_account_update()

                return True, f"Successfully linked @{username} to Slot #{slot_id}!"
            else:
                return False, "Invalid or expired .ROBLOSECURITY cookie."
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def launch_account(self, slot_id: int):
        """Generates an auth ticket, launches Roblox, and uses a delayed post-initialization handle snip."""
        print(f"\n[DEBUG] --- Starting launch sequence for Slot #{slot_id} ---")
        
        account = self.db.get_account(slot_id)
        if not account:
            return False

        cookie = account["cookie"]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.roblox.com/"
        }
        
        try:
            cookies = {".ROBLOSECURITY": cookie}

            # 1. Get CSRF Token
            csrf_resp = requests.post(
                "https://auth.roblox.com/v1/authentication-ticket",
                cookies=cookies, headers=headers, json={}, timeout=10
            )
            csrf_token = csrf_resp.headers.get("x-csrf-token")
            if not csrf_token:
                return False

            # 2. Get Authentication Ticket
            headers["x-csrf-token"] = csrf_token
            ticket_resp = requests.post(
                "https://auth.roblox.com/v1/authentication-ticket",
                cookies=cookies, headers=headers, json={}, timeout=10
            )
            ticket = ticket_resp.headers.get("rbx-authentication-ticket")
            if not ticket:
                return False

            # 3. Launch protocol handler
            launch_url = f"roblox-player:1+launchmode:app+gameinfo:{ticket}"
            os.startfile(launch_url)
            
            # 4. Spawn a delayed background worker to wait for full init, then snip the mutex
            def _delayed_handle_release():
                # Wait 7 seconds for the Roblox client to fully boot past its initial loader
                print(f"[DEBUG] Waiting for process to fully initialize before snipping singleton...")
                time.sleep(7.0)
                
                current_pids = get_roblox_pids()
                if not current_pids:
                    return

                # Find the newest PID that isn't already fully mapped or track the latest spawned one
                pids_before = set(self.active_slots.values())
                new_pids = [p for p in current_pids if p not in pids_before]
                target_pid = new_pids[-1] if new_pids else current_pids[-1]

                # Aggressively clear the mutex handle multiple times to ensure it stays deleted
                for attempt in range(6):
                    success = close_singleton_handle(target_pid)
                    if success:
                        print(f"[DEBUG] Post-init singleton handle successfully snipped on attempt {attempt + 1} for PID {target_pid}")
                    time.sleep(0.8)

                # Map PID and declare parent if needed
                self.active_slots[slot_id] = target_pid
                if not self.parent_slot_id or self.parent_slot_id not in self.active_slots.values():
                    if len([p for p in self.active_slots.values() if p in get_roblox_pids()]) <= 1:
                        self.parent_slot_id = slot_id
                        print(f"[DEBUG] Slot #{slot_id} designated as Parent Instance post-initialization.")

                if self.on_account_update:
                    self.on_account_update()

            threading.Thread(target=_delayed_handle_release, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"[!] Launch error: {e}")
            return False