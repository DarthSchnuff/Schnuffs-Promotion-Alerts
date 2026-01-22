import json
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Signal

from core.paths import data  # ✅ Fallback-Default aus Bundle

APP_NAME = "SchnuffsPromotionAlerts"


def user_config_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def user_streamers_path() -> Path:
    return user_config_dir() / "streamers.json"


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

    def _read_streamers_file(self, path: Path) -> dict:
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
        except Exception:
            pass
        return {}

    def load_streamers(self):
        # 1) User-Config (writable, stabil)
        user_path = user_streamers_path()
        data_obj = self._read_streamers_file(user_path)

        # 2) Fallback: Default aus /data (Bundle)
        if not data_obj:
            data_obj = self._read_streamers_file(data("streamers.json"))

        self.streamers = data_obj.get("streamers", [])
        self.list.clear()

        for name in self.streamers:
            self.list.addItem(QListWidgetItem(name))

        self.streamers_changed.emit(self.streamers)

    def save_streamers(self):
        path = user_streamers_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"streamers": self.streamers}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

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
        if name in self.streamers:
            self.streamers.remove(name)

        self.list.takeItem(self.list.row(item))
        self.save_streamers()
        self.streamers_changed.emit(self.streamers)
