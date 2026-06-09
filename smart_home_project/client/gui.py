"""Tkinter GUI client for the smart-home system."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable, Dict, List, Optional

from smart_home_project.client.smart_home_client import SmartHomeClient
from smart_home_project.common.protocol import Protocol
from smart_home_project.common.server_discovery import DISCOVERY_PORT, discover_servers


class ClientGUI:
    """Dark desktop GUI with welcome, sign-in/sign-up, and device controls."""

    BG = "#151922"
    PANEL = "#202635"
    PANEL_SOFT = "#252d3d"
    TEXT = "#edf2f7"
    MUTED = "#a7b0c0"
    ACCENT = "#5fa8d3"
    ACCENT_DARK = "#316b8c"
    ERROR = "#ff8a8a"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Smart Home Control")
        self.root.minsize(760, 560)
        self.root.configure(bg=self.BG)
        self.client: Optional[SmartHomeClient] = None
        self.devices: List[Dict[str, Any]] = []
        self.visible_device_indexes: List[int] = []
        self.selected_device: Optional[Dict[str, Any]] = None
        self.device_icon_canvas: Optional[tk.Canvas] = None
        self.turn_on_button: Optional[tk.Button] = None
        self.turn_off_button: Optional[tk.Button] = None
        self.update_client: Optional[SmartHomeClient] = None
        self.live_updates_running = False
        self.device_revision = 0
        self.current_user: Optional[Dict[str, str]] = None
        self.users: List[Dict[str, str]] = []
        self.user_list: Optional[tk.Listbox] = None
        self.selected_username: Optional[str] = None

        self.profile_var = tk.StringVar(value="Raspberry Pi")
        self.host_var = tk.StringVar(value="192.168.1.209")
        self.port_var = tk.StringVar(value=str(Protocol.PORT))
        self.username_var = tk.StringVar(value="admin")
        self.password_var = tk.StringVar(value="admin123")
        self.signup_username_var = tk.StringVar()
        self.signup_password_var = tk.StringVar()
        self.signup_role_var = tk.StringVar(value="guest")
        self.value_var = tk.StringVar(value="50")
        self.status_var = tk.StringVar(value="Not connected")
        self.connection_profiles = {
            "Localhost": ("127.0.0.1", str(Protocol.PORT)),
            "Auto Discover": ("", str(Protocol.PORT)),
            "Raspberry Pi": ("192.168.1.209", str(Protocol.PORT)),
            "Custom IP": (self.host_var.get(), self.port_var.get()),
        }

        self._configure_style()
        self._show_auth_screen()
        self.root.after(350, self.find_server)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=self.BG, foreground=self.TEXT, fieldbackground=self.PANEL, font=("Segoe UI", 10))
        style.configure("TFrame", background=self.BG)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BG, foreground=self.TEXT)
        style.configure("Muted.TLabel", background=self.BG, foreground=self.MUTED)
        style.configure("Panel.TLabel", background=self.PANEL, foreground=self.TEXT)
        style.configure("Small.Panel.TLabel", background=self.PANEL, foreground=self.MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 25, "bold"))
        style.configure("Subtitle.TLabel", background=self.BG, foreground=self.MUTED, font=("Segoe UI", 11))
        style.configure("TEntry", padding=6, borderwidth=0)
        style.configure(
            "TCombobox",
            padding=5,
            fieldbackground=self.PANEL_SOFT,
            background=self.PANEL_SOFT,
            foreground=self.TEXT,
            arrowcolor=self.TEXT,
            bordercolor=self.PANEL_SOFT,
            lightcolor=self.PANEL_SOFT,
            darkcolor=self.PANEL_SOFT,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.PANEL_SOFT)],
            foreground=[("readonly", self.TEXT)],
            selectbackground=[("readonly", self.PANEL_SOFT)],
            selectforeground=[("readonly", self.TEXT)],
        )
        self.root.option_add("*TCombobox*Listbox.background", self.PANEL_SOFT)
        self.root.option_add("*TCombobox*Listbox.foreground", self.TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", self.ACCENT_DARK)
        self.root.option_add("*TCombobox*Listbox.selectForeground", self.TEXT)
        style.configure("TButton", background=self.PANEL_SOFT, foreground=self.TEXT, padding=(12, 7), borderwidth=0)
        style.map("TButton", background=[("active", self.ACCENT_DARK)])
        style.configure("Accent.TButton", background=self.ACCENT, foreground="#0b1118")
        style.map("Accent.TButton", background=[("active", "#74bee8")])
        style.configure("Small.TButton", padding=(8, 4), font=("Segoe UI", 9))
        style.configure("TLabelframe", background=self.PANEL, foreground=self.TEXT, bordercolor=self.PANEL_SOFT)
        style.configure("TLabelframe.Label", background=self.PANEL, foreground=self.MUTED)

    def _clear_root(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def _show_auth_screen(self) -> None:
        self._clear_root()
        shell = ttk.Frame(self.root)
        shell.grid(row=0, column=0, sticky="nsew", padx=34, pady=28)
        shell.columnconfigure(0, weight=3)
        shell.columnconfigure(1, weight=2)
        shell.rowconfigure(0, weight=1)

        welcome = ttk.Frame(shell)
        welcome.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
        welcome.columnconfigure(0, weight=1)
        ttk.Label(welcome, text="Welcome home", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(40, 8))
        ttk.Label(
            welcome,
            text="Control the doll-house lights, gadgets, sensors, and cooling from one encrypted desktop client.",
            style="Subtitle.TLabel",
            wraplength=420,
        ).grid(row=1, column=0, sticky="w")
        ttk.Label(
            welcome,
            textvariable=self.status_var,
            style="Muted.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(28, 0))

        auth_panel = ttk.Frame(shell, style="Panel.TFrame", padding=22)
        auth_panel.grid(row=0, column=1, sticky="nsew")
        auth_panel.columnconfigure(0, weight=1)
        auth_panel.columnconfigure(1, weight=1)

        ttk.Label(auth_panel, text="Sign in", style="Panel.TLabel", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(auth_panel, text="sign up", style="Small.TButton", command=self._show_signup_dialog).grid(
            row=0, column=1, sticky="e"
        )

        ttk.Label(auth_panel, text="Profile", style="Small.Panel.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 3))
        profile = ttk.Combobox(
            auth_panel,
            textvariable=self.profile_var,
            values=list(self.connection_profiles.keys()),
            state="readonly",
        )
        profile.grid(row=2, column=0, columnspan=2, sticky="ew")
        profile.bind("<<ComboboxSelected>>", self._apply_connection_profile)
        connection = ttk.Frame(auth_panel, style="Panel.TFrame")
        connection.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        connection.columnconfigure(0, weight=3)
        connection.columnconfigure(1, weight=1)
        ttk.Label(connection, text="Server IP", style="Small.Panel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(connection, text="Port", style="Small.Panel.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Entry(connection, textvariable=self.host_var).grid(row=1, column=0, sticky="ew")
        ttk.Entry(connection, textvariable=self.port_var).grid(row=1, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(auth_panel, text="Find Server", command=self.find_server).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self._entry(auth_panel, "Username", self.username_var, 5)
        self._entry(auth_panel, "Password", self.password_var, 7, show="*")
        ttk.Button(auth_panel, text="Connect and sign in", style="Accent.TButton", command=self.connect_and_login).grid(
            row=9, column=0, columnspan=2, sticky="ew", pady=(18, 4)
        )

    def _entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, show: str = "") -> ttk.Entry:
        ttk.Label(parent, text=label, style="Small.Panel.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 3))
        entry = ttk.Entry(parent, textvariable=variable, show=show)
        entry.grid(row=row + 1, column=0, columnspan=2, sticky="ew")
        return entry

    def _apply_connection_profile(self, _event=None) -> None:
        profile = self.profile_var.get()
        if profile == "Custom IP":
            return
        if profile == "Auto Discover":
            self.find_server()
            return
        host, port = self.connection_profiles[profile]
        self.host_var.set(host)
        self.port_var.set(port)

    def find_server(self) -> None:
        self._run_async(self._find_server_sync)

    def _find_server_sync(self) -> None:
        self.root.after(0, lambda: self.status_var.set("Searching for smart-home server..."))
        servers = discover_servers(DISCOVERY_PORT, timeout=2.0)
        if not servers:
            self.root.after(0, lambda: self.status_var.set("No server found automatically"))
            return
        server = servers[0]
        self.root.after(0, lambda: self._apply_discovered_server(server.host, server.port, server.name))

    def _apply_discovered_server(self, host: str, port: int, name: str) -> None:
        self.host_var.set(host)
        self.port_var.set(str(port))
        self.profile_var.set("Auto Discover")
        self.status_var.set(f"Found {name} at {host}:{port}")

    def _show_signup_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Sign up")
        dialog.configure(bg=self.BG)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, style="Panel.TFrame", padding=18)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Create account", style="Panel.TLabel", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Label(frame, text="New accounts are saved with hashed passwords.", style="Small.Panel.TLabel").grid(
            row=1, column=0, sticky="w", pady=(0, 8)
        )
        self._entry(frame, "Username", self.signup_username_var, 2)
        self._entry(frame, "Password", self.signup_password_var, 4, show="*")
        ttk.Label(frame, text="Role", style="Small.Panel.TLabel").grid(row=6, column=0, sticky="w", pady=(12, 3))
        role = ttk.Combobox(frame, textvariable=self.signup_role_var, values=["guest", "child"], state="readonly")
        role.grid(row=7, column=0, sticky="ew")
        ttk.Button(frame, text="Create account", style="Accent.TButton", command=lambda: self.sign_up(dialog)).grid(
            row=8, column=0, sticky="ew", pady=(16, 0)
        )

    def _show_dashboard(self) -> None:
        self._stop_live_updates()
        self._clear_root()
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, padding=(16, 12))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ttk.Label(top, text="Smart Home Control", style="Title.TLabel", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Button(top, text="Refresh", command=self.refresh_devices).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(top, text="Demo Reset", command=self.demo_reset).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(top, text="Disconnect", command=self.disconnect).grid(row=0, column=3, padx=(8, 0))

        main = ttk.Frame(self.root, padding=(16, 4, 16, 12))
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=2)
        main.columnconfigure(1, weight=3)
        main.columnconfigure(2, weight=2)
        main.rowconfigure(0, weight=1)

        list_panel = ttk.Frame(main, style="Panel.TFrame", padding=12)
        list_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        list_panel.rowconfigure(1, weight=1)
        list_panel.columnconfigure(0, weight=1)
        ttk.Label(list_panel, text="Devices", style="Panel.TLabel", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        self.device_list = tk.Listbox(
            list_panel,
            height=14,
            bg=self.PANEL_SOFT,
            fg=self.TEXT,
            selectbackground=self.ACCENT_DARK,
            selectforeground=self.TEXT,
            highlightthickness=0,
            borderwidth=0,
            activestyle="none",
        )
        self.device_list.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.device_list.bind("<<ListboxSelect>>", self.on_device_selected)

        details = ttk.Frame(main, style="Panel.TFrame", padding=12)
        details.grid(row=0, column=1, sticky="nsew")
        for column in range(4):
            details.columnconfigure(column, weight=1)
        details.rowconfigure(1, weight=1)
        ttk.Label(details, text="Device", style="Panel.TLabel", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        self.device_icon_canvas = tk.Canvas(
            details,
            width=86,
            height=64,
            bg=self.PANEL,
            highlightthickness=0,
            borderwidth=0,
        )
        self.device_icon_canvas.grid(row=0, column=3, sticky="e")
        self.details_text = tk.Text(
            details,
            height=10,
            state="disabled",
            bg=self.PANEL_SOFT,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            highlightthickness=0,
            borderwidth=0,
            padx=10,
            pady=10,
        )
        self.details_text.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=(8, 10))

        self.turn_on_button = tk.Button(
            details,
            text="Turn On",
            command=lambda: self.perform_action("TURN_ON"),
            bg=self.PANEL_SOFT,
            fg=self.TEXT,
            activebackground="#2f9e67",
            activeforeground=self.TEXT,
            relief="flat",
            padx=10,
            pady=7,
        )
        self.turn_on_button.grid(row=2, column=0, sticky="ew", padx=4, pady=4)
        self.turn_off_button = tk.Button(
            details,
            text="Turn Off",
            command=lambda: self.perform_action("TURN_OFF"),
            bg=self.PANEL_SOFT,
            fg=self.TEXT,
            activebackground="#b84848",
            activeforeground=self.TEXT,
            relief="flat",
            padx=10,
            pady=7,
        )
        self.turn_off_button.grid(row=2, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(details, text="Status", command=self.refresh_selected_status).grid(row=2, column=2, sticky="ew", padx=4, pady=4)
        ttk.Entry(details, textvariable=self.value_var).grid(row=3, column=0, sticky="ew", padx=4, pady=4)
        ttk.Button(details, text="Set Brightness", command=lambda: self.perform_action("SET_BRIGHTNESS", self.value_var.get())).grid(row=3, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(details, text="Set Temp", command=lambda: self.perform_action("SET_TEMPERATURE", self.value_var.get())).grid(row=3, column=2, sticky="ew", padx=4, pady=4)
        ttk.Button(details, text="Set Position", command=lambda: self.perform_action("SET_POSITION", self.value_var.get())).grid(row=3, column=3, sticky="ew", padx=4, pady=4)

        if self.current_user and self.current_user.get("role") == "admin":
            self._build_admin_panel(main)

        ttk.Label(self.root, textvariable=self.status_var, style="Muted.TLabel").grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        self._start_live_updates()

    def _build_admin_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        panel.grid(row=0, column=2, sticky="nsew", padx=(12, 0))
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="Users", style="Panel.TLabel", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        self.user_list = tk.Listbox(
            panel,
            height=10,
            bg=self.PANEL_SOFT,
            fg=self.TEXT,
            selectbackground=self.ACCENT_DARK,
            selectforeground=self.TEXT,
            highlightthickness=0,
            borderwidth=0,
            activestyle="none",
            exportselection=False,
        )
        self.user_list.grid(row=1, column=0, sticky="nsew", pady=(8, 8))
        self.user_list.bind("<<ListboxSelect>>", self.on_user_selected)

        role_var = tk.StringVar(value="guest")
        role = ttk.Combobox(panel, textvariable=role_var, values=["admin", "parent", "child", "guest"], state="readonly")
        role.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(panel, text="Change role", command=lambda: self.update_selected_user_role(role_var.get())).grid(
            row=3,
            column=0,
            sticky="ew",
        )
        ttk.Button(panel, text="Add user", command=self.show_admin_add_user_dialog).grid(row=4, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(panel, text="Delete user", command=self.delete_selected_user).grid(row=5, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(panel, text="Refresh users", command=self.refresh_users).grid(row=6, column=0, sticky="ew", pady=(8, 0))
        self.refresh_users()

    def connect_and_login(self) -> None:
        self._run_async(self._connect_and_login)

    def _connect_and_login(self) -> None:
        try:
            self._open_client()
            response = self.client.login(self.username_var.get(), self.password_var.get()) if self.client else {}
            if response.get("status") != "ok":
                raise RuntimeError(response.get("message", "Login failed"))
            self.current_user = response.get("data")
            self.root.after(0, self._show_dashboard)
            self.root.after(0, lambda: self.status_var.set(f"Signed in as {self.username_var.get()}"))
            self._refresh_devices_sync(silent=True)
        except Exception as exc:
            self._close_client_quietly()
            self._show_error("Connection error", exc)
            self.root.after(0, lambda: self.status_var.set("Not connected"))

    def sign_up(self, dialog: tk.Toplevel) -> None:
        self._run_async(lambda: self._sign_up_sync(dialog))

    def _sign_up_sync(self, dialog: tk.Toplevel) -> None:
        try:
            self._open_client()
            ping = self.client.ping() if self.client else {}
            if ping.get("status") != "ok" or not ping.get("data", {}).get("supports_signup"):
                raise RuntimeError("This server does not support sign up yet. Stop the server and start it again.")
            response = self.client.sign_up(
                self.signup_username_var.get(),
                self.signup_password_var.get(),
                self.signup_role_var.get(),
            ) if self.client else {}
            if response.get("status") != "ok":
                raise RuntimeError(response.get("message", "Sign up failed"))
            self.username_var.set(self.signup_username_var.get())
            self.password_var.set(self.signup_password_var.get())
            self.signup_password_var.set("")
            self.root.after(0, dialog.destroy)
            self.root.after(0, lambda: messagebox.showinfo("Sign up", "Account created. You can sign in now."))
        except Exception as exc:
            self._show_error("Sign up error", exc)
        finally:
            self._close_client_quietly()

    def _open_client(self) -> None:
        self._close_client_quietly()
        self.client = SmartHomeClient(self.host_var.get(), int(self.port_var.get()))
        self.client.connect()

    def refresh_devices(self) -> None:
        self._run_async(lambda: self._refresh_devices_sync(silent=False))

    def demo_reset(self) -> None:
        if not messagebox.askyesno("Demo Reset", "Turn devices off and reset servo positions?"):
            return
        self._run_async(self._demo_reset_sync)

    def _demo_reset_sync(self) -> None:
        if not self.client:
            raise RuntimeError("Not connected")
        response = self.client.demo_reset()
        if response.get("status") != "ok":
            raise RuntimeError(response.get("message", "Demo reset failed"))
        self._refresh_devices_sync(silent=True)
        self.root.after(0, lambda: self.status_var.set("Demo reset complete"))

    def refresh_users(self) -> None:
        self._run_async(self._refresh_users_sync)

    def _refresh_users_sync(self) -> None:
        if not self.client:
            raise RuntimeError("Not connected")
        users = self.client.list_users()
        self.root.after(0, lambda: self._show_users(users))

    def _show_users(self, users: List[Dict[str, str]]) -> None:
        self.users = users
        if not self.user_list:
            return
        self.user_list.delete(0, tk.END)
        selected_index = None
        for index, user in enumerate(users):
            self.user_list.insert(tk.END, f"{user['username']} ({user['role']})")
            if user["username"] == self.selected_username:
                selected_index = index
        if selected_index is not None:
            self.user_list.selection_set(selected_index)
            self.user_list.activate(selected_index)

    def on_user_selected(self, _event=None) -> None:
        if not self.user_list:
            return
        selection = self.user_list.curselection()
        if selection:
            self.selected_username = self.users[selection[0]]["username"]

    def update_selected_user_role(self, role: str) -> None:
        if not self.user_list:
            return
        selection = self.user_list.curselection()
        if selection:
            self.selected_username = self.users[selection[0]]["username"]
        if not self.selected_username:
            messagebox.showinfo("Users", "Select a user first")
            return
        admin_password = self._ask_admin_password("Confirm role change")
        if not admin_password:
            return
        self._run_async(lambda: self._update_user_role_sync(self.selected_username, role, admin_password))

    def _update_user_role_sync(self, username: str, role: str, admin_password: str) -> None:
        if not self.client:
            raise RuntimeError("Not connected")
        response = self.client.update_role(username, role, admin_password)
        if response.get("status") != "ok":
            raise RuntimeError(response.get("message", "Unable to update role"))
        self._refresh_users_sync()
        self.root.after(0, lambda: self.status_var.set(f"Updated {username} to {role}"))

    def show_admin_add_user_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Add user")
        dialog.configure(bg=self.BG)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, style="Panel.TFrame", padding=18)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        username_var = tk.StringVar()
        password_var = tk.StringVar()
        role_var = tk.StringVar(value="guest")

        ttk.Label(frame, text="Add user", style="Panel.TLabel", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, sticky="w")
        self._entry(frame, "Username", username_var, 1)
        self._entry(frame, "Password", password_var, 3, show="*")
        ttk.Label(frame, text="Role", style="Small.Panel.TLabel").grid(row=5, column=0, sticky="w", pady=(12, 3))
        role = ttk.Combobox(frame, textvariable=role_var, values=["admin", "parent", "child", "guest"], state="readonly")
        role.grid(row=6, column=0, sticky="ew")
        ttk.Button(
            frame,
            text="Create user",
            style="Accent.TButton",
            command=lambda: self.add_user_from_admin_dialog(dialog, username_var.get(), password_var.get(), role_var.get()),
        ).grid(row=7, column=0, sticky="ew", pady=(16, 0))

    def add_user_from_admin_dialog(self, dialog: tk.Toplevel, username: str, password: str, role: str) -> None:
        admin_password = self._ask_admin_password("Confirm new user")
        if not admin_password:
            return
        self._run_async(lambda: self._add_user_sync(dialog, username, password, role, admin_password))

    def _add_user_sync(self, dialog: tk.Toplevel, username: str, password: str, role: str, admin_password: str) -> None:
        if not self.client:
            raise RuntimeError("Not connected")
        response = self.client.create_user(username, password, role, admin_password)
        if response.get("status") != "ok":
            raise RuntimeError(response.get("message", "Unable to create user"))
        self.selected_username = username
        self._refresh_users_sync()
        self.root.after(0, dialog.destroy)
        self.root.after(0, lambda: self.status_var.set(f"Created user {username}"))

    def delete_selected_user(self) -> None:
        if not self.user_list:
            return
        selection = self.user_list.curselection()
        if selection:
            self.selected_username = self.users[selection[0]]["username"]
        if not self.selected_username:
            messagebox.showinfo("Users", "Select a user first")
            return
        if not messagebox.askyesno("Delete user", f"Delete user '{self.selected_username}'?"):
            return
        admin_password = self._ask_admin_password("Confirm delete")
        if not admin_password:
            return
        self._run_async(lambda: self._delete_user_sync(self.selected_username, admin_password))

    def _delete_user_sync(self, username: str, admin_password: str) -> None:
        if not self.client:
            raise RuntimeError("Not connected")
        response = self.client.delete_user(username, admin_password)
        if response.get("status") != "ok":
            raise RuntimeError(response.get("message", "Unable to delete user"))
        self.selected_username = None
        self._refresh_users_sync()
        self.root.after(0, lambda: self.status_var.set(f"Deleted user {username}"))

    def _ask_admin_password(self, title: str) -> Optional[str]:
        return simpledialog.askstring(title, "Enter your admin password:", show="*", parent=self.root)

    def _refresh_devices_sync(self, silent: bool = False) -> None:
        if not self.client:
            raise RuntimeError("Not connected")
        devices = self.client.list_devices()
        self.root.after(0, lambda: self._show_devices(devices, silent=silent))

    def _show_devices(self, devices: List[Dict[str, Any]], silent: bool = False) -> None:
        selected_id = self.selected_device.get("device_id") if self.selected_device else None
        self.devices = devices
        self.visible_device_indexes = []
        self.device_list.delete(0, tk.END)
        selected_index = None
        current_room = None
        for index, device in enumerate(devices):
            room = device.get("room", "General")
            if room != current_room:
                current_room = room
                self.device_list.insert(tk.END, f"== {room} ==")
                self.visible_device_indexes.append(-1)
            self.device_list.insert(tk.END, self._device_list_label(device))
            self.visible_device_indexes.append(index)
            if device.get("device_id") == selected_id:
                selected_index = len(self.visible_device_indexes) - 1

        if selected_index is not None:
            self.device_list.selection_set(selected_index)
            self.device_list.activate(selected_index)
            device_index = self.visible_device_indexes[selected_index]
            self.selected_device = devices[device_index]
            self._set_details(self.selected_device)
        elif self.selected_device:
            self.selected_device = None

        if not silent:
            self.status_var.set(f"{len(devices)} devices loaded")

    def on_device_selected(self, _event=None) -> None:
        selection = self.device_list.curselection()
        if not selection:
            return
        device_index = self.visible_device_indexes[selection[0]]
        if device_index < 0:
            self.device_list.selection_clear(selection[0])
            return
        self.selected_device = self.devices[device_index]
        self._set_details(self.selected_device)

    def refresh_selected_status(self) -> None:
        if not self.selected_device:
            messagebox.showinfo("Device", "Select a device first")
            return
        self._run_async(lambda: self._refresh_status_sync(self.selected_device["device_id"]))

    def _refresh_status_sync(self, device_id: str) -> None:
        if not self.client:
            raise RuntimeError("Not connected")
        response = self.client.get_status(device_id)
        self._handle_action_response(response)

    def perform_action(self, command: str, value: Any = None) -> None:
        if not self.selected_device:
            messagebox.showinfo("Device", "Select a device first")
            return
        self._run_async(lambda: self._perform_action_sync(command, self.selected_device["device_id"], value))

    def _perform_action_sync(self, command: str, device_id: str, value: Any = None) -> None:
        if not self.client:
            raise RuntimeError("Not connected")
        response = self.client.control_device(command, device_id, value)
        self._handle_action_response(response)

    def _handle_action_response(self, response: Dict[str, Any]) -> None:
        def update() -> None:
            if response.get("status") == "ok":
                data = response.get("data")
                if isinstance(data, dict):
                    self.selected_device = data
                    self._replace_device(data)
                    self._set_details(data)
                self.status_var.set(response.get("message", "OK"))
            else:
                messagebox.showerror(response.get("code", "Error"), response.get("message", "Command failed"))
                self.status_var.set(response.get("message", "Command failed"))

        self.root.after(0, update)

    def _set_details(self, device: Dict[str, Any]) -> None:
        lines = [f"{key}: {value}" for key, value in device.items()]
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, "\n".join(lines))
        self.details_text.configure(state="disabled")
        self._draw_device_icon(device)
        self._update_power_buttons(device)

    def _replace_device(self, updated_device: Dict[str, Any]) -> None:
        for index, device in enumerate(self.devices):
            if device.get("device_id") == updated_device.get("device_id"):
                self.devices[index] = updated_device
                if hasattr(self, "device_list"):
                    self._show_devices(self.devices, silent=True)
                return

    def _device_list_label(self, device: Dict[str, Any]) -> str:
        marker = self._device_marker(device)
        state = device.get("state", "unknown")
        extras = []
        if "brightness" in device:
            extras.append(f"{device['brightness']}%")
        if "position" in device:
            extras.append(f"{device['position']} deg")
        if device.get("online") is True:
            extras.append("online")
        elif device.get("type", "").startswith("esp_"):
            extras.append("not discovered")
        detail = f" - {state}"
        if extras:
            detail += f" ({', '.join(str(item) for item in extras)})"
        return f"  {marker} {device['name']}{detail}"

    def _device_marker(self, device: Dict[str, Any]) -> str:
        device_type = device.get("type", "")
        if device_type in {"led_strip", "esp_led"}:
            return "[LED]"
        if device_type == "esp_servo":
            return "[SERVO]"
        if device_type == "esp_relay":
            return "[RELAY]"
        if device_type == "mini_fridge":
            return "[COLD]"
        if device_type in {"fan", "esp_fan"}:
            return "[FAN]"
        if device_type == "sensor":
            return "[SENSOR]"
        return "[DEVICE]"

    def _update_power_buttons(self, device: Dict[str, Any]) -> None:
        if not self.turn_on_button or not self.turn_off_button:
            return
        is_on = device.get("state") == "on"
        self.turn_on_button.configure(bg="#2f9e67" if is_on else self.PANEL_SOFT)
        self.turn_off_button.configure(bg=self.PANEL_SOFT if is_on else "#b84848")

    def _draw_device_icon(self, device: Dict[str, Any]) -> None:
        canvas = self.device_icon_canvas
        if not canvas:
            return
        canvas.delete("all")
        device_type = device.get("type", "")
        is_on = device.get("state") == "on"
        glow = "#5fd38d" if is_on else "#e06262"
        line = "#d7e2ee"
        muted = "#768399"

        if device_type == "led_strip":
            canvas.create_line(12, 34, 74, 34, fill=line, width=4, capstyle=tk.ROUND)
            for x in (18, 32, 46, 60, 72):
                canvas.create_oval(x - 5, 24, x + 5, 34, fill=glow, outline="")
                canvas.create_line(x, 36, x, 44, fill=muted, width=2)
        elif device_type == "mini_fridge":
            canvas.create_rectangle(24, 8, 62, 58, fill="#e8eef5", outline=line, width=2)
            canvas.create_line(24, 25, 62, 25, fill=muted, width=2)
            canvas.create_rectangle(53, 31, 57, 45, fill=muted, outline="")
            canvas.create_oval(33, 35, 45, 47, fill="#75c7f0", outline="")
        elif device_type in {"fan", "esp_fan"}:
            canvas.create_oval(22, 10, 64, 52, outline=line, width=2)
            canvas.create_oval(39, 27, 47, 35, fill=glow, outline="")
            canvas.create_polygon(43, 30, 25, 20, 35, 32, fill=muted, outline="")
            canvas.create_polygon(44, 32, 61, 43, 50, 31, fill=muted, outline="")
            canvas.create_polygon(44, 31, 48, 12, 39, 25, fill=muted, outline="")
        elif device_type == "sensor":
            canvas.create_rectangle(27, 12, 59, 52, fill="#dce5ee", outline=line, width=2)
            canvas.create_oval(37, 22, 49, 34, fill=glow, outline="")
            canvas.create_arc(18, 14, 72, 56, start=300, extent=120, style=tk.ARC, outline=muted, width=2)
        elif device_type == "esp_servo":
            canvas.create_rectangle(24, 24, 58, 48, fill="#dce5ee", outline=line, width=2)
            canvas.create_oval(35, 28, 47, 40, fill=glow, outline="")
            canvas.create_line(41, 34, 67, 16, fill=line, width=4, capstyle=tk.ROUND)
            canvas.create_oval(63, 12, 71, 20, fill=muted, outline="")
        else:
            canvas.create_rectangle(22, 18, 64, 50, fill="#dce5ee", outline=line, width=2)
            canvas.create_oval(38, 28, 48, 38, fill=glow, outline="")

    def disconnect(self) -> None:
        self._stop_live_updates()
        self._close_client_quietly()
        self.current_user = None
        self.status_var.set("Not connected")
        self._show_auth_screen()

    def _close_client_quietly(self) -> None:
        self._stop_live_updates()
        if self.client:
            self.client.close()
            self.client = None

    def _start_live_updates(self) -> None:
        if self.live_updates_running:
            return
        self.live_updates_running = True
        threading.Thread(target=self._live_update_loop, daemon=True).start()

    def _stop_live_updates(self) -> None:
        self.live_updates_running = False
        if self.update_client:
            self.update_client.abort()
            self.update_client = None

    def _live_update_loop(self) -> None:
        try:
            self.update_client = SmartHomeClient(self.host_var.get(), int(self.port_var.get()), timeout=10.0)
            self.update_client.connect()
            login = self.update_client.login(self.username_var.get(), self.password_var.get())
            if login.get("status") != "ok":
                raise RuntimeError(login.get("message", "Live update login failed"))

            while self.live_updates_running and self.update_client:
                response = self.update_client.get_updates(self.device_revision, timeout=25.0)
                if response.get("status") != "ok":
                    raise RuntimeError(response.get("message", "Live update failed"))
                data = response.get("data", {})
                self.device_revision = int(data.get("revision", self.device_revision))
                if data.get("changed"):
                    devices = data.get("devices", [])
                    self.root.after(0, lambda devices=devices: self._show_devices(devices, silent=True))
        except Exception as exc:
            if self.live_updates_running:
                self.root.after(0, lambda error_text=str(exc): self.status_var.set(f"Live sync paused: {error_text}"))
        finally:
            if self.update_client:
                self.update_client.abort()
                self.update_client = None

    def _show_error(self, title: str, exc: Exception) -> None:
        self.root.after(0, lambda error_text=str(exc): messagebox.showerror(title, error_text))

    def _run_async(self, target: Callable[[], None]) -> None:
        def wrapped() -> None:
            try:
                target()
            except Exception as exc:
                self._show_error("Error", exc)

        threading.Thread(target=wrapped, daemon=True).start()
