import os
import json

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QGraphicsOpacityEffect
)
from PySide6.QtGui import QIcon
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QPropertyAnimation, QEasingCurve


class SithCard(QFrame):
    def __init__(self, title, value, bg_path=None, highlight=False):
        super().__init__()

        # ObjectName für QSS
        if highlight:
            self.setObjectName("DashboardCardHighlight")
        else:
            self.setObjectName("DashboardCard")

        self.setFixedHeight(140)
        self.setFrameShape(QFrame.NoFrame)

        # 🔴 Pulse-Animation vorbereiten
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pulse_anim.setDuration(1600)
        self.pulse_anim.setStartValue(0.85)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        self.pulse_anim.setLoopCount(-1)

        layout = QGridLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setVerticalSpacing(6)

        # optionaler PNG-Hintergrund
        if bg_path:
            self.bg_label = QLabel(self)
            pixmap = QPixmap(bg_path)
            self.bg_label.setPixmap(pixmap)
            self.bg_label.setScaledContents(True)
            self.bg_label.lower()

            if not highlight:
                self.bg_label.setStyleSheet(
                    "background-color: rgba(0, 0, 0, 180);"
                )
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setPixmap(
            QIcon("images/icons/sith.png").pixmap(32, 32)
)
        self.icon_label.setObjectName("CardIcon")

        self.title_label = QLabel(title)
        self.title_label.setObjectName("CardTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("CardValue")

        layout.addWidget(self.icon_label, 0, 0, 2, 1)
        layout.addWidget(self.title_label, 0, 1)
        layout.addWidget(self.value_label, 1, 1)


        # initialer Zustand
        if highlight:
            self.pulse_anim.start()

    def resizeEvent(self, event):
        if hasattr(self, "bg_label"):
            self.bg_label.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def set_highlight(self, active: bool):
        if active:
            self.setObjectName("DashboardCardHighlight")
            self.pulse_anim.start()
        else:
            self.setObjectName("DashboardCard")
            self.pulse_anim.stop()
            self.opacity_effect.setOpacity(1.0)

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


# ================= STREAMER CARD =================
class StreamerCard(QFrame):
    def __init__(self, name: str, online: bool = False):
        super().__init__()
        self.setObjectName("DashboardCardHighlight" if online else "DashboardCard")

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self.title = QLabel(name)
        self.title.setObjectName("CardValue")

        self.status = QLabel("🟢 Live" if online else "🔴 Offline")
        self.status.setObjectName("CardSubtitle")

        layout.addWidget(self.title)
        layout.addWidget(self.status)
        layout.addStretch()

    def set_online(self, online: bool):
        self.status.setText("🟢 Live" if online else "🔴 Offline")
        self.setObjectName(
            "DashboardCardHighlight" if online else "DashboardCard"
        )
        self.style().unpolish(self)
        self.style().polish(self)


# ================= DASHBOARD PAGE =================
class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        self.streamer_cards = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(20)

        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        self.grid = QGridLayout()
        self.grid.setSpacing(20)
        root.addLayout(self.grid)

        self.load_streamers()

    # ================= LOAD STREAMERS =================
    def load_streamers(self):
        self.clear_grid()

        path = "streamers.json"
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        streamers = data.get("streamers", [])
        columns = 3

        for index, name in enumerate(streamers):
            row = index // columns
            col = index % columns

            card = StreamerCard(name, online=False)
            self.grid.addWidget(card, row, col)

            self.streamer_cards[name] = card

    # ================= CLEAR GRID =================
    def clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # ================= UPDATE FROM API (STEP 2 READY) =================
    def update_streamer_status(self, name: str, online: bool):
        card = self.streamer_cards.get(name)
        if card:
            card.set_online(online)


