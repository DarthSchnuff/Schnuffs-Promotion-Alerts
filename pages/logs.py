from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QScrollArea
)
from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QSystemTrayIcon
import os


class LogEntry(QFrame):
    def __init__(self, level, message):
        super().__init__()
        self.level = level.lower()
        self.setObjectName(f"LogEntry_{self.level}")

        layout = QVBoxLayout(self)
        time = QDateTime.currentDateTime().toString("HH:mm:ss")

        header = QLabel(f"[{time}] {level}")
        header.setObjectName("LogHeader")

        text = QLabel(message)
        text.setWordWrap(True)
        text.setObjectName("LogMessage")

        layout.addWidget(header)
        layout.addWidget(text)


class LogsPage(QWidget):
    def __init__(self, on_new_log=None):
        super().__init__()
        self.on_new_log = on_new_log
        self.MAX_LOG_ENTRIES = 300

        root = QVBoxLayout(self)

        title = QLabel("Logs")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.container.setObjectName("LogsContainer")
        self.layout = QVBoxLayout(self.container)
        self.layout.addStretch()

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)

    def add_log(self, level, message):
        entry = LogEntry(level, message)
        self.layout.insertWidget(self.layout.count() - 1, entry)
        self.enforce_limit()
        self.write_log(level, message)

        if level == "ERROR":
            QSystemTrayIcon.showMessage(
                QSystemTrayIcon(),
                "ERROR",
                message,
                QSystemTrayIcon.Critical
            )

        if self.on_new_log:
            self.on_new_log(level)

    def enforce_limit(self):
        while self.layout.count() - 1 > self.MAX_LOG_ENTRIES:
            w = self.layout.itemAt(0).widget()
            if w:
                w.deleteLater()

    def write_log(self, level, message):
        os.makedirs("logs", exist_ok=True)
        date = QDateTime.currentDateTime().toString("yyyy-MM-dd")
        with open(f"logs/{date}.log", "a", encoding="utf-8") as f:
            time = QDateTime.currentDateTime().toString("HH:mm:ss")
            f.write(f"[{time}] {level}: {message}\n")



