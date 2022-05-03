# python-readchar is an open-source project hosted here: https://github.com/magmax/python-readchar
# It is licensed under MIT license
# We include it in our project to have control over the changes
import sys


if sys.platform.startswith("linux") or sys.platform == "darwin":
    from moodle_dl.utils.readchar.read_linux import readchar, readkey
    from moodle_dl.utils.readchar import key_linux as key
elif sys.platform in ("win32", "cygwin"):
    from moodle_dl.utils.readchar.read_windows import readchar, readkey
    from moodle_dl.utils.readchar import key_windows as key
else:
    raise NotImplementedError(f"The platform {sys.platform} is not supported yet")


__all__ = ["readchar", "readkey", "key"]
