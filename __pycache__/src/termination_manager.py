import psutil

def get_roblox_processes():
    """Finds all active RobloxPlayerBeta.exe process objects."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == "robloxplayerbeta.exe":
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

def terminate_all_roblox():
    """Forcibly terminates all running Roblox instances."""
    procs = get_roblox_processes()
    if not procs:
        print("[-] No active Roblox instances found to terminate.")
        return 0

    killed_count = 0
    for proc in procs:
        try:
            pid = proc.pid
            proc.kill()
            print(f"[+] Terminated Roblox process PID {pid}")
            killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"[!] Could not terminate PID {proc.pid}: {e}")

    return killed_count

def terminate_roblox_by_pid(pid):
    """Terminates a specific Roblox instance by PID."""
    try:
        proc = psutil.Process(pid)
        proc.kill()
        print(f"[+] Terminated target PID {pid}")
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"[!] Failed to kill PID {pid}: {e}")
        return False

if __name__ == "__main__":
    print("[*] Testing Termination Manager...")
    count = terminate_all_roblox()
    print(f"[+] Terminated {count} Roblox process(es).")