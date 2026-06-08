import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from pywacli.cli.__main__ import app

if __name__ == "__main__":
    app()
