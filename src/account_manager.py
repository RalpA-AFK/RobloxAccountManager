import requests
import os
import time
import threading
import psutil
import win32gui
import win32process
import subprocess
from database import DatabaseManager
from handle_manager import get_roblox_pids, get_xbox_pids, close_singleton_handle

class AccountManager:
    def __init__(self, on_account_update=None):
        self.db = DatabaseManager()
        self.on_account_update = on_account_update
        self.active_watch_running = False
        self.active_slots = {}  # slot_index -> pid for web accounts
        self.xbox_slots = {}    # slot_index -> pid for xbox instances
        self.parent_slot_id = None
        self.launch_in_progress = False
        self.close_in_progress = False

    def start_watcher(self):
        if self.active_watch_running:
            return
        self.active_watch_running = True
        def _watcher_loop():
            last_pids = set(get_roblox_pids() + get_xbox_pids())
            while self.active_watch_running:
                try:
                    current_pids = set(get_roblox_pids() + get_xbox_pids())
                    if current_pids != last_pids:
                        last_pids = current_pids
                        if self.on_account_update:
                            self.on_account_update()
                except Exception as e:
                    pass
                time.sleep(2)
        threading.Thread(target=_watcher_loop, daemon=True).start()

    def fetch_active_instances(self):
        accounts = self.db.get_all_accounts()
        current_pids = get_roblox_pids()
        xbox_pids = get_xbox_pids()
        
        focused_pid = None
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, focused_pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            pass

        instances = []
        tracked_xbox_pids = set(self.xbox_slots.values())
        available_xbox_pids = [p for p in xbox_pids if p not in tracked_xbox_pids]
        
        for acc in accounts:
            slot_id = acc["slot_index"]
            is_xbox = not acc.get("cookie") or acc.get("cookie") == ""
            
            if is_xbox:
                pid = self.xbox_slots.get(slot_id, 0)
                if pid not in xbox_pids:
                    if available_xbox_pids:
                        pid = available_xbox_pids.pop(0)
                        self.xbox_slots[slot_id] = pid
                    else:
                        pid = 0
                        if slot_id in self.xbox_slots:
                            del self.xbox_slots[slot_id]
                
                is_running = pid in xbox_pids if pid != 0 else False
                state = "Active: Focus" if pid == focused_pid else ("Active: Idle" if is_running else "Closed")
                
                instances.append({
                    "slot_index": slot_id,
                    "username": "Xbox Instance",
                    "display_name": f"PID: {pid}" if pid != 0 else "Xbox App",
                    "custom_label": acc.get("custom_label", f"Xbox Slot #{slot_id}"),
                    "is_active": is_running,
                    "state": state,
                    "pid": pid,
                    "is_xbox": True
                })
            else:
                pid = self.active_slots.get(slot_id, 0)
                is_running = pid in current_pids if pid != 0 else False
                if not is_running and slot_id in self.active_slots:
                    del self.active_slots[slot_id]
                    pid = 0

                state = "Active: Focus" if pid == focused_pid else ("Active: Idle" if is_running else "Closed")
                
                instances.append({
                    "slot_index": slot_id,
                    "username": acc["username"],
                    "display_name": acc["display_name"],
                    "custom_label": acc.get("custom_label", ""),
                    "is_active": is_running,
                    "state": state,
                    "pid": pid,
                    "is_xbox": False
                })

        return instances

    def launch_xbox_roblox(self):
        """Dynamically finds and launches the Roblox Microsoft Store / Xbox app cleanly via Appx package data."""
        try:
            ps_cmd = (
            "$pkg = Get-AppxPackage -Name '*Roblox*'; "
            "if ($pkg) { "
            "    $manifest = [xml](Get-AppxPackageManifest -Package $pkg); "
            "    $appId = $manifest.Package.Applications.Application.Id; "
            "    $pfn = $pkg.PackageFamilyName; "
            "    Start-Process 'explorer.exe' \"shell:AppsFolder\\${pfn}!${appId}\"; "
            "} else { "
            "    throw 'Roblox Microsoft Store app not found'; "
            "}"
            )
            result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
        
            if result.returncode != 0:
                return False, f"Failed to launch Xbox Roblox: {result.stderr.strip()}"

            if self.on_account_update:
                self.on_account_update()
                return True, "Successfully launched Roblox Xbox version!"
        except Exception as e:
            return False, f"Failed to launch Xbox Roblox: {str(e)}"

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

            csrf_resp = requests.post(
                "https://auth.roblox.com/v1/authentication-ticket",
                cookies=cookies, headers=headers, json={}, timeout=10
            )
            csrf_token = csrf_resp.headers.get("x-csrf-token")
            if not csrf_token:
                self.launch_in_progress = False
                return False, "expired" 

            headers["x-csrf-token"] = csrf_token
            ticket_resp = requests.post(
                "https://auth.roblox.com/v1/authentication-ticket",
                cookies=cookies, headers=headers, json={}, timeout=10
            )
            ticket = ticket_resp.headers.get("rbx-authentication-ticket")
            if not ticket:
                self.launch_in_progress = False
                return False, "ticket_error"

            launch_url = f"roblox-player:1+launchmode:app+gameinfo:{ticket}"
            os.startfile(launch_url)
            
            def _delayed_handle_release():
                try:
                    time.sleep(7.0)
                    current_pids = get_roblox_pids()
                    if not current_pids:
                        return

                    pids_before = set(self.active_slots.values())
                    new_pids = [p for p in current_pids if p not in pids_before]
                    target_pid = new_pids[-1] if new_pids else current_pids[-1]

                    start_time = time.time()
                    while time.time() - start_time < 30.0:
                        if target_pid not in get_roblox_pids():
                            break

                        success = close_singleton_handle(target_pid)
                        if success:
                            break
                        time.sleep(2.5)

                    self.active_slots[slot_id] = target_pid
                    if not self.parent_slot_id or self.parent_slot_id not in self.active_slots.values():
                        if len([p for p in self.active_slots.values() if p in get_roblox_pids()]) <= 1:
                            self.parent_slot_id = slot_id

                finally:
                    self.launch_in_progress = False
                    if self.on_account_update:
                        self.on_account_update()

            threading.Thread(target=_delayed_handle_release, daemon=True).start()
            return True, "success"
        except Exception as e:
            self.launch_in_progress = False
            return False, f"error: {str(e)}"