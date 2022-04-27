# -*- coding: utf-8 -*-
# This file is based on this gist:
# http://code.activestate.com/recipes/134892/
# So real authors are DannyYoo and company.

import msvcrt


def readchar(blocking=False):
    """reads a single character from the input stream. Retruns None if none is avalable.
    If blocking=True the function waits for the next character."""

    if blocking or msvcrt.kbhit():
        # manual byte decoding because some bytes in windows are not utf-8 encodable.
        return chr(int.from_bytes(msvcrt.getch(), "big"))
    else:
        return None


def readkey():
    """Get a single character on Windows. If an extended key is pressed, the
    Windows scan code is translated into a the unicode sequences readchar
    expects (see key_windows.py)."""

    ch = readchar(blocking=True)

    if ch == "\x03":
        raise KeyboardInterrupt

    # if it is a normal character:
    if ch not in "\x00\xe0":
        return ch

    # if it is a scpeal key, read second half:
    ch2 = readchar()

    return "\x00" + ch2
