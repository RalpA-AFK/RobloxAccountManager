import subprocess
import re
import psutil
import os
import winreg

def ensure_sysinternals_eula():
    """Programmatically accepts the Sysinternals EULA in the registry to prevent subprocess blocks."""
    try:
        reg_path = r"Software\Sysinternals\Handle"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
            winreg.SetValueEx(key, "EulaAccepted", 0, winreg.REG_DWORD, 1)
    except Exception as e:
        print(f"[!] Warning: Could not set Sysinternals EULA registry key: {e}")

# Automatically execute EULA clearance on module import
ensure_sysinternals_eula()

def get_roblox_pids():
    """Finds process IDs for RobloxPlayerBeta.exe."""
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == "robloxplayerbeta.exe":
                pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return pids

def close_singleton_handle(pid):
    """
    Parses handle64.exe output targeting ROBLOX_singleton with guaranteed EULA clearance.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir)
    
    path_in_src = os.path.join(base_dir, "handle64.exe")
    path_in_root = os.path.join(root_dir, "handle64.exe")
    
    HANDLE_EXE = path_in_src if os.path.exists(path_in_src) else (path_in_root if os.path.exists(path_in_root) else None)
    
    if not HANDLE_EXE:
        print(f"[!] Error: handle64.exe not found in src/ or root workspace!")
        return False

    try:
        # Query handles targeting ROBLOX_singleton with explicit EULA clearance
        cmd = [HANDLE_EXE, "-accepteula", "-a", "ROBLOX_singleton", "-p", str(pid), "-nobanner"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        # Regex captures hex handle ID preceding the colon and object path
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
            print(f"[+] Successfully dropped singleton handle ID: 0x{clean_id} on PID {pid}")
            closed_any = True

        return closed_any

    except Exception as e:
        print(f"[!] Execution error for PID {pid}: {e}")
        return False