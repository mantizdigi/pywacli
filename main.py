import sys
import os

sys.path.append(os.path.dirname(__file__))

from src.cli.__main__ import app

if __name__ == "__main__":
    app()
