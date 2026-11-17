#!/usr/bin/env python
import os
import subprocess
import sys
from pathlib import Path


def _use_project_venv():
    """If launched with a Python outside the project's venv, re-run with the venv's Python.

    Lets `python manage.py ...` work even when the venv hasn't been activated.
    """
    root = Path(__file__).resolve().parent.parent
    candidates = [root / "venv" / "Scripts" / "python.exe", root / "venv" / "bin" / "python"]
    venv_python = next((p for p in candidates if p.exists()), None)
    if venv_python is None or os.environ.get("RAFIKI_NO_VENV_SWITCH"):
        return
    if Path(sys.prefix).resolve() == venv_python.parent.parent.resolve():
        return  # already inside the venv
    env = {**os.environ, "RAFIKI_NO_VENV_SWITCH": "1"}
    sys.exit(subprocess.call([str(venv_python), *sys.argv], env=env))


def main():
    _use_project_venv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
