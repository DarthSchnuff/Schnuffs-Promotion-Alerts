import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from core.app_controller import AppController
from core.paths import root


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # ================= STYLE =================
    style_path = root("style.qss")
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))

    # ================= APP CONTROLLER =================
    controller = AppController()

    # ================= MAIN WINDOW =================
    window = MainWindow(controller)
    window.show()

    # ================= CONTROLLER → UI =================
    controller.status_message.connect(
        window.page_dashboard.update_status
    )

    controller.start()

    # ================= CLEAN EXIT =================
    app.aboutToQuit.connect(controller.shutdown)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
