import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from pywacli.cli.__main__ import app

if __name__ == "__main__":
    app()
