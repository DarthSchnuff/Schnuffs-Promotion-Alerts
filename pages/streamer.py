import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Signal


STREAMER_FILE = "streamers.json"


class StreamerPage(QWidget):
    streamers_changed = Signal(list)

    def __init__(self, controller):
        super().__init__()
        
        self.controller = controller
        self.streamers: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title = QLabel("Streamer")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        add_bar = QHBoxLayout()

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Streamer-Name (Twitch)")
        self.input_name.setClearButtonEnabled(True)

        self.btn_add = QPushButton("Hinzufügen")

        add_bar.addWidget(self.input_name)
        add_bar.addWidget(self.btn_add)
        layout.addLayout(add_bar)

        self.list = QListWidget()
        layout.addWidget(self.list)

        self.btn_remove = QPushButton("Ausgewählten entfernen")
        layout.addWidget(self.btn_remove)

        layout.addStretch()

        self.btn_add.clicked.connect(self.add_streamer)
        self.btn_remove.clicked.connect(self.remove_streamer)
        self.input_name.returnPressed.connect(self.add_streamer)

        self.load_streamers()

    def load_streamers(self):
        if os.path.exists(STREAMER_FILE):
            try:
                with open(STREAMER_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        else:
            data = {}

        self.streamers = data.get("streamers", [])
        self.list.clear()

        for name in self.streamers:
            self.list.addItem(QListWidgetItem(name))

        self.streamers_changed.emit(self.streamers)

    def save_streamers(self):
        with open(STREAMER_FILE, "w", encoding="utf-8") as f:
            json.dump({"streamers": self.streamers}, f, indent=2)

    def get_streamers(self) -> list[str]:
        return list(self.streamers)

    def add_streamer(self):
        name = self.input_name.text().strip().lower()
        if not name or name in self.streamers:
            return

        self.streamers.append(name)
        self.list.addItem(QListWidgetItem(name))
        self.input_name.clear()
        self.save_streamers()
        self.streamers_changed.emit(self.streamers)

    def remove_streamer(self):
        item = self.list.currentItem()
        if not item:
            return

        name = item.text()
        self.streamers.remove(name)
        self.list.takeItem(self.list.row(item))
        self.save_streamers()
        self.streamers_changed.emit(self.streamers)
