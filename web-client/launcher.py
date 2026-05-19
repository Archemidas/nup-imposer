#!/usr/bin/env python3
"""
NupImposerWeb — local HTTP launcher.

Serves nup_imposer_web.html on a random localhost port and opens the
default browser automatically.  Works both in source form and as a
PyInstaller --onefile executable.

Press Ctrl+C (or close the window) to stop the server.
"""
import os
import sys
import socket
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler


def resource_dir() -> str:
    """Return the directory that contains nup_imposer_web.html."""
    if getattr(sys, "frozen", False):
        # PyInstaller --onefile extracts data files to sys._MEIPASS
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Handler(SimpleHTTPRequestHandler):
    """Quiet handler that serves files from the resource directory."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=resource_dir(), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass  # comment out to re-enable access log


def main() -> None:
    port = find_free_port()
    server = HTTPServer(("127.0.0.1", port), _Handler)

    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()

    url = f"http://127.0.0.1:{port}/nup_imposer_web.html"
    print(f"\n  NupImposer Web  ->  {url}\n  Close this window to stop.\n", flush=True)

    def _open_browser():
        time.sleep(0.7)
        import webbrowser
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
