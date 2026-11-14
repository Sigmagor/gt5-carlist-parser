import sys
import platform
import ctypes


def beautiful_print(s, bp, window):
    if len(bp) < window:
        print(s)
        bp.append(s + "\033[K")
    else:
        print(f"\033[{window}A", flush=True, end="")
        del bp[0]
        bp.append(s + "\033[K")
        print(*bp, flush=True, sep="\n")


def is_win10():
    if sys.platform != "win32":
        return False
    try:
        ver = platform.version()  # например "10.0.19045"
        parts = ver.split(".")
        major = int(parts[0])
        build = int(parts[2]) if len(parts) > 2 else 0
        return major == 10 and build < 22000
    except Exception as e:
        print(repr(e))
        return False


def enable_ansi_support():
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        new_mode = mode.value | 0x0004
        kernel32.SetConsoleMode(handle, new_mode)
