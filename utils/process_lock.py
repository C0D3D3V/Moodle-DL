"""
A very simple lock mechanism to prevent multiple downloaders being started for the same Moodle.

The functions are not resistant to high frequency calls.
Raise conditions will occur!
"""

from pathlib import Path


class LockError(Exception):
    """An Exception which gets thrown if a Downloader is already running."""

    pass


def lock(dir_path: str):
    """Test if a lock is already set in a directory, if not it creates the lock."""
    path = Path(dir_path) / 'running.lock'
    if Path(path).exists():
        raise LockError('A downloader is already running. Delete {} if you think this is wrong.'.format(str(path)))
    Path(path).touch()


def unlock(dir_path: str):
    """Remove a lock in a directory."""
    path = Path(dir_path) / 'running.lock'
    try:
        Path(path).unlink()
    except Exception:
        pass
