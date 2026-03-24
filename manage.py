#!/usr/bin/env python3
"""
Django's command-line utility for administrative tasks.
This is a wrapper for frepplectl.py to support standard Django command muscle memory.
"""
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freppledb.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # If Django is not installed, it could be that the virtualenv is not active.
        # So we try to run via frepplectl.py which has auto-venv-activation.
        frepplectl = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frepplectl.py')
        if os.path.exists(frepplectl):
            os.execv(sys.executable, [sys.executable, frepplectl] + sys.argv[1:])
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    
    # Normally we just execute frepplectl.py directly as it handles the frePPLe specific setup
    frepplectl = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frepplectl.py')
    if os.path.exists(frepplectl):
        os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))
        os.execv(sys.executable, [sys.executable, frepplectl] + sys.argv[1:])
    else:
        execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
