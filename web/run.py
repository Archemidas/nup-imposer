#!/usr/bin/env python3
"""
Convenience launcher for Nup Imposer Web.

Usage:
    python run.py

The server starts on http://localhost:8000 and the browser opens automatically.
Press Ctrl+C to stop.
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def check_deps():
    missing = []
    for pkg in ["fastapi", "uvicorn", "PIL", "fitz", "multipart"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("Installing required packages…")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r",
             os.path.join(HERE, "requirements.txt")],
            stdout=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    check_deps()
    os.chdir(HERE)   # so main.py can find index.html
    # Import and run after deps are installed
    import threading, time, webbrowser, uvicorn
    from main import app

    def _open():
        time.sleep(1.4)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=_open, daemon=True).start()
    print("\n  Nup Imposer Web  →  http://localhost:8000\n  Press Ctrl+C to stop.\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
