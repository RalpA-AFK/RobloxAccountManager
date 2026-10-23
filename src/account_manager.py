import requests
import os
import time
import threading
import psutil
import win32gui
import win32process
from database import DatabaseManager
from external_database import ExternalDatabaseManager
from handle_manager import get_roblox_pids, close_singleton_handle

class AccountManager:
    def __init__(self, on_account_update=None):
        self.db = DatabaseManager()
        self.ext_db = ExternalDatabaseManager()
        self.on_account_update = on_account_update
        self.active_watch_running = False
        self.active_slots = {}  # slot_index -> pid
        self.parent_slot_id = None  # Tracks the master parent instance
        self.launch_in_progress = False  # Grace lock during launch sequence
        self.close_in_progress = False   # Grace lock during termination/closing

    def start_watcher(self):
        """Spawns a background daemon thread to continuously monitor active Roblox Pids and sync states."""
        if self.active_watch_running:
            return
            
        self.active_watch_running = True
        
        def _watcher_loop():
            last_pids = set(get_roblox_pids())
            while self.active_watch_running:
                try:
                    current_pids_list = get_roblox_pids()
                    current_pids_set = set(current_pids_list)
                    current_time = time.time()
                    
                    # 1. Clean up internal slots whose PIDs have closed externally
                    slots_to_remove = []
                    for slot_id, pid in self.active_slots.items():
                        if pid not in current_pids_set:
                            slots_to_remove.append(slot_id)
                    
                    has_changes = False
                    for slot_id in slots_to_remove:
                        print(f"[WATCHER] Slot #{slot_id} (PID {self.active_slots[slot_id]}) has closed.")
                        del self.active_slots[slot_id]
                        if slot_id == self.parent_slot_id:
                            self.parent_slot_id = None
                        has_changes = True

                    # 2. Register external PIDs ONLY if neither launch nor close sequences are active
                    if not self.launch_in_progress and not self.close_in_progress:
                        tracked_db_pids = set(self.active_slots.values())
                        unmanaged_pids = [p for p in current_pids_set if p not in tracked_db_pids]

                        # Register newly seen unmanaged PIDs with timestamp
                        for pid in unmanaged_pids:
                            self.ext_db.register_or_get_instance(pid, current_time)

                    # Clean up closed or unstable external PIDs from the ephemeral DB
                    stored_exts = self.ext_db.get_all_external_instances()
                    for ext in stored_exts:
                        ext_pid = ext["pid"]
                        if ext_pid not in current_pids_set:
                            print(f"[WATCHER] External instance PID {ext_pid} has closed. Purging from ephemeral db.")
                            self.ext_db.remove_external_instance(ext_pid)
                            has_changes = True

                    # 3. Detect if any extra/unmanaged processes opened or closed
                    if current_pids_set != last_pids:
                        last_pids = current_pids_set
                        has_changes = True

                    if has_changes and self.on_account_update:
                        self.on_account_update()
                            
                except Exception as e:
                    print(f"[WATCHER] Error in monitoring loop: {e}")
                    
                time.sleep(2)

        threading.Thread(target=_watcher_loop, daemon=True).start()

    def fetch_active_instances(self):
        """Fetches stored accounts from database, checks their live states, and filters external instances through a 5-second delay buffer."""
        accounts = self.db.get_all_accounts()
        current_pids = get_roblox_pids()
        current_time = time.time()
        
        focused_pid = None
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, focused_pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            pass

        instances = []
        tracked_pids = set(self.active_slots.values())

        # Process registered database slots
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
                state = "Active: Focus" if pid == focused_pid else "Active: Idle"
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
                "pid": pid,
                "is_external": False
            })
            
        # Catch extra/unmanaged Roblox instances, applying the 5-second delay buffer and grace locks to avoid ghost spam
        if not self.launch_in_progress and not self.close_in_progress:
            unmanaged_pids = [p for p in current_pids if p not in tracked_pids]
            valid_ext_idx = 1
            for ext_pid in unmanaged_pids:
                ext_record = self.ext_db.register_or_get_instance(ext_pid, current_time)
                first_seen = ext_record.get("first_seen", current_time)

                # ONLY render to GUI if the instance has been alive for >= 5 seconds (filters out ghost helper spawns)
                if current_time - first_seen >= 5.0:
                    custom_label = ext_record["custom_label"]
                    is_focused = (ext_pid == focused_pid)
                    ext_state = "Active: Focus" if is_focused else "Active: Idle"
                    
                    instances.append({
                        "slot_index": f"Ext-{valid_ext_idx}",
                        "username": "External Instance",
                        "display_name": f"PID: {ext_pid}",
                        "custom_label": custom_label,
                        "is_active": True,
                        "state": ext_state,
                        "pid": ext_pid,
                        "is_external": True
                    })
                    valid_ext_idx += 1
            
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
        """Generates an auth ticket, sets launch lock, launches Roblox, and uses a delayed post-initialization handle snip."""
        print(f"\n[DEBUG] --- Starting launch sequence for Slot #{slot_id} ---")
        self.launch_in_progress = True
        
        account = self.db.get_account(slot_id)
        if not account:
            self.launch_in_progress = False
            return False, "not_found"

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
                self.launch_in_progress = False
                return False, "expired" 

            # 2. Get Authentication Ticket
            headers["x-csrf-token"] = csrf_token
            ticket_resp = requests.post(
                "https://auth.roblox.com/v1/authentication-ticket",
                cookies=cookies, headers=headers, json={}, timeout=10
            )
            ticket = ticket_resp.headers.get("rbx-authentication-ticket")
            if not ticket:
                self.launch_in_progress = False
                return False, "ticket_error"

            # 3. Launch protocol handler
            launch_url = f"roblox-player:1+launchmode:app+gameinfo:{ticket}"
            os.startfile(launch_url)
            
            # 4. Spawn a delayed background worker to wait for full init, then snip the mutex
            def _delayed_handle_release():
                try:
                    print(f"[DEBUG] Waiting for process to fully initialize before snipping singleton...")
                    time.sleep(7.0)
                    
                    current_pids = get_roblox_pids()
                    if not current_pids:
                        return

                    pids_before = set(self.active_slots.values())
                    new_pids = [p for p in current_pids if p not in pids_before]
                    target_pid = new_pids[-1] if new_pids else current_pids[-1]

                    clean_checks = 0
                    start_time = time.time()

                    while time.time() - start_time < 30.0:
                        if target_pid not in get_roblox_pids():
                            break

                        success = close_singleton_handle(target_pid)
                        if success:
                            print(f"[DEBUG] Singleton handle snipped successfully on PID {target_pid}. Clean checks: {clean_checks}/3")
                        else:
                             print(f"[DEBUG] Failed to snip singleton handle on PID {target_pid}. Resetting clean checks.") 
                             
                        active_count = len([p for p in get_roblox_pids()])
                        if clean_checks >= 1:
                            if active_count >= 2:
                                print(f"[DEBUG] Multi-instance concurrency confirmed stable for PID {target_pid}")
                                break
                        time.sleep(2.5)

                    self.active_slots[slot_id] = target_pid
                    if not self.parent_slot_id or self.parent_slot_id not in self.active_slots.values():
                        if len([p for p in self.active_slots.values() if p in get_roblox_pids()]) <= 1:
                            self.parent_slot_id = slot_id
                            print(f"[DEBUG] Slot #{slot_id} designated as Parent Instance post-initialization.")

                finally:
                    self.launch_in_progress = False
                    if self.on_account_update:
                        self.on_account_update()

            threading.Thread(target=_delayed_handle_release, daemon=True).start()
            
            return True, "success"
        except requests.exceptions.Timeout:
            self.launch_in_progress = False
            return False, "error: Request timed out. Please check your internet connection."
        except Exception as e:
            self.launch_in_progress = False
            print(f"[!] Launch error: {e}")
            return False, f"error: {str(e)}"

    def claim_external_instance(self, pid: int, label: str):
        self.ext_db.update_custom_label(pid, label)
        if self.on_account_update:
            self.on_account_update()

    def remove_external_tracking(self, pid: int):
        self.ext_db.remove_external_instance(pid)