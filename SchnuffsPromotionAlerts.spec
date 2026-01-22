# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_all

block_cipher = None

def _to_2tuples(items):
    """Spec expects (src, dest). Some helpers return (src, dest, typecode)."""
    out = []
    for item in items:
        out.append((item[0], item[1]))
    return out

def _collect_files(folder: Path, prefix: str):
    """
    Collect all files under folder recursively.
    Returns list of (src, dest_dir_inside_bundle).
    Keeps subfolder structure under 'prefix'.
    """
    folder = folder.resolve()
    collected = []
    if not folder.exists():
        return collected

    for p in folder.rglob("*"):
        if not p.is_file():
            continue
        rel_parent = p.relative_to(folder).parent  # '.' or subdir
        if str(rel_parent) == ".":
            dest = prefix
        else:
            dest = f"{prefix}/{rel_parent.as_posix()}"
        collected.append((str(p), dest))
    return collected

# -----------------------------------------------------------------------------
# Paths (spec executed via exec; __file__ may be undefined)
# -----------------------------------------------------------------------------
SPEC_DIR = Path(__spec__.origin).resolve().parent
PROJECT_ROOT = SPEC_DIR
ENTRY_SCRIPT = PROJECT_ROOT / "main.py"

# -----------------------------------------------------------------------------
# Hidden imports
# -----------------------------------------------------------------------------
hiddenimports = []
hiddenimports += collect_submodules("pages")
hiddenimports += collect_submodules("services")
hiddenimports += collect_submodules("core")
hiddenimports += collect_submodules("tools")

hiddenimports += [
    "cv2",
    "requests",
    "urllib3",
    "certifi",
    "idna",
    "charset_normalizer",
]

# -----------------------------------------------------------------------------
# PySide6 / Qt collection (plugins, platforms, dlls)
# -----------------------------------------------------------------------------
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")
hiddenimports += pyside6_hiddenimports

# normalize to (src, dest)
pyside6_datas = _to_2tuples(pyside6_datas)
pyside6_binaries = _to_2tuples(pyside6_binaries)

# -----------------------------------------------------------------------------
# Datas: assets/, data/, style.qss (all EXE-safe, no hard paths)
# -----------------------------------------------------------------------------
datas = []
datas += _collect_files(PROJECT_ROOT / "assets", "assets")
datas += _collect_files(PROJECT_ROOT / "data", "data")

style_file = PROJECT_ROOT / "style.qss"
if style_file.exists():
    datas.append((str(style_file), "."))

# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------
a = Analysis(
    [str(ENTRY_SCRIPT)],
    pathex=[str(PROJECT_ROOT)],
    binaries=pyside6_binaries,
    datas=datas + pyside6_datas,
    hiddenimports=list(dict.fromkeys(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "pytest",
        "unittest",
        "matplotlib",
        "scipy",
        "IPython",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SchnuffsPromotionAlerts",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(PROJECT_ROOT / "assets" / "SchnuffTwitchAlertIcon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="SchnuffsPromotionAlerts",
)
