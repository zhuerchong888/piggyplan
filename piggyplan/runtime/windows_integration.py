"""Win32 桥：托盘图标、全局热键与消息泵。"""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from typing import Any
from pathlib import Path

from ..constants import APP_NAME, HOTKEY_DEFAULT
from ..util import display_hotkey, normalize_hotkey
from .paths import log_event


if sys.platform == "win32":
    _WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    class _WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", _WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", ctypes.c_void_p),
            ("hIcon", ctypes.c_void_p),
            ("hCursor", ctypes.c_void_p),
            ("hbrBackground", ctypes.c_void_p),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
        ]

    class _MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt_x", ctypes.c_long),
            ("pt_y", ctypes.c_long),
        ]

    class _NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", ctypes.c_void_p),
            ("szTip", wintypes.WCHAR * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", wintypes.WCHAR * 256),
            ("uTimeout", wintypes.UINT),
            ("szInfoTitle", wintypes.WCHAR * 64),
            ("dwInfoFlags", wintypes.DWORD),
            ("guidItem", ctypes.c_byte * 16),
            ("hBalloonIcon", ctypes.c_void_p),
        ]
else:  # pragma: no cover - the product target is Windows
    _WNDPROC = None
    _WNDCLASSW = None
    _MSG = None
    _NOTIFYICONDATAW = None


class WindowsIntegration:
    """Owns the tray icon, the global hotkey and the message pump.

    `app` is duck-typed: this module calls show_tray_menu / open_quick_add /
    show_main_window on it and reads .settings / .db.  Keeping it untyped here
    is what lets runtime/ stay importable without the UI layer.
    """

    WM_TRAYICON = 0x0401  # WM_USER + 1
    WM_HOTKEY = 0x0312
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONUP = 0x0205
    WM_TASKBARCREATED = 0x0000  # _setup 里用 RegisterWindowMessageW 取真实值
    NIM_ADD = 0x00000000
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    HOTKEY_ID = 0x5047

    def __init__(self, app: "Any") -> None:
        self.app = app
        self.available = False
        self.tray_available = False
        self.hwnd: int | None = None
        self._hotkey_registered = False
        self.current_hotkey: str | None = None
        self.hotkey_error: str | None = None
        self._class_name = f"PiggyPlanMessageWindow_{os.getpid()}"
        self._wnd_proc = None
        self.user32 = None
        self.kernel32 = None
        self.shell32 = None
        if sys.platform == "win32":
            try:
                self._setup()
            except Exception as error:  # pragma: no cover - depends on host Win32 state
                log_event("Windows integration setup failed", error)

    def _setup(self) -> None:
        if _WNDPROC is None or _WNDCLASSW is None or _MSG is None or _NOTIFYICONDATAW is None:
            return
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = ctypes.c_void_p
        self.user32.RegisterClassW.argtypes = [ctypes.POINTER(_WNDCLASSW)]
        self.user32.RegisterClassW.restype = wintypes.ATOM
        self.user32.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self.user32.CreateWindowExW.restype = wintypes.HWND
        self.user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.DefWindowProcW.restype = ctypes.c_ssize_t
        self.user32.PeekMessageW.argtypes = [ctypes.POINTER(_MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
        self.user32.TranslateMessage.argtypes = [ctypes.POINTER(_MSG)]
        self.user32.DispatchMessageW.argtypes = [ctypes.POINTER(_MSG)]
        self.user32.DestroyWindow.argtypes = [wintypes.HWND]
        self.user32.LoadIconW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        self.user32.LoadIconW.restype = ctypes.c_void_p
        self.user32.LoadImageW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.user32.LoadImageW.restype = ctypes.c_void_p
        self.user32.DestroyIcon.argtypes = [ctypes.c_void_p]
        self.user32.DestroyIcon.restype = wintypes.BOOL
        self.user32.LoadCursorW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        self.user32.LoadCursorW.restype = ctypes.c_void_p
        self.shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(_NOTIFYICONDATAW)]
        self.shell32.Shell_NotifyIconW.restype = wintypes.BOOL
        self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user32.RegisterHotKey.restype = wintypes.BOOL
        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.GetCursorPos.argtypes = [ctypes.POINTER(ctypes.c_long * 2)]
        self.user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
        self.user32.RegisterWindowMessageW.restype = wintypes.UINT
        # Explorer 重启后会广播 TaskbarCreated，托盘图标需要重新注册。
        self.WM_TASKBARCREATED = self.user32.RegisterWindowMessageW("TaskbarCreated")

        self._wnd_proc = _WNDPROC(self._window_proc)
        instance = self.kernel32.GetModuleHandleW(None)
        window_class = _WNDCLASSW()
        window_class.lpfnWndProc = self._wnd_proc
        window_class.hInstance = instance
        window_class.hIcon = self.user32.LoadIconW(None, ctypes.cast(ctypes.c_void_p(32512), wintypes.LPCWSTR))
        window_class.hCursor = self.user32.LoadCursorW(None, ctypes.cast(ctypes.c_void_p(32512), wintypes.LPCWSTR))
        window_class.lpszClassName = self._class_name
        if not self.user32.RegisterClassW(ctypes.byref(window_class)):
            error_code = ctypes.get_last_error()
            if error_code != 1410:  # ERROR_CLASS_ALREADY_EXISTS
                raise ctypes.WinError(error_code)
        created = self.user32.CreateWindowExW(0, self._class_name, self._class_name, 0, 0, 0, 0, 0, None, None, instance, None)
        if not created:
            raise ctypes.WinError(ctypes.get_last_error())
        self.hwnd = int(created)
        self.available = True
        self._add_tray_icon()
        self.register_hotkey(self.app.settings.get("global_hotkey", HOTKEY_DEFAULT))
        self.app.after(50, self._pump_messages)

    def _window_proc(self, hwnd, message, wparam, lparam):
        if message == self.WM_TASKBARCREATED and self.hwnd:
            self._add_tray_icon()
            if not self.tray_available:
                self.app.after(3000, self._add_tray_icon)
        elif message == self.WM_HOTKEY and int(wparam) == self.HOTKEY_ID:
            self.app.after_idle(self.app.open_quick_add)
        elif message == self.WM_TRAYICON:
            event = int(lparam) & 0xFFFF
            if event == self.WM_LBUTTONUP:
                self.app.after_idle(self.app.show_main_window)
            elif event == self.WM_RBUTTONUP:
                self.app.after_idle(self.app.show_tray_menu)
        if self.user32:
            return self.user32.DefWindowProcW(hwnd, message, wparam, lparam)
        return 0

    def _pump_messages(self) -> None:
        if not self.available or not self.hwnd or not self.user32 or not _MSG:
            return
        message = _MSG()
        while self.user32.PeekMessageW(ctypes.byref(message), wintypes.HWND(self.hwnd), 0, 0, 1):
            self.user32.TranslateMessage(ctypes.byref(message))
            self.user32.DispatchMessageW(ctypes.byref(message))
        if self.app.winfo_exists():
            self.app.after(50, self._pump_messages)

    @staticmethod
    def _hotkey_parts(value: str) -> tuple[int, int] | None:
        normalized = normalize_hotkey(value)
        if not normalized:
            return None
        parts = normalized.split("+")
        modifiers = 0x4000  # MOD_NOREPEAT
        for part in parts[:-1]:
            modifiers |= {"alt": 0x0001, "ctrl": 0x0002, "shift": 0x0004, "win": 0x0008}.get(part, 0)
        key = parts[-1]
        if len(key) == 1:
            virtual_key = ord(key.upper())
        elif key.startswith("f"):
            virtual_key = 0x6F + int(key[1:])
        else:
            virtual_key = {"space": 0x20, "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28}.get(key, 0)
        return (modifiers, virtual_key) if virtual_key else None

    def register_hotkey(self, value: str | None) -> bool:
        if not self.available or not self.hwnd or not self.user32:
            return False
        normalized = normalize_hotkey(value or HOTKEY_DEFAULT)
        parts = self._hotkey_parts(normalized or "")
        if not parts:
            self.hotkey_error = "快捷键格式无效"
            return False
        previous = self.current_hotkey if self._hotkey_registered else None
        if self._hotkey_registered:
            self.user32.UnregisterHotKey(wintypes.HWND(self.hwnd), self.HOTKEY_ID)
            self._hotkey_registered = False
        registered = bool(self.user32.RegisterHotKey(wintypes.HWND(self.hwnd), self.HOTKEY_ID, parts[0], parts[1]))
        if registered:
            self._hotkey_registered = True
            self.current_hotkey = normalized
            self.hotkey_error = None
        else:
            self.hotkey_error = f"{display_hotkey(normalized)} 与其他软件冲突"
            log_event(f"global hotkey registration failed: {display_hotkey(normalized)}")
            if previous:
                old_parts = self._hotkey_parts(previous)
                if old_parts and self.user32.RegisterHotKey(wintypes.HWND(self.hwnd), self.HOTKEY_ID, old_parts[0], old_parts[1]):
                    self._hotkey_registered = True
                    self.current_hotkey = previous
        return registered

    def _add_tray_icon(self) -> None:
        if not self.user32 or not self.shell32 or not self.hwnd or not _NOTIFYICONDATAW:
            return
        data = _NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(_NOTIFYICONDATAW)
        data.hWnd = wintypes.HWND(self.hwnd)
        data.uID = 1
        data.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
        data.uCallbackMessage = self.WM_TRAYICON
        icon_path = Path(__file__).resolve().parents[2] / "icon.ico"
        self._owned_tray_icon = self.user32.LoadImageW(None, str(icon_path), 1, 16, 16, 0x0010)
        data.hIcon = self._owned_tray_icon or self.user32.LoadIconW(None, ctypes.cast(ctypes.c_void_p(32512), wintypes.LPCWSTR))
        data.szTip = APP_NAME
        self._tray_data = data
        self.tray_available = bool(self.shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(data)))
        if not self.tray_available:
            log_event("system tray icon registration failed")

    def cursor_position(self) -> tuple[int, int]:
        if self.user32:
            point = (ctypes.c_long * 2)()
            if self.user32.GetCursorPos(ctypes.byref(point)):
                return int(point[0]), int(point[1])
        return (self.app.winfo_rootx() + 20, self.app.winfo_rooty() + 20)

    def destroy(self) -> None:
        if not self.user32:
            return
        if self._hotkey_registered and self.hwnd:
            self.user32.UnregisterHotKey(wintypes.HWND(self.hwnd), self.HOTKEY_ID)
            self._hotkey_registered = False
        if self.hwnd and self.shell32 and hasattr(self, "_tray_data"):
            self.shell32.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(self._tray_data))
        if self.hwnd:
            self.user32.DestroyWindow(wintypes.HWND(self.hwnd))
        if getattr(self, "_owned_tray_icon", None):
            self.user32.DestroyIcon(self._owned_tray_icon)
            self._owned_tray_icon = None
        self.hwnd = None
        self.available = False
        self.tray_available = False
