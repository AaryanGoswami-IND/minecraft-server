"""
Minecraft Server Manager v3
Web-style UI with sidebar navigation and tabbed content
"""

import customtkinter as ctk
import subprocess
import threading
import queue
import os
import re
from datetime import datetime

# Configure appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Color scheme matching web app
COLORS = {
    "bg_primary": "#0d0d0d",
    "bg_secondary": "#141414",
    "bg_tertiary": "#1a1a1a",
    "bg_card": "#1e1e1e",
    "bg_hover": "#252525",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0a0",
    "text_muted": "#666666",
    "accent_green": "#22c55e",
    "accent_red": "#ef4444",
    "accent_yellow": "#eab308",
    "accent_blue": "#3b82f6",
    "accent_purple": "#a855f7",
    "border": "#2a2a2a",
}


class MinecraftServerManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("Minecraft Server Manager")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        # Server configuration
        self.server_dir = os.path.dirname(os.path.abspath(__file__))
        self.server_jar = "server.jar"
        self.java_args = ["-Xms1G", "-Xmx2G", "-XX:+UseG1GC"]
        
        # Server state
        self.server_process = None
        self.server_status = "offline"
        self.output_queue = queue.Queue()
        self.player_count = 0
        self.max_players = 20
        self.online_players = []
        self.recent_activity = []
        
        # Playit.gg state
        self.playit_process = None
        self.playit_running = False
        self.playit_exe = os.path.join(self.server_dir, "playit.exe")
        
        # Backup state
        self.backup_interval = 600000  # 10 minutes in ms
        self.last_backup = None
        
        # Build UI
        self.create_ui()
        
        # Start output reader
        self.after(100, self.process_output_queue)
        
        # Start backup timer
        self.after(self.backup_interval, self.auto_backup)
    
    def create_ui(self):
        """Build the web-style UI layout"""
        
        # Configure main window colors
        self.configure(fg_color=COLORS["bg_primary"])
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ===== Sidebar =====
        self.create_sidebar()
        
        # ===== Main Content =====
        self.main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_primary"])
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header
        self.create_header()
        
        # Tab Content Container
        self.content_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 24))
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)
        
        # Create all tabs
        self.create_console_tab()
        self.create_players_tab()
        self.create_settings_tab()
        self.create_backup_tab()
        
        # Show console tab by default
        self.show_tab("console")
    
    def create_sidebar(self):
        """Create the sidebar with navigation"""
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=COLORS["bg_secondary"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)
        self.sidebar.grid_propagate(False)
        
        # Logo section - compact
        self.logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.logo_frame.grid(row=0, column=0, padx=16, pady=(16, 12), sticky="ew")
        
        self.logo_icon = ctk.CTkLabel(
            self.logo_frame,
            text="⛏️",
            font=ctk.CTkFont(size=24)
        )
        self.logo_icon.grid(row=0, column=0, padx=(0, 8))
        
        self.logo_text = ctk.CTkLabel(
            self.logo_frame,
            text="MC Server",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent_green"]
        )
        self.logo_text.grid(row=0, column=1)
        
        # Separator
        sep1 = ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["border"])
        sep1.grid(row=1, column=0, sticky="ew", padx=0)
        
        # Navigation - compact buttons
        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=12)
        
        self.nav_buttons = {}
        nav_items = [
            ("console", "📟", "Console"),
            ("players", "👥", "Players"),
            ("settings", "⚙️", "Settings"),
            ("backup", "💾", "Backup"),
        ]
        
        for i, (tab_id, icon, text) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.nav_frame,
                text=f"{icon}  {text}",
                font=ctk.CTkFont(size=13),
                height=36,
                anchor="w",
                fg_color="transparent",
                text_color=COLORS["text_secondary"],
                hover_color=COLORS["bg_hover"],
                corner_radius=6,
                command=lambda t=tab_id: self.show_tab(t)
            )
            btn.pack(fill="x", pady=1)
            self.nav_buttons[tab_id] = btn
        
        # Combined status section - compact
        self.info_section = ctk.CTkFrame(self.sidebar, fg_color=COLORS["bg_tertiary"], corner_radius=8)
        self.info_section.grid(row=3, column=0, sticky="sew", padx=10, pady=10)
        
        # Server status row
        server_row = ctk.CTkFrame(self.info_section, fg_color="transparent")
        server_row.pack(fill="x", padx=12, pady=(10, 4))
        
        ctk.CTkLabel(
            server_row,
            text="Server",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        ).pack(side="left")
        
        self.status_indicator = ctk.CTkLabel(
            server_row,
            text="●",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["accent_red"]
        )
        self.status_indicator.pack(side="right", padx=(0, 4))
        
        self.status_label = ctk.CTkLabel(
            server_row,
            text="Offline",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.status_label.pack(side="right")
        
        # Playit status row
        playit_row = ctk.CTkFrame(self.info_section, fg_color="transparent")
        playit_row.pack(fill="x", padx=12, pady=(0, 4))
        
        ctk.CTkLabel(
            playit_row,
            text="Tunnel",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        ).pack(side="left")
        
        self.playit_indicator = ctk.CTkLabel(
            playit_row,
            text="●",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["accent_red"]
        )
        self.playit_indicator.pack(side="right", padx=(0, 4))
        
        self.playit_status = ctk.CTkLabel(
            playit_row,
            text="Offline",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.playit_status.pack(side="right")
        
        # Tunnel address
        self.playit_address_label = ctk.CTkLabel(
            self.info_section,
            text="",
            font=ctk.CTkFont(size=9),
            text_color=COLORS["accent_green"],
            wraplength=160
        )
        self.playit_address_label.pack(fill="x", padx=12, pady=(0, 10))
        
        self.playit_address = ""
    
    def create_header(self):
        """Create the header with title and control buttons"""
        self.header = ctk.CTkFrame(self.main_frame, fg_color=COLORS["bg_secondary"], height=60, corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)
        self.header.grid_propagate(False)
        
        # Title
        self.header_title = ctk.CTkLabel(
            self.header,
            text="Minecraft Server",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        self.header_title.grid(row=0, column=0, padx=24, pady=16, sticky="w")
        
        # Control buttons frame
        self.controls_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.controls_frame.grid(row=0, column=1, padx=24, pady=16, sticky="e")
        
        # Start button
        self.start_btn = ctk.CTkButton(
            self.controls_frame,
            text="▶ Start",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=85,
            height=32,
            fg_color=COLORS["accent_green"],
            hover_color="#16a34a",
            text_color="#ffffff",
            corner_radius=6,
            command=self.start_server
        )
        self.start_btn.pack(side="left", padx=3)
        
        # Restart button
        self.restart_btn = ctk.CTkButton(
            self.controls_frame,
            text="🔄 Restart",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=95,
            height=32,
            fg_color=COLORS["accent_yellow"],
            hover_color="#ca8a04",
            text_color="#000000",
            corner_radius=6,
            command=self.restart_server,
            state="disabled"
        )
        self.restart_btn.pack(side="left", padx=3)
        
        # Stop button
        self.stop_btn = ctk.CTkButton(
            self.controls_frame,
            text="⏹ Stop",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=85,
            height=32,
            fg_color=COLORS["accent_red"],
            hover_color="#dc2626",
            text_color="#ffffff",
            corner_radius=6,
            command=self.stop_server,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=3)
    
    def create_console_tab(self):
        """Create the Console tab content"""
        self.console_tab = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.console_tab.grid_columnconfigure(0, weight=1)
        self.console_tab.grid_rowconfigure(0, weight=1)
        
        # Console container (matches web app style)
        self.console_container = ctk.CTkFrame(self.console_tab, fg_color=COLORS["bg_card"], corner_radius=12)
        self.console_container.grid(row=0, column=0, sticky="nsew")
        self.console_container.grid_columnconfigure(0, weight=1)
        self.console_container.grid_rowconfigure(1, weight=1)
        
        # Console header
        self.console_header = ctk.CTkFrame(self.console_container, fg_color=COLORS["bg_tertiary"], corner_radius=0)
        self.console_header.grid(row=0, column=0, sticky="ew")
        self.console_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            self.console_header,
            text="Server Console",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=16, pady=12, sticky="w")
        
        self.clear_btn = ctk.CTkButton(
            self.console_header,
            text="Clear",
            width=60,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_hover"],
            hover_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_secondary"],
            corner_radius=6,
            command=self.clear_console
        )
        self.clear_btn.grid(row=0, column=1, padx=16, pady=12, sticky="e")
        
        # Console output
        self.console = ctk.CTkTextbox(
            self.console_container,
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color=COLORS["bg_primary"],
            text_color="#e0e0e0",
            corner_radius=0
        )
        self.console.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.console.configure(state="disabled")
        
        # Console input area
        self.console_input_frame = ctk.CTkFrame(self.console_container, fg_color=COLORS["bg_tertiary"], corner_radius=0)
        self.console_input_frame.grid(row=2, column=0, sticky="ew")
        self.console_input_frame.grid_columnconfigure(1, weight=1)
        
        self.prompt_label = ctk.CTkLabel(
            self.console_input_frame,
            text=">",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLORS["accent_green"]
        )
        self.prompt_label.grid(row=0, column=0, padx=(16, 8), pady=12)
        
        self.command_input = ctk.CTkEntry(
            self.console_input_frame,
            font=ctk.CTkFont(family="Consolas", size=13),
            placeholder_text="Enter command...",
            fg_color=COLORS["bg_primary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=38,
            corner_radius=8
        )
        self.command_input.grid(row=0, column=1, sticky="ew", pady=12)
        self.command_input.bind("<Return>", self.send_command)
        
        self.send_btn = ctk.CTkButton(
            self.console_input_frame,
            text="Send",
            width=80,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent_blue"],
            hover_color="#2563eb",
            corner_radius=8,
            command=lambda: self.send_command(None)
        )
        self.send_btn.grid(row=0, column=2, padx=16, pady=12)
        
        # Initial console message
        self.log_message("[Manager] Server Manager ready", "info")
        self.log_message(f"[Manager] Server: {self.server_dir}", "info")
    
    def create_players_tab(self):
        """Create the Players tab content"""
        self.players_tab = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.players_tab.grid_columnconfigure(0, weight=1)
        self.players_tab.grid_rowconfigure(0, weight=1)
        
        # Players card
        self.players_card = ctk.CTkFrame(self.players_tab, fg_color=COLORS["bg_card"], corner_radius=12)
        self.players_card.grid(row=0, column=0, sticky="nsew")
        self.players_card.grid_columnconfigure(0, weight=1)
        self.players_card.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            self.players_card,
            text="Online Players",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, padx=24, pady=(24, 8), sticky="w")
        
        self.player_count_label = ctk.CTkLabel(
            self.players_card,
            text="Player list will appear when server is running.",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_muted"]
        )
        self.player_count_label.grid(row=0, column=0, padx=24, pady=(24, 8), sticky="e")
        
        # Players list
        self.players_list = ctk.CTkScrollableFrame(
            self.players_card,
            fg_color="transparent"
        )
        self.players_list.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 16))
        
        self.no_players_label = ctk.CTkLabel(
            self.players_list,
            text="No players online",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_muted"]
        )
        self.no_players_label.pack(pady=20)
    
    def create_settings_tab(self):
        """Create the Settings tab content with editable config files"""
        self.settings_tab = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.settings_tab.grid_columnconfigure(0, weight=1)
        self.settings_tab.grid_rowconfigure(0, weight=1)
        
        # Settings card
        self.settings_card = ctk.CTkFrame(self.settings_tab, fg_color=COLORS["bg_card"], corner_radius=12)
        self.settings_card.grid(row=0, column=0, sticky="nsew")
        self.settings_card.grid_columnconfigure(0, weight=1)
        self.settings_card.grid_rowconfigure(2, weight=1)
        
        # Header with file selector and save button
        header_frame = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header_frame,
            text="Config File:",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"]
        ).grid(row=0, column=0, padx=(0, 10), sticky="w")
        
        # Define available config files
        self.config_files = {
            "server.properties": "server.properties",
            "bukkit.yml": "bukkit.yml",
            "spigot.yml": "spigot.yml",
            "paper-global.yml": "config/paper-global.yml",
            "paper-world-defaults.yml": "config/paper-world-defaults.yml",
            "commands.yml": "commands.yml",
            "permissions.yml": "permissions.yml",
            "Geyser config.yml": "plugins/Geyser-Spigot/config.yml",
            "Floodgate config.yml": "plugins/floodgate/config.yml",
            "AdvancedTeleport config.yml": "plugins/AdvancedTeleport/config.yml",
            "VeinMining config.yml": "plugins/VeinMining/config.yml",
            "TreeFeller config.yml": "plugins/TreeFeller/config.yml",
        }
        
        self.current_config = "server.properties"
        
        self.file_selector = ctk.CTkOptionMenu(
            header_frame,
            values=list(self.config_files.keys()),
            font=ctk.CTkFont(size=13),
            width=200,
            height=32,
            fg_color=COLORS["bg_tertiary"],
            button_color=COLORS["accent_blue"],
            button_hover_color="#2563eb",
            dropdown_fg_color=COLORS["bg_secondary"],
            command=self.on_config_selected
        )
        self.file_selector.grid(row=0, column=1, sticky="w")
        
        # Search entry
        self.search_entry = ctk.CTkEntry(
            header_frame,
            placeholder_text="🔍 Search...",
            font=ctk.CTkFont(size=12),
            width=120,
            height=32,
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6
        )
        self.search_entry.grid(row=0, column=2, padx=(10, 0), sticky="w")
        self.search_entry.bind("<Return>", lambda e: self.search_property())
        self.search_entry.bind("<KeyRelease>", lambda e: self.search_property())
        
        self.save_config_btn = ctk.CTkButton(
            header_frame,
            text="💾 Save",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=80,
            height=32,
            fg_color=COLORS["accent_green"],
            hover_color="#16a34a",
            corner_radius=6,
            command=self.save_config
        )
        self.save_config_btn.grid(row=0, column=3, padx=(8, 0), sticky="e")
        
        # File path label
        self.file_path_label = ctk.CTkLabel(
            self.settings_card,
            text="",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_muted"]
        )
        self.file_path_label.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="w")
        
        # Scrollable content frame
        self.config_scroll = ctk.CTkScrollableFrame(
            self.settings_card,
            fg_color="transparent"
        )
        self.config_scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.config_scroll.grid_columnconfigure(0, weight=1)
        self.config_scroll.grid_columnconfigure(1, weight=1)
        
        # Store entry widgets and current file type
        self.config_entries = {}
        self.current_file_path = ""
        self.current_file_type = "properties"
        
        # Load initial file
        self.load_config("server.properties")
    
    def create_backup_tab(self):
        """Create the Backup Logs tab content"""
        self.backup_tab = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.backup_tab.grid_columnconfigure(0, weight=1)
        self.backup_tab.grid_rowconfigure(0, weight=1)
        
        # Backup card
        backup_card = ctk.CTkFrame(self.backup_tab, fg_color=COLORS["bg_card"], corner_radius=12)
        backup_card.grid(row=0, column=0, sticky="nsew")
        backup_card.grid_columnconfigure(0, weight=1)
        backup_card.grid_rowconfigure(2, weight=1)
        
        # Header with title and manual backup button
        header = ctk.CTkFrame(backup_card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            header,
            text="Backup Logs",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        ).grid(row=0, column=0, sticky="w")
        
        self.manual_backup_btn = ctk.CTkButton(
            header,
            text="📤 Backup Now",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=120,
            height=32,
            fg_color=COLORS["accent_blue"],
            hover_color="#2563eb",
            corner_radius=6,
            command=self.run_backup
        )
        self.manual_backup_btn.grid(row=0, column=1, sticky="e")
        
        # Last backup info
        self.last_backup_label = ctk.CTkLabel(
            backup_card,
            text="Last backup: Never",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        )
        self.last_backup_label.grid(row=1, column=0, padx=20, pady=(0, 4), sticky="w")
        
        # Backup log textbox
        self.backup_log = ctk.CTkTextbox(
            backup_card,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=COLORS["bg_primary"],
            text_color=COLORS["text_primary"],
            state="disabled"
        )
        self.backup_log.grid(row=2, column=0, sticky="nsew", padx=16, pady=(8, 16))
        
        # Initial message
        self.log_backup("Backup system initialized")
        self.log_backup(f"Auto-backup every 10 minutes while server runs")
    
    def log_backup(self, message):
        """Add a message to the backup log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.backup_log.configure(state="normal")
        self.backup_log.insert("end", f"[{timestamp}] {message}\n")
        self.backup_log.see("end")
        self.backup_log.configure(state="disabled")
    
    def update_last_backup_label(self):
        """Update the last backup label with current time"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_backup_label.configure(text=f"Last backup: {timestamp}")
    
    def on_config_selected(self, selection):
        """Handle config file selection"""
        self.load_config(selection)
    
    def load_config(self, config_name):
        """Load a config file"""
        self.current_config = config_name
        relative_path = self.config_files.get(config_name, config_name)
        self.current_file_path = os.path.join(self.server_dir, relative_path)
        
        # Update path label
        self.file_path_label.configure(text=f"📁 {relative_path}")
        
        # Clear existing widgets
        for widget in self.config_scroll.winfo_children():
            widget.destroy()
        self.config_entries.clear()
        
        if not os.path.exists(self.current_file_path):
            ctk.CTkLabel(
                self.config_scroll,
                text=f"File not found: {relative_path}",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["accent_red"]
            ).pack(pady=20)
            return
        
        # Determine file type
        if self.current_file_path.endswith('.properties'):
            self.current_file_type = "properties"
            self.load_properties_file()
        elif self.current_file_path.endswith(('.yml', '.yaml')):
            self.current_file_type = "yaml"
            self.load_yaml_file()
        else:
            self.current_file_type = "text"
            self.load_text_file()
    
    def load_properties_file(self):
        """Load .properties file"""
        properties = []
        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        properties.append((key.strip(), value.strip()))
        except Exception as e:
            self.log_message(f"[Settings] Error: {e}", "error")
            return
        
        self.create_property_entries(properties)
        self.log_message(f"[Settings] Loaded {len(properties)} properties", "info")
    
    def load_yaml_file(self):
        """Load YAML file as key-value pairs"""
        properties = []
        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#') and ':' in stripped:
                        # Simple YAML parsing (key: value format)
                        parts = stripped.split(':', 1)
                        key = parts[0].strip()
                        value = parts[1].strip() if len(parts) > 1 else ""
                        # Skip section headers (no value)
                        if value or not stripped.endswith(':'):
                            properties.append((key, value))
        except Exception as e:
            self.log_message(f"[Settings] Error: {e}", "error")
            return
        
        self.create_property_entries(properties)
        self.log_message(f"[Settings] Loaded {len(properties)} settings", "info")
    
    def load_text_file(self):
        """Load text file in a textbox"""
        try:
            with open(self.current_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.text_editor = ctk.CTkTextbox(
                self.config_scroll,
                font=ctk.CTkFont(family="Consolas", size=12),
                fg_color=COLORS["bg_primary"],
                text_color=COLORS["text_primary"]
            )
            self.text_editor.pack(fill="both", expand=True, pady=8)
            self.text_editor.insert("1.0", content)
        except Exception as e:
            self.log_message(f"[Settings] Error: {e}", "error")
    
    def create_property_entries(self, properties):
        """Create entry widgets for properties"""
        for i, (key, value) in enumerate(properties):
            row = i // 2
            col = i % 2
            
            prop_frame = ctk.CTkFrame(self.config_scroll, fg_color=COLORS["bg_tertiary"], corner_radius=6)
            prop_frame.grid(row=row, column=col, sticky="ew", padx=4, pady=3)
            prop_frame.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(
                prop_frame,
                text=key,
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color=COLORS["text_secondary"],
                wraplength=100
            ).grid(row=0, column=0, padx=(8, 4), pady=6, sticky="w")
            
            entry = ctk.CTkEntry(
                prop_frame,
                font=ctk.CTkFont(family="Consolas", size=10),
                fg_color=COLORS["bg_primary"],
                border_color=COLORS["border"],
                text_color=COLORS["accent_green"],
                height=26,
                corner_radius=4
            )
            entry.insert(0, value)
            entry.grid(row=0, column=1, padx=(0, 8), pady=6, sticky="ew")
            
            self.config_entries[key] = entry
    
    def save_config(self):
        """Save current config file"""
        if not self.current_file_path or not os.path.exists(self.current_file_path):
            self.log_message("[Settings] No file to save", "warn")
            return
        
        try:
            if self.current_file_type == "text":
                # Save text file
                content = self.text_editor.get("1.0", "end-1c")
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                # Save properties/yaml file
                lines = []
                with open(self.current_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                separator = '=' if self.current_file_type == "properties" else ':'
                new_lines = []
                
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#') and separator in stripped:
                        key = stripped.split(separator, 1)[0].strip()
                        if key in self.config_entries:
                            new_value = self.config_entries[key].get()
                            # Preserve indentation
                            indent = len(line) - len(line.lstrip())
                            new_lines.append(f"{' ' * indent}{key}{separator} {new_value}\n" if separator == ':' else f"{key}={new_value}\n")
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            
            self.log_message(f"[Settings] Saved {self.current_config}!", "success")
            self.save_config_btn.configure(text="✓ Saved")
            self.after(2000, lambda: self.save_config_btn.configure(text="💾 Save"))
            
        except Exception as e:
            self.log_message(f"[Settings] Error saving: {e}", "error")
    
    def search_property(self):
        """Search and highlight matching properties"""
        query = self.search_entry.get().lower().strip()
        
        if not query:
            # Reset all entries to normal color
            for entry in self.config_entries.values():
                entry.configure(border_color=COLORS["border"])
            return
        
        # Skip search if query too short
        if len(query) < 2:
            return
        
        for key, entry in self.config_entries.items():
            if query in key.lower():
                entry.configure(border_color=COLORS["accent_green"])
            else:
                entry.configure(border_color=COLORS["border"])
    
    def clear_console(self):
        """Clear the console output"""
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")
    
    def show_tab(self, tab_name):
        """Switch between tabs"""
        # Store all tabs
        tabs = {
            "console": self.console_tab,
            "players": self.players_tab,
            "settings": self.settings_tab,
            "backup": self.backup_tab
        }
        
        # Hide all tabs
        for tab in tabs.values():
            tab.grid_forget()
        
        # Show selected tab
        tabs[tab_name].grid(row=0, column=0, sticky="nsew")
        
        # Update nav button highlighting
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == tab_name:
                btn.configure(fg_color="#1a2e1a", text_color=COLORS["text_primary"])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["text_secondary"])
    
    def add_activity(self, text, activity_type="info"):
        """Add an activity entry (now logs to console)"""
        # Icon based on type
        icons = {"join": "🟢", "leave": "🔴", "info": "ℹ️", "warn": "⚠️"}
        icon = icons.get(activity_type, "📌")
        
        # Log activity to console
        self.log_message(f"{icon} {text}", activity_type)
        self.recent_activity.append(text)
        
        # Keep activity list limited
        if len(self.recent_activity) > 10:
            self.recent_activity.pop(0)
    
    def update_player_list(self):
        """Update the online players list"""
        # Clear existing
        for widget in self.players_list.winfo_children():
            widget.destroy()
        
        if not self.online_players:
            self.no_players_label = ctk.CTkLabel(
                self.players_list,
                text="No players online",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["text_muted"]
            )
            self.no_players_label.pack(pady=20)
        else:
            for i, player in enumerate(self.online_players):
                frame = ctk.CTkFrame(self.players_list, fg_color=COLORS["bg_tertiary"], corner_radius=8)
                frame.pack(fill="x", pady=4)
                
                ctk.CTkLabel(
                    frame,
                    text=f"👤 {player}",
                    font=ctk.CTkFont(size=14),
                    text_color=COLORS["text_primary"]
                ).pack(padx=16, pady=12, anchor="w")
    
    def log_message(self, message, level="normal"):
        """Add a message to the console"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.console.configure(state="normal")
        self.console.insert("end", f"[{timestamp}] {message}\n")
        
        # Limit console to last 500 lines for performance
        line_count = int(self.console.index('end-1c').split('.')[0])
        if line_count > 500:
            self.console.delete("1.0", "100.0")
        
        self.console.see("end")
        self.console.configure(state="disabled")
    
    def update_status(self, status):
        """Update the server status"""
        self.server_status = status
        
        if status == "running":
            self.status_indicator.configure(text_color=COLORS["accent_green"])
            self.status_label.configure(text="Online")
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.restart_btn.configure(state="normal")
        elif status == "offline":
            self.status_indicator.configure(text_color=COLORS["accent_red"])
            self.status_label.configure(text="Offline")
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.restart_btn.configure(state="disabled")
            self.player_count = 0
            self.online_players = []
            self.update_player_list()
            self.player_count_label.configure(text=f"0/{self.max_players} online")
        else:
            self.status_indicator.configure(text_color=COLORS["accent_yellow"])
            self.status_label.configure(text=status.capitalize())
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="disabled")
            self.restart_btn.configure(state="disabled")
    
    def start_server(self):
        """Start the Minecraft server"""
        if self.server_process is not None:
            return
        
        self.update_status("starting")
        self.log_message("[Manager] Starting server...", "info")
        self.add_activity("Server starting...", "info")
        
        cmd = ["java"] + self.java_args + ["-jar", self.server_jar, "nogui"]
        
        try:
            self.server_process = subprocess.Popen(
                cmd,
                cwd=self.server_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            thread = threading.Thread(target=self.read_output, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log_message(f"[Manager] Failed: {e}", "error")
            self.update_status("offline")
    
    def stop_server(self):
        """Stop the Minecraft server"""
        if self.server_process is None:
            return
        
        self.update_status("stopping")
        self.log_message("[Manager] Stopping server...", "info")
        
        try:
            self.server_process.stdin.write("stop\n")
            self.server_process.stdin.flush()
        except:
            self.server_process.terminate()
    
    def restart_server(self):
        """Restart the server"""
        if self.server_process is not None:
            self._restart_pending = True
            self.stop_server()
        else:
            self.start_server()
    
    def send_command(self, event):
        """Send a command to the server"""
        cmd = self.command_input.get().strip()
        if not cmd or self.server_process is None:
            return
        
        try:
            self.server_process.stdin.write(cmd + "\n")
            self.server_process.stdin.flush()
            self.log_message(f"> {cmd}")
        except:
            pass
        
        self.command_input.delete(0, "end")
    
    def read_output(self):
        """Read server output"""
        try:
            for line in iter(self.server_process.stdout.readline, ''):
                if line:
                    self.output_queue.put(line.strip())
                    
                    if "Done" in line and "For help" in line:
                        self.output_queue.put("__STATUS_RUNNING__")
                    
                    # Detect player join/leave
                    if " joined the game" in line:
                        match = re.search(r'(\w+) joined the game', line)
                        if match:
                            self.output_queue.put(f"__PLAYER_JOIN__{match.group(1)}")
                    elif " left the game" in line:
                        match = re.search(r'(\w+) left the game', line)
                        if match:
                            self.output_queue.put(f"__PLAYER_LEAVE__{match.group(1)}")
            
            self.output_queue.put("__STATUS_STOPPED__")
        except:
            pass
    
    def process_output_queue(self):
        """Process output queue"""
        try:
            while True:
                line = self.output_queue.get_nowait()
                
                if line == "__STATUS_RUNNING__":
                    self.update_status("running")
                    self.log_message("[Manager] Server is ONLINE!", "success")
                    self.add_activity("Server is now online", "info")
                    # Auto-start Playit tunnel when server comes online
                    if not self.playit_running:
                        self.start_playit()
                elif line == "__STATUS_STOPPED__":
                    self.server_process = None
                    self.update_status("offline")
                    self.log_message("[Manager] Server stopped", "info")
                    self.add_activity("Server stopped", "info")
                    # Auto-stop Playit tunnel when server stops
                    if self.playit_running:
                        self.stop_playit()
                    
                    if getattr(self, '_restart_pending', False):
                        self._restart_pending = False
                        self.after(1000, self.start_server)
                elif line.startswith("__PLAYER_JOIN__"):
                    player = line.replace("__PLAYER_JOIN__", "")
                    self.online_players.append(player)
                    self.player_count = len(self.online_players)
                    self.player_count_label.configure(text=f"{self.player_count}/{self.max_players} online")
                    self.update_player_list()
                    self.add_activity(f"{player} joined", "join")
                elif line.startswith("__PLAYER_LEAVE__"):
                    player = line.replace("__PLAYER_LEAVE__", "")
                    if player in self.online_players:
                        self.online_players.remove(player)
                    self.player_count = len(self.online_players)
                    self.player_count_label.configure(text=f"{self.player_count}/{self.max_players} online")
                    self.update_player_list()
                    self.add_activity(f"{player} left", "leave")
                elif line.startswith("__PLAYIT_ADDRESS__"):
                    addr = line.replace("__PLAYIT_ADDRESS__", "")
                    self.playit_address = addr
                    self.playit_address_label.configure(text=f"🔗 {addr}")
                    self.log_message(f"[Playit] Tunnel: {addr}", "success")
                elif line.startswith("[Playit]"):
                    self.log_message(line)
                else:
                    self.log_message(line)
        except queue.Empty:
            pass
        
        # Poll queue less frequently for better performance
        self.after(100, self.process_output_queue)
    
    def toggle_playit(self):
        """Toggle playit.gg tunnel"""
        if self.playit_running:
            self.stop_playit()
        else:
            self.start_playit()
    
    def start_playit(self):
        """Start playit tunnel"""
        if not os.path.exists(self.playit_exe):
            self.log_message("[Playit] playit.exe not found!", "error")
            return
        
        self.log_message("[Playit] Starting tunnel...", "info")
        
        try:
            self.playit_process = subprocess.Popen(
                [self.playit_exe],
                cwd=self.server_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            self.playit_running = True
            self.playit_indicator.configure(text_color=COLORS["accent_green"])
            self.playit_status.configure(text="Online")
            self.add_activity("Tunnel started", "info")
            
            thread = threading.Thread(target=self.read_playit_output, daemon=True)
            thread.start()
        except Exception as e:
            self.log_message(f"[Playit] Error: {e}", "error")
    
    def stop_playit(self):
        """Stop playit tunnel"""
        if self.playit_process:
            self.playit_process.terminate()
            self.playit_process = None
        
        self.playit_running = False
        self.playit_indicator.configure(text_color=COLORS["accent_red"])
        self.playit_status.configure(text="Offline")
        self.playit_address = ""
        self.playit_address_label.configure(text="")
        self.log_message("[Playit] Tunnel stopped", "info")
        self.add_activity("Tunnel stopped", "info")
    
    def read_playit_output(self):
        """Read playit output and detect tunnel address"""
        try:
            for line in iter(self.playit_process.stdout.readline, ''):
                if line:
                    line_stripped = line.strip()
                    self.output_queue.put(f"[Playit] {line_stripped}")
                    
                    # Detect tunnel address patterns
                    # Common patterns: "tunnel address: xyz.playit.gg:12345" or URL patterns
                    if ".playit.gg" in line_stripped or "playit.gg:" in line_stripped:
                        # Try to extract address
                        import re
                        match = re.search(r'([a-zA-Z0-9-]+\.playit\.gg(?::\d+)?)', line_stripped)
                        if match:
                            self.output_queue.put(f"__PLAYIT_ADDRESS__{match.group(1)}")
                    
                    # Also check for "address" or "connect" keywords
                    if "address" in line_stripped.lower() or "connect" in line_stripped.lower():
                        match = re.search(r'(\S+\.playit\.gg(?::\d+)?)', line_stripped)
                        if match:
                            self.output_queue.put(f"__PLAYIT_ADDRESS__{match.group(1)}")
        except:
            pass
    
    def copy_playit_address(self):
        """Copy the playit address to clipboard"""
        if self.playit_address:
            self.clipboard_clear()
            self.clipboard_append(self.playit_address)
            self.log_message(f"[Playit] Address copied: {self.playit_address}", "info")
            # Briefly change button text to show copied
            self.copy_btn.configure(text="✓ Copied")
            self.after(1500, lambda: self.copy_btn.configure(text="📋 Copy"))
    
    def auto_backup(self):
        """Automatically backup to GitHub"""
        # Only backup if server is running
        if self.server_status == "running":
            self.run_backup()
        
        # Schedule next backup
        self.after(self.backup_interval, self.auto_backup)
    
    def run_backup(self):
        """Run git backup to GitHub with rolling 2-commit history"""
        self.log_message("[Backup] Starting backup to GitHub...", "info")
        
        def do_backup():
            try:
                # Git add all changes
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=self.server_dir,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Git commit
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                commit_result = subprocess.run(
                    ["git", "commit", "-m", f"Backup: {timestamp}"],
                    cwd=self.server_dir,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # Check if there were changes to commit
                if "nothing to commit" in commit_result.stdout:
                    self.after(0, lambda: self.log_backup("No changes to backup"))
                    self.output_queue.put("[Backup] No changes to backup")
                    return
                
                # Count commits
                count_result = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=self.server_dir,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                commit_count = int(count_result.stdout.strip()) if count_result.returncode == 0 else 0
                
                # If more than 2 commits, squash old ones
                if commit_count > 2:
                    self.after(0, lambda c=commit_count: self.log_backup(f"Cleaning old backups ({c} -> 2)"))
                    self.output_queue.put(f"[Backup] Cleaning old backups ({commit_count} -> 2)")
                    
                    # Reset to squash, keeping files
                    subprocess.run(
                        ["git", "reset", "--soft", "HEAD~" + str(commit_count - 1)],
                        cwd=self.server_dir,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    # Re-commit as single commit
                    subprocess.run(
                        ["git", "commit", "-m", f"Previous backup"],
                        cwd=self.server_dir,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    # Add current changes again
                    subprocess.run(
                        ["git", "add", "-A"],
                        cwd=self.server_dir,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    # New commit for current backup
                    subprocess.run(
                        ["git", "commit", "-m", f"Backup: {timestamp}"],
                        cwd=self.server_dir,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                
                # Force push to update remote
                push_result = subprocess.run(
                    ["git", "push", "origin", "main", "--force"],
                    cwd=self.server_dir,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if push_result.returncode == 0:
                    self.after(0, lambda: self.log_backup("✓ Backup pushed to GitHub!"))
                    self.after(0, lambda: self.update_last_backup_label())
                    self.output_queue.put("[Backup] ✓ Backup pushed to GitHub!")
                    self.last_backup = datetime.now()
                else:
                    # Try 'master' branch
                    push_result = subprocess.run(
                        ["git", "push", "origin", "master", "--force"],
                        cwd=self.server_dir,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if push_result.returncode == 0:
                        self.after(0, lambda: self.log_backup("✓ Backup pushed to GitHub!"))
                        self.after(0, lambda: self.update_last_backup_label())
                        self.output_queue.put("[Backup] ✓ Backup pushed to GitHub!")
                        self.last_backup = datetime.now()
                    else:
                        self.after(0, lambda: self.log_backup(f"Push failed: {push_result.stderr}"))
                        self.output_queue.put(f"[Backup] Push failed: {push_result.stderr}")
                        
            except Exception as e:
                self.output_queue.put(f"[Backup] Error: {e}")
        
        # Run backup in background thread
        thread = threading.Thread(target=do_backup, daemon=True)
        thread.start()
    
    def on_closing(self):
        """Handle window close"""
        if self.playit_running:
            self.stop_playit()
        if self.server_process and self.server_status == "running":
            self.stop_server()
            self.after(3000, self.destroy)
            return
        self.destroy()


if __name__ == "__main__":
    app = MinecraftServerManager()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
