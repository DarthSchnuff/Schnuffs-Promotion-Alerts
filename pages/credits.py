from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import sys
from pathlib import Path


def resource_path(relative_path):
    """Gibt den absoluten Pfad zurück, auch wenn PyInstaller gepackt ist"""
    try:
        # Pfad, wenn EXE gepackt ist
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # normaler Start
        base_path = Path(__file__).parent.parent
    return base_path / relative_path


class CreditsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(30)

        # =========================
        # LEFT SIDE – SCROLLABLE TEXT
        # =========================
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("border: none;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll_layout.setSpacing(16)

        credits_label = QLabel()
        credits_label.setTextFormat(Qt.RichText)
        credits_label.setOpenExternalLinks(True)
        credits_label.setWordWrap(True)
        credits_label.setAlignment(Qt.AlignTop)

        credits_label.setText("""
        <h2>Credits & Dankeschön</h2>

        <p>
        Dieses Projekt wäre nicht möglich ohne die großartige Arbeit
        vieler Open-Source-Entwickler:innen und Tester.
        </p>

        <h3>Besitzer · Programmierer · Ersteller</h3>
        <ul>
            <li>
                <b><a href="https://www.twitch.tv/darthschnuff">DarthSchnuff</a></b><br>
                Twitch Channel
            </li>
        </ul>

        <h3>Frameworks & Libraries</h3>
        <ul>
            <li>
                <b>PySide6 (Qt for Python)</b><br>
                <a href="https://doc.qt.io/qtforpython/">https://doc.qt.io/qtforpython/</a>
            </li>
            <li>
                <b>requests</b><br>
                <a href="https://docs.python-requests.org/">https://docs.python-requests.org/</a>
            </li>
            <li>
                <b>OpenCV (cv2)</b><br>
                <a href="https://opencv.org/">https://opencv.org/</a>
            </li>
        </ul>

        <h3>APIs & Services</h3>
        <ul>
            <li>
                <b>Twitch API</b><br>
                <a href="https://dev.twitch.tv/">https://dev.twitch.tv/</a>
            </li>
            <li>
                <b>GamerPower API</b><br>
                <a href="https://www.gamerpower.com/api-read">
                https://www.gamerpower.com/api-read
                </a>
            </li>
        </ul>

        <h3>Tester & Mitwirkende</h3>
        <ul>
            <li>
                <b>
                    <a href="https://www.twitch.tv/captain_kiosk">
                        Captain_Kiosk
                    </a>
                </b><br>
                Testing, Feedback & Feature-Validierung
            </li>
        </ul>

        <p>
        Vielen Dank an alle Unterstützer, Tester und Nutzer ❤️<br>
        Weitere Credits können jederzeit ergänzt werden.
        </p>
        """)

        scroll_layout.addWidget(credits_label)
        scroll_layout.addStretch(1)

        scroll_area.setWidget(scroll_content)

        # =========================
        # RIGHT SIDE – IMAGE
        # =========================
        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)
        image_layout.setAlignment(Qt.AlignCenter)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)

        # 🔥 PyInstaller-kompatibler Pfad
        pixmap_path = resource_path("assets/credits.png")
        pixmap = QPixmap(str(pixmap_path))
        image_label.setPixmap(
            pixmap.scaled(
                500,
                700,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

        image_layout.addWidget(image_label)

        # =========================
        # ADD TO MAIN LAYOUT
        # =========================
        main_layout.addWidget(scroll_area, 1)
        main_layout.addWidget(image_container, 1)
