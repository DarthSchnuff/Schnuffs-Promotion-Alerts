import cv2
import subprocess
import sys
import time
import json
import numpy as np
from enum import Enum
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSlider, QCheckBox, QGroupBox,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import QTimer, Qt, QSettings, QStandardPaths
from PySide6.QtGui import QImage, QPixmap, QGuiApplication

from core.paths import asset  # ✅ EXE-sicher


class WebcamEffect(Enum):
    NONE = "Kein Effekt"
    RAINBOW = "🌈 Rainbow"
    GRAYSCALE = "⚫ Schwarz/Weiß"
    MIRROR = "🔁 Spiegeln"
    EDGES = "🔲 Kanten"


class WebcamPage(QWidget):
    def __init__(self):
        super().__init__()

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.settings = QSettings("Schnuff", "PromotionAlerts")

        # Effect/state
        self.current_effect = WebcamEffect.NONE
        self.last_frame = None
        self.last_frame_time = time.time()

        # FPS
        self._frame_count = 0
        self._last_fps_time = time.time()
        self.fps = 0.0

        # Diagnostics
        self.freeze_warnings = 0
        self.frame_drops = 0

        # Capabilities (best effort)
        self.capabilities = {
            "autofocus": False,
            "focus": False,
            "sharpness": False,
            "zoom_hw": False,
            "auto_exposure": False,
            "exposure": False,
        }

        # Zoom + face detection
        self.digital_zoom = 1.0
        self.use_hw_zoom = False

        self.face_enabled = False
        self.face_cascade = None
        self._face_every_n = 5
        self._face_frame_counter = 0
        self._last_faces = []
        self.face_hits = 0

        # Recording
        self.is_recording = False
        self.record_writer = None
        self.record_start_ts = 0.0
        self.record_duration = 5.0
        self.record_path = None
        self._record_frame_size = None  # (w,h)

        # Test run
        self.test_active = False
        self.test_start_ts = 0.0
        self.test_duration = 10.0
        self.test_fps_samples = []
        self.test_frames = 0
        self.test_backend = None

        # Exposure mapping (driver-specific)
        self._exp_min = -13
        self._exp_max = -1

        # ===== Scan mode state =====
        self.supported_modes = {}  # {(w,h): {fps:int -> measured_fps:float}}
        self._scan_active = False
        self._scan_queue = []
        self._scan_current = None
        self._scan_frames = 0
        self._scan_start = 0.0
        self._scan_duration = 0.8
        self._scan_accept_factor = 0.70
        self._scan_profile = "Schnell"

        self._scan_step_timer = QTimer(self)
        self._scan_step_timer.timeout.connect(self._scan_step)

        self._scan_measure_timer = QTimer(self)
        self._scan_measure_timer.timeout.connect(self._scan_measure_tick)

        # ===== Apply burst measurement =====
        self._apply_burst_active = False
        self._apply_burst_start = 0.0
        self._apply_burst_frames = 0
        self._apply_burst_duration = 0.5
        self._apply_burst_timer = QTimer(self)
        self._apply_burst_timer.timeout.connect(self._apply_burst_tick)
        self._apply_last_target = None  # (w,h,fps_target)

        self.init_ui()
        self.scan_cameras()
        self.restore_last_camera()

    # ================= UI =================
    def init_ui(self):
        # Root with scroll (prevents cut-off on small displays)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Title
        title = QLabel("Webcam Hardware-Test")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Camera selection
        top = QHBoxLayout()
        top.addWidget(QLabel("Kamera:"))

        self.cam_select = QComboBox()
        self.cam_select.setMinimumWidth(320)
        top.addWidget(self.cam_select)

        self.btn_refresh = QPushButton("🔄 Neu scannen")
        self.btn_refresh.clicked.connect(self.scan_cameras)
        top.addWidget(self.btn_refresh)

        top.addStretch()
        layout.addLayout(top)

        # Video display
        self.video_label = QLabel("Kamera nicht aktiv")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(480, 270)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setStyleSheet("background:#111; color:#777; border-radius:8px;")
        layout.addWidget(self.video_label)

        # Actions
        actions = QHBoxLayout()
        self.toggle_btn = QPushButton("▶ Webcam starten")
        self.toggle_btn.clicked.connect(self.toggle_camera)
        actions.addWidget(self.toggle_btn)

        self.btn_screenshot = QPushButton("📸 Screenshot")
        self.btn_screenshot.clicked.connect(self.save_screenshot)
        self.btn_screenshot.setEnabled(False)
        actions.addWidget(self.btn_screenshot)

        self.btn_record = QPushButton("⏺ 5s Aufnahme")
        self.btn_record.clicked.connect(self.start_recording_5s)
        self.btn_record.setEnabled(False)
        actions.addWidget(self.btn_record)

        self.btn_test = QPushButton("🧪 10s Testlauf")
        self.btn_test.clicked.connect(self.start_test_run_10s)
        self.btn_test.setEnabled(False)
        actions.addWidget(self.btn_test)

        self.btn_report = QPushButton("🧾 Report exportieren")
        self.btn_report.clicked.connect(self.export_report)
        self.btn_report.setEnabled(False)
        actions.addWidget(self.btn_report)

        actions.addStretch()
        layout.addLayout(actions)

        # Status label
        self.diag_label = QLabel("Status: bereit")
        self.diag_label.setStyleSheet("opacity: 0.75;")
        layout.addWidget(self.diag_label)

        # ===== Video settings group =====
        vs = QGroupBox("Video-Einstellungen (Auflösung / FPS)")
        vs_layout = QVBoxLayout(vs)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Auflösung:"))

        self.res_select = QComboBox()
        self._res_presets = [
            (640, 480),
            (1280, 720),
            (1920, 1080),
            (2560, 1440),
            (3840, 2160),
        ]
        for w, h in self._res_presets:
            self.res_select.addItem(f"{w}×{h}", (w, h))
        self.res_select.setCurrentIndex(1)
        self.res_select.setEnabled(False)
        self.res_select.currentIndexChanged.connect(self._on_res_changed)
        row1.addWidget(self.res_select)

        row1.addWidget(QLabel("FPS:"))
        self.fps_select = QComboBox()
        self.fps_select.addItem("Auto", None)
        self.fps_select.addItem("30", 30)
        self.fps_select.addItem("60", 60)
        self.fps_select.setEnabled(False)
        row1.addWidget(self.fps_select)

        self.btn_apply_video = QPushButton("✅ Anwenden")
        self.btn_apply_video.clicked.connect(self.apply_video_settings)
        self.btn_apply_video.setEnabled(False)
        row1.addWidget(self.btn_apply_video)

        self.scan_profile_select = QComboBox()
        self.scan_profile_select.addItem("Schnell (≈0.6s/Modus)", "Schnell")
        self.scan_profile_select.addItem("Gründlich (≈2.0s/Modus)", "Gründlich")
        self.scan_profile_select.setEnabled(False)
        row1.addWidget(self.scan_profile_select)

        self.btn_scan_modes = QPushButton("🔎 Scan")
        self.btn_scan_modes.clicked.connect(self.start_scan_modes)
        self.btn_scan_modes.setEnabled(False)
        self.btn_scan_modes.setToolTip(
            "Schnell: grob filtern\nGründlich: stabilere Ergebnisse\nHinweis: 4K@60 benötigt oft USB 3.x + MJPEG/H.264."
        )
        row1.addWidget(self.btn_scan_modes)

        row1.addStretch()
        vs_layout.addLayout(row1)

        self.video_actual_label = QLabel("Aktuell: —")
        self.video_actual_label.setStyleSheet("opacity: 0.75;")
        vs_layout.addWidget(self.video_actual_label)

        self.scan_result_label = QLabel("Scan: —")
        self.scan_result_label.setStyleSheet("opacity: 0.75;")
        vs_layout.addWidget(self.scan_result_label)

        self.usb_warn_label = QLabel("")
        self.usb_warn_label.setStyleSheet("opacity: 0.8;")
        vs_layout.addWidget(self.usb_warn_label)

        layout.addWidget(vs)

        # ===== Advanced controls group =====
        adv = QGroupBox("Test-Funktionen (Zoom / Gesichtserkennung / Belichtung)")
        adv_layout = QVBoxLayout(adv)

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(300)
        self.zoom_slider.setValue(10)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_row.addWidget(self.zoom_slider)
        self.zoom_value = QLabel("1.0x")
        self.zoom_value.setMinimumWidth(55)
        zoom_row.addWidget(self.zoom_value)
        adv_layout.addLayout(zoom_row)

        face_row = QHBoxLayout()
        self.face_checkbox = QCheckBox("Gesichtserkennung (Software)")
        self.face_checkbox.setChecked(False)
        self.face_checkbox.stateChanged.connect(self.on_face_toggled)
        face_row.addWidget(self.face_checkbox)
        face_row.addStretch()
        adv_layout.addLayout(face_row)

        layout.addWidget(adv)

        # Effects
        effects_layout = QHBoxLayout()
        self.effect_buttons = {}
        for effect in WebcamEffect:
            btn = QPushButton(effect.value)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, e=effect: self.set_effect(e, checked))
            effects_layout.addWidget(btn)
            self.effect_buttons[effect] = btn
        self.effect_buttons[WebcamEffect.NONE].setChecked(True)
        layout.addLayout(effects_layout)

        layout.addStretch()

    # ================= Camera enumeration =================
    def scan_cameras(self):
        self.cam_select.clear()
        cams = self.list_cameras_with_names()
        if not cams:
            self.cam_select.addItem("❌ Keine Kamera gefunden", -1)
            return
        for idx, name in cams:
            self.cam_select.addItem(f"{self.get_camera_icon(name)} {name}", idx)

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
            names = [line.strip() for line in output.decode("utf-8", errors="ignore").split("\n") if line.strip()]
            return [(idx, name) for idx, name in enumerate(names)]
        except Exception:
            return []

    def get_camera_icon(self, name):
        n = name.lower()
        if "obs" in n or "virtual" in n:
            return "🎬"
        if "droid" in n or "phone" in n:
            return "📱"
        if "logitech" in n or "webcam" in n:
            return "🎥"
        if "integrated" in n:
            return "💻"
        return "📷"

    # ================= Camera control =================
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

        self.detect_capabilities()
        self.init_face_cascade_from_assets()

        for b in (self.btn_screenshot, self.btn_record, self.btn_test, self.btn_report):
            b.setEnabled(True)
        self.res_select.setEnabled(True)
        self.fps_select.setEnabled(True)
        self.btn_apply_video.setEnabled(True)
        self.scan_profile_select.setEnabled(True)
        self.btn_scan_modes.setEnabled(True)

        self.toggle_btn.setText("⏸ Webcam stoppen")
        self.video_label.clear()

        self.last_frame = None
        self.last_frame_time = time.time()
        self._last_faces = []
        self._face_frame_counter = 0

        self.timer.start(30)
        self.save_camera_selection(index)

        self.apply_video_settings()
        self.update_actual_video_label()
        self.diag_label.setText("Status: Kamera läuft")

    def stop_camera(self):
        self.timer.stop()
        self.stop_recording_if_active()
        self.stop_test_if_active(finalize=False)
        self.stop_scan_if_active()
        self._stop_apply_burst_if_active()

        self.last_frame = None
        self.last_frame_time = time.time()
        self._last_faces = []
        self._face_frame_counter = 0

        self._frame_count = 0
        self._last_fps_time = time.time()
        self.fps = 0.0
        self.freeze_warnings = 0
        self.frame_drops = 0
        self.face_hits = 0

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        self.video_label.setText("Kamera gestoppt")
        self.toggle_btn.setText("▶ Webcam starten")

        for b in (self.btn_screenshot, self.btn_record, self.btn_test, self.btn_report):
            b.setEnabled(False)
        self.res_select.setEnabled(False)
        self.fps_select.setEnabled(False)
        self.btn_apply_video.setEnabled(False)
        self.scan_profile_select.setEnabled(False)
        self.btn_scan_modes.setEnabled(False)

        self.video_actual_label.setText("Aktuell: —")
        self.scan_result_label.setText("Scan: —")
        self.usb_warn_label.setText("")

        self.diag_label.setText("Status: bereit")

    # ================= helpers =================
    def _try_set(self, prop: int, value: float) -> bool:
        try:
            return bool(self.cap and self.cap.set(prop, value))
        except Exception:
            return False

    def _try_get(self, prop: int):
        try:
            return self.cap.get(prop) if self.cap else None
        except Exception:
            return None

    def update_actual_video_label(self):
        w = int(self._try_get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(self._try_get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fps = float(self._try_get(cv2.CAP_PROP_FPS) or 0.0)
        if w > 0 and h > 0:
            self.video_actual_label.setText(f"Aktuell: {w}×{h} @ {fps:.1f} FPS")
        else:
            self.video_actual_label.setText("Aktuell: (unbekannt)")

    def _update_usb_warning(self, w: int, h: int, fps_target: int | None, fps_measured: float | None = None):
        warn = ""
        high_res = (w >= 3840 and h >= 2160) or (w >= 2560 and h >= 1440)
        if high_res and (fps_target == 60 or (fps_target is None)):
            warn = "Hinweis: 4K/High-FPS braucht oft USB 3.x + MJPEG/H.264 (sonst fällt FPS ab)."
        if fps_target == 60 and fps_measured is not None and fps_measured < 45.0:
            warn = (warn + " " if warn else "") + "Warnung: 60 FPS gewählt, aber effektiv deutlich weniger gemessen."
        self.usb_warn_label.setText(warn)

    # ================= Apply burst measurement =================
    def _stop_apply_burst_if_active(self):
        self._apply_burst_timer.stop()
        self._apply_burst_active = False
        self._apply_last_target = None

    def _start_apply_burst(self, w: int, h: int, fps_target: int | None):
        if not self.cap or self._scan_active:
            return
        self._apply_last_target = (w, h, fps_target)
        self._apply_burst_active = True
        self._apply_burst_frames = 0
        self._apply_burst_start = time.monotonic()

        for _ in range(2):
            try:
                self.cap.read()
            except Exception:
                break

        self._apply_burst_timer.start(0)

    def _apply_burst_tick(self):
        if not self._apply_burst_active or not self.cap:
            self._stop_apply_burst_if_active()
            return

        try:
            ret, _ = self.cap.read()
            if ret:
                self._apply_burst_frames += 1
        except Exception:
            pass

        elapsed = time.monotonic() - self._apply_burst_start
        if elapsed >= self._apply_burst_duration:
            self._apply_burst_timer.stop()
            self._apply_burst_active = False

            fps_meas = (self._apply_burst_frames / elapsed) if elapsed > 0 else 0.0
            self.update_actual_video_label()

            if self._apply_last_target:
                w, h, fps_target = self._apply_last_target
                self._update_usb_warning(w, h, fps_target, fps_measured=fps_meas)

            base = self.video_actual_label.text().replace("Aktuell: ", "")
            self.diag_label.setText(f"Video angewendet: {base} | gemessen: {fps_meas:.1f} FPS")

    # ================= Video settings apply =================
    def apply_video_settings(self):
        if not self.cap or self._scan_active:
            return

        # Reset caches (resolution may change)
        self.last_frame = None
        self.last_frame_time = time.time()
        self._last_faces = []
        self._face_frame_counter = 0

        self._stop_apply_burst_if_active()

        res = self.res_select.currentData()
        fps_target = self.fps_select.currentData()

        if isinstance(res, tuple):
            w, h = res
        else:
            w, h = 1280, 720

        ok_w = self._try_set(cv2.CAP_PROP_FRAME_WIDTH, float(w))
        ok_h = self._try_set(cv2.CAP_PROP_FRAME_HEIGHT, float(h))

        ok_fps = True
        if fps_target is not None:
            ok_fps = self._try_set(cv2.CAP_PROP_FPS, float(fps_target))

        self.update_actual_video_label()
        self._update_usb_warning(w, h, fps_target)

        self.diag_label.setText(
            f"Video angewendet: setW={ok_w} setH={ok_h} setFPS={ok_fps} | {self.video_actual_label.text().replace('Aktuell: ', '')} | messe…"
        )
        self._start_apply_burst(w, h, fps_target)

    def _on_res_changed(self):
        if not self.supported_modes:
            return
        res = self.res_select.currentData()
        if not isinstance(res, tuple):
            return
        w, h = res

        fps_map = self.supported_modes.get((w, h), {})
        self.fps_select.blockSignals(True)
        self.fps_select.clear()
        self.fps_select.addItem("Auto", None)
        for fps in sorted(fps_map.keys(), reverse=True):
            meas = fps_map[fps]
            self.fps_select.addItem(f"{fps} (gemessen {meas:.1f})", fps)
        if self.fps_select.count() == 1:
            self.fps_select.addItem("30", 30)
            self.fps_select.addItem("60", 60)
        self.fps_select.blockSignals(False)

    # ================= Scan mode =================
    def start_scan_modes(self):
        if not self.cap or self._scan_active:
            return

        profile = self.scan_profile_select.currentData() or "Schnell"
        self._scan_profile = profile
        if profile == "Gründlich":
            self._scan_duration = 2.0
            self._scan_accept_factor = 0.85
        else:
            self._scan_duration = 0.6
            self._scan_accept_factor = 0.70

        # reset caches for scan
        self.last_frame = None
        self.last_frame_time = time.time()
        self._last_faces = []
        self._face_frame_counter = 0

        self._stop_apply_burst_if_active()

        self.timer.stop()
        self._scan_active = True
        self.supported_modes = {}
        self.scan_result_label.setText(f"Scan: läuft… ({profile})")
        self.diag_label.setText(f"Scan-Modus ({profile}): teste Presets (bis 4K) + 30/60 FPS…")

        self.btn_apply_video.setEnabled(False)
        self.btn_scan_modes.setEnabled(False)
        self.res_select.setEnabled(False)
        self.fps_select.setEnabled(False)
        self.scan_profile_select.setEnabled(False)

        fps_targets = [30, 60]
        self._scan_queue = [(w, h, fps) for (w, h) in self._res_presets for fps in fps_targets]
        self._scan_step_timer.start(0)

    def stop_scan_if_active(self):
        if not self._scan_active:
            return
        self._scan_active = False
        self._scan_step_timer.stop()
        self._scan_measure_timer.stop()
        self._scan_queue = []
        self._scan_current = None
        self.last_frame = None
        self.last_frame_time = time.time()
        if self.cap:
            self.timer.start(30)

    def _scan_step(self):
        if not self._scan_active:
            return
        if not self._scan_queue:
            self._finish_scan()
            return

        w, h, fps = self._scan_queue.pop(0)
        self._scan_current = (w, h, fps)

        self._try_set(cv2.CAP_PROP_FRAME_WIDTH, float(w))
        self._try_set(cv2.CAP_PROP_FRAME_HEIGHT, float(h))
        self._try_set(cv2.CAP_PROP_FPS, float(fps))

        for _ in range(4):
            self.cap.read()

        self._scan_frames = 0
        self._scan_start = time.monotonic()
        self._scan_measure_timer.start(0)

    def _scan_measure_tick(self):
        if not self._scan_active or not self.cap or not self._scan_current:
            self._scan_measure_timer.stop()
            return

        ret, _ = self.cap.read()
        if ret:
            self._scan_frames += 1

        elapsed = time.monotonic() - self._scan_start
        if elapsed >= self._scan_duration:
            self._scan_measure_timer.stop()
            self._scan_evaluate_current(elapsed)
            self._scan_step_timer.start(0)

    def _scan_evaluate_current(self, elapsed: float):
        w_req, h_req, fps_req = self._scan_current

        w_act = int(self._try_get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h_act = int(self._try_get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fps_meas = (self._scan_frames / elapsed) if elapsed > 0 else 0.0

        res_ok = (w_act == w_req and h_act == h_req) or (abs(w_act - w_req) <= 8 and abs(h_act - h_req) <= 8)
        fps_ok = fps_meas >= (fps_req * self._scan_accept_factor)

        if res_ok and fps_ok:
            self.supported_modes.setdefault((w_req, h_req), {})
            prev = self.supported_modes[(w_req, h_req)].get(fps_req, 0.0)
            self.supported_modes[(w_req, h_req)][fps_req] = max(prev, fps_meas)

        total = len(self._res_presets) * 2
        done = total - len(self._scan_queue)
        self.scan_result_label.setText(
            f"Scan: {done}/{total} ({self._scan_profile}) | {w_req}×{h_req}@{fps_req} → read {w_act}×{h_act}, gemessen {fps_meas:.1f}"
        )

    def _finish_scan(self):
        self._scan_active = False
        self._scan_step_timer.stop()
        self._scan_measure_timer.stop()

        self.last_frame = None
        self.last_frame_time = time.time()

        if self.cap:
            self.timer.start(30)

        supported_res = sorted(self.supported_modes.keys(), key=lambda r: (r[0] * r[1]))
        self.res_select.blockSignals(True)
        self.res_select.clear()

        if supported_res:
            for (w, h) in supported_res:
                fps_map = self.supported_modes.get((w, h), {})
                fps_list = ",".join(str(x) for x in sorted(fps_map.keys()))
                self.res_select.addItem(f"{w}×{h} (FPS: {fps_list})", (w, h))
            self.scan_result_label.setText(f"Scan: fertig ✅ ({self._scan_profile}) | Modi: {len(supported_res)}")
        else:
            for w, h in self._res_presets:
                self.res_select.addItem(f"{w}×{h}", (w, h))
            self.scan_result_label.setText(f"Scan: fertig ⚠️ ({self._scan_profile}) | keine stabilen Modi erkannt")

        self.res_select.blockSignals(False)

        if self.cap:
            self.btn_apply_video.setEnabled(True)
            self.btn_scan_modes.setEnabled(True)
            self.res_select.setEnabled(True)
            self.fps_select.setEnabled(True)
            self.scan_profile_select.setEnabled(True)

        self._on_res_changed()
        self.update_actual_video_label()

        res = self.res_select.currentData()
        fps_target = self.fps_select.currentData()
        if isinstance(res, tuple):
            self._update_usb_warning(res[0], res[1], fps_target)

        self.diag_label.setText("Scan-Modus: abgeschlossen")

    # ================= Capabilities (best effort) =================
    def detect_capabilities(self):
        if not self.cap:
            return
        # We only detect; actual set behavior depends on driver.
        self.capabilities["autofocus"] = self._try_get(cv2.CAP_PROP_AUTOFOCUS) not in (None, -1)
        self.capabilities["focus"] = self._try_get(cv2.CAP_PROP_FOCUS) not in (None, -1)
        self.capabilities["sharpness"] = self._try_get(cv2.CAP_PROP_SHARPNESS) not in (None, -1)
        self.capabilities["zoom_hw"] = self._try_get(cv2.CAP_PROP_ZOOM) not in (None, -1)
        self.capabilities["auto_exposure"] = self._try_get(cv2.CAP_PROP_AUTO_EXPOSURE) not in (None, -1)
        self.capabilities["exposure"] = self._try_get(cv2.CAP_PROP_EXPOSURE) not in (None, -1)

    # ================= Face detection =================
    def init_face_cascade_from_assets(self):
        try:
            xml_path = asset("cascades/haarcascade_frontalface_default.xml")
            c = cv2.CascadeClassifier(str(xml_path))
            self.face_cascade = None if c.empty() else c
        except Exception:
            self.face_cascade = None

        if self.face_cascade is None and self.face_checkbox.isChecked():
            self.face_checkbox.setChecked(False)
            self.face_enabled = False

    def on_face_toggled(self, state: int):
        self.face_enabled = (state == Qt.Checked)
        if self.face_enabled and self.face_cascade is None:
            self.face_enabled = False
            self.face_checkbox.setChecked(False)
            self.diag_label.setText("Gesichtserkennung: XML fehlt/ungültig")

    def _apply_face_detection(self, frame_rgb: np.ndarray) -> np.ndarray:
        if not self.face_enabled or self.face_cascade is None:
            return frame_rgb

        self._face_frame_counter += 1
        if self._face_frame_counter % self._face_every_n == 0:
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            self._last_faces = list(faces) if faces is not None else []

        if self._last_faces:
            self.face_hits += 1

        for (x, y, w, h) in self._last_faces:
            cv2.rectangle(frame_rgb, (x, y), (x + w, y + h), (0, 255, 0), 2)

        return frame_rgb

    # ================= Effects + zoom =================
    def set_effect(self, effect, checked):
        if not checked:
            # keep one checked
            self.effect_buttons[effect].setChecked(True)
            return
        self.current_effect = effect
        for e, btn in self.effect_buttons.items():
            if e != effect:
                btn.setChecked(False)

    def apply_effect(self, frame_rgb: np.ndarray) -> np.ndarray:
        if self.current_effect == WebcamEffect.GRAYSCALE:
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        if self.current_effect == WebcamEffect.MIRROR:
            return cv2.flip(frame_rgb, 1)
        if self.current_effect == WebcamEffect.EDGES:
            edges = cv2.Canny(frame_rgb, 100, 200)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        if self.current_effect == WebcamEffect.RAINBOW:
            hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
            shift = int((time.time() * 60) % 180)
            hsv[..., 0] = (hsv[..., 0].astype("int16") + shift) % 180
            hsv[..., 0] = hsv[..., 0].astype("uint8")
            return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        return frame_rgb

    def on_zoom_changed(self, value: int):
        self.digital_zoom = max(1.0, value / 10.0)
        self.zoom_value.setText(f"{self.digital_zoom:.1f}x")

    def apply_digital_zoom(self, frame_rgb: np.ndarray) -> np.ndarray:
        z = float(self.digital_zoom)
        if z <= 1.0:
            return frame_rgb
        h, w = frame_rgb.shape[:2]
        new_w = int(w / z)
        new_h = int(h / z)
        if new_w <= 0 or new_h <= 0:
            return frame_rgb
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2
        crop = frame_rgb[y1:y1 + new_h, x1:x1 + new_w]
        return cv2.resize(crop, (w, h), interpolation=cv2.INTER_LINEAR)

    # ================= Output paths =================
    def _output_dir(self) -> Path:
        base = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation) or str(Path.home())
        out = Path(base) / "SchnuffsPromotionAlerts" / "WebcamTest"
        out.mkdir(parents=True, exist_ok=True)
        return out

    def save_screenshot(self):
        if self.last_frame is None:
            self.diag_label.setText("Status: kein Frame für Screenshot")
            return
        out = self._output_dir()
        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        path = out / f"webcam_screenshot_{ts}.png"
        bgr = cv2.cvtColor(self.last_frame, cv2.COLOR_RGB2BGR)
        ok = cv2.imwrite(str(path), bgr)
        self.diag_label.setText(f"Screenshot gespeichert: {path.name}" if ok else "Screenshot fehlgeschlagen")

    def start_recording_5s(self):
        if not self.cap or self.is_recording or self._scan_active:
            return

        out = self._output_dir()
        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.record_path = out / f"webcam_record_{ts}.avi"

        w = int(self._try_get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(self._try_get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if w <= 0 or h <= 0:
            w, h = 640, 480

        fps = float(self.fps) if self.fps and self.fps > 5 else 30.0
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        self.record_writer = cv2.VideoWriter(str(self.record_path), fourcc, fps, (w, h))
        if not self.record_writer.isOpened():
            self.record_writer = None
            self.diag_label.setText("Aufnahme konnte nicht gestartet werden (VideoWriter).")
            return

        self.is_recording = True
        self._record_frame_size = (w, h)
        self.record_start_ts = time.time()
        self.record_duration = 5.0
        self.diag_label.setText(f"Aufnahme läuft (5s): {self.record_path.name}")

    def stop_recording_if_active(self):
        if self.is_recording:
            self.is_recording = False
            try:
                if self.record_writer:
                    self.record_writer.release()
            except Exception:
                pass
            self.record_writer = None
            self._record_frame_size = None

    # ================= Test run + report =================
    def start_test_run_10s(self):
        if not self.cap or self.test_active or self._scan_active:
            return
        self.test_active = True
        self.test_start_ts = time.time()
        self.test_duration = 10.0
        self.test_fps_samples = []
        self.test_frames = 0
        self.freeze_warnings = 0
        self.frame_drops = 0
        self.face_hits = 0
        self.test_backend = "CAP_DSHOW" if sys.platform == "win32" else "OpenCV"
        self.diag_label.setText("Testlauf: läuft (10s)…")

    def stop_test_if_active(self, finalize: bool = True):
        if not self.test_active:
            return
        self.test_active = False
        if finalize:
            self.export_report(auto=True)

    def export_report(self, auto: bool = False):
        out = self._output_dir()
        ts = time.strftime("%Y-%m-%d_%H-%M-%S")
        report_path = out / f"webcam_testreport_{ts}.txt"

        fps_avg = (sum(self.test_fps_samples) / len(self.test_fps_samples)) if self.test_fps_samples else self.fps
        fps_min = min(self.test_fps_samples) if self.test_fps_samples else self.fps
        fps_max = max(self.test_fps_samples) if self.test_fps_samples else self.fps

        cam_name = self.cam_select.currentText()
        w = int(self._try_get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(self._try_get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fps_read = float(self._try_get(cv2.CAP_PROP_FPS) or 0.0)

        lines = []
        lines.append("Schnuffs Promotion Alerts - Webcam Testreport")
        lines.append("=" * 56)
        lines.append(f"Zeit: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Kamera: {cam_name}")
        lines.append(f"Backend: {self.test_backend or 'n/a'}")
        lines.append(f"Auflösung/FPS (readback): {w} x {h} @ {fps_read:.1f} FPS")
        lines.append("")
        lines.append("Messwerte")
        lines.append("-" * 56)
        lines.append(f"FPS avg: {fps_avg:.2f}")
        lines.append(f"FPS min: {fps_min:.2f}")
        lines.append(f"FPS max: {fps_max:.2f}")
        lines.append(f"Frame Drops: {self.frame_drops}")
        lines.append(f"Freeze Warnungen: {self.freeze_warnings}")
        lines.append(f"Gesichtserkennung aktiv: {bool(self.face_checkbox.isChecked())}")
        lines.append(f"Face-Hits (Frames mit Gesicht): {self.face_hits}")
        lines.append("")
        lines.append(f"Scan-Profil zuletzt: {self._scan_profile}")
        lines.append("Scan-Ergebnisse (falls gelaufen)")
        lines.append("-" * 56)
        if self.supported_modes:
            for (rw, rh), fps_map in sorted(self.supported_modes.items(), key=lambda x: x[0][0] * x[0][1]):
                for f, meas in sorted(fps_map.items()):
                    lines.append(f"{rw}×{rh} @ {f} → gemessen {meas:.1f}")
        else:
            lines.append("—")

        try:
            report_path.write_text("\n".join(lines), encoding="utf-8")
            self.diag_label.setText(
                f"Testlauf fertig. Report: {report_path.name}" if auto else f"Report exportiert: {report_path.name}"
            )
        except Exception:
            self.diag_label.setText("Report export fehlgeschlagen")

    # ================= Frame update =================
    def update_frame(self):
        if not self.cap or self._scan_active:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.frame_drops += 1
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

        if self.test_active:
            self.test_fps_samples.append(float(self.fps))
            self.test_frames += 1

        # Freeze detection (robust against resolution changes)
        if self.last_frame is not None:
            if self.last_frame.shape == frame.shape:
                diff = np.mean(cv2.absdiff(self.last_frame, frame))
                if diff < 1.0 and time.time() - self.last_frame_time > 2:
                    self.freeze_warnings += 1
                if diff >= 1.0:
                    self.last_frame_time = time.time()
            else:
                self.last_frame_time = time.time()
                self.last_frame = None
                self._last_faces = []
                self._face_frame_counter = 0

        self.last_frame = frame.copy()

        # Effect + Face + Zoom
        frame = self.apply_effect(frame)
        frame = self._apply_face_detection(frame)
        frame = self.apply_digital_zoom(frame)

        # Recording safe (stop if resolution changed)
        if self.is_recording and self.record_writer and self._record_frame_size:
            rw, rh = self._record_frame_size
            if frame.shape[1] != rw or frame.shape[0] != rh:
                self.stop_recording_if_active()
                self.diag_label.setText("Aufnahme beendet: Auflösung hat sich geändert.")
            else:
                try:
                    self.record_writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                except Exception:
                    pass
                if time.time() - self.record_start_ts >= self.record_duration:
                    self.stop_recording_if_active()
                    if self.record_path:
                        self.diag_label.setText(f"Aufnahme gespeichert: {self.record_path.name}")

        # Test end
        if self.test_active and (time.time() - self.test_start_ts >= self.test_duration):
            self.stop_test_if_active(finalize=True)

        # Display
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
        self.video_label.setPixmap(
            QPixmap.fromImage(img).scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

    # ================= Settings =================
    def save_camera_selection(self, index):
        self.settings.setValue("webcam/last_index", index)

    def restore_last_camera(self):
        last = self.settings.value("webcam/last_index", 0, int)
        for i in range(self.cam_select.count()):
            if self.cam_select.itemData(i) == last:
                self.cam_select.setCurrentIndex(i)
                break

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()
