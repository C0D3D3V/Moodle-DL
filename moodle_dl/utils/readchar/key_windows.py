# -*- coding: utf-8 -*-

# common
LF = "\x0a"
CR = "\x0d"
ENTER = CR
BACKSPACE = "\x08"
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

# Windows uses scan codes for extended characters. This dictionary
# translates the second half of the scan codes of special Keys
# into the corresponding variable used by readchar.
#
# for windows scan codes see:
#   https://msdn.microsoft.com/en-us/library/aa299374
#      or
#   https://www.freepascal.org/docs-html/rtl/keyboard/kbdscancode.html

# cursors
UP = "\x00\x48"
DOWN = "\x00\x50"
LEFT = "\x00\x4b"
RIGHT = "\x00\x4d"

# other
ESC_2 = "\x00\x01"
ENTER_2 = "\x00\x1c"
F1 = "\x00\x3b"
F2 = "\x00\x3c"
F3 = "\x00\x3d"
F4 = "\x00\x3e"
F5 = "\x00\x3f"
F6 = "\x00\x40"
F7 = "\x00\x41"
F8 = "\x00\x42"
F9 = "\x00\x43"
F10 = "\x00\x44"
F11 = "\x00\x85"  # only in second source
F12 = "\x00\x86"  # only in second source

# don't have table entries for...
# ALT_[A-Z]
# CTRL_ALT_A, # Ctrl-Alt-A, etc.
# CTRL_ALT_SUPR,
# CTRL-F1

PAGE_UP = "\x00\x49"
PAGE_DOWN = "\x00\x51"
HOME = "\x00\x47"
END = "\x00\x4f"

INSERT = "\x00\x52"
SUPR = "\x00\x53"  # key.py uses SUPR not DELETE
