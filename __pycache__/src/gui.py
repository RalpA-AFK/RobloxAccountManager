import customtkinter as ctk
import threading
import psutil
from handle_manager import get_roblox_pids, close_singleton_handle

# Appearance Setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Roblox Account Manager")
        self.geometry("600x400")
        self.resizable(False, False)

        # --- Top Left: Green Author Box ---
        self.author_frame = ctk.CTkFrame(
            self, 
            width=150, 
            height=60, 
            fg_color="transparent", 
            border_color="#2ecc71", 
            border_width=2, 
            corner_radius=8
        )
        self.author_frame.place(x=20, y=20)

        self.author_label = ctk.CTkLabel(
            self.author_frame, 
            text="Authors:\nAli_Reaper0456\nKaydenV210", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#2ecc71",
            justify="center"
        )
        self.author_label.place(relx=0.5, rely=0.5, anchor="center")

        # --- Top Right: Grey Big Title Box ---
        self.title_frame = ctk.CTkFrame(
            self, 
            width=380, 
            height=60, 
            fg_color="#333333", 
            corner_radius=10
        )
        self.title_frame.place(x=190, y=20)

        self.title_label = ctk.CTkLabel(
            self.title_frame, 
            text="Roblox Account Manager", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FFFFFF"
        )
        self.title_label.place(relx=0.5, rely=0.5, anchor="center")

        # --- Center: Circular Singleton Termination Button ---
        self.btn_singleton = ctk.CTkButton(
            self,
            text="Bypass Singleton",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            height=120,
            corner_radius=60,  # Makes the button a circle
            fg_color="#555555",
            hover_color="#777777",
            command=self.run_singleton_bypass_thread
        )
        self.btn_singleton.place(x=240, y=120)

        # --- Bottom Center: Terminate All Instances Button ---
        self.btn_terminate_all = ctk.CTkButton(
            self,
            text="Terminate All Instances",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=180,
            height=40,
            corner_radius=20,
            fg_color="#000000",
            hover_color="#222222",
            border_color="#444444",
            border_width=1,
            command=self.terminate_all_roblox_thread
        )
        self.btn_terminate_all.place(x=210, y=270)

        # --- Bottom Status Label ---
        self.status_label = ctk.CTkLabel(
            self, 
            text="Status: Idle", 
            font=ctk.CTkFont(size=12)
        )
        self.status_label.place(x=20, y=360)

    # --- Actions & Logic ---

    def run_singleton_bypass(self):
        self.status_label.configure(text="Status: Scanning for singleton handles...")
        pids = get_roblox_pids()
        if not pids:
            self.status_label.configure(text="Status: No active Roblox instances found.")
            return

        closed_count = 0
        for pid in pids:
            if close_singleton_handle(pid):
                closed_count += 1

        if closed_count > 0:
            self.status_label.configure(text="Status: Singleton cleared! Ready to launch next account.")
        else:
            self.status_label.configure(text="Status: Singleton already cleared or not detected.")

    def terminate_all_roblox(self):
        self.status_label.configure(text="Status: Terminating all Roblox instances...")
        pids = get_roblox_pids()
        if not pids:
            self.status_label.configure(text="Status: No active Roblox instances to terminate.")
            return

        terminated = 0
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                proc.kill()
                terminated += 1
            except Exception as e:
                print(f"[!] Failed to kill PID {pid}: {e}")

        self.status_label.configure(text=f"Status: Successfully terminated {terminated} Roblox process(es).")

    # Threading wrappers to keep the UI smooth and responsive
    def run_singleton_bypass_thread(self):
        threading.Thread(target=self.run_singleton_bypass, daemon=True).start()

    def terminate_all_roblox_thread(self):
        threading.Thread(target=self.terminate_all_roblox, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()