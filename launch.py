"""Start Streamlit on a Python host; optionally prepare a fictional demo."""
import os
from pathlib import Path
import subprocess
import sys

from demo import seed
from store import Store


def prepare_demo():
    enabled = os.environ.get('BRANDSHIELD_DEMO_MODE', '').lower() == 'true'
    if enabled and not Store().has_users():
        seed()


def start_command():
    return [
        sys.executable, '-m', 'streamlit', 'run', 'app.py',
        '--server.address', '0.0.0.0',
        '--server.port', os.environ.get('PORT', '8501'),
        '--server.headless', 'true',
    ]


def main():
    os.chdir(Path(__file__).resolve().parent)
    prepare_demo()
    return subprocess.call(start_command())


if __name__ == '__main__':
    raise SystemExit(main())
