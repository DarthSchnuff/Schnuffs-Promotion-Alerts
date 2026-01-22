import sys
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]

def resource_path(relative_path: PathLike) -> Path:
    """
    Gibt den absoluten Pfad zurück, auch wenn die App als EXE gepackt ist.
    """
    try:
        # Pfad, wenn PyInstaller gepackt ist
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # Normaler Start im Projekt
        base_path = Path(__file__).resolve().parents[1]

    return (base_path / relative_path).resolve()


def asset(name: str) -> Path:
    """
    Pfad zu einer Datei im assets-Ordner
    """
    return resource_path(f"assets/{name}")


def data(name: str) -> Path:
    """
    Pfad zu einer Datei im data-Ordner
    """
    return resource_path(f"data/{name}")


def root(name: str) -> Path:
    """
    Pfad zu einer Datei im Projekt-Root (z.B. style.qss)
    """
    return resource_path(name)


def open_data(name: str, mode="r", **kwargs):
    """
    Shortcut für `open(data(...))` – JSON, Logs, Cache etc.
    """
    return open(data(name), mode, **kwargs)


def open_root(name: str, mode="r", **kwargs):
    """
    Shortcut für `open(root(...))` – z.B. style.qss, version.py
    """
    return open(root(name), mode, **kwargs)
