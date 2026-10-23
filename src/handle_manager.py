import subprocess
import re
import psutil
import os
import winreg

def ensure_sysinternals_eula():
    try:
        reg_path = r"Software\Sysinternals\Handle"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            winreg.SetValueEx(key, "EulaAccepted", 0, winreg.REG_DWORD, 1)
    except Exception as e:
        print(f"[!] Warning: Could not set Sysinternals EULA registry key: {e}")

ensure_sysinternals_eula()

def get_roblox_pids():
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == "robloxplayerbeta.exe":
                pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids

def get_xbox_pids():
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == "windows10universal.exe":
                pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids

def close_singleton_handle(pid):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)
    path_in_src = os.path.join(base_dir, "handle64.exe")
    path_in_root = os.path.join(root_dir, "handle64.exe")
    HANDLE_EXE = path_in_src if os.path.exists(path_in_src) else (path_in_root if os.path.exists(path_in_root) else None)
    if not HANDLE_EXE:
        return False
    try:
        cmd = [HANDLE_EXE, "-accepteula", "-a", "ROBLOX_singleton", "-p", str(pid), "-nobanner"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        matches = re.findall(r"([0-9A-Fa-f]+):\s+\\Sessions", result.stdout)
        if not matches:
            matches = re.findall(r"([0-9A-Fa-f]+):", result.stdout)
        if not matches:
            return False
        closed_any = False
        for handle_id in set(matches):
            clean_id = handle_id.strip()
            if clean_id == str(pid) or len(clean_id) < 2:
                continue
            close_cmd = [HANDLE_EXE, "-accepteula", "-c", clean_id, "-p", str(pid), "-y", "-nobanner"]
            subprocess.run(close_cmd, capture_output=True, text=True, timeout=5)
            closed_any = True
        return closed_any
    except Exception as e:
        return False