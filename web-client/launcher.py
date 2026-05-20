#!/usr/bin/env python3
"""
NupImposerWeb — system-tray launcher.

On startup:
  1. Starts a local HTTP server on a random port.
  2. Opens the default browser to the app.
  3. Places an icon in the system notification area (system tray).
     - Double-click or select "Open NupImposer Web" to reopen the browser.
     - Select "Quit" to close everything.

Works both as a plain Python script and as a PyInstaller --onefile EXE.
"""
import os
import sys
import socket
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resource_dir() -> str:
    """Absolute path to the directory containing nup_imposer_web.html."""
    if getattr(sys, "frozen", False):
        # PyInstaller --onefile: data files are extracted to sys._MEIPASS
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=resource_dir(), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass  # silence access log


# ---------------------------------------------------------------------------
# Tray icon image (drawn with Pillow — no external image files needed)
# ---------------------------------------------------------------------------

def _make_icon(size: int = 64):
    """
    Returns a PIL.Image representing the tray icon:
    a blue rounded square containing a 2×2 grid of white rectangles —
    visually referencing the n-up layout concept.
    """
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Blue rounded square background
    r = max(4, size // 7)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r,
                         fill=(37, 99, 235, 255))       # #2563eb

    # 2×2 grid of white "pages" — represent n-up copies
    margin = max(5, size // 7)
    gap    = max(2, size // 14)
    cell   = (size - 2 * margin - gap) // 2

    for row in range(2):
        for col in range(2):
            x = margin + col * (cell + gap)
            y = margin + row * (cell + gap)
            cr = max(1, cell // 6)
            d.rounded_rectangle([x, y, x + cell - 1, y + cell - 1],
                                  radius=cr,
                                  fill=(255, 255, 255, 210))

    return img


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    port   = find_free_port()
    server = HTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    url = f"http://127.0.0.1:{port}/nup_imposer_web.html"

    # --- Browser helpers ---
    def open_browser(icon=None, item=None):
        import webbrowser
        webbrowser.open(url)

    def _delayed_open():
        time.sleep(0.8)
        open_browser()

    # --- Try to use a system-tray icon ---
    try:
        import pystray

        icon_img = _make_icon(64)
        menu = pystray.Menu(
            pystray.MenuItem("Open NupImposer Web", open_browser, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda icon, item: icon.stop()),
        )
        tray = pystray.Icon(
            "NupImposerWeb",
            icon_img,
            f"NupImposer Web  →  localhost:{port}",
            menu,
        )

        def _setup(icon):
            icon.visible = True
            threading.Thread(target=_delayed_open, daemon=True).start()

        tray.run(_setup)          # blocks until Quit is chosen
        server.shutdown()

    except Exception:
        # Fallback: no tray available — run with a visible terminal window
        print(f"\n  NupImposer Web  →  {url}")
        print("  Press Ctrl+C to quit.\n", flush=True)
        threading.Thread(target=_delayed_open, daemon=True).start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
