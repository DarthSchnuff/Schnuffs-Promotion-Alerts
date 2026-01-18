import cv2
import subprocess
import sys
import time
import numpy as np
from enum import Enum

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox
)
from PySide6.QtCore import QTimer, Qt, QSettings
from PySide6.QtGui import QImage, QPixmap


# ================= EFFECT ENUM =================

class WebcamEffect(Enum):
    NONE = "Kein Effekt"
    RAINBOW = "🌈 Rainbow"
    GRAYSCALE = "⚫ Schwarz/Weiß"
    MIRROR = "🔁 Spiegeln"
    EDGES = "🔲 Kanten"


# ================= MAIN PAGE =================

class WebcamPage(QWidget):
    def __init__(self):  # ← KEIN app_controller Parameter!
        super().__init__()

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.settings = QSettings("Schnuff", "PromotionAlerts")

        # Effekt / Test Status
        self.current_effect = WebcamEffect.NONE
        self.last_frame = None
        self.last_frame_time = time.time()

        self._frame_count = 0
        self._last_fps_time = time.time()
        self.fps = 0.0

        self.init_ui()
        self.scan_cameras()
        self.restore_last_camera()

    # ================= UI SETUP =================

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("Webcam Hardware-Test")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # ===== CAMERA SELECTION =====
        top = QHBoxLayout()

        cam_label = QLabel("Kamera:")
        self.cam_select = QComboBox()
        self.cam_select.setMinimumWidth(300)

        self.btn_refresh = QPushButton("🔄 Neu scannen")
        self.btn_refresh.clicked.connect(self.scan_cameras)

        top.addWidget(cam_label)
        top.addWidget(self.cam_select)
        top.addWidget(self.btn_refresh)
        top.addStretch()

        layout.addLayout(top)

        # ===== VIDEO DISPLAY =====
        self.video_label = QLabel("Kamera nicht aktiv")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet(
            "background:#111; color:#777; border-radius:8px;"
        )
        layout.addWidget(self.video_label)

        # ===== CONTROLS =====
        self.toggle_btn = QPushButton("▶ Webcam starten")
        self.toggle_btn.clicked.connect(self.toggle_camera)
        layout.addWidget(self.toggle_btn, alignment=Qt.AlignLeft)

        # ===== EFFECT BUTTONS =====
        effects_layout = QHBoxLayout()
        self.effect_buttons = {}

        for effect in WebcamEffect:
            btn = QPushButton(effect.value)
            btn.setCheckable(True)
            btn.clicked.connect(
                lambda checked, e=effect: self.set_effect(e, checked)
            )
            effects_layout.addWidget(btn)
            self.effect_buttons[effect] = btn

        self.effect_buttons[WebcamEffect.NONE].setChecked(True)
        layout.addLayout(effects_layout)

    # ================= CAMERA SCANNING =================

    def scan_cameras(self):
        self.cam_select.clear()
        cams = self.list_cameras_with_names()

        if not cams:
            self.cam_select.addItem("❌ Keine Kamera gefunden", -1)
            return

        for idx, name in cams:
            icon = self.get_camera_icon(name)
            self.cam_select.addItem(f"{icon} {name}", idx)

    def list_cameras_with_names(self):
        result = []

        try:
            from pygrabber.dshow_graph import FilterGraph
            graph = FilterGraph()
            devices = graph.get_input_devices()
            for idx, name in enumerate(devices):
                result.append((idx, name))
            return result
        except ImportError:
            pass

        result = self.get_cameras_via_powershell()

        if not result:
            for idx in range(10):
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    result.append((idx, f"Kamera {idx}"))
                    cap.release()
                else:
                    break

        return result

    def get_cameras_via_powershell(self):
        try:
            cmd = [
                "powershell",
                "-WindowStyle", "Hidden",
                "-Command",
                "Get-PnpDevice -Class Camera | Select-Object -ExpandProperty FriendlyName"
            ]

            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=creationflags
            )

            output, _ = process.communicate(timeout=5)
            names = [
                line.strip()
                for line in output.decode("utf-8", errors="ignore").split("\n")
                if line.strip()
            ]

            return [(idx, name) for idx, name in enumerate(names)]

        except Exception:
            return []

    def get_camera_icon(self, name):
        name = name.lower()
        if "obs" in name or "virtual" in name:
            return "🎬"
        if "droid" in name or "phone" in name:
            return "📱"
        if "logitech" in name or "webcam" in name:
            return "🎥"
        if "integrated" in name:
            return "💻"
        return "📷"

    # ================= CAMERA CONTROL =================

    def toggle_camera(self):
        if self.cap:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        index = self.cam_select.currentData()
        if index is None or index < 0:
            self.video_label.setText("❌ Keine Kamera ausgewählt")
            return

        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.video_label.setText("❌ Kamera konnte nicht geöffnet werden")
            self.cap = None
            return

        self.toggle_btn.setText("⏸ Webcam stoppen")
        self.video_label.clear()
        self.timer.start(30)
        self.save_camera_selection(index)

    def stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_label.setText("Kamera gestoppt")
        self.toggle_btn.setText("▶ Webcam starten")

    # ================= EFFECTS =================

    def set_effect(self, effect, checked):
        if not checked:
            self.effect_buttons[effect].setChecked(True)
            return

        self.current_effect = effect
        for e, btn in self.effect_buttons.items():
            if e != effect:
                btn.setChecked(False)

    def apply_effect(self, frame):
        if self.current_effect == WebcamEffect.GRAYSCALE:
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

        if self.current_effect == WebcamEffect.MIRROR:
            return cv2.flip(frame, 1)

        if self.current_effect == WebcamEffect.EDGES:
            edges = cv2.Canny(frame, 100, 200)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

        if self.current_effect == WebcamEffect.RAINBOW:
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
            shift = int((time.time() * 60) % 180)
            hsv[..., 0] = (hsv[..., 0].astype("int16") + shift) % 180
            hsv[..., 0] = hsv[..., 0].astype("uint8")

            return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

        return frame

    # ================= FRAME UPDATE =================

    def update_frame(self):
        if not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.stop_camera()
            self.video_label.setText("❌ Kamerasignal verloren")
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # FPS
        self._frame_count += 1
        now = time.time()
        if now - self._last_fps_time >= 1.0:
            self.fps = self._frame_count / (now - self._last_fps_time)
            self._frame_count = 0
            self._last_fps_time = now

        # Freeze detection
        if self.last_frame is not None:
            diff = np.mean(cv2.absdiff(self.last_frame, frame))
            if diff < 1.0 and time.time() - self.last_frame_time > 2:
                self.video_label.setText("⚠️ Kamerabild eingefroren")
                return
            if diff >= 1.0:
                self.last_frame_time = time.time()

        self.last_frame = frame.copy()

        # Effect
        frame = self.apply_effect(frame)

        # Overlay
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, self.current_effect.value, (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)

        self.video_label.setPixmap(
            QPixmap.fromImage(img).scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

    # ================= SETTINGS =================

    def save_camera_selection(self, index):
        self.settings.setValue("webcam/last_index", index)

    def restore_last_camera(self):
        last = self.settings.value("webcam/last_index", 0, int)
        for i in range(self.cam_select.count()):
            if self.cam_select.itemData(i) == last:
                self.cam_select.setCurrentIndex(i)
                break

    # ================= CLEANUP =================

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()
