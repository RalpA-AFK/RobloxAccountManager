import customtkinter as ctk
import threading
import time
import webbrowser
from account_manager import AccountManager
from termination_manager import terminate_all_roblox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.account_manager = AccountManager(on_account_update=self.safe_refresh_ui)

        self.title("Kaizen Codes - Roblox Account Manager")
        self.geometry("650x500")
        self.resizable(False, False)
        self.configure(fg_color="#0a0a0a")

        self.current_tab = "accounts"  # "accounts" or "manager"

        # --- Top Navigation Tabs ---
        self.tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_frame.place(x=20, y=15)

        self.btn_tab_accounts = ctk.CTkButton(
            self.tab_frame, text="Accounts", font=ctk.CTkFont(size=12, weight="bold"),
            width=295, height=35, corner_radius=6,
            fg_color="#002b11", hover_color="#004d1f",
            border_color="#00FF66", border_width=1, text_color="#00FF66",
            command=lambda: self.switch_tab("accounts")
        )
        self.btn_tab_accounts.pack(side="left", padx=(0, 10))

        self.btn_tab_manager = ctk.CTkButton(
            self.tab_frame, text="Account Manager", font=ctk.CTkFont(size=12, weight="bold"),
            width=295, height=35, corner_radius=6,
            fg_color="#121212", hover_color="#1f1f1f",
            border_color="#333333", border_width=1, text_color="#888888",
            command=lambda: self.switch_tab("manager")
        )
        self.btn_tab_manager.pack(side="left")

        # --- Content Area Frame ---
        self.content_frame = ctk.CTkFrame(
            self, fg_color="#121212", border_color="#00FF66", border_width=1, 
            corner_radius=8, width=610, height=380
        )
        self.content_frame.place(x=20, y=65)

        # Scrollable container inside content area
        self.account_scroll_frame = ctk.CTkScrollableFrame(
            self.content_frame, fg_color="transparent", width=580, height=300
        )
        self.account_scroll_frame.place(x=15, y=15)

        # --- Bottom Control Area ---
        self.bottom_action_frame = ctk.CTkFrame(self, fg_color="transparent", width=610, height=35)
        self.bottom_action_frame.place(x=20, y=455)

        # --- Status Label ---
        self.status_label = ctk.CTkLabel(
            self, text="Status: Idle | Monitoring instances...", 
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#00FF66"
        )
        self.status_label.place(x=20, y=515)

        self.is_launching_lock = False

        self.account_manager.start_watcher()
        self.render_current_tab()

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        if tab_name == "accounts":
            self.btn_tab_accounts.configure(fg_color="#002b11", border_color="#00FF66", text_color="#00FF66")
            self.btn_tab_manager.configure(fg_color="#121212", border_color="#333333", text_color="#888888")
        else:
            self.btn_tab_manager.configure(fg_color="#002b11", border_color="#00FF66", text_color="#00FF66")
            self.btn_tab_accounts.configure(fg_color="#121212", border_color="#333333", text_color="#888888")
        
        self.render_current_tab()

    def safe_refresh_ui(self):
        self.after(0, self.render_current_tab)
        self.after(0, lambda: self.status_label.configure(text="Status: Instance state synced."))

    def render_current_tab(self):
        for widget in self.account_scroll_frame.winfo_children():
            widget.destroy()
        
        for widget in self.bottom_action_frame.winfo_children():
            widget.destroy()

        instances = self.account_manager.fetch_active_instances()

        if self.current_tab == "accounts":
            self.render_accounts_tab(instances)
        else:
            self.render_manager_tab(instances)

    def render_accounts_tab(self, instances):
        if not instances:
            empty_lbl = ctk.CTkLabel(
                self.account_scroll_frame, text="No active accounts detected.\nLaunch an account to begin.",
                text_color="#666666", font=ctk.CTkFont(size=11)
            )
            empty_lbl.pack(pady=80)
        else:
            for inst in instances:
                slot_idx = inst["slot_index"]
                display_name = inst["display_name"]
                is_active = inst["is_active"]
                state = inst["state"]
                pid = inst["pid"]
                is_xbox = inst.get("is_xbox", False)
                
                is_parent = (not is_xbox and slot_idx == self.account_manager.parent_slot_id)

                if is_xbox:
                    row_border = "#ffaa00"
                else:
                    row_border = "#ff3333" if is_parent and is_active else "#00FF66" if is_active else "#333333"

                row_frame = ctk.CTkFrame(
                    self.account_scroll_frame, fg_color="#1a1a1a", 
                    border_color=row_border, border_width=1, corner_radius=6,
                    height=45
                )
                row_frame.pack(fill="x", padx=5, pady=4)

                def on_enter(e, f=row_frame):
                    f.configure(fg_color="#222222")
                def on_leave(e, f=row_frame):
                    f.configure(fg_color="#1a1a1a")

                row_frame.bind("<Enter>", on_enter)
                row_frame.bind("<Leave>", on_leave)

                badge_text = f"#{slot_idx}"
                badge_color = "#ffaa00" if is_xbox else "#00FF66"
                slot_lbl = ctk.CTkLabel(
                    row_frame, text=badge_text, font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=badge_color, width=55
                )
                slot_lbl.pack(side="left", padx=(10, 5), pady=8)

                name_lbl = ctk.CTkLabel(
                    row_frame, text=display_name, font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#ffffff", width=190, anchor="w"
                )
                name_lbl.pack(side="left", padx=5, pady=8)

                state_color = "#ffaa00" if is_xbox else ("#00FF66" if "Focus" in state else "#ffaa00" if "Idle" in state else "#666666")
                status_badge = ctk.CTkLabel(
                    row_frame, text=state, font=ctk.CTkFont(size=10, weight="bold"),
                    text_color=state_color, width=105
                )
                status_badge.pack(side="left", padx=5, pady=8)

                btn_state = "disabled" if self.is_launching_lock else "normal"
                if is_active and pid != 0:
                    kill_btn = ctk.CTkButton(
                        row_frame, text="Close", font=ctk.CTkFont(size=10, weight="bold"),
                        width=65, height=26, fg_color="#4d0000", hover_color="#800000",
                        text_color="#ff9999", state=btn_state,
                        command=lambda p=pid: self.terminate_single_pid_action(p)
                    )
                    kill_btn.pack(side="right", padx=10, pady=8)
                else:
                    launch_btn = ctk.CTkButton(
                        row_frame, text="Launch", font=ctk.CTkFont(size=10, weight="bold"),
                        width=65, height=26, fg_color="#332200" if is_xbox else "#002b11", 
                        hover_color="#664400" if is_xbox else "#004d1f",
                        text_color="#ffaa00" if is_xbox else "#00FF66", state=btn_state,
                        command=lambda idx=slot_idx: self.launch_account_thread(idx)
                    )
                    launch_btn.pack(side="right", padx=10, pady=8)

        # --- Terminate All Button at bottom ---
        btn_terminate_all = ctk.CTkButton(
            self.bottom_action_frame, text="TERMINATE ALL INSTANCES", font=ctk.CTkFont(size=11, weight="bold"),
            width=610, height=32, corner_radius=6, fg_color="#3d0000",
            hover_color="#660000", border_color="#ff3333", border_width=1,
            text_color="#ff3333", command=self.terminate_all_roblox_thread
        )
        btn_terminate_all.pack(fill="x")

    def render_manager_tab(self, instances):
        btn_add = ctk.CTkButton(
            self.bottom_action_frame, text="+ Add / Link New Account", font=ctk.CTkFont(size=11, weight="bold"),
            width=610, height=32, corner_radius=6, fg_color="#002b11",
            hover_color="#004d1f", border_color="#00FF66", border_width=1,
            text_color="#00FF66", command=self.link_account_thread
        )
        btn_add.pack(fill="x")

        if not instances:
            empty_lbl = ctk.CTkLabel(
                self.account_scroll_frame, text="No accounts linked yet.\nClick '+ Add / Link New Account' below.",
                text_color="#666666", font=ctk.CTkFont(size=11)
            )
            empty_lbl.pack(pady=80)
            return

        for inst in instances:
            slot_idx = inst["slot_index"]
            custom_label = inst["custom_label"]
            is_xbox = inst.get("is_xbox", False)
            display_name = inst["display_name"]

            row_frame = ctk.CTkFrame(
                self.account_scroll_frame, fg_color="#1a1a1a", 
                border_color="#333333", border_width=1, corner_radius=6,
                height=45
            )
            row_frame.pack(fill="x", padx=5, pady=4)

            slot_lbl = ctk.CTkLabel(
                row_frame, text=f"#{slot_idx}", font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#ffaa00" if is_xbox else "#00FF66", width=45
            )
            slot_lbl.pack(side="left", padx=(10, 5), pady=8)

            name_text = f"{display_name} (Xbox Slot)" if is_xbox else f"{display_name} (@{inst['username']})"
            name_lbl = ctk.CTkLabel(
                row_frame, text=name_text, font=ctk.CTkFont(size=11),
                text_color="#cccccc", width=240, anchor="w"
            )
            name_lbl.pack(side="left", padx=5, pady=8)

            if not is_xbox:
                cookie_btn = ctk.CTkButton(
                    row_frame, text="Cookie", font=ctk.CTkFont(size=10, weight="bold"),
                    width=65, height=24, fg_color="#1f1f1f", hover_color="#2a2a2a",
                    border_color="#00FF66", border_width=1, text_color="#00FF66",
                    command=lambda s=slot_idx: self.prompt_cookie_update(s)
                )
                cookie_btn.pack(side="right", padx=(5, 10), pady=8)

            edit_btn = ctk.CTkButton(
                row_frame, text="Edit Name", font=ctk.CTkFont(size=10, weight="bold"),
                width=75, height=24, fg_color="#1f1f1f", hover_color="#2a2a2a",
                border_color="#888888", border_width=1, text_color="#cccccc",
                command=lambda s=slot_idx, curr=custom_label: self.edit_custom_label(s, curr)
            )
            edit_btn.pack(side="right", padx=5, pady=8)

    def edit_custom_label(self, slot_index, current_label):
        dialog = ctk.CTkInputDialog(
            text=f"Edit custom label for Slot #{slot_index}:", 
            title="Edit Account Label"
        )
        new_label = dialog.get_input()
        if new_label is not None:
            self.account_manager.db.update_custom_label(slot_index, new_label.strip())
            self.render_current_tab()
            self.status_label.configure(text=f"Status: Updated label for Slot #{slot_index}.")

    def prompt_cookie_update(self, slot_index):
        update_win = ctk.CTkToplevel(self)
        update_win.title(f"Update Cookie - Slot #{slot_index}")
        update_win.geometry("450x380")
        update_win.resizable(False, False)
        update_win.configure(fg_color="#121212")
        update_win.attributes("-topmost", True)
        update_win.lift()
        update_win.focus_force()
        update_win.grab_set()

        lbl = ctk.CTkLabel(
            update_win, text=f"Paste new .ROBLOSECURITY Cookie for Slot #{slot_index}:",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#00FF66"
        )
        lbl.pack(pady=(20, 10))

        cookie_textbox = ctk.CTkTextbox(
            update_win, width=410, height=120, fg_color="#1a1a1a",
            text_color="#cccccc", font=ctk.CTkFont(size=10), wrap="word"
        )
        cookie_textbox.pack(padx=20, pady=5)

        def save_cookie():
            raw_cookie = cookie_textbox.get("1.0", "end-1c").strip()
            update_win.destroy()
            if not raw_cookie:
                self.status_label.configure(text="Status: Cookie update cancelled.")
                return

            self.status_label.configure(text=f"Status: Validating cookie for Slot #{slot_index}...")
            acc = self.account_manager.db.get_account(slot_index)
            current_label = acc.get("custom_label", f"Slot #{slot_index}") if acc else f"Slot #{slot_index}"
            
            success, message = self.account_manager.link_manual_account(slot_index, raw_cookie, current_label)
            self.status_label.configure(text=f"Status: {message}")
            if success:
                self.render_current_tab()

        save_btn = ctk.CTkButton(
            update_win, text="Save & Validate Cookie", width=200, height=30,
            fg_color="#002b11", hover_color="#004d1f", border_color="#00FF66", border_width=1,
            text_color="#00FF66", command=save_cookie
        )
        save_btn.pack(pady=10)

        help_btn = ctk.CTkButton(
            update_win, text="❓ How to get Cookie (Instructions)", width=200, height=25,
            fg_color="#1f1f1f", hover_color="#2a2a2a", border_color="#555555", border_width=1,
            text_color="#aaaaaa", command=self.show_cookie_help
        )
        help_btn.pack(pady=(0, 15))

    def link_account_action(self):
        existing = self.account_manager.db.get_all_accounts()
        next_slot = len(existing) + 1
        self.prompt_cookie_update(next_slot)

    def link_account_thread(self):
        threading.Thread(target=self.link_account_action, daemon=True).start()

    def launch_account_thread(self, slot_index):
        def task():
            self.is_launching_lock = True
            self.after(0, self.render_current_tab)
            self.after(0, lambda: self.status_label.configure(text=f"Status: Launching slot #{slot_index}..."))
            
            success, reason = self.account_manager.launch_account(slot_index)
            
            time.sleep(5.0)
            self.is_launching_lock = False
            self.after(0, self.render_current_tab)
            
            if success:
                self.after(0, lambda: self.status_label.configure(text=f"Status: Slot #{slot_index} launched successfully!"))
            elif reason == "expired":
                self.after(0, lambda: self.status_label.configure(text=f"Status: Cookie expired for Slot #{slot_index}. Updating..."))
                self.after(0, lambda: self.prompt_cookie_update(slot_index))
            else:
                self.after(0, lambda: self.status_label.configure(text=f"Status: Launch failed ({reason})."))
                
        threading.Thread(target=task, daemon=True).start()

    def terminate_single_pid_action(self, pid):
        from termination_manager import terminate_single_pid
        terminate_single_pid(pid)
        self.render_current_tab()
        self.status_label.configure(text="Status: Terminated instance.")

    def terminate_all_roblox(self):
        self.after(0, lambda: self.status_label.configure(text="Status: Terminating all Roblox instances..."))
        terminated = terminate_all_roblox()
        self.account_manager.active_slots.clear()
        self.account_manager.parent_slot_id = None
        self.after(0, lambda: self.status_label.configure(text=f"Status: Terminated {terminated} Roblox process(es)."))
        self.after(0, self.render_current_tab)

    def terminate_all_roblox_thread(self):
        threading.Thread(target=self.terminate_all_roblox, daemon=True).start()

    def show_cookie_help(self):
        help_window = ctk.CTkToplevel(self)
        help_window.title("How to get your .ROBLOSECURITY Cookie")
        help_window.geometry("480x420")
        help_window.resizable(False, False)
        help_window.configure(fg_color="#121212")
        
        help_window.attributes("-topmost", True)
        help_window.lift()
        help_window.focus_force()
        help_window.grab_set()

        title_lbl = ctk.CTkLabel(
            help_window, text="How to Find Your Security Cookie",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#00FF66"
        )
        title_lbl.pack(pady=(15, 10))

        instructions = (
            "1. Open your regular web browser and log into Roblox.\n\n"
            "2. Press F12 (or Right Click -> Inspect) to open Developer Tools.\n\n"
            "3. Go to the 'Application' tab (Chrome/Edge) or 'Storage' tab (Firefox).\n\n"
            "4. Expand 'Cookies' and click on 'https://www.roblox.com'.\n\n"
            "5. Copy the entire 'Value' string of .ROBLOSECURITY.\n\n"
            "⚠️ IMPORTANT NOTE FOR 5+ ACCOUNTS:\n"
            "Roblox's native account switcher caps at 5 accounts. If you log in "
            "past 5 accounts in the same browser, it will log you out of an older session "
            "and invalidate its cookie. If managing >5 accounts, use separate browser "
            "profiles (Chrome Profiles / Firefox Containers) to harvest each cookie safely."
        )
        text_box = ctk.CTkTextbox(
            help_window, width=440, height=260, fg_color="#1a1a1a",
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
        close_btn.pack(pady=12)