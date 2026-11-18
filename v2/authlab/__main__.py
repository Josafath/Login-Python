"""Entry point: `python -m authlab` (or `authlab` once installed)."""
import argparse
import sys
from pathlib import Path

from .auth import AuthService
from .storage import UserStore

# How to get Tkinter on each OS, shown when it's missing instead of a traceback.
TK_HELP = {
    "win32": "Re-run the python.org installer, choose 'Modify' and tick 'tcl/tk and IDLE'.",
    "darwin": "Install Python from python.org (includes Tk), or with Homebrew: brew install python-tk",
    "linux": "Install it with your package manager, e.g. sudo apt install python3-tk",
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="authlab", description="Sign up / log in app built on hand-written algorithms.")
    parser.add_argument("--data-file", type=Path, help="where to keep the users file")
    args = parser.parse_args()
    try:
        from .gui import run  # imported late so --help works without Tk installed
    except ImportError:
        hint = TK_HELP.get(sys.platform, TK_HELP["linux"])
        sys.exit(f"This app needs Tkinter, which isn't available in this Python.\n{hint}")

    run(AuthService(UserStore(args.data_file)))


if __name__ == "__main__":
    main()
