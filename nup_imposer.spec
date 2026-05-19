# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Nup Imposer — single-file portable Windows exe.

Build with:
    pyinstaller nup_imposer.spec --noconfirm

Output:
    dist/NupImposer.exe  — fully self-contained GUI executable.
    No DLL folder, no installation, no terminal window.
    Double-click to open the GUI.  CLI args still work from a terminal.

Switch from --onedir to --onefile:
  binaries + datas are embedded directly in EXE (no COLLECT block).
  First launch extracts to %TEMP%\\_MEIxxxxxx; subsequent launches use the
  same temp folder when the exe has not changed (Windows file-hash cache).
"""

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# ---------------------------------------------------------------------------
# Deep-collect packages that PyInstaller misses with static analysis alone.
# collect_all() returns (datas, binaries, hiddenimports) for the package.
# ---------------------------------------------------------------------------

def _safe_collect(pkg):
    """collect_all wrapper — returns empty lists if the package isn't installed."""
    try:
        return collect_all(pkg)
    except Exception:
        return [], [], []

datas_mupdf,  binaries_mupdf,  hi_mupdf  = _safe_collect('pymupdf')
datas_psd,    binaries_psd,    hi_psd    = _safe_collect('psd_tools')
datas_pillow, binaries_pillow, hi_pillow = _safe_collect('PIL')

a = Analysis(
    ['src/nup_imposer/__main__.py'],
    pathex=['src'],
    binaries=binaries_mupdf + binaries_psd + binaries_pillow,
    datas=datas_mupdf + datas_psd + datas_pillow,
    hiddenimports=[
        # ── Pillow ──────────────────────────────────────────────────────────
        'PIL._imaging',
        'PIL.ImageCms',
        'PIL.ImageQt',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL.TiffImagePlugin',
        'PIL.Jpeg2KImagePlugin',
        'PIL.JpegImagePlugin',
        'PIL.PngImagePlugin',
        'PIL.BmpImagePlugin',
        'PIL.GifImagePlugin',
        'PIL.WebPImagePlugin',
        'PIL.IcoImagePlugin',
        *hi_pillow,
        # ── PyMuPDF / fitz ──────────────────────────────────────────────────
        'fitz',
        'fitz.fitz',
        'pymupdf',
        *hi_mupdf,
        # ── psd-tools ───────────────────────────────────────────────────────
        'psd_tools',
        'psd_tools.api',
        'psd_tools.api.psd_image',
        'psd_tools.compression',
        'psd_tools.constants',
        *hi_psd,
        # ── PyQt6 ───────────────────────────────────────────────────────────
        'PyQt6',
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtOpenGL',
        'PyQt6.QtOpenGLWidgets',
        # ── stdlib / misc ───────────────────────────────────────────────────
        'importlib.metadata',
        'importlib.resources',
        'pkg_resources',
        'colorsys',
        'zlib',
        'struct',
        'logging',
        'logging.handlers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        '_tkinter',
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'numpy.tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------------------------------------------------------------------------
# Single-file EXE — include all binaries and datas inside the exe itself.
# No COLLECT block means no separate DLL folder.
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,   # embed all DLLs / .so files inside the exe
    a.zipfiles,
    a.datas,      # embed Qt plugins, Pillow data, fonts, etc.
    name='NupImposer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,     # compress if UPX is on PATH; no-op otherwise (safe with Qt)
    console=False,  # no terminal window — pure GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('assets', 'icon.ico')
         if os.path.exists(os.path.join('assets', 'icon.ico')) else None,
)
# No COLLECT block → output is dist/NupImposer.exe only.
