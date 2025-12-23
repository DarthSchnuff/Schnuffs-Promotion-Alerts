from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QFrame, QStackedWidget,
    QSystemTrayIcon, QMenu, QApplication
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QTimer

from services.twitch_watcher import TwitchWatcher
from services.discord_notifier import DiscordNotifier

from pages.settings import SettingsPage
from pages.dashboard import DashboardPage
from pages.streamer import StreamerPage
from pages.logs import LogsPage

import json
import os

SETTINGS_FILE = "settings.json"


# ================= SIDEBAR =================
class Sidebar(QWidget):
    def __init__(self, switch_page_callback):
        super().__init__()
        self.setObjectName("Sidebar")

        self.expanded_width = 220
        self.collapsed_width = 64
        self.is_collapsed = False
        self.setFixedWidth(self.expanded_width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(12)

        self.buttons = {}

        for key, text in [
            ("dashboard", "Dashboard"),
            ("streamer", "Streamer"),
            ("settings", "Einstellungen"),
            ("logs", "Logs"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("SidebarButton")
            btn.clicked.connect(lambda _, k=key: switch_page_callback(k))
            layout.addWidget(btn)
            self.buttons[key] = btn

        # Log Badge
        self.badge = QLabel("0")
        self.badge.setObjectName("LogBadge")
        self.badge.hide()

        badge_layout = QHBoxLayout(self.buttons["logs"])
        badge_layout.setContentsMargins(0, 0, 6, 0)
        badge_layout.addStretch()
        badge_layout.addWidget(self.badge)

        layout.addStretch()

        self.status_label = QLabel("● Service: Offline")
        self.status_label.setObjectName("SidebarStatus")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

    def collapse(self):
        if self.is_collapsed:
            return
        self.is_collapsed = True
        self.setFixedWidth(self.collapsed_width)
        for btn in self.buttons.values():
            btn.setText("")

    def expand(self):
        if not self.is_collapsed:
            return
        self.is_collapsed = False
        self.setFixedWidth(self.expanded_width)
        labels = {
            "dashboard": "Dashboard",
            "streamer": "Streamer",
            "settings": "Einstellungen",
            "logs": "Logs",
        }
        for key, btn in self.buttons.items():
            btn.setText(labels[key])


# ================= MAIN WINDOW =================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Schnuffs Promotion Alerts")
        self.resize(1100, 700)

        self.unread_logs = 0
        self.twitch = None
        self.discord = None

        self.setup_tray()
        self.build_ui()

        self.switch_page("dashboard")
        self.set_service_status(False)

        # Services erst starten, wenn UI komplett steht
        QTimer.singleShot(0, self.start_services)

    # ================= UI =================
    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        # ---------- HEADER ----------
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(120)

        h = QHBoxLayout(header)
        h.setContentsMargins(20, 10, 20, 10)

        logo = QLabel()
        pix = QPixmap("assets/logo.png")
        logo.setPixmap(pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        h.addWidget(logo)

        titles = QVBoxLayout()
        title = QLabel("Schnuffs Promotion Alerts")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel("Twitch • Discord • Live Monitoring")
        subtitle.setObjectName("HeaderSubtitle")

        titles.addWidget(title)
        titles.addWidget(subtitle)
        h.addLayout(titles)
        h.addStretch()

        root.addWidget(header)

        # ---------- BODY ----------
        body = QHBoxLayout()
        root.addLayout(body)

        self.sidebar = Sidebar(self.switch_page)
        body.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.page_dashboard = DashboardPage()
        self.page_streamer = StreamerPage()
        self.page_settings = SettingsPage()
        self.page_logs = LogsPage(on_new_log=self.increment_log_badge)

        self.pages_map = {
            "dashboard": self.page_dashboard,
            "streamer": self.page_streamer,
            "settings": self.page_settings,
            "logs": self.page_logs,
        }

        for page in self.pages_map.values():
            self.pages.addWidget(page)

        body.addWidget(self.pages)

    # ================= SERVICES =================
    def start_services(self):
        settings = self.load_settings()

        twitch_cfg = settings.get("twitch")
        streamers = self.page_streamer.get_streamers()

        if not twitch_cfg:
            self.page_logs.add_log("WARN", "Twitch nicht konfiguriert")
            return

        if not streamers:
            self.page_logs.add_log("WARN", "Keine Streamer eingetragen")
            return

        self.twitch = TwitchWatcher(
            client_id=twitch_cfg["client_id"],
            token=twitch_cfg["access_token"],
            streamers=streamers,
            callback=self.on_streamer_status,
            interval=60
        )
        self.twitch.start()

        # Discord
        webhook = settings.get("discord", {}).get("webhook")
        if webhook:
            self.discord = DiscordNotifier(webhook)
            self.page_logs.add_log("INFO", "Discord Webhook aktiv")

        self.set_service_status(True)
        self.page_logs.add_log("INFO", "Monitoring gestartet")

    def on_streamer_status(self, streamer, is_live):
        if is_live:
            self.page_logs.add_log("INFO", f"{streamer} ist LIVE")
            if self.discord:
                self.discord.streamer_live(streamer)
        else:
            self.page_logs.add_log("INFO", f"{streamer} ist offline")
            if self.discord:
                self.discord.streamer_offline(streamer)

    # ================= RESPONSIVE =================
    def resizeEvent(self, event):
        if self.width() < 600:
            self.sidebar.collapse()
        else:
            self.sidebar.expand()
        super().resizeEvent(event)

    # ================= TRAY =================
    def setup_tray(self):
        self.tray = QSystemTrayIcon(QIcon("assets/logo.png"), self)
        menu = QMenu()
        menu.addAction("Öffnen", self.showNormal)
        menu.addAction("Beenden", self.force_quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Schnuffs Promotion Alerts",
            "App läuft im Hintergrund",
            QSystemTrayIcon.Information
        )

    def force_quit(self):
        if self.twitch:
            self.twitch.stop()
        self.tray.hide()
        QApplication.quit()

    # ================= LOG BADGE =================
    def increment_log_badge(self, level=None):
        if level not in ("WARN", "ERROR"):
            return
        self.unread_logs += 1
        self.sidebar.badge.setText(str(self.unread_logs))
        self.sidebar.badge.show()

    def clear_log_badge(self):
        self.unread_logs = 0
        self.sidebar.badge.hide()

    # ================= NAV =================
    def switch_page(self, key):
        self.pages.setCurrentWidget(self.pages_map[key])
        self.set_active_sidebar(key)
        if key == "logs":
            self.clear_log_badge()

    def set_active_sidebar(self, active_key):
        for key, btn in self.sidebar.buttons.items():
            btn.setProperty("active", key == active_key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ================= STATUS =================
    def set_service_status(self, online):
        self.sidebar.status_label.setText(
            "● Service: Online" if online else "● Service: Offline"
        )
        self.sidebar.status_label.setProperty(
            "status", "online" if online else "offline"
        )
        self.sidebar.status_label.style().polish(self.sidebar.status_label)

    # ================= SETTINGS =================
    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return {}
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
