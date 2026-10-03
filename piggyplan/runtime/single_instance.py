"""单实例互斥锁与已启动窗口的激活。"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from ..constants import APP_MUTEX_NAME, APP_NAME
from .paths import log_event


class SingleInstance:
    """Prevent two desktop processes from writing the same SQLite file."""

    def __init__(self) -> None:
        self.handle: int | None = None

    def acquire(self) -> bool:
        if sys.platform != "win32":
            return True
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, True, APP_MUTEX_NAME)
        if not handle:
            log_event("single-instance mutex could not be created")
            return True
        self.handle = int(handle)
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(ctypes.c_void_p(self.handle))
            self.handle = None
            return False
        return True

    def release(self) -> None:
        if self.handle and sys.platform == "win32":
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(ctypes.c_void_p(self.handle))
            self.handle = None


def activate_existing_window() -> None:
    if sys.platform != "win32":
        return
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    hwnd = user32.FindWindowW(None, APP_NAME)
    if hwnd:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
