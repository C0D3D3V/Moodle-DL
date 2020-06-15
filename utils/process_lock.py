from pathlib import Path

"""
A very simple lock mechanism to prevent multiple downloaders
being started for the same Moodle.

The functions are not resistant to high frequency calls.
Raise conditions will occur!
"""


class LockError(Exception):
    """An Exception which gets thrown if a Downloader is already running"""
    pass


def lock(dir_path: str):
    """
    Tests if a lock is already set in a directory, if not it creates the lock
    """
    path = Path(dir_path) / "running.lock"
    if(Path(path).exists()):
        raise LockError(
            "A downloader is already running." +
            " Delete {} if you think this is wrong.".format(str(path)))
    Path(path).touch()


def unlock(dir_path: str):
    """
    Removes a lock in a directory
    """
    path = Path(dir_path) / "running.lock"
    Path(path).unlink(missing_ok=True)
