# -*- coding: utf-8 -*-
import sys
import termios
import tty
import select


# idea from:
# https://repolinux.wordpress.com/2012/10/09/non-blocking-read-from-stdin-in-python/
# Thanks to REPOLINUX
def kbhit():
    return sys.stdin in select.select([sys.stdin], [], [], 0)[0]


# Initially taken from:
# http://code.activestate.com/recipes/134892/
# Thanks to Danny Yoo
def readchar(blocking=False):
    if not blocking and not kbhit():
        return None
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def readkey():
    """Get a single character on Linux. If an escaped key is pressed, the
    following characters are read as well (see key_linux.py)."""

    c1 = readchar(blocking=True)

    if c1 == "\x03":
        raise KeyboardInterrupt

    if c1 != "\x1B":
        return c1

    c2 = readchar(blocking=True)
    if c2 not in ["\x4F", "\x5B"]:
        return c1 + c2

    c3 = readchar(blocking=True)
    if c3 not in ["\x31", "\x32", "\x33", "\x35", "\x36"]:
        return c1 + c2 + c3

    c4 = readchar(blocking=True)
    if c2 != "\x4F" or c4 not in ["\x30", "\x31", "\x33", "\x34", "\x35", "\x37", "\x38", "\x39"]:
        return c1 + c2 + c3 + c4

    c5 = readchar(blocking=True)
    return c1 + c2 + c3 + c4 + c5
