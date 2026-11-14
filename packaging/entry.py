"""PyInstaller entry point for CMO-Scenario-Studio.exe."""

import sys

from cmo_studio.app import main

if __name__ == "__main__":
    sys.exit(main())
