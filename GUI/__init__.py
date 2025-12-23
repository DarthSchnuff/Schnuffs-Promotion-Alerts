class Sidebar(QWidget):
    def __init__(self, switch_page_callback):
        super().__init__()
        self.setObjectName("Sidebar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(12)

        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_streamer = QPushButton("Streamer")
        self.btn_settings = QPushButton("Einstellungen")
        self.btn_logs = QPushButton("Logs")

        for btn in (
            self.btn_dashboard,
            self.btn_streamer,
            self.btn_settings,
            self.btn_logs
        ):
            btn.setObjectName("SidebarButton")
            layout.addWidget(btn)

        layout.addStretch()

        # 🔗 Callbacks
        self.btn_dashboard.clicked.connect(lambda: switch_page_callback("dashboard"))
        self.btn_streamer.clicked.connect(lambda: switch_page_callback("streamer"))
        self.btn_settings.clicked.connect(lambda: switch_page_callback("settings"))
        self.btn_logs.clicked.connect(lambda: switch_page_callback("logs"))
