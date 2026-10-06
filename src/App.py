import customtkinter as ctk
import threading
import multiprocessing
import webbrowser

import requests
from account_manager import AccountManager
from termination_manager import terminate_all_roblox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.account_manager = AccountManager(on_account_update=self.safe_refresh_ui)

        self.title("Roblox Account Manager")
        self.geometry("750x550")
        self.resizable(False, False)
        self.configure(fg_color="#0a0a0a")

        # QoL #2: Lock application to the front of all screens (Always-On-Top)
        self.attributes("-topmost", True)

        # --- Top Left: Author Box ---
        self.author_frame = ctk.CTkFrame(
            self, width=150, height=60, fg_color="#121212", 
            border_color="#00FF66", border_width=2, corner_radius=8
        )
        self.author_frame.place(x=20, y=20)

        self.author_label = ctk.CTkLabel(
            self.author_frame, text="Authors:\nAli_Reaper0456\nKaydenV210", 
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#00FF66", justify="center"
        )
        self.author_label.place(relx=0.5, rely=0.5, anchor="center")

        # --- Top Right: Title Box ---
        self.title_frame = ctk.CTkFrame(
            self, width=530, height=60, fg_color="#121212", 
            border_color="#00FF66", border_width=1, corner_radius=10
        )
        self.title_frame.place(x=190, y=20)

        self.title_label = ctk.CTkLabel(
            self.title_frame, text="ROBLOX ACCOUNT MANAGER", 
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#00FF66"
        )
        self.title_label.place(relx=0.5, rely=0.5, anchor="center")

        # --- Left Center: Account Management Hub ---
        self.account_frame = ctk.CTkScrollableFrame(
            self, width=420, height=290, fg_color="#121212", 
            border_color="#00FF66", border_width=1, corner_radius=8
        )
        self.account_frame.place(x=20, y=90)

        # --- Below Account Management: Add Account Button ---
        self.btn_add_account = ctk.CTkButton(
            self, text="+ Add / Link Account", font=ctk.CTkFont(size=12, weight="bold"),
            width=420, height=35, corner_radius=6, fg_color="#002b11",
            hover_color="#004d1f", border_color="#00FF66", border_width=1,
            text_color="#00FF66", command=self.link_account_thread
        )
        self.btn_add_account.place(x=20, y=395)

        # --- Below Add Account: Help / Tutorial Button ---
        self.btn_help_cookie = ctk.CTkButton(
            self, text="❓ How to get Cookie (Instructions)", font=ctk.CTkFont(size=11),
            width=420, height=25, corner_radius=6, fg_color="#121212",
            hover_color="#1f1f1f", border_color="#00FF66", border_width=1,
            text_color="#00FF66", command=lambda: self.show_cookie_help()
        )
        self.btn_help_cookie.place(x=20, y=435)

        # --- Right Side: TERMINATE ALL INSTANCES Button ---
        self.btn_terminate_all = ctk.CTkButton(
            self, text="TERMINATE ALL\nINSTANCES", font=ctk.CTkFont(size=12, weight="bold"),
            width=240, height=120, corner_radius=12, fg_color="#3d0000",
            hover_color="#660000", border_color="#ff3333", border_width=1,
            text_color="#ff3333", command=self.terminate_all_roblox_thread
        )
        self.btn_terminate_all.place(x=480, y=130)

        # --- Bottom Status Label ---
        self.status_label = ctk.CTkLabel(
            self, text="Status: Idle | Monitoring instances...", 
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#00FF66"
        )
        self.status_label.place(x=20, y=510)

        self.account_manager.start_watcher()
        self.refresh_account_ui()

    def safe_refresh_ui(self):
        self.after(0, self.refresh_account_ui)
        self.after(0, lambda: self.status_label.configure(text="Status: Instance state synced."))

    def refresh_account_ui(self):
        for widget in self.account_frame.winfo_children():
            widget.destroy()

        instances = self.account_manager.fetch_active_instances()
        if not instances:
            empty_lbl = ctk.CTkLabel(
                self.account_frame, text="No accounts linked yet.\nClick '+ Add / Link Account' below to begin.",
                text_color="#666666", font=ctk.CTkFont(size=11)
            )
            empty_lbl.pack(pady=40)
            return

        for inst in instances:
            slot_idx = inst["slot_index"]
            username = inst["username"]
            custom_label = inst["custom_label"]
            is_active = inst["is_active"]
            state = inst["state"]
            pid = inst["pid"]
            
            is_parent = (slot_idx == self.account_manager.parent_slot_id)

            row_border = "#ff3333" if is_parent and is_active else "#00FF66" if is_active else "#333333"
            row_frame = ctk.CTkFrame(
                self.account_frame, fg_color="#1a1a1a", 
                border_color=row_border, border_width=1 if is_parent and is_active else 0, 
                corner_radius=6
            )
            row_frame.pack(fill="x", padx=5, pady=4)

            # Slot ID & Parent Indicator
            slot_text = f"#{slot_idx} (Parent)" if is_parent and is_active else f"#{slot_idx}"
            num_label = ctk.CTkLabel(
                row_frame, text=slot_text, font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#ff3333" if is_parent and is_active else "#00FF66", width=75
            )
            num_label.pack(side="left", padx=(6, 2), pady=6)

            # Username Tag (Widened)
            user_lbl = ctk.CTkLabel(
                row_frame, text=f"@{username}", font=ctk.CTkFont(size=11),
                text_color="#cccccc", width=110, anchor="w"
            )
            user_lbl.pack(side="left", padx=2, pady=6)

            # Custom Tag Display (Widened significantly to prevent cutting off)
            label_text = custom_label if custom_label else f"Slot #{slot_idx}"
            label_lbl = ctk.CTkLabel(
                row_frame, text=label_text, font=ctk.CTkFont(size=10, slant="italic"),
                text_color="#888888", width=110, anchor="w"
            )
            label_lbl.pack(side="left", padx=2, pady=6)
            label_lbl.bind("<Double-Button-1>", lambda e, s=slot_idx, curr=custom_label: self.edit_custom_label(s, curr))

            # State Badge
            badge_color = "#00FF66" if "Focus" in state else "#ffaa00" if "Idle" in state else "#666666"
            status_badge = ctk.CTkLabel(
                row_frame, text=state, font=ctk.CTkFont(size=10, weight="bold"),
                text_color=badge_color, width=75
            )
            status_badge.pack(side="left", padx=2, pady=6)

            # Action Button Toggle (Launch vs Kill with a buffer safety lock)
            if is_active and pid != 0:
                kill_btn = ctk.CTkButton(
                    row_frame, text="Kill", font=ctk.CTkFont(size=10, weight="bold"),
                    width=45, height=22, 
                    fg_color="#222222" if is_parent else "#4d0000", 
                    hover_color="#222222" if is_parent else "#800000",
                    text_color="#666666" if is_parent else "#ff9999",
                    state="disabled" if is_parent else "disabled",
                    command=lambda p=pid: self.terminate_single_pid_action(p)
                )
                kill_btn.pack(side="right", padx=6, pady=6)
                
                if not is_parent:
                    self.after(3000, lambda b=kill_btn: b.configure(state="normal") if b.winfo_exists() else None)
            else:
                launch_btn = ctk.CTkButton(
                    row_frame, text="Launch", font=ctk.CTkFont(size=10, weight="bold"),
                    width=45, height=22, fg_color="#002b11", hover_color="#004d1f",
                    text_color="#00FF66", state="normal",
                    command=lambda idx=slot_idx: self.launch_account_thread(idx)
                )
                launch_btn.pack(side="right", padx=6, pady=6)
                
    def edit_custom_label(self, slot_index, current_label):
        """Allows editing the custom label via input dialog upon double-clicking the tag."""
        dialog = ctk.CTkInputDialog(
            text=f"Edit custom label for Slot #{slot_index}:", 
            title="Edit Account Label"
        )
        new_label = dialog.get_input()
        if new_label is not None:
            self.account_manager.db.update_custom_label(slot_index, new_label.strip())
            self.refresh_account_ui()
            self.status_label.configure(text=f"Status: Updated label for Slot #{slot_index}.")

    def link_account_action(self):
        existing = self.account_manager.db.get_all_accounts()
        next_slot = len(existing) + 1

        dialog = ctk.CTkInputDialog(
            text=f"Paste your .ROBLOSECURITY Cookie for Slot #{next_slot}:", 
            title=f"Link Account - Slot #{next_slot}"
        )
        raw_cookie = dialog.get_input()

        if not raw_cookie:
            self.after(0, lambda: self.status_label.configure(text="Status: Account linking cancelled."))
            return

        label_dialog = ctk.CTkInputDialog(
            text="Enter a custom name/tag for this account (e.g., Main Alt):", 
            title="Account Label"
        )
        custom_label = label_dialog.get_input() or f"Slot #{next_slot}"

        self.after(0, lambda: self.status_label.configure(text=f"Status: Validating cookie for Slot #{next_slot}..."))
        
        success, message = self.account_manager.link_manual_account(next_slot, raw_cookie, custom_label)
        
        if success:
            self.after(0, lambda: self.status_label.configure(text=f"Status: {message}"))
            self.after(0, self.refresh_account_ui)
        else:
            self.after(0, lambda: self.status_label.configure(text=f"Status: {message}"))

    def link_account_thread(self):
        threading.Thread(target=self.link_account_action, daemon=True).start()

    def launch_account_thread(self, slot_index):
        def task():
            self.after(0, lambda: self.status_label.configure(text=f"Status: Launching account slot #{slot_index}..."))
            success, reason = self.account_manager.launch_account(slot_index)
            if success:
                self.after(0, lambda: self.status_label.configure(text=f"Status: Slot #{slot_index} launched successfully!"))
            elif reason == "expired":
                self.after(0, lambda: self.status_label.configure(text=f"Status: Slot #{slot_index} has an expired cookie."))
                
                self.after(0, lambda: self.prompt_reauth_for_slot(slot_index))
            else:
                self.after(0, lambda: self.status_label.configure(text=f"Status: Launch failed ({reason})."))
        threading.Thread(target=task, daemon=True).start()

    def prompt_reauth_for_slot(self, slot_index):
        dialog = ctk.CTkInputDialog(
            text = f"The cookie for slot #{slot_index} has expired. \n Please enter your updated .ROBLOSECURITY cookie:",
            title = "Re-authentication Required for Slot #{slot_index}" 
        )
        raw_cookie = dialog.get_input()

        if not raw_cookie:
            self.status_label.configure(text=f"Status: Re-authentication cancelled for slot #{slot_index}")
            return

        acc = self.account_manager.db.get_account(slot_index)
        if not acc: 
            return

        expected_username = acc["username"]
        current_label = acc.get("custom_Label", f"Slot #{slot_index}") if acc else f"Slot #{slot_index}"

        self.status_label.configure(text=f"Status: Validating new cookie for Slot #{slot_index}")

        test_cookies = {".ROBLOSECURITY": raw_cookie.strip()}
        test_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try: 
            response = requests.get(
                "https://users.roblox.com/v1/users/authenticated",
                cookies=test_cookies,
                headers=test_headers,
                timeout=10
            )
            if response.status_code != 200:
                self.status_label.configure(text = "Status:Re-auth failed. The provided cookie is invalid or expired.")
                return 

            user_data = response.json()
            pasted_username = user_data.get("name")

            if pasted_username.lower() != expected_username.lower():
                self.status_label.configure(text = f"Status: Error! Cookie belongs to @{pasted_username}")
                return
        except Exception as e: 
            self.status_label.configure(text=f"Status: Validation error: {str(e)}")
            return 
        
        success, message = self.account_manager.link_manual_account(slot_index, raw_cookie, current_label)

        self.status_label.configure(text=f"Status: {message}")

        if(success):
            self.refresh_account_ui()

            self.launch_account_thread(slot_index)

    def terminate_single_pid_action(self, pid):
        from termination_manager import terminate_single_pid
        terminate_single_pid(pid)
        self.refresh_account_ui()
        self.status_label.configure(text="Status: Terminated instance.")

    def terminate_all_roblox(self):
        self.after(0, lambda: self.status_label.configure(text="Status: Terminating all Roblox instances..."))
        terminated = terminate_all_roblox()
        self.account_manager.active_slots.clear()
        self.account_manager.parent_slot_id = None
        self.after(0, lambda: self.status_label.configure(text=f"Status: Terminated {terminated} Roblox process(es)."))
        self.after(0, self.refresh_account_ui)

    def terminate_all_roblox_thread(self):
        threading.Thread(target=self.terminate_all_roblox, daemon=True).start()

    def show_cookie_help(self):
        help_window = ctk.CTkToplevel(self)
        help_window.title("How to get your .ROBLOSECURITY Cookie")
        help_window.geometry("480x380")
        help_window.resizable(False, False)
        help_window.configure(fg_color="#121212")
        help_window.grab_set()

        title_lbl = ctk.CTkLabel(
            help_window, text="How to Find Your Security Cookie",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#00FF66"
        )
        title_lbl.pack(pady=(15, 10))

        instructions = (
            "1. Open your regular web browser (Chrome, Edge, Firefox) and log into Roblox.\n\n"
            "2. Press F12 (or Right Click -> Inspect) to open Developer Tools.\n\n"
            "3. Go to the 'Application' tab (Chrome/Edge) or 'Storage' tab (Firefox).\n\n"
            "4. On the left sidebar, expand 'Cookies' and click on 'https://www.roblox.com'.\n\n"
            "5. Look for the cookie named .ROBLOSECURITY.\n\n"
            "6. Copy the entire 'Value' string and paste it into the app when prompted."
        )

        text_box = ctk.CTkTextbox(
            help_window, width=440, height=220, fg_color="#1a1a1a",
            text_color="#cccccc", font=ctk.CTkFont(size=11), wrap="word"
        )
        text_box.pack(padx=20, pady=5)
        text_box.insert("1.0", instructions)
        text_box.configure(state="disabled")

        close_btn = ctk.CTkButton(
            help_window, text="Got it", width=120, height=30,
            fg_color="#002b11", hover_color="#004d1f",
            border_color="#00FF66", border_width=1, text_color="#00FF66",
            command=help_window.destroy
        )
        close_btn.pack(pady=15)