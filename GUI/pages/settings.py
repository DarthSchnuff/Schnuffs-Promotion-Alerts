from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit
)
from PySide6.QtCore import Qt
import webbrowser
import json
import os
from pages.settings import save_settings, load_settings

from version import APP_VERSION
from update_checker import check_for_update


SETTINGS_FILE = "settings.json"


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # ================= TITLE =================
        title = QLabel("Einstellungen")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # ================= UPDATE BOX =================
        update_box = QFrame()
        update_box.setObjectName("DashboardCard")
        update_layout = QVBoxLayout(update_box)

        self.update_label = QLabel(f"Version: {APP_VERSION}")
        self.update_status = QLabel("Nach Updates wurde noch nicht gesucht.")
        self.update_btn = QPushButton("Nach Updates suchen")

        update_layout.addWidget(self.update_label)
        update_layout.addWidget(self.update_status)
        update_layout.addWidget(self.update_btn)

        layout.addWidget(update_box)

        # ===== Discord Webhook =====
        discord_box = QFrame()
        discord_box.setObjectName("DashboardCard")
        discord_layout = QVBoxLayout(discord_box)

        discord_title = QLabel("Discord Webhook")
        self.discord_input = QLineEdit()
        self.discord_input.setPlaceholderText(
            "https://discord.com/api/webhooks/..."
        )

        settings = load_settings()
        self.discord_input.setText(
        settings.get("discord", {}).get("webhook", "")
        )

        save_btn = QPushButton("Webhook speichern")
        save_btn.clicked.connect(self.save_discord)

        discord_layout.addWidget(discord_title)
        discord_layout.addWidget(self.discord_input)
        discord_layout.addWidget(save_btn)

        layout.addWidget(discord_box)


        # ================= EVENTS =================
        self.update_btn.clicked.connect(self.check_update)
        self.save_btn.clicked.connect(self.save_settings)

        # ================= LOAD SETTINGS =================
        self.load_settings()

    # ================= UPDATE =================
    def check_update(self):
        result = check_for_update(APP_VERSION)

        if result.get("update"):
            self.update_status.setText(
                f"Update verfügbar: {result['latest']}"
            )
            self.update_btn.setText("Update öffnen")
            self.update_btn.clicked.disconnect()
            self.update_btn.clicked.connect(
                lambda: webbrowser.open(result["url"])
            )
        else:
            self.update_status.setText(
                "Du hast die neueste Version ✅"
            )

    # ================= SETTINGS =================
    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            discord = data.get("discord", {})
            self.discord_webhook_input.setText(
                discord.get("webhook", "")
            )
        except Exception:
            pass

    def save_settings(self):
        data = {}

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        data["discord"] = {
            "webhook": self.discord_webhook_input.text().strip()
        }

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        self.update_status.setText("Einstellungen gespeichert ✅")
