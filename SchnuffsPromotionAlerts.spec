# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules
from glob import glob
block_cipher = None

# ================= HIDDEN IMPORTS =================
hiddenimports = []
hiddenimports += collect_submodules("pages")
hiddenimports += collect_submodules("services")
hiddenimports += collect_submodules("core")
hiddenimports += collect_submodules("tools")

# 🔥 EXTERNE LIBRARIES EXPLIZIT
hiddenimports += [
    "cv2",
    "requests",
    "urllib3",
    "certifi",
    "idna",
    "charset_normalizer",
]

# ================= ANALYSIS =================
a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        *[(f, "assets") for f in glob("assets/*")],  # packt alle Dateien im assets-Ordner
        ("data/settings.json", "data"), # Template Settings (leer)
        ("data/streamers.json", "data"),# Template Streamer-Liste (leer)
        ("style.qss", "."),             # Stylesheet
        ("services", "services"),       # alle Services, außer streamdeck
        ("pages", "pages"),             # GUI-Seiten
        ("core", "core"),               # Kernlogik
        ("tools", "tools"),             # Webcam-Tools
    ],
    hiddenimports=hiddenimports,
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

# ================= PYZ =================
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# ================= EXE =================
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SchnuffsPromotionAlerts",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/SchnuffTwitchAlertIcon.ico",
)
