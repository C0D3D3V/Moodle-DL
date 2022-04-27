# -*- coding: utf-8 -*-

# common
LF = "\x0a"
CR = "\x0d"
ENTER = LF
BACKSPACE = "\x7F"
SPACE = "\x20"
ESC = "\x1b"
TAB = "\x09"

# CTRL
CTRL_A = "\x01"
CTRL_B = "\x02"
CTRL_C = "\x03"
CTRL_D = "\x04"
CTRL_E = "\x05"
CTRL_F = "\x06"
CTRL_G = "\x07"
CTRL_H = "\x08"
CTRL_I = "\t"
CTRL_J = "\n"
CTRL_K = "\x0b"
CTRL_L = "\x0c"
CTRL_M = "\r"
CTRL_N = "\x0e"
CTRL_O = "\x0f"
CTRL_P = "\x10"
CTRL_Q = "\x11"
CTRL_R = "\x12"
CTRL_S = "\x13"
CTRL_T = "\x14"
CTRL_U = "\x15"
CTRL_V = "\x16"
CTRL_W = "\x17"
CTRL_X = "\x18"
CTRL_Y = "\x19"
CTRL_Z = "\x1a"

# ALT
ALT_A = "\x1b\x61"

# CTRL + ALT
CTRL_ALT_A = "\x1b\x01"

# cursors
UP = "\x1b\x5b\x41"
DOWN = "\x1b\x5b\x42"
LEFT = "\x1b\x5b\x44"
RIGHT = "\x1b\x5b\x43"

CTRL_ALT_SUPR = "\x1b\x5b\x33\x5e"

# other
F1 = "\x1b\x4f\x50"
F2 = "\x1b\x4f\x51"
F3 = "\x1b\x4f\x52"
F4 = "\x1b\x4f\x53"
F5 = "\x1b\x4f\x31\x35\x7e"
F6 = "\x1b\x4f\x31\x37\x7e"
F7 = "\x1b\x4f\x31\x38\x7e"
F8 = "\x1b\x4f\x31\x39\x7e"
F9 = "\x1b\x4f\x32\x30\x7e"
F10 = "\x1b\x4f\x32\x31\x7e"
F11 = "\x1b\x4f\x32\x33\x7e"
F12 = "\x1b\x4f\x32\x34\x7e"

PAGE_UP = "\x1b\x5b\x35\x7e"
PAGE_DOWN = "\x1b\x5b\x36\x7e"
HOME = "\x1b\x5b\x48"
END = "\x1b\x5b\x46"

INSERT = "\x1b\x5b\x32\x7e"
SUPR = "\x1b\x5b\x33\x7e"


ESCAPE_SEQUENCES = (
    ESC,
    ESC + "\x5b",
    ESC + "\x5b" + "\x31",
    ESC + "\x5b" + "\x32",
    ESC + "\x5b" + "\x33",
    ESC + "\x5b" + "\x35",
    ESC + "\x5b" + "\x36",
    ESC + "\x5b" + "\x31" + "\x35",
    ESC + "\x5b" + "\x31" + "\x36",
    ESC + "\x5b" + "\x31" + "\x37",
    ESC + "\x5b" + "\x31" + "\x38",
    ESC + "\x5b" + "\x31" + "\x39",
    ESC + "\x5b" + "\x32" + "\x30",
    ESC + "\x5b" + "\x32" + "\x31",
    ESC + "\x5b" + "\x32" + "\x32",
    ESC + "\x5b" + "\x32" + "\x33",
    ESC + "\x5b" + "\x32" + "\x34",
    ESC + "\x4f",
    ESC + ESC,
    ESC + ESC + "\x5b",
    ESC + ESC + "\x5b" + "\x32",
    ESC + ESC + "\x5b" + "\x33",
)
