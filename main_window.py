from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QFrame, QStackedWidget,
    QSystemTrayIcon, QMenu, QListWidgetItem
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QTimer
import requests

from pages.settings import SettingsPage
from pages.dashboard import DashboardPage
from pages.streamer import StreamerPage
from pages.logs import LogsPage
from pages.credits import CreditsPage
from pages.webcam import WebcamPage
from pages.freegames_page import FreegamesPage


# ================= SIDEBAR =================
class Sidebar(QWidget):
    def __init__(self, switch_page_callback):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(12)

        self.buttons = {}
        for key, text in [
            ("dashboard", "Dashboard"),
            ("streamer", "Streamer"),
            ("webcam", "Webcam Test"),
            ("freegames", "Freegames"),
            ("settings", "Einstellungen"),
            ("credits", "Credits"),
            ("logs", "Logs"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("SidebarButton")
            btn.clicked.connect(lambda _, k=key: switch_page_callback(k))
            layout.addWidget(btn)
            self.buttons[key] = btn

        layout.addStretch()

        self.status_label = QLabel("● Service: Offline")
        self.status_label.setObjectName("SidebarStatus")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)


# ================= MAIN WINDOW =================
class MainWindow(QMainWindow):
    def __init__(self, app_controller):
        super().__init__()

        self.app_controller = app_controller

        self.setWindowTitle("Schnuffs Promotion Alerts")
        self.resize(1100, 700)

        self.build_ui()
        self.setup_tray()

        # Streamer → Dashboard
        self.page_streamer.streamers_changed.connect(
            self.page_dashboard.load_streamers
        )

        # Initial Load
        self.page_dashboard.load_streamers(
            self.page_streamer.get_streamers()
        )

        self.switch_page("dashboard")
        self.set_service_status(False)

        # Service Check Timer
        self.service_timer = QTimer()
        self.service_timer.timeout.connect(self.check_service_online)
        self.service_timer.start(5 * 60 * 1000)  # alle 5 Minuten
        self.check_service_online()  # einmal direkt beim Start

        self.hide()

    # ================= UI =================
    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        # ===== HEADER =====
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(120)

        h = QHBoxLayout(header)
        h.setContentsMargins(20, 10, 20, 10)

        logo = QLabel()
        pix = QPixmap("assets/logo.png")
        logo.setPixmap(
            pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
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

        # ===== BODY =====
        body = QHBoxLayout()
        root.addLayout(body)

        self.sidebar = Sidebar(self.switch_page)
        body.addWidget(self.sidebar)

        self.pages = QStackedWidget()

        self.page_dashboard = DashboardPage(self.app_controller)
        self.page_streamer = StreamerPage(self.app_controller)
        self.page_webcam = WebcamPage()
        self.page_settings = SettingsPage()
        self.page_credits = CreditsPage()
        self.page_logs = LogsPage()
        self.page_freegames = FreegamesPage(settings={"discord_webhook_url": None})

        self.pages_map = {
            "dashboard": self.page_dashboard,
            "streamer": self.page_streamer,
            "webcam": self.page_webcam,
            "settings": self.page_settings,
            "credits": self.page_credits,
            "logs": self.page_logs,
            "freegames": self.page_freegames,
        }

        for page in self.pages_map.values():
            self.pages.addWidget(page)

        body.addWidget(self.pages)

    # ================= TRAY =================
    def setup_tray(self):
        self.tray = QSystemTrayIcon(QIcon("assets/logo.png"), self)
        menu = QMenu()
        menu.addAction("Öffnen", self.showNormal)
        menu.addSeparator()
        menu.addAction("Beenden", self.close)
        self.tray.setContextMenu(menu)
        self.tray.show()

    # ================= NAV =================
    def switch_page(self, key):
        # Webcam sicher stoppen beim Verlassen
        current = self.pages.currentWidget()
        if current == self.page_webcam:
            self.page_webcam.stop_camera()

        self.pages.setCurrentWidget(self.pages_map[key])

        for k, btn in self.sidebar.buttons.items():
            btn.setProperty("active", k == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ================= SERVICE CHECK =================
    def check_service_online(self):
        try:
            response = requests.get("https://www.gamerpower.com/api/giveaways", timeout=5)
            self.set_service_status(response.status_code == 200)
        except:
            self.set_service_status(False)

    def set_service_status(self, online: bool):
        self.sidebar.status_label.setText(
            "● Service: Online" if online else "● Service: Offline"
        )

    # ================= CLEAN EXIT =================
    def closeEvent(self, event):
        """Sauberes Beenden aller Services"""
        if hasattr(self, "page_webcam"):
            self.page_webcam.stop_camera()
        if hasattr(self, "page_freegames"):
            self.page_freegames.cleanup()
        if hasattr(self, "app_controller"):
            self.app_controller.shutdown()  # <- hier Bugfix: alle Threads stoppen
        event.accept()

