import subprocess
import re
import psutil
import os

HANDLE_EXE = os.path.join(os.path.dirname(__file__), "handle64.exe")

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
    Parses handle64.exe output targeting ROBLOX_singletonEvent and ROBLOX_singletonMutex.
    """
    if not os.path.exists(HANDLE_EXE):
        print(f"[!] Error: {HANDLE_EXE} not found!")
        return False

    try:
        # Query handles targeting ROBLOX_singleton for the specific PID
        cmd = [HANDLE_EXE, "-accepteula", "-a", "ROBLOX_singleton", "-p", str(pid), "-nobanner"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        # Regex captures hex handle ID preceding the colon and object path
        # Matches format: "type: Event          4E4: \Sessions..."
        matches = re.findall(r"([0-9A-Fa-f]+):\s+\\Sessions", result.stdout)

        if not matches:
            # Fallback regex capturing any hex value right before the colon in lines with ROBLOX_singleton
            matches = re.findall(r"([0-9A-Fa-f]+):", result.stdout)

        if not matches:
            print(f"[-] No matching singleton handles found for PID {pid}.")
            return False

        closed_any = False
        for handle_id in set(matches):
            clean_id = handle_id.strip()
            
            # Skip process ID numbers if captured by fallback
            if clean_id == str(pid) or len(clean_id) < 2:
                continue

            print(f"[+] Closing Singleton Handle ID: 0x{clean_id} on PID {pid}")
            close_cmd = [HANDLE_EXE, "-accepteula", "-c", clean_id, "-p", str(pid), "-y", "-nobanner"]
            subprocess.run(close_cmd, capture_output=True, text=True, timeout=5)
            print(f"[+] Handle 0x{clean_id} closed successfully.")
            closed_any = True

        return closed_any

    except Exception as e:
        print(f"[!] Execution error: {e}")
        return False

if __name__ == "__main__":
    pids = get_roblox_pids()
    if not pids:
        print("[-] No Roblox instances detected.")
    else:
        for pid in pids:
            print(f"[+] Found Roblox PID: {pid}")
            if close_singleton_handle(pid):
                print(f"[+] Singletons cleared for PID {pid}. Ready to launch second instance!")