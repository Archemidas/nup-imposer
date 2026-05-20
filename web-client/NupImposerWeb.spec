# -*- mode: python ; coding: utf-8 -*-
"""
NupImposerWeb.spec — PyInstaller build spec.

Build (from the web-client/ directory):
    pyinstaller NupImposerWeb.spec

Output:
    dist/NupImposerWeb.exe   (Windows)
    dist/NupImposerWeb       (macOS / Linux)

The executable bundles launcher.py + nup_imposer_web.html.  On launch it
starts a local HTTP server, places a system-tray icon, and opens the
default browser automatically.  Closing via the tray "Quit" item shuts
everything down cleanly.
"""

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[("nup_imposer_web.html", ".")],
    hiddenimports=[
        # pystray Windows backend
        "pystray._win32",
        # Pillow core (icon drawing)
        "PIL._imaging",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "PIL.ImageChops",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Strip large stdlib modules we never use
        "tkinter", "unittest", "email", "http.cookiejar",
        "xmlrpc", "distutils", "ensurepip", "lib2to3",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="NupImposerWeb",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # No terminal window — tray icon is the UI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
