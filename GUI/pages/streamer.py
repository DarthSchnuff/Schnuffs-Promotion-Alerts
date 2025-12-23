import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt


STREAMER_FILE = "streamers.json"


class StreamerPage(QWidget):
    def __init__(self):
        super().__init__()

        self.streamers = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("Streamer")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # ===== Add Streamer =====
        add_bar = QHBoxLayout()

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Streamer-Name (Twitch)")

        self.btn_add = QPushButton("Hinzufügen")

        add_bar.addWidget(self.input_name)
        add_bar.addWidget(self.btn_add)

        layout.addLayout(add_bar)

        # ===== List =====
        self.list = QListWidget()
        layout.addWidget(self.list)

        # ===== Remove =====
        self.btn_remove = QPushButton("Ausgewählten entfernen")
        layout.addWidget(self.btn_remove)

        layout.addStretch()

        # Events
        self.btn_add.clicked.connect(self.add_streamer)
        self.btn_remove.clicked.connect(self.remove_streamer)

        self.load_streamers()

    # ================= DATA =================
    def load_streamers(self):
        if not os.path.exists(STREAMER_FILE):
            self.save_streamers()
            return

        with open(STREAMER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.streamers = data.get("streamers", [])

        self.list.clear()
        for name in self.streamers:
            self.list.addItem(QListWidgetItem(name))

    def save_streamers(self):
        data = {
            "streamers": self.streamers
        }

        with open(STREAMER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ================= ACTIONS =================
    def add_streamer(self):
        name = self.input_name.text().strip().lower()

        if not name or name in self.streamers:
            return

        self.streamers.append(name)
        self.list.addItem(QListWidgetItem(name))
        self.input_name.clear()
        self.save_streamers()

    def remove_streamer(self):
        item = self.list.currentItem()
        if not item:
            return

        name = item.text()
        self.streamers.remove(name)
        self.list.takeItem(self.list.row(item))
        self.save_streamers()
