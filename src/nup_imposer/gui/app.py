"""Qt application bootstrap."""
import sys


def run_gui() -> int:
    """Launch the GUI. Returns process exit code."""
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print(
            "PyQt6 is required for the GUI. Install with:\n"
            "    pip install PyQt6\n"
            "Or use the CLI: python -m nup_imposer <args>",
            file=sys.stderr,
        )
        return 1

    from .main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Nup Imposer")
    app.setOrganizationName("Archemidas")

    window = MainWindow()
    window.show()
    return app.exec()
