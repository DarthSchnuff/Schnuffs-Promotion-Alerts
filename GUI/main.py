import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow
from pathlib import Path

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # wichtig für Systray

    style_path = Path(__file__).parent / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
