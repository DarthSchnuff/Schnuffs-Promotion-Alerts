from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QFormLayout
)
import webbrowser

from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, Qt, Signal  # ✅ Signal dazu

from core.config import load_settings, save_settings
from core.paths import asset
from version import APP_VERSION
from update_checker import check_for_update
from services.autostart import is_enabled, enable, disable

PAYPAL_DONATION_URL = "https://www.paypal.me/DarthSchnuff"


class SettingsPage(QWidget):
    # ✅ NEU: Signal, damit MainWindow/Controller reagieren kann
    settings_saved = Signal()

    def __init__(self):
        super().__init__()

        self.settings = load_settings()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # ================= TITLE =================
        title = QLabel("Einstellungen")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # ================= UPDATE =================
        update_box = QFrame()
        update_box.setObjectName("DashboardCard")
        update_layout = QVBoxLayout(update_box)

        self.update_label = QLabel(f"Version: {APP_VERSION}")
        self.update_status = QLabel("Noch nicht geprüft")
        self.update_btn = QPushButton("Nach Updates suchen")
        self.update_btn.clicked.connect(self.check_update)

        update_layout.addWidget(self.update_label)
        update_layout.addWidget(self.update_status)
        update_layout.addWidget(self.update_btn)

        layout.addWidget(update_box)

        # ================= AUTOSTART =================
        autostart_box = QFrame()
        autostart_box.setObjectName("DashboardCard")
        autostart_layout = QVBoxLayout(autostart_box)

        autostart_title = QLabel("Autostart")
        autostart_title.setStyleSheet("font-weight: bold")

        self.autostart_btn = QPushButton()
        self.autostart_btn.clicked.connect(self.toggle_autostart)

        autostart_layout.addWidget(autostart_title)
        autostart_layout.addWidget(self.autostart_btn)

        layout.addWidget(autostart_box)
        self.update_autostart_btn()

        # ================= TWITCH =================
        twitch_box = QFrame()
        twitch_box.setObjectName("DashboardCard")
        twitch_layout = QVBoxLayout(twitch_box)

        twitch_title = QLabel("Twitch API")
        twitch_title.setStyleSheet("font-weight: bold")

        form = QFormLayout()

        self.twitch_client_id = QLineEdit()
        self.twitch_client_secret = QLineEdit()
        self.twitch_client_secret.setEchoMode(QLineEdit.Password)

        twitch_cfg = self.settings.get("twitch", {})
        self.twitch_client_id.setText(twitch_cfg.get("client_id", ""))
        self.twitch_client_secret.setText(twitch_cfg.get("client_secret", ""))

        form.addRow("Client ID", self.twitch_client_id)
        form.addRow("Client Secret", self.twitch_client_secret)

        save_twitch_btn = QPushButton("Twitch speichern")
        save_twitch_btn.clicked.connect(self.save_twitch)

        twitch_layout.addWidget(twitch_title)
        twitch_layout.addLayout(form)
        twitch_layout.addWidget(save_twitch_btn)

        layout.addWidget(twitch_box)

        # ================= DISCORD =================
        discord_box = QFrame()
        discord_box.setObjectName("DashboardCard")
        discord_layout = QVBoxLayout(discord_box)

        discord_title = QLabel("Discord Webhooks")
        discord_title.setStyleSheet("font-weight: bold")

        discord_form = QFormLayout()
        discord_cfg = self.settings.get("discord", {})

        self.discord_twitch_input = QLineEdit()
        self.discord_twitch_input.setPlaceholderText("Webhook für Twitch Alerts")
        self.discord_twitch_input.setText(discord_cfg.get("twitch_webhook", ""))

        self.discord_freegames_input = QLineEdit()
        self.discord_freegames_input.setPlaceholderText("Webhook für Free Games Alerts")
        self.discord_freegames_input.setText(discord_cfg.get("freegames_webhook", ""))

        discord_form.addRow("Twitch Webhook", self.discord_twitch_input)
        discord_form.addRow("Free Games Webhook", self.discord_freegames_input)

        save_discord_btn = QPushButton("Discord Webhooks speichern")
        save_discord_btn.clicked.connect(self.save_discord)

        discord_layout.addWidget(discord_title)
        discord_layout.addLayout(discord_form)
        discord_layout.addWidget(save_discord_btn)

        layout.addWidget(discord_box)

        # ================= DONATION =================
        donation_box = QFrame()
        donation_box.setObjectName("DashboardCard")
        donation_layout = QVBoxLayout(donation_box)

        donation_title = QLabel(
            "Wenn dir das Projekt gefällt, freue ich mich über eine kleine freiwillige Unterstützung. Vielen lieben Dank ❤️"
        )
        donation_title.setWordWrap(True)
        donation_title.setStyleSheet("font-weight: bold")

        donation_btn = QPushButton()
        donation_btn.setIcon(QIcon(str(asset("donate_heart_blue.png"))))
        donation_btn.setIconSize(QSize(64, 64))
        donation_btn.setFixedSize(80, 80)
        donation_btn.setToolTip("Über PayPal unterstützen")

        donation_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.05);
                border-radius: 40px;
            }
        """)

        donation_btn.clicked.connect(lambda: webbrowser.open(PAYPAL_DONATION_URL))

        donation_layout.addWidget(donation_title)
        donation_layout.addWidget(donation_btn, alignment=Qt.AlignLeft)

        layout.addWidget(donation_box)
        layout.addStretch()

    # ================= UPDATE =================
    def check_update(self):
        result = check_for_update(APP_VERSION)

        if result.get("update"):
            self.update_status.setText(f"Update verfügbar: {result['latest']}")
            self.update_btn.setText("Release öffnen")
            self.update_btn.clicked.disconnect()
            self.update_btn.clicked.connect(lambda: webbrowser.open(result["url"]))
        else:
            self.update_status.setText("Du hast die neueste Version ✅")

    # ================= AUTOSTART =================
    def update_autostart_btn(self):
        self.autostart_btn.setText(
            "Autostart deaktivieren" if is_enabled() else "Autostart aktivieren"
        )

    def toggle_autostart(self):
        if is_enabled():
            disable()
            self.update_status.setText("Autostart deaktiviert")
        else:
            enable()
            self.update_status.setText("Autostart aktiviert")
        self.update_autostart_btn()

    # ================= TWITCH =================
    def save_twitch(self):
        client_id = self.twitch_client_id.text().strip()
        client_secret = self.twitch_client_secret.text().strip()

        if not client_id or not client_secret:
            self.update_status.setText("Twitch-Daten unvollständig ⚠️")
            return

        self.settings.setdefault("twitch", {})
        self.settings["twitch"]["client_id"] = client_id
        self.settings["twitch"]["client_secret"] = client_secret

        save_settings(self.settings)
        self.update_status.setText("Twitch gespeichert ✅")

        # ✅ NEU: informieren, dass Settings geändert wurden
        self.settings_saved.emit()

    # ================= DISCORD =================
    def save_discord(self):
        twitch_webhook = self.discord_twitch_input.text().strip()
        freegames_webhook = self.discord_freegames_input.text().strip()

        self.settings.setdefault("discord", {})
        self.settings["discord"]["twitch_webhook"] = twitch_webhook
        self.settings["discord"]["freegames_webhook"] = freegames_webhook

        save_settings(self.settings)
        self.update_status.setText("Discord Webhooks gespeichert ✅")

        # ✅ NEU: informieren, dass Settings geändert wurden
        self.settings_saved.emit()
