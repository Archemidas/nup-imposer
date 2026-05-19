"""Entry point: python -m nup_imposer launches the GUI."""
import sys

from .gui.app import run_gui


def main() -> int:
    """Run the application.

    If called with arguments, route to CLI. Otherwise launch the GUI.
    """
    if len(sys.argv) > 1 and sys.argv[1] not in ("--gui", "-g"):
        from .cli import main as cli_main
        return cli_main()
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
