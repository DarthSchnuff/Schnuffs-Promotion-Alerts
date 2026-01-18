import os
import sys
import winshell
from win32com.client import Dispatch


APP_NAME = "Schnuffs Promotion Alerts"
STARTUP_DIR = winshell.startup()


def get_exe_path():
    # Für .exe (Installer)
    if getattr(sys, "frozen", False):
        return sys.executable
    # Für Entwicklung (python main.py)
    return os.path.abspath(sys.argv[0])


def shortcut_path():
    return os.path.join(STARTUP_DIR, f"{APP_NAME}.lnk")


def is_enabled() -> bool:
    return os.path.exists(shortcut_path())


def enable():
    path = shortcut_path()
    target = get_exe_path()

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = target
    shortcut.WorkingDirectory = os.path.dirname(target)
    shortcut.IconLocation = target
    shortcut.save()


def disable():
    path = shortcut_path()
    if os.path.exists(path):
        os.remove(path)
