import subprocess
from handle_manager import get_roblox_pids


def terminate_all_roblox() -> int:
    pids = get_roblox_pids()
    if not pids:
        return 0

    terminated_count = 0
    for pid in pids:
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            if result.returncode == 0:
                terminated_count += 1
        except Exception as e:
            print(f"[!] Error terminating Roblox PID {pid}: {e}")
            
    return terminated_count

def terminate_single_pid(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[!] Error terminating specific PID {pid}: {e}")
        return False