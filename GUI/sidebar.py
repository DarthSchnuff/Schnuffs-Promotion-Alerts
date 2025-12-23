from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton

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
            for btn in self.buttons:
            btn.setObjectName("SidebarButton")
            self.layout().addWidget(btn)


        layout.addStretch()

        # 🔗 Callbacks
        self.btn_dashboard.clicked.connect(lambda: self.switch("dashboard"))
        self.btn_streamer.clicked.connect(lambda: self.switch("streamer"))
        self.btn_settings.clicked.connect(lambda: self.switch("settings"))
        self.btn_logs.clicked.connect(lambda: self.switch("logs"))

    def switch(self, page_key):
    for btn in self.buttons:
        btn.setProperty("active", False)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

        sender = self.sender()
        sender.setProperty("active", True)
        sender.style().unpolish(sender)
        sender.style().polish(sender)

        self.switch_page(page_key)

