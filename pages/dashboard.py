from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
)
from PySide6.QtCore import Qt


class DashboardPage(QWidget):
    def __init__(self, app_controller):
        super().__init__()
        self.app_controller = app_controller
        
        # Speichere alle Streamer-Stati
        self.streamer_data = {}  # {name: {"is_online": bool, "title": str}}
        
        # ================= LAYOUT =================
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # ================= TITLE =================
        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        main_layout.addWidget(title)
        
        # ================= STATUS =================
        self.status_label = QLabel("Bereit")
        self.status_label.setObjectName("StatusLabel")
        main_layout.addWidget(self.status_label)
        
        # ================= STREAMER AREA =================
        self.streamer_area = QScrollArea()
        self.streamer_area.setWidgetResizable(True)
        self.streamer_area.setFrameShape(QFrame.NoFrame)
        
        self.streamer_container = QWidget()
        self.streamer_layout = QVBoxLayout(self.streamer_container)
        self.streamer_layout.setSpacing(10)
        self.streamer_layout.addStretch()
        
        self.streamer_area.setWidget(self.streamer_container)
        main_layout.addWidget(self.streamer_area)
        
        # ================= SIGNALS =================
        self.app_controller.status_message.connect(
            self.update_status
        )
        
        # Dashboard empfängt Streamer-Updates
        if hasattr(self.app_controller, "streamer_updated"):
            self.app_controller.streamer_updated.connect(self.load_streamers)
    
    # ==================================================
    # STREAMER
    # ==================================================
    
    def load_streamers(self, streamer_data):
        """
        Callback - kann 2 Formate empfangen:
        1. Von StreamerPage: list[str] (nur Namen)
        2. Von TwitchWatcher: dict (Name + Status)
        """
        # Fall 1: Liste von Namen (von StreamerPage)
        if isinstance(streamer_data, list):
            for name in streamer_data:
                if name not in self.streamer_data:
                    self.streamer_data[name] = {
                        "is_online": False,
                        "title": ""
                    }
        
        # Fall 2: Dict mit Status (von TwitchWatcher)
        elif isinstance(streamer_data, dict):
            name = streamer_data.get("name")
            if name:
                self.streamer_data[name] = {
                    "is_online": streamer_data.get("is_online", False),
                    "title": streamer_data.get("title", "")
                }
        
        # Zeige ALLE Streamer an
        self._refresh_display()
    
    def _refresh_display(self):
        """Aktualisiert die Anzeige mit allen gespeicherten Streamern"""
        # Konvertiere dict zu list für update_streamer_status
        streamers = [
            {
                "name": name,
                "is_online": data["is_online"],
                "title": data["title"]
            }
            for name, data in self.streamer_data.items()
        ]
        
        self.update_streamer_status(streamers)
    
    def update_streamer_status(self, streamers: list | None):
        """Aktualisiert die Streamer-Cards im Dashboard"""
        # alte Cards löschen
        while self.streamer_layout.count() > 1:
            item = self.streamer_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not streamers:
            empty = QLabel("Keine Streamer konfiguriert")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("opacity: 0.6;")
            self.streamer_layout.insertWidget(0, empty)
            self.update_status("Keine Streamer konfiguriert")
            return
        
        online_count = 0
        for s in streamers:
            if isinstance(s, dict):
                name = s.get("name", "Unknown")
                online = s.get("is_online", False)
                title = s.get("title", "")
            else:
                name = getattr(s, "name", "Unknown")
                online = getattr(s, "is_online", False)
                title = getattr(s, "title", "")
            
            if online:
                online_count += 1
            
            card = self._create_streamer_card(name, online, title)
            self.streamer_layout.insertWidget(
                self.streamer_layout.count() - 1,
                card
            )
        
        self.update_status(
            f"👥 {len(streamers)} Streamer überwacht | {online_count} online"
        )
    
    # ==================================================
    # UI
    # ==================================================
    
    def update_status(self, text: str):
        """Aktualisiert das Status-Label"""
        self.status_label.setText(text)
    
    def _create_streamer_card(self, name: str, online: bool, title: str):
        """Erstellt eine Streamer-Status-Card"""
        card = QFrame()
        card.setObjectName("DashboardCard")
        layout = QVBoxLayout(card)
        
        # Status & Name
        status = "🟢 Online" if online else "🔴 Offline"
        name_label = QLabel(f"{status} {name}")
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(name_label)
        
        # Titel (wenn online)
        if online and title:
            title_label = QLabel(f"📺 {title}")
            title_label.setWordWrap(True)
            title_label.setStyleSheet("opacity: 0.8;")
            layout.addWidget(title_label)
        
        return card