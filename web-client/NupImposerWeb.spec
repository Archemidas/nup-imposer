# -*- mode: python ; coding: utf-8 -*-
"""
NupImposerWeb.spec — PyInstaller build spec.

Build (from the web-client/ directory):
    pyinstaller NupImposerWeb.spec

Output:
    dist/NupImposerWeb.exe   (Windows)
    dist/NupImposerWeb       (macOS / Linux)

The executable bundles launcher.py + nup_imposer_web.html into a single
portable file.  On launch it starts a local HTTP server and opens the
default browser automatically.  All PDF processing happens in the browser
via jsPDF — no Python web framework dependencies required.
"""

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[("nup_imposer_web.html", ".")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude large stdlib modules we don't use
        "tkinter", "unittest", "email", "html", "http.cookiejar",
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
    console=True,    # Shows a small terminal window — closing it stops the server
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
