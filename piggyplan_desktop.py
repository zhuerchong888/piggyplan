"""PiggyPlan native Windows desktop application.

The app deliberately uses only Python's standard library: Tkinter for the
window and sqlite3 for local persistence.  This keeps the first desktop build
offline-friendly and makes it straightforward to package with PyInstaller
later, while keeping the data model close to the product specification.
"""

from __future__ import annotations

import ctypes
import json
import os
import sqlite3
import sys
import tempfile
from ctypes import wintypes
from datetime import date, datetime
from pathlib import Path
from typing import Any

def _prepare_tcl_runtime() -> None:
    """Repair the library search path on Python builds with a relocated Tcl."""

    if sys.platform != "win32":
        return
    candidates: list[tuple[Path, Path, Path]] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        root = Path(bundle_root)
        candidates.append((root / "_tcl_data", root / "_tk_data", root / "tcl86t.dll"))
    install_root = Path(sys.base_prefix)
    candidates.append((install_root / "tcl" / "tcl8.6", install_root / "tcl" / "tk8.6", install_root / "DLLs" / "tcl86t.dll"))
    runtime = next(((tcl_dir, tk_dir, dll) for tcl_dir, tk_dir, dll in candidates if tcl_dir.is_dir() and dll.is_file()), None)
    if runtime is None:
        return
    tcl_library, tk_library, tcl_dll = runtime
    try:
        # PyInstaller's generic runtime hook exports TCL_LIBRARY.  On this
        # Windows Tcl build that environment override is rejected even though
        # init.tcl is present; the Tcl API path below is the reliable source.
        if not bundle_root:
            os.environ.pop("TCL_LIBRARY", None)
        if tk_library.is_dir():
            os.environ["TK_LIBRARY"] = str(tk_library)
        tcl = ctypes.CDLL(str(tcl_dll))
        tcl.Tcl_FindExecutable.argtypes = [ctypes.c_char_p]
        tcl.Tcl_FindExecutable(str(sys.executable).encode())
        tcl.Tcl_NewStringObj.argtypes = [ctypes.c_char_p, ctypes.c_int]
        tcl.Tcl_NewStringObj.restype = ctypes.c_void_p
        tcl.TclSetLibraryPath.argtypes = [ctypes.c_void_p]
        tcl.TclSetLibraryPath.restype = None
        path = str(tcl_library).replace("\\", "/").encode()
        tcl.TclSetLibraryPath(tcl.Tcl_NewStringObj(path, -1))
    except (AttributeError, OSError):
        # A normally installed Python does not need this compatibility hook.
        pass


_prepare_tcl_runtime()

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from piggyplan.constants import APP_MUTEX_NAME, APP_NAME, APP_VERSION, HOTKEY_DEFAULT, THEMES
from piggyplan.database import Database
from piggyplan.runtime.paths import app_backup_dir, app_data_dir, app_log_dir, log_event
from piggyplan.util import (category_label, date_text, display_hotkey, end_of_week,
                            normalize_hotkey, offset_date, parse_date, set_windows_autostart,
                            split_tags, start_of_week, today_key, today_text)


def run_self_test() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        db = Database(root / "test.db", seed=False)
        assert db.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()[0] == "1"
        goal_id = db.create_goal("测试目标")
        task_id = db.create_task("测试待办", planned_date=today_key(), goal_id=goal_id, tags=["测试"])
        assert db.goal_stats(goal_id)["progress"] == 0
        assert db.plan_stats(today_key(), today_key())["total"] == 1
        db.toggle_task(task_id)
        assert db.get_task(task_id)["status"] == "completed"
        assert db.goal_stats(goal_id)["progress"] == 100
        assert db.plan_stats(today_key(), today_key())["rate"] == 100
        db.toggle_task(task_id)
        assert db.get_task(task_id)["status"] == "todo"
        db.update_task(task_id, {"planned_date": offset_date(2)})
        assert db.plan_stats(today_key(), today_key())["total"] == 1
        db.delete_task(task_id)
        db.restore_task(task_id)
        assert db.get_task(task_id)["status"] == "todo"

        future_old = offset_date(3)
        future_new = offset_date(4)
        future_task = db.create_task("提前改期", planned_date=future_old)
        db.update_task(future_task, {"planned_date": future_new})
        old_plan = db.conn.execute("SELECT cancelled_before_due FROM task_plan_history WHERE task_id=? AND planned_date=?", (future_task, future_old)).fetchone()
        assert old_plan[0] == 1

        overdue_day = offset_date(-2)
        overdue_task = db.create_task("逾期改期", planned_date=overdue_day)
        db.update_task(overdue_task, {"planned_date": offset_date(2)})
        assert db.plan_stats(overdue_day, overdue_day) == {"total": 1, "on_time": 0, "rate": 0}

        restore_task = db.create_task("删除后恢复", planned_date=offset_date(5))
        db.delete_task(restore_task)
        assert db.conn.execute("SELECT cancelled_before_due FROM task_plan_history WHERE task_id=?", (restore_task,)).fetchone()[0] == 1
        db.restore_task(restore_task)
        assert db.conn.execute("SELECT cancelled_before_due FROM task_plan_history WHERE task_id=?", (restore_task,)).fetchone()[0] == 0

        sqlite_backup = root / "snapshot.db"
        db.backup_database(sqlite_backup)
        copy = sqlite3.connect(sqlite_backup)
        try:
            assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            copy.close()

        json_backup = root / "backup.json"
        db.export_json(json_backup)
        restored = Database(root / "restored.db", seed=False)
        restored.import_json(json_backup)
        assert len(restored.list_tasks(include_completed=True, status="all")) == len(db.list_tasks(include_completed=True, status="all"))
        before_invalid = len(restored.list_tasks(include_completed=True, status="all"))
        invalid_backup = root / "invalid.json"
        invalid_backup.write_text(json.dumps({"tasks": [{"id": "bad", "title": "无效关联", "goal_id": "missing"}], "goals": []}, ensure_ascii=False), encoding="utf-8")
        try:
            restored.import_json(invalid_backup)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid backup was accepted")
        assert len(restored.list_tasks(include_completed=True, status="all")) == before_invalid
        restored.close()
        db.close()
    print("desktop-database-self-test: ok")


def run_gui_smoke_test() -> None:
    """Build one hidden native window and render every main page once."""

    with tempfile.TemporaryDirectory() as folder:
        database = Database(Path(folder) / "gui-smoke.db", seed=False)
        goal_id = database.create_goal("界面测试目标")
        task_id = database.create_task("界面测试待办", planned_date=today_key(), goal_id=goal_id, tags=["界面"], subtasks=["步骤一", "步骤二"])
        app = None
        try:
            app = PiggyPlanApp(database=database)
            app.withdraw()
            for view in ("today", "upcoming", "all", "goals", "archive", "settings"):
                app.navigate(view)
                app.update_idletasks()
                app.update()
            app.open_task_dialog(task_id)
            app.update_idletasks()
            app.destroy_top_level()
            app.open_goal_dialog(goal_id)
            app.update_idletasks()
            app.destroy_top_level()
            app.open_filter_dialog()
            app.update_idletasks()
            app.destroy_top_level()
            app.open_quick_add()
            app.update_idletasks()
            app.destroy_top_level()
            app.open_goal_detail(goal_id)
            app._set_goal_mode("board")
            app.update_idletasks()
            app._set_goal_mode("list")
            app.navigate("all")
            app.selected_task_ids.add(task_id)
            app.render()
            app.update_idletasks()
            app.selected_task_ids.clear()
            app._exiting = True
            app.on_close()
        finally:
            if app is not None:
                try:
                    app._exiting = True
                    if app.winfo_exists():
                        app.on_close()
                except tk.TclError:
                    database.close()
            else:
                database.close()
    print("native-gui-smoke-test: ok")


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
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
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
    """Small standard-library Win32 bridge for tray, hotkey and app activation."""

    WM_TRAYICON = 0x0401  # WM_USER + 1
    WM_HOTKEY = 0x0312
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONUP = 0x0205
    NIM_ADD = 0x00000000
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    HOTKEY_ID = 0x5047

    def __init__(self, app: "PiggyPlanApp") -> None:
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
        self.user32.LoadCursorW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        self.user32.LoadCursorW.restype = ctypes.c_void_p
        self.shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(_NOTIFYICONDATAW)]
        self.shell32.Shell_NotifyIconW.restype = wintypes.BOOL
        self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user32.RegisterHotKey.restype = wintypes.BOOL
        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.GetCursorPos.argtypes = [ctypes.POINTER(ctypes.c_long * 2)]

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
        if message == self.WM_HOTKEY and int(wparam) == self.HOTKEY_ID:
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
        data.hIcon = self.user32.LoadIconW(None, ctypes.cast(ctypes.c_void_p(32512), wintypes.LPCWSTR))
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
        self.hwnd = None
        self.available = False
        self.tray_available = False


class PiggyPlanApp(tk.Tk):
    """Native desktop UI.  All writes go through Database."""

    # Warm neutrals keep the pink theme recognisable without turning the
    # workspace into a large coloured panel.  Surfaces are separated by tone
    # and whitespace rather than a grid of hard outlines.
    BG = "#FFF9F8"
    SURFACE = "#FFFFFF"
    SURFACE_SOFT = "#FFF1F5"
    LINE = "#F7E8ED"
    LINE_STRONG = "#EEC6D4"
    TEXT = "#34272C"
    TEXT_SOFT = "#806A72"
    TEXT_FAINT = "#B8A4AC"
    HIGH = "#D95F73"
    WARNING = "#CB8750"
    SUCCESS = "#55A781"

    def __init__(self, database: Database | None = None, start_minimized: bool = False):
        super().__init__()
        self.db = database or Database(app_data_dir() / "piggyplan.db")
        self.settings = self.db.settings()
        defaults = {
            "theme": "pink",
            "default_category": "work",
            "startup_page": "today",
            "close_to_tray": "1",
            "startup_enabled": "0",
            "startup_minimized": "0",
            "global_hotkey": HOTKEY_DEFAULT,
            "reduce_motion": "0",
        }
        for key, value in defaults.items():
            if key not in self.settings:
                self.db.set_setting(key, value)
                self.settings[key] = value
        self.theme_key = self.settings.get("theme", "pink") if self.settings.get("theme", "pink") in THEMES else next(iter(THEMES))
        startup_page = self.settings.get("startup_page", self.settings.get("last_view", "today"))
        self.view = startup_page if startup_page in {"today", "upcoming", "all", "goals", "archive", "settings"} else "today"
        self.selected_goal_id: str | None = None
        self.completed_open = False
        self.all_mode = "list"
        self.goal_mode = "list"
        self.archive_tab = "tasks"
        self.selected_task_ids: set[str] = set()
        self.filter_values = {"category": "all", "priority": "all", "goal": "all", "status": "todo", "tag": "all"}
        self.archive_query = ""
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._search_changed)
        self._search_after: str | None = None
        self.toast: tk.Toplevel | None = None
        self.toast_undo_callback = None
        self.tray_menu: tk.Menu | None = None
        self._exiting = False
        self._compact_window = False
        self._resize_after: str | None = None
        self._natural_day = today_key()
        self._drag_task_id: str | None = None
        self._drag_widget: tk.Widget | None = None
        self._drag_start_y = 0
        self.start_minimized = start_minimized or self.settings.get("startup_minimized") == "1"
        self.configure(bg=self.BG)
        self.title(APP_NAME)
        self.minsize(860, 600)
        geometry = self.settings.get("geometry", "1160x760")
        try:
            self.geometry(geometry)
        except tk.TclError:
            self.geometry("1160x760")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Configure>", self._window_resized)
        self._configure_styles()
        self._build_shell()
        self._bind_shortcuts()
        self.integration = WindowsIntegration(self)
        self.create_daily_backup()
        self.render()
        self.after(60_000, self._check_natural_day)
        if self.start_minimized and self.integration.tray_available:
            self.after(10, self.withdraw)

    @property
    def colors(self) -> dict[str, str]:
        theme = THEMES[self.theme_key]
        return {**theme, "bg": self.BG, "surface": self.SURFACE, "soft_surface": self.SURFACE_SOFT, "line": self.LINE, "text": self.TEXT, "text_soft": self.TEXT_SOFT, "text_faint": self.TEXT_FAINT, "high": self.HIGH, "warning": self.WARNING, "success": self.SUCCESS}

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        colors = self.colors
        style.configure("TEntry", padding=(11, 9), fieldbackground=colors["soft"], background=colors["soft"], foreground=colors["text"], bordercolor=colors["soft"], lightcolor=colors["soft"], darkcolor=colors["soft"], font=("Microsoft YaHei UI", 10))
        style.map("TEntry", bordercolor=[("focus", colors["strong"])], lightcolor=[("focus", colors["strong"])], darkcolor=[("focus", colors["strong"])])
        style.configure("TCombobox", padding=(10, 8), fieldbackground=colors["soft"], background=colors["soft"], foreground=colors["text"], bordercolor=colors["soft"], lightcolor=colors["soft"], darkcolor=colors["soft"], arrowcolor=colors["strong"], font=("Microsoft YaHei UI", 10))
        style.map("TCombobox", bordercolor=[("focus", colors["strong"])], lightcolor=[("focus", colors["strong"])], darkcolor=[("focus", colors["strong"])])
        style.configure("Vertical.TScrollbar", troughcolor=colors["bg"], background=colors["line"], arrowcolor=colors["text_soft"], bordercolor=colors["bg"], lightcolor=colors["bg"], darkcolor=colors["bg"])

    def _build_shell(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.sidebar = tk.Frame(self, width=248, bg=self.colors["soft_surface"], highlightthickness=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.main = tk.Frame(self, bg=self.BG)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)
        self.header = tk.Frame(self.main, bg=self.BG, height=76)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(2, weight=1)
        self.body = tk.Frame(self.main, bg=self.BG)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self.body, bg=self.BG, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self.body, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.page = tk.Frame(self.canvas, bg=self.BG)
        self.page_window = self.canvas.create_window((0, 0), window=self.page, anchor="nw")
        self.page.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.page_window, width=event.width))
        self.page.grid_columnconfigure(0, weight=1)
        self.page.grid_columnconfigure(1, minsize=266)
        self.center = tk.Frame(self.page, bg=self.BG)
        self.center.grid(row=0, column=0, sticky="nsew", padx=(34, 22), pady=(30, 40))
        self.rail = tk.Frame(self.page, bg=self.BG, width=266)
        self.rail.grid(row=0, column=1, sticky="nsew", padx=(0, 34), pady=(30, 40))
        self._build_header()
        self._build_sidebar()

    def _build_header(self) -> None:
        self.header.grid_columnconfigure(0, weight=0)
        self.header.grid_columnconfigure(1, weight=0)
        self.header.grid_columnconfigure(2, weight=1)
        self.header.grid_columnconfigure(3, weight=0)
        self.header_title = tk.Label(self.header, text="今天", bg=self.BG, fg=self.TEXT, font=("Microsoft YaHei UI", 23, "bold"))
        self.header_title.grid(row=0, column=0, sticky="w", padx=(34, 10), pady=(22, 0))
        self.header_caption = tk.Label(self.header, text=today_text(), bg=self.BG, fg=self.TEXT_SOFT, font=("Microsoft YaHei UI", 10))
        self.header_caption.grid(row=1, column=0, sticky="w", padx=(34, 10), pady=(2, 18))
        search_wrap = tk.Frame(self.header, bg=self.BG)
        search_wrap.grid(row=0, column=2, rowspan=2, sticky="ew", padx=26, pady=23)
        search_wrap.grid_columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(search_wrap, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky="ew", ipady=3)
        self.search_entry.insert(0, "")
        self.search_entry.configure(width=32)
        self.new_button = self._button(self.header, "+  新建待办", self.open_new_task, "primary", width=12)
        self.new_button.grid(row=0, column=3, rowspan=2, padx=(0, 34), pady=23, sticky="e")

    def _build_sidebar(self) -> None:
        self.sidebar.grid_rowconfigure(10, weight=1)
        brand = tk.Frame(self.sidebar, bg=self.colors["soft_surface"])
        brand.grid(row=0, column=0, sticky="ew", padx=20, pady=(26, 22))
        self._pig_mark(brand).pack(side="left")
        brand_text = tk.Frame(brand, bg=self.colors["soft_surface"])
        brand_text.pack(side="left", padx=10)
        tk.Label(brand_text, text="日常", bg=self.colors["soft_surface"], fg=self.TEXT, font=("Microsoft YaHei UI", 17, "bold")).pack(anchor="w")
        tk.Label(brand_text, text="PIGGYPLAN · LOCAL FIRST", bg=self.colors["soft_surface"], fg=self.TEXT_FAINT, font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(1, 0))
        self.sidebar_new = self._button(self.sidebar, "+  新建待办", self.open_new_task, "primary", width=24)
        self.sidebar_new.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 20), ipady=4)
        self.nav_frame = tk.Frame(self.sidebar, bg=self.colors["soft_surface"])
        self.nav_frame.grid(row=2, column=0, sticky="new", padx=10)
        self.nav_buttons: dict[str, tk.Button] = {}
        self._nav_button("today", "今日清单", 0)
        self._nav_button("upcoming", "之后安排", 1)
        self._nav_button("all", "全部待办", 2, True)
        tk.Frame(self.nav_frame, bg=self.LINE, height=1).grid(row=3, column=0, sticky="ew", padx=10, pady=(13, 10))
        self._nav_button("goals", "长期目标", 4, True)
        self._nav_button("archive", "完成归档", 5)
        tk.Frame(self.nav_frame, bg=self.LINE, height=1).grid(row=6, column=0, sticky="ew", padx=10, pady=(13, 10))
        self._nav_button("settings", "偏好设置", 7)
        footer = tk.Frame(self.sidebar, bg=self.colors["soft_surface"])
        footer.grid(row=11, column=0, sticky="sew", padx=16, pady=17)
        footer_card = tk.Frame(footer, bg=self.colors["soft"], highlightthickness=0)
        footer_card.pack(fill="x")
        tk.Label(footer_card, text="小猪的本地日常", bg=self.colors["soft"], fg=self.colors["strong"], font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(footer_card, text="数据只保存在本机 SQLite\n不联网，也能安心使用", justify="left", bg=self.colors["soft"], fg=self.TEXT_SOFT, font=("Microsoft YaHei UI", 9)).pack(anchor="w", padx=14, pady=(0, 12))
        tk.Label(footer, text=f"版本 {APP_VERSION}", bg=self.colors["soft_surface"], fg=self.TEXT_FAINT, font=("Microsoft YaHei UI", 8)).pack(anchor="w", pady=(9, 0))

    def _nav_button(self, view: str, text: str, row: int, show_count: bool = False) -> None:
        frame = tk.Frame(self.nav_frame, bg=self.colors["soft_surface"])
        frame.grid(row=row, column=0, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        button = tk.Button(frame, text=text, command=lambda v=view: self.navigate(v), anchor="w", relief="flat", bd=0, padx=14, pady=10, font=("Microsoft YaHei UI", 10), cursor="hand2")
        button.grid(row=0, column=0, sticky="ew")
        if show_count:
            count = tk.Label(frame, text="", width=4, font=("Microsoft YaHei UI", 8, "bold"), padx=4, pady=2)
            count.grid(row=0, column=1, padx=(0, 8))
            button._count_label = count  # type: ignore[attr-defined]
        self.nav_buttons[view] = button

    def _button(self, parent: tk.Misc, text: str, command, kind: str = "ghost", width: int | None = None) -> tk.Button:
        colors = self.colors
        palettes = {
            "primary": (colors["strong"], "#FFFFFF", colors["accent"]),
            "ghost": (colors["soft_surface"], colors["text_soft"], colors["soft"]),
            "outline": (colors["soft"], colors["strong"], colors["accent"]),
            "danger": ("#FFF0F0", "#C9575B", "#F3D4D4"),
            "link": (colors["bg"], colors["strong"], colors["soft"]),
        }
        bg, fg, active = palettes.get(kind, palettes["ghost"])
        button = tk.Button(parent, text=text, command=command, relief="flat", bd=0, bg=bg, fg=fg, activebackground=active, activeforeground=fg, font=("Microsoft YaHei UI", 9, "bold" if kind in ("primary", "link") else "normal"), cursor="hand2", padx=13, pady=8)
        if width:
            button.configure(width=width)
        return button

    def _pig_mark(self, parent: tk.Misc) -> tk.Canvas:
        """Draw a small, crisp pig face without relying on emoji font support."""

        colors = self.colors
        canvas = tk.Canvas(parent, width=44, height=44, bg=self.colors["soft_surface"], highlightthickness=0, bd=0)
        canvas.create_oval(5, 7, 39, 41, fill=colors["accent"], outline="")
        canvas.create_polygon(8, 13, 7, 3, 17, 9, fill=colors["accent"], outline="")
        canvas.create_polygon(36, 13, 37, 3, 27, 9, fill=colors["accent"], outline="")
        canvas.create_oval(14, 18, 17, 21, fill=self.TEXT, outline="")
        canvas.create_oval(27, 18, 30, 21, fill=self.TEXT, outline="")
        canvas.create_oval(15, 25, 29, 35, fill="#F9AFC4", outline="")
        canvas.create_oval(18, 28, 21, 31, fill="#A94E6D", outline="")
        canvas.create_oval(23, 28, 26, 31, fill="#A94E6D", outline="")
        return canvas

    def _label(self, parent: tk.Misc, text: str, size: int = 10, color: str | None = None, bold: bool = False, **kwargs) -> tk.Label:
        return tk.Label(parent, text=text, bg=kwargs.pop("bg", self.BG), fg=color or self.TEXT, font=("Microsoft YaHei UI", size, "bold" if bold else "normal"), **kwargs)

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-n>", lambda _event: self.open_new_task())
        self.bind_all("<Control-f>", lambda _event: self.focus_search())
        self.bind_all("<Control-Key-1>", lambda _event: self.navigate("today"))
        self.bind_all("<Control-Key-2>", lambda _event: self.navigate("upcoming"))
        self.bind_all("<Control-Key-3>", lambda _event: self.navigate("all"))
        self.bind_all("<Escape>", lambda _event: self.destroy_top_level())

    def _search_changed(self, *_args) -> None:
        if self._search_after:
            self.after_cancel(self._search_after)
        self._search_after = self.after(150, self.render)

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, tk.END)

    def destroy_top_level(self) -> None:
        for child in self.winfo_children():
            if isinstance(child, tk.Toplevel):
                child.destroy()
                return

    def show_main_window(self) -> None:
        self.deiconify()
        try:
            self.state("normal")
        except tk.TclError:
            pass
        self.lift()
        self.focus_force()

    def show_tray_menu(self) -> None:
        if not self.integration.tray_available:
            self.show_main_window()
            return
        if self.tray_menu and self.tray_menu.winfo_exists():
            self.tray_menu.destroy()
        remaining = len(self.db.list_tasks())
        startup_label = "开机自启  ✓" if self.settings.get("startup_enabled") == "1" else "开机自启"
        menu = tk.Menu(self, tearoff=0, bg=self.SURFACE, fg=self.TEXT, activebackground=self.colors["soft"], activeforeground=self.TEXT, bd=0, relief="flat", font=("Microsoft YaHei UI", 9))
        menu.add_command(label="快速添加待办", command=self.open_quick_add)
        menu.add_command(label="打开主界面", command=self.show_main_window)
        menu.add_command(label=f"今天剩余 {remaining} 项", command=lambda: self.show_main_window() or self.navigate("today"))
        menu.add_separator()
        menu.add_command(label=startup_label, command=lambda: self._save_startup_enabled(self.settings.get("startup_enabled") != "1"))
        menu.add_separator()
        menu.add_command(label="退出", command=self.quit_from_tray)
        self.tray_menu = menu
        x, y = self.integration.cursor_position()
        menu.tk_popup(x, y)
        menu.grab_release()

    def quit_from_tray(self) -> None:
        self._exiting = True
        self.on_close()

    def open_quick_add(self) -> None:
        existing = getattr(self, "quick_add_dialog", None)
        if existing and existing.winfo_exists():
            existing.deiconify()
            existing.lift()
            existing.focus_force()
            return
        dialog = tk.Toplevel(self)
        self.quick_add_dialog = dialog
        dialog.title("+ 快速添加待办")
        dialog.configure(bg=self.BG)
        dialog.transient(self)
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)
        dialog.geometry("500x286")
        dialog.columnconfigure(0, weight=1)
        self._label(dialog, "+  快速添加待办", 15, self.TEXT, True, bg=self.BG).grid(row=0, column=0, sticky="w", padx=22, pady=(19, 2))
        self._label(dialog, "只记录一个想法也可以，默认不会计入今天的计划。", 9, self.TEXT_SOFT, False, bg=self.BG).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 14))
        title_var = tk.StringVar()
        title_entry = ttk.Entry(dialog, textvariable=title_var, font=("Microsoft YaHei UI", 12))
        title_entry.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 14), ipady=5)
        options = tk.Frame(dialog, bg=self.BG)
        options.grid(row=3, column=0, sticky="ew", padx=22)
        options.grid_columnconfigure(1, weight=1)
        self._label(options, "计划日期", 8, self.TEXT_SOFT, True, bg=self.BG).grid(row=0, column=0, sticky="w", padx=(0, 8))
        date_var = tk.StringVar(value="")
        date_entry = ttk.Entry(options, textvariable=date_var, width=13)
        date_entry.grid(row=0, column=1, sticky="w")
        for label, value in (("未安排", ""), ("今天", today_key()), ("明天", offset_date(1))):
            self._button(options, label, lambda value=value: date_var.set(value), "ghost").grid(row=0, column=2 + ((0 if label == "未安排" else 1) if label != "明天" else 2), padx=(5, 0))
        self._label(options, "格式 YYYY-MM-DD", 8, self.TEXT_FAINT, False, bg=self.BG).grid(row=1, column=1, sticky="w", pady=(3, 0))
        properties = tk.Frame(dialog, bg=self.BG)
        properties.grid(row=4, column=0, sticky="ew", padx=22, pady=(14, 14))
        self._label(properties, "分类", 8, self.TEXT_SOFT, True, bg=self.BG).pack(side="left")
        category_var = tk.StringVar(value=category_label(self.settings.get("default_category", "work")))
        ttk.Combobox(properties, textvariable=category_var, values=["工作", "生活"], state="readonly", width=8).pack(side="left", padx=(7, 20))
        self._label(properties, "优先级", 8, self.TEXT_SOFT, True, bg=self.BG).pack(side="left")
        priority_var = tk.StringVar(value="普通")
        ttk.Combobox(properties, textvariable=priority_var, values=["普通", "高"], state="readonly", width=8).pack(side="left", padx=(7, 0))
        footer = tk.Frame(dialog, bg=self.SURFACE_SOFT, highlightthickness=0)
        footer.grid(row=5, column=0, sticky="ew")
        error = self._label(footer, "", 8, self.HIGH, False, bg=self.SURFACE)
        error.pack(side="left", padx=22)

        def close() -> None:
            if dialog.winfo_exists():
                dialog.destroy()

        def save() -> None:
            title = title_var.get().strip()
            planned = date_var.get().strip() or None
            if not title:
                error.configure(text="标题不能为空")
                title_entry.focus_set()
                return
            if planned and not parse_date(planned):
                error.configure(text="日期格式应为 YYYY-MM-DD")
                date_entry.focus_set()
                return
            self.db.create_task(title, category="life" if category_var.get() == "生活" else "work", priority="high" if priority_var.get() == "高" else "normal", planned_date=planned)
            close()
            if self.state() != "withdrawn":
                self.render()
                self.show_toast("待办已快速添加")

        self._button(footer, "取消", close, "ghost").pack(side="right", padx=(0, 7), pady=10)
        self._button(footer, "保存待办", save, "primary").pack(side="right", padx=(0, 20), pady=10)
        dialog.bind("<Return>", lambda _event: save())
        dialog.bind("<Escape>", lambda _event: close())
        title_entry.focus_set()

    def create_daily_backup(self) -> None:
        """Keep one SQLite snapshot per day and retain the latest 14 snapshots."""

        try:
            folder = app_backup_dir()
            folder.mkdir(parents=True, exist_ok=True)
            destination = folder / f"{date.today().isoformat()}.db"
            if not destination.exists():
                self.db.backup_database(destination)
            snapshots = sorted(folder.glob("*.db"), key=lambda item: item.stat().st_mtime, reverse=True)
            for old in snapshots[14:]:
                old.unlink()
        except Exception as error:
            log_event("daily backup failed", error)

    def export_json(self) -> None:
        path = filedialog.asksaveasfilename(title="导出完整备份", defaultextension=".json", initialfile=f"piggyplan-backup-{date.today().strftime('%Y%m%d')}.json", filetypes=[("JSON 备份", "*.json"), ("所有文件", "*.*")])
        if path:
            try:
                self.db.export_json(path)
                self.show_toast("完整备份已导出")
            except Exception as error:
                log_event("JSON export failed", error)
                messagebox.showerror("导出失败", "完整备份没有成功导出。", parent=self)

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(title="导出历史 CSV", defaultextension=".csv", initialfile=f"piggyplan-history-{date.today().strftime('%Y%m%d')}.csv", filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")])
        if path:
            try:
                self.db.export_csv(path)
                self.show_toast("历史 CSV 已导出")
            except Exception as error:
                log_event("CSV export failed", error)
                messagebox.showerror("导出失败", "历史 CSV 没有成功导出。", parent=self)

    def import_json(self) -> None:
        path = filedialog.askopenfilename(title="从备份恢复", filetypes=[("JSON 备份", "*.json"), ("所有文件", "*.*")])
        if not path:
            return
        if not messagebox.askyesno("覆盖当前数据", "恢复备份会覆盖当前任务、目标、标签和模板。是否继续？", parent=self):
            return
        try:
            before = app_backup_dir() / f"before-import-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            self.db.backup_database(before)
            self.db.import_json(path)
            self.settings = self.db.settings()
            self.theme_key = self.settings.get("theme", "pink") if self.settings.get("theme", "pink") in THEMES else next(iter(THEMES))
            self.selected_goal_id = None
            self.selected_task_ids.clear()
            if self.integration.available:
                self.integration.register_hotkey(self.settings.get("global_hotkey", HOTKEY_DEFAULT))
            self.render()
            self.show_toast("备份已恢复")
        except Exception as error:
            log_event("JSON import failed", error)
            messagebox.showerror("恢复失败", "备份文件无效或无法恢复；当前数据未被覆盖。", parent=self)

    def clear_all(self) -> None:
        if not messagebox.askyesno("清空所有数据", "确定清空全部任务、目标、标签和模板吗？这一步可以通过恢复备份找回。", parent=self):
            return
        try:
            before = app_backup_dir() / f"before-clear-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            self.db.backup_database(before)
            self.db.clear_all()
            self.selected_goal_id = None
            self.selected_task_ids.clear()
            self.render()
            self.show_toast("数据已清空，清空前快照已保留")
        except Exception as error:
            log_event("clear data failed", error)
            messagebox.showerror("操作失败", "数据没有成功清空。", parent=self)

    def open_data_folder(self) -> None:
        folder = self.db.path.parent
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(folder))

    def open_log_folder(self) -> None:
        folder = app_log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(folder))

    def navigate(self, view: str) -> None:
        self.view = view
        self.selected_goal_id = None
        self.selected_task_ids.clear()
        self.search_var.set("")
        self.render()

    def _window_resized(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        compact = int(event.width) < 1080
        if compact == self._compact_window:
            return
        self._compact_window = compact
        if self._resize_after:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(80, self.render)

    def _check_natural_day(self) -> None:
        current = today_key()
        if current != self._natural_day:
            self._natural_day = current
            if self.state() != "withdrawn":
                self.render()
        if self.winfo_exists():
            self.after(60_000, self._check_natural_day)

    def on_close(self) -> None:
        if not self._exiting and self.settings.get("close_to_tray", "1") == "1" and self.integration.tray_available:
            self.withdraw()
            return
        self._exiting = True
        self.db.set_setting("geometry", self.geometry())
        self.db.set_setting("last_view", self.view)
        self.db.set_setting("theme", self.theme_key)
        self.integration.destroy()
        self.db.close()
        self.destroy()

    def clear(self, parent: tk.Misc) -> None:
        for child in parent.winfo_children():
            child.destroy()

    def render(self) -> None:
        self._configure_styles()
        self._refresh_sidebar()
        query = self.search_var.get().strip()
        if self.selected_goal_id:
            title, caption = "目标详情", "把目标落到每一个可以执行的动作上"
            show_rail = False
        elif query:
            title, caption = "搜索", f"正在查找「{query}」"
            show_rail = False
        else:
            title_map = {"today": "今天", "upcoming": "之后", "all": "全部", "goals": "长期目标", "archive": "归档", "settings": "设置"}
            caption_map = {"today": date_text(today_key(), True), "upcoming": "把未来安排看得清楚", "all": "所有未完成事项的全局视图", "goals": "让长期方向有清晰的下一步", "archive": "回看已经完成的事情", "settings": "让软件更贴合你的工作方式"}
            title, caption = title_map.get(self.view, "今天"), caption_map.get(self.view, date_text(today_key(), True))
            show_rail = self.view in {"today", "upcoming", "all"} and not self._compact_window
        self.header_title.configure(text=title)
        self.header_caption.configure(text=caption)
        self.clear(self.center)
        self.clear(self.rail)
        if query:
            self.render_search(self.center, query)
        elif self.selected_goal_id:
            self.render_goal_detail(self.center, self.selected_goal_id)
        elif self.view == "today":
            self.render_today(self.center)
        elif self.view == "upcoming":
            self.render_upcoming(self.center)
        elif self.view == "all":
            self.render_all(self.center)
        elif self.view == "goals":
            self.render_goals(self.center)
        elif self.view == "archive":
            self.render_archive(self.center)
        else:
            self.render_settings(self.center)
        if show_rail:
            self.page.grid_columnconfigure(1, minsize=250)
            self.render_rail(self.rail)
            self.rail.grid()
        else:
            self.page.grid_columnconfigure(1, minsize=0)
            self.rail.grid_remove()
        self.canvas.yview_moveto(0)

    def _refresh_sidebar(self) -> None:
        colors = self.colors
        for view, button in self.nav_buttons.items():
            active = (view == "goals" and self.selected_goal_id) or (view == self.view and not self.search_var.get().strip() and not self.selected_goal_id)
            button.configure(bg=colors["accent"] if active else colors["soft_surface"], fg=colors["strong"] if active else self.TEXT_SOFT, activebackground=colors["soft"] if active else colors["surface"], font=("Microsoft YaHei UI", 10, "bold" if active else "normal"))
            count_label = getattr(button, "_count_label", None)
            if count_label:
                if view == "today":
                    count_label.configure(text=str(len(self.db.list_tasks(mode="default"))))
                elif view == "all":
                    count_label.configure(text=str(len(self.db.list_tasks())))
                elif view == "goals":
                    count_label.configure(text=str(len(self.db.list_goals(status="active"))))
                count_label.configure(bg=colors["accent"] if active else colors["soft_surface"], fg=colors["strong"] if active else self.TEXT_FAINT)

    def page_header(self, parent: tk.Misc, eyebrow: str, title: str, description: str, stat: tuple[str, str] | None = None) -> tk.Frame:
        header = tk.Frame(parent, bg=self.BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 22))
        header.grid_columnconfigure(0, weight=1)
        label = self._label(header, f"PIGGY MOMENT · {eyebrow.upper()}", 8, self.colors["strong"], True)
        label.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self._label(header, title, 22, self.TEXT, True).grid(row=1, column=0, sticky="w")
        self._label(header, description, 9, self.TEXT_SOFT, False, wraplength=610, justify="left").grid(row=2, column=0, sticky="w", pady=(6, 0))
        if stat:
            stat_box = tk.Frame(header, bg=self.colors["soft"], highlightthickness=0)
            stat_box.grid(row=0, column=1, rowspan=3, sticky="e", padx=(18, 0))
            self._label(stat_box, stat[0], 19, self.colors["strong"], True, bg=self.colors["soft"]).pack(anchor="e", padx=18, pady=(13, 0))
            self._label(stat_box, stat[1], 8, self.TEXT_SOFT, False, bg=self.colors["soft"]).pack(anchor="e", padx=18, pady=(0, 13))
        return header

    def section_title(self, parent: tk.Misc, title: str, count: int | None = None, action_text: str | None = None, command=None, color: str | None = None) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.BG)
        left = tk.Frame(frame, bg=self.BG)
        left.pack(side="left")
        dot = tk.Frame(left, width=6, height=6, bg=color or self.colors["strong"])
        dot.pack(side="left", padx=(2, 9), pady=5)
        dot.pack_propagate(False)
        self._label(left, title, 10, color or self.TEXT, True).pack(side="left")
        if count is not None:
            self._label(left, str(count), 8, self.TEXT_FAINT, False).pack(side="left", padx=8)
        if action_text and command:
            self._button(frame, f"+ {action_text}", command, "link").pack(side="right")
        return frame

    def card(self, parent: tk.Misc, padx: int = 16, pady: int = 14) -> tk.Frame:
        frame = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0)
        frame.pack(fill="x", pady=(0, 10))
        frame_inner = tk.Frame(frame, bg=self.SURFACE)
        frame_inner.pack(fill="both", expand=True, padx=padx, pady=pady)
        return frame_inner

    def badge(self, parent: tk.Misc, text: str, bg: str | None = None, fg: str | None = None) -> tk.Label:
        label = tk.Label(parent, text=text, bg=bg or self.colors["soft"], fg=fg or "#A04868", font=("Microsoft YaHei UI", 8, "bold"), padx=7, pady=3)
        return label

    def _scrollable_task_holder(self, parent: tk.Misc) -> tk.Frame:
        holder = tk.Frame(parent, bg=self.BG)
        holder.pack(fill="both", expand=True)
        return holder

    def task_row(self, parent: tk.Misc, task: dict[str, Any], show_date: bool = True, compact: bool = False, selectable: bool = False) -> tk.Frame:
        colors = self.colors
        frame = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0, cursor="hand2")
        frame.pack(fill="x", pady=(0, 9))
        stripe = tk.Frame(frame, width=3, bg=self.HIGH if task["priority"] == "high" else colors["accent"])
        stripe.pack(side="left", fill="y")
        body = tk.Frame(frame, bg=self.SURFACE)
        body.pack(fill="both", expand=True, padx=12, pady=11)
        if selectable:
            chosen = tk.BooleanVar(value=task["id"] in self.selected_task_ids)
            selector = tk.Checkbutton(body, variable=chosen, command=lambda tid=task["id"], var=chosen: self._toggle_selection(tid, var.get()), bg=self.SURFACE, activebackground=self.SURFACE, selectcolor=self.SURFACE, bd=0, highlightthickness=0)
            selector.pack(side="left", padx=(0, 6))
        check = tk.Button(body, text="✓" if task["status"] == "completed" else "·", command=lambda tid=task["id"]: self.toggle_task(tid), width=2, height=1, relief="flat", bd=0, font=("Segoe UI", 10, "bold"), bg=colors["strong"] if task["status"] == "completed" else colors["soft"], fg="white" if task["status"] == "completed" else colors["accent"], activebackground=colors["strong"], activeforeground="white", cursor="hand2", highlightthickness=0)
        check.pack(side="left", padx=(0, 11))
        middle = tk.Frame(body, bg=self.SURFACE)
        middle.pack(side="left", fill="x", expand=True)
        title = self._label(middle, task["title"], 10, self.TEXT_SOFT if task["status"] == "completed" else self.TEXT, True, bg=self.SURFACE, anchor="w")
        title.pack(fill="x")
        if task.get("note") and not compact:
            self._label(middle, task["note"], 8, self.TEXT_FAINT, False, bg=self.SURFACE, anchor="w").pack(fill="x", pady=(3, 0))
        meta = tk.Frame(middle, bg=self.SURFACE)
        meta.pack(fill="x", pady=(6, 0))
        if show_date:
            planned = task.get("planned_date")
            date_color = self.HIGH if planned and planned < today_key() and task["status"] == "todo" else colors["strong"] if planned == today_key() else self.WARNING if planned == offset_date(1) else self.TEXT_FAINT
            self._label(meta, f"◷  {date_text(planned)}", 8, date_color, planned and planned < today_key() and task["status"] == "todo", bg=self.SURFACE).pack(side="left", padx=(0, 11))
        self.badge(meta, "生活" if task["category"] == "life" else "工作", "#FDF2E4" if task["category"] == "life" else colors["soft"], "#A06830" if task["category"] == "life" else "#A04868").pack(side="left", padx=(0, 6))
        for tag in task.get("tags", [])[:2 if not compact else 1]:
            self.badge(meta, f"#{tag}", "#F5EEF0", "#8B6B73").pack(side="left", padx=(0, 5))
        if task.get("goal_title"):
            self.badge(meta, f"◎ {task['goal_title']}", colors["soft"], "#A04868").pack(side="left", padx=(0, 5))
        if task.get("subtasks"):
            done = sum(1 for step in task["subtasks"] if step["completed"])
            self._label(meta, f"☷ {done}/{len(task['subtasks'])}", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(side="left")
        actions = tk.Frame(body, bg=self.SURFACE)
        actions.pack(side="right", padx=(6, 0))
        self._button(actions, "详情", lambda tid=task["id"]: self.open_task_dialog(tid), "ghost").pack(side="left")
        self._button(actions, "⋮", lambda tid=task["id"], widget=frame: self.open_context_menu(tid, widget), "ghost").pack(side="left")
        self._bind_right_click(frame, task["id"])
        frame._task_id = task["id"]  # type: ignore[attr-defined]
        for child in (frame, body, middle, title, meta):
            child.bind("<Double-Button-1>", lambda _event, tid=task["id"]: self.open_task_dialog(tid))
            child.bind("<ButtonPress-1>", lambda event, tid=task["id"], row=frame: self._drag_start(event, tid, row), add="+")
            child.bind("<B1-Motion>", self._drag_motion, add="+")
            child.bind("<ButtonRelease-1>", self._drag_release, add="+")
        return frame

    def _drag_start(self, event: tk.Event, task_id: str, row: tk.Widget) -> None:
        self._drag_task_id = task_id
        self._drag_widget = row
        self._drag_start_y = int(event.y_root)

    def _drag_motion(self, event: tk.Event) -> None:
        if not self._drag_widget or abs(int(event.y_root) - self._drag_start_y) < 5:
            return
        try:
            self._drag_widget.configure(highlightbackground=self.colors["strong"], highlightthickness=2)
        except tk.TclError:
            pass

    def _drag_release(self, event: tk.Event) -> None:
        task_id = self._drag_task_id
        row = self._drag_widget
        self._drag_task_id = None
        self._drag_widget = None
        if not task_id or not row or abs(int(event.y_root) - self._drag_start_y) < 5:
            return
        parent = row.master
        siblings = [child for child in parent.winfo_children() if getattr(child, "_task_id", None)]
        ordered = [getattr(child, "_task_id") for child in siblings]
        if task_id not in ordered:
            return
        ordered.remove(task_id)
        insert_at = len(ordered)
        target_task_id: str | None = None
        for child in siblings:
            child_id = getattr(child, "_task_id")
            if child_id == task_id:
                continue
            middle = child.winfo_rooty() + child.winfo_height() / 2
            if int(event.y_root) < middle:
                insert_at = ordered.index(child_id)
                target_task_id = child_id
                break
        ordered.insert(insert_at, task_id)
        dragged = self.db.get_task(task_id)
        target = self.db.get_task(target_task_id) if target_task_id else (self.db.get_task(ordered[-2]) if len(ordered) > 1 else None)
        if dragged and target and dragged["priority"] != target["priority"]:
            self.db.update_task(task_id, {"priority": target["priority"]})
        self.db.reorder_tasks(ordered)
        self.render()
        self.show_toast("任务顺序已更新")

    def _bind_right_click(self, widget: tk.Misc, task_id: str) -> None:
        widget.bind("<Button-3>", lambda event, tid=task_id: self.open_context_menu(tid, event))
        for child in widget.winfo_children():
            self._bind_right_click(child, task_id)

    def _toggle_selection(self, task_id: str, selected: bool) -> None:
        if selected:
            self.selected_task_ids.add(task_id)
        else:
            self.selected_task_ids.discard(task_id)
        self.render()

    def empty_state(self, parent: tk.Misc, title: str, description: str, command=None) -> None:
        box = tk.Frame(parent, bg=self.SURFACE_SOFT, highlightthickness=0)
        managers = {child.winfo_manager() for child in parent.winfo_children()}
        if "grid" in managers and "pack" not in managers:
            box.grid(sticky="ew", pady=4)
        else:
            box.pack(fill="x", pady=4)
        self._label(box, "🐷", 27, self.colors["strong"], False, bg=self.colors["soft"]).pack(pady=(26, 8), ipadx=14, ipady=7)
        self._label(box, title, 10, self.TEXT, True, bg=self.SURFACE_SOFT).pack()
        self._label(box, description, 8, self.TEXT_SOFT, False, bg=self.SURFACE_SOFT).pack(pady=(4, 0))
        if command:
            self._button(box, "+ 新建第一条", command, "link").pack(pady=(10, 20))
        else:
            self._label(box, "", 6, self.TEXT_SOFT, False, bg=self.SURFACE_SOFT).pack(pady=(0, 16))

    def render_today(self, parent: tk.Misc) -> None:
        tasks = self.db.list_tasks()
        overdue = [task for task in tasks if task.get("planned_date") and task["planned_date"] < today_key()]
        planned_today = [task for task in tasks if task.get("planned_date") == today_key()]
        completed_today = self.db.completed_on(today_key())
        planned_total = len(planned_today) + len([task for task in completed_today if task.get("planned_date") == today_key()])
        done_today = len([task for task in completed_today if task.get("planned_date") == today_key()])
        percent = round(done_today / planned_total * 100) if planned_total else 0
        self.page_header(parent, "执行焦点", "今天要做的事", "逾期不会自动消失，今天只保留真正需要你决定的下一步。", (f"{len(planned_today)} 项", f"今天待办 · {percent}% 已按计划完成"))
        if overdue:
            notice = tk.Frame(parent, bg="#FFF0F1", highlightthickness=0)
            notice.grid(row=1, column=0, sticky="ew", pady=(0, 18))
            self._label(notice, f"🐷  有 {len(overdue)} 项逾期，原计划日期会保留。先处理最重要的一件。", 9, self.HIGH, True, bg="#FFF0EE").pack(side="left", padx=13, pady=11)
            self._button(notice, "查看逾期", lambda: self.canvas.yview_moveto(0.15), "link").pack(side="right", padx=10)
        row = 2
        if overdue:
            self.section_title(parent, "逾期", len(overdue), color=self.HIGH).grid(row=row, column=0, sticky="ew")
            row += 1
            block = tk.Frame(parent, bg=self.BG)
            block.grid(row=row, column=0, sticky="ew", pady=(0, 20))
            for task in overdue:
                self.task_row(block, task)
            row += 1
        self.section_title(parent, "今天", len(planned_today), "添加到今天", lambda: self.open_new_task(date_key=today_key())).grid(row=row, column=0, sticky="ew")
        row += 1
        today_block = tk.Frame(parent, bg=self.BG)
        today_block.grid(row=row, column=0, sticky="ew")
        high = [task for task in planned_today if task["priority"] == "high"]
        normal = [task for task in planned_today if task["priority"] != "high"]
        if high:
            self._label(today_block, "高优先级", 9, self.TEXT_SOFT, True, bg=self.BG).pack(anchor="w", pady=(0, 7))
            for task in high:
                self.task_row(today_block, task, show_date=False)
        if normal:
            self._label(today_block, "普通优先级", 9, self.TEXT_SOFT, True, bg=self.BG).pack(anchor="w", pady=(11, 7) if high else (0, 7))
            for task in normal:
                self.task_row(today_block, task, show_date=False)
        if not planned_today:
            self.empty_state(today_block, "今天没有安排事项", "需要做的事可以先放到之后或未安排。", self.open_new_task)
        row += 1
        completed_box = tk.Frame(parent, bg=self.SURFACE_SOFT, highlightthickness=0)
        completed_box.grid(row=row, column=0, sticky="ew", pady=(20, 0))
        header = tk.Frame(completed_box, bg=self.SURFACE_SOFT)
        header.pack(fill="x")
        arrow = "▾" if self.completed_open else "›"
        self._button(header, f"{arrow}  已完成  {len(completed_today)}", self.toggle_completed, "ghost").pack(side="left", padx=9, pady=6)
        self._label(header, "今天实际完成", 8, self.TEXT_FAINT, False, bg=self.SURFACE_SOFT).pack(side="right", padx=12)
        if self.completed_open:
            for task in completed_today:
                self.task_row(completed_box, task, compact=True)
            if not completed_today:
                self.empty_state(completed_box, "今天还没有完成记录", "完成的事项会在这里留下痕迹。")

    def render_upcoming(self, parent: tk.Misc) -> None:
        self.page_header(parent, "轻量规划", "之后", "未来按日期展开，未安排的想法留在最底部，不占用计划完成率。", (str(len(self.db.list_tasks())), "项未来安排"))
        toolbar = tk.Frame(parent, bg=self.BG)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        self._label(toolbar, "把未来安排放在合适的日期，今天只看今天。", 9, self.TEXT_SOFT, False, bg=self.BG).pack(side="left")
        self._button(toolbar, "+ 添加到明天", lambda: self.open_new_task(date_key=offset_date(1)), "outline").pack(side="right")
        tasks = self.db.list_tasks()
        groups: dict[str, list[dict[str, Any]]] = {}
        for task in tasks:
            if task.get("planned_date") and task["planned_date"] > today_key() or not task.get("planned_date"):
                groups.setdefault(task.get("planned_date") or "unplanned", []).append(task)
        keys = sorted((key for key in groups if key != "unplanned")) + (["unplanned"] if "unplanned" in groups else [])
        row = 2
        if not keys:
            self.empty_state(parent, "之后还没有安排", "把想法记录下来，或为待办选一个未来日期。", self.open_new_task)
            return
        for key in keys:
            title = "未安排" if key == "unplanned" else date_text(key)
            subtitle = "先记录，之后再决定" if key == "unplanned" else key
            self.section_title(parent, f"{title}  ·  {subtitle}", len(groups[key]), "添加", lambda value=None, key=key: self.open_new_task(date_key=None if key == "unplanned" else key)).grid(row=row, column=0, sticky="ew")
            row += 1
            block = tk.Frame(parent, bg=self.BG)
            block.grid(row=row, column=0, sticky="ew", pady=(0, 17))
            for task in sorted(groups[key], key=lambda item: self.db._task_sort_key(item, "upcoming")):
                self.task_row(block, task, show_date=False)
            row += 1

    def render_all(self, parent: tk.Misc) -> None:
        tasks = self.db.list_tasks(include_completed=self.filter_values["status"] != "todo", mode="all", category=self.filter_values["category"], priority=self.filter_values["priority"], status=self.filter_values["status"])
        tasks = self._apply_task_filters(tasks)
        self.page_header(parent, "全局掌握", "全部待办", "工作与生活放在同一条执行线上，日期通过显式操作调整。", (str(len(tasks)), "符合当前筛选"))
        toolbar = tk.Frame(parent, bg=self.BG)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 13))
        self._button(toolbar, "筛选", self.open_filter_dialog, "outline").pack(side="left")
        self._label(toolbar, self._filter_summary(), 8, self.TEXT_SOFT, False, bg=self.BG).pack(side="left", padx=9)
        modes = tk.Frame(toolbar, bg=self.SURFACE_SOFT, highlightthickness=0)
        modes.pack(side="right")
        self._button(modes, "列表", lambda: self._set_all_mode("list"), "primary" if self.all_mode == "list" else "ghost").pack(side="left", padx=3, pady=3)
        self._button(modes, "看板", lambda: self._set_all_mode("board"), "primary" if self.all_mode == "board" else "ghost").pack(side="left", padx=3, pady=3)
        if self.selected_task_ids:
            self.render_batch_bar(parent, 2)
            row = 3
        else:
            row = 2
        if self.all_mode == "board":
            self.render_board(parent, tasks, row)
            return
        if not tasks:
            self.empty_state(parent, "没有符合条件的待办", "试试清除筛选，或者新建一条待办。", self.open_new_task)
            return
        for priority, title in (("high", "高优先级"), ("normal", "普通优先级")):
            subset = [task for task in tasks if task["priority"] == priority]
            self.section_title(parent, title, len(subset), color=self.HIGH if priority == "high" else self.TEXT_SOFT).grid(row=row, column=0, sticky="ew")
            row += 1
            block = tk.Frame(parent, bg=self.BG)
            block.grid(row=row, column=0, sticky="ew", pady=(0, 18))
            for task in subset:
                self.task_row(block, task, selectable=True)
            if not subset:
                self._label(block, "这一组暂时是空的。", 8, self.TEXT_FAINT, False, bg=self.BG).pack(anchor="w", padx=12, pady=8)
            row += 1

    def _apply_task_filters(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        relation = self.filter_values.get("goal", "all")
        if relation == "linked":
            tasks = [task for task in tasks if task.get("goal_id")]
        elif relation == "standalone":
            tasks = [task for task in tasks if not task.get("goal_id")]
        tag = self.filter_values.get("tag", "all")
        if tag != "all":
            tasks = [task for task in tasks if tag in task.get("tags", [])]
        return tasks

    def _filter_summary(self) -> str:
        values = []
        if self.filter_values["category"] != "all": values.append("生活" if self.filter_values["category"] == "life" else "工作")
        if self.filter_values["priority"] != "all": values.append("高优" if self.filter_values["priority"] == "high" else "普通")
        if self.filter_values["goal"] != "all": values.append("已关联" if self.filter_values["goal"] == "linked" else "独立")
        if self.filter_values["status"] != "todo": values.append("已完成" if self.filter_values["status"] == "completed" else "全部状态")
        if self.filter_values.get("tag", "all") != "all": values.append(f"#{self.filter_values['tag']}")
        return " · ".join(values) if values else "待办 · 全部分类 · 高优先级置顶"

    def render_batch_bar(self, parent: tk.Misc, row: int) -> None:
        bar = tk.Frame(parent, bg=self.colors["soft"], highlightthickness=0)
        bar.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        self._label(bar, f"已选择 {len(self.selected_task_ids)} 项", 9, "#A04868", True, bg=self.colors["soft"]).pack(side="left", padx=12, pady=9)
        for text, callback in (("清除", lambda: (self.selected_task_ids.clear(), self.render())), ("删除", self.batch_delete), ("设置日期", self.batch_set_date), ("完成", self.batch_complete)):
            self._button(bar, text, callback, "ghost").pack(side="right", padx=(0, 4), pady=4)
        more = tk.Menubutton(bar, text="更多操作 ▾", relief="flat", bd=0, bg=self.SURFACE, fg=self.TEXT_SOFT, activebackground=self.colors["accent"], font=("Microsoft YaHei UI", 9), cursor="hand2", padx=10, pady=7)
        menu = tk.Menu(more, tearoff=0, bg=self.SURFACE, fg=self.TEXT, activebackground=self.colors["soft"], activeforeground=self.TEXT, bd=0)
        menu.add_command(label="分类：工作", command=lambda: self.batch_set("category", "work"))
        menu.add_command(label="分类：生活", command=lambda: self.batch_set("category", "life"))
        menu.add_separator()
        menu.add_command(label="优先级：高", command=lambda: self.batch_set("priority", "high"))
        menu.add_command(label="优先级：普通", command=lambda: self.batch_set("priority", "normal"))
        menu.add_separator()
        menu.add_command(label="挂载到目标", command=self.batch_attach_goal)
        menu.add_command(label="解除目标关联", command=lambda: self._batch_set_goal(None))
        more.configure(menu=menu)
        more.pack(side="right", padx=(0, 4), pady=4)

    def render_board(self, parent: tk.Misc, tasks: list[dict[str, Any]], row: int, goal_id: str | None = None) -> None:
        board = tk.Frame(parent, bg=self.BG)
        board.grid(row=row, column=0, sticky="ew")
        todo = [task for task in tasks if task["status"] == "todo"]
        completed = self.db.list_tasks(include_completed=True, status="completed", category=self.filter_values["category"], priority=self.filter_values["priority"], goal_id=goal_id)
        completed = self._apply_task_filters(completed)
        for col, (title, values, status) in enumerate((("待办", todo, "todo"), ("已完成", completed, "completed"))):
            column = tk.Frame(board, bg=self.SURFACE_SOFT, highlightthickness=0)
            column.grid(row=0, column=col, sticky="nsew", padx=(0, 10) if col == 0 else (10, 0))
            board.grid_columnconfigure(col, weight=1)
            head = tk.Frame(column, bg=self.SURFACE_SOFT)
            head.pack(fill="x", padx=14, pady=12)
            self._label(head, title, 10, self.TEXT, True, bg=self.SURFACE_SOFT).pack(side="left")
            self.badge(head, str(len(values)), self.SURFACE, self.TEXT_SOFT).pack(side="right")
            body = tk.Frame(column, bg=self.SURFACE_SOFT)
            body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            if values:
                for task in values:
                    self.task_row(body, task, compact=True, selectable=True)
            else:
                self._label(body, "这一栏暂时是空的。", 8, self.TEXT_FAINT, False, bg=self.SURFACE_SOFT).pack(anchor="w", padx=8, pady=14)

    def render_goals(self, parent: tk.Misc) -> None:
        goals = self.db.list_goals(status="active")
        active_count = len(goals)
        average = round(sum(goal["progress"] for goal in goals) / active_count) if active_count else 0
        self.page_header(parent, "长期方向", "长期目标", "目标只负责承载成果，真正推进它的，是一件件进入待办的具体动作。", (f"{active_count} 个", f"进行中目标 · 平均 {average}%"))
        toolbar = tk.Frame(parent, bg=self.BG)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 17))
        self._label(toolbar, "所有目标共用工作 / 生活与高 / 普通两套简单规则。", 9, self.TEXT_SOFT, False, bg=self.BG).pack(side="left")
        self._button(toolbar, "+ 新建目标", self.open_new_goal, "primary").pack(side="right")
        filter_bar = tk.Frame(parent, bg=self.BG)
        filter_bar.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self._label(filter_bar, "状态", 8, self.TEXT_FAINT, True, bg=self.BG).pack(side="left", padx=(0, 6))
        for value, title in (("active", "进行中"), ("all", "全部"), ("achieved", "已达成")):
            self._button(filter_bar, title, lambda value=value: self._set_goal_status(value), "primary" if getattr(self, "goal_status", "active") == value else "ghost").pack(side="left", padx=(0, 3))
        self._label(filter_bar, "分类", 8, self.TEXT_FAINT, True, bg=self.BG).pack(side="left", padx=(19, 6))
        for value, title in (("all", "全部"), ("work", "工作"), ("life", "生活")):
            self._button(filter_bar, title, lambda value=value: self._set_goal_category(value), "primary" if getattr(self, "goal_category", "all") == value else "ghost").pack(side="left", padx=(0, 3))
        selected_status = getattr(self, "goal_status", "active")
        selected_category = getattr(self, "goal_category", "all")
        goals = self.db.list_goals(status=selected_status, category=selected_category)
        grid = tk.Frame(parent, bg=self.BG)
        grid.grid(row=3, column=0, sticky="ew")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        if not goals:
            self.empty_state(grid, "还没有符合条件的目标", "设定一个长期目标，把它拆成具体待办。", self.open_new_goal)
            return
        for index, goal in enumerate(goals):
            self.goal_card(grid, goal).grid(row=index // 2, column=index % 2, sticky="nsew", padx=(0, 7) if index % 2 == 0 else (7, 0), pady=(0, 13))

    def goal_card(self, parent: tk.Misc, goal: dict[str, Any]) -> tk.Frame:
        colors = self.colors
        outer = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0, cursor="hand2")
        stripe = tk.Frame(outer, bg=self.HIGH if goal["priority"] == "high" else colors["accent"], height=4)
        stripe.pack(fill="x")
        body = tk.Frame(outer, bg=self.SURFACE)
        body.pack(fill="both", expand=True, padx=15, pady=13)
        top = tk.Frame(body, bg=self.SURFACE)
        top.pack(fill="x")
        title = self._label(top, goal["title"], 11, self.TEXT, True, bg=self.SURFACE, anchor="w")
        title.pack(side="left", fill="x", expand=True)
        self.badge(top, "已达成" if goal["status"] == "achieved" else "进行中", "#E8F5EE" if goal["status"] == "achieved" else colors["soft"], "#4A9B72" if goal["status"] == "achieved" else "#A04868").pack(side="right")
        badges = tk.Frame(body, bg=self.SURFACE)
        badges.pack(fill="x", pady=(8, 0))
        self.badge(badges, "生活" if goal["category"] == "life" else "工作", "#FDF2E4" if goal["category"] == "life" else colors["soft"], "#A06830" if goal["category"] == "life" else "#A04868").pack(side="left", padx=(0, 6))
        if goal["priority"] == "high":
            self.badge(badges, "高优先级", "#FFF0F0", "#C95D61").pack(side="left")
        self._label(body, goal["note"] or "还没有目标说明，把它拆成下一步就好。", 8, self.TEXT_SOFT, False, bg=self.SURFACE, anchor="w", wraplength=330, justify="left").pack(fill="x", pady=(13, 14))
        progress_row = tk.Frame(body, bg=self.SURFACE)
        progress_row.pack(fill="x")
        self._label(progress_row, f"{goal['progress']}%", 18, colors["strong"], True, bg=self.SURFACE).pack(side="left")
        self._label(progress_row, f"{goal['completed']} / {goal['total']} 个待办完成", 8, self.TEXT_SOFT, False, bg=self.SURFACE).pack(side="right", pady=5)
        track = tk.Frame(body, bg=self.SURFACE_SOFT, height=8)
        track.pack(fill="x", pady=(8, 0))
        fill = tk.Frame(track, bg=self.SUCCESS if goal["status"] == "achieved" else colors["accent"], height=8)
        fill.place(relwidth=max(0, min(1, goal["progress"] / 100)), relheight=1)
        footer = tk.Frame(body, bg=self.SURFACE)
        footer.pack(fill="x", pady=(13, 0))
        self._label(footer, f"◷  {date_text(goal['planned_finish_date']) if goal.get('planned_finish_date') else '暂无计划完成日期'}", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(side="left")
        edit = self._button(footer, "编辑", lambda gid=goal["id"]: self.open_goal_dialog(gid), "ghost")
        edit.pack(side="right")
        self._bind_click_recursive(outer, lambda gid=goal["id"]: self.open_goal_detail(gid), skip=(edit,))
        return outer

    def _bind_click_recursive(self, widget: tk.Misc, callback, skip: tuple[tk.Misc, ...] = ()) -> None:
        if widget not in skip:
            widget.bind("<Button-1>", lambda _event: callback())
        for child in widget.winfo_children():
            self._bind_click_recursive(child, callback, skip)

    def render_goal_detail(self, parent: tk.Misc, goal_id: str) -> None:
        goal = self.db.get_goal(goal_id)
        if not goal:
            self.selected_goal_id = None
            self.render_goals(parent)
            return
        back = self._button(parent, "‹  返回长期目标", lambda: self.navigate("goals"), "link")
        back.grid(row=0, column=0, sticky="w", pady=(0, 15))
        summary = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0)
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 22))
        summary.grid_columnconfigure(0, weight=1)
        info = tk.Frame(summary, bg=self.SURFACE)
        info.grid(row=0, column=0, sticky="ew", padx=18, pady=17)
        self._label(info, goal["title"], 18, self.TEXT, True, bg=self.SURFACE).pack(anchor="w")
        badges = tk.Frame(info, bg=self.SURFACE)
        badges.pack(anchor="w", pady=(8, 0))
        self.badge(badges, "生活" if goal["category"] == "life" else "工作", "#FDF2E4" if goal["category"] == "life" else self.colors["soft"], "#A06830" if goal["category"] == "life" else "#A04868").pack(side="left", padx=(0, 6))
        if goal["priority"] == "high": self.badge(badges, "高优先级", "#FFF0F0", "#C95D61").pack(side="left", padx=(0, 6))
        self.badge(badges, "已达成" if goal["status"] == "achieved" else "进行中", "#E8F5EE" if goal["status"] == "achieved" else self.colors["soft"], "#4A9B72" if goal["status"] == "achieved" else "#A04868").pack(side="left")
        self._label(info, goal["note"] or "这个目标还没有说明。", 9, self.TEXT_SOFT, False, bg=self.SURFACE, wraplength=610, justify="left").pack(anchor="w", pady=(10, 10))
        self._label(info, f"◷  {('计划完成 ' + date_text(goal['planned_finish_date'])) if goal.get('planned_finish_date') else '暂未设置计划完成日期'}     ✓  {goal['completed']} / {goal['total']} 个待办", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(anchor="w")
        progress = tk.Frame(summary, bg=self.SURFACE)
        progress.grid(row=0, column=1, sticky="e", padx=22, pady=17)
        self._label(progress, f"{goal['progress']}%", 28, self.colors["strong"], True, bg=self.SURFACE).pack(anchor="e")
        self._label(progress, "自动进度", 8, self.TEXT_SOFT, False, bg=self.SURFACE).pack(anchor="e")
        buttons = tk.Frame(progress, bg=self.SURFACE)
        buttons.pack(anchor="e", pady=(9, 0))
        self._button(buttons, "编辑", lambda gid=goal_id: self.open_goal_dialog(gid), "outline").pack(side="left", padx=(0, 5))
        if goal["status"] == "active": self._button(buttons, "达成目标", lambda gid=goal_id: self.confirm_goal_achieve(gid), "primary").pack(side="left")
        else: self._button(buttons, "恢复进行中", lambda gid=goal_id: self.db.restore_goal(gid) or self.render(), "outline").pack(side="left")
        toolbar = tk.Frame(parent, bg=self.BG)
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 13))
        self._label(toolbar, f"关联待办 · {goal['total']} 项", 9, self.TEXT_SOFT, True, bg=self.BG).pack(side="left")
        self._button(toolbar, "+ 新增关联待办", lambda gid=goal_id: self.open_new_task(goal_id=gid), "outline").pack(side="right")
        self._button(toolbar, "看板", lambda: self._set_goal_mode("board"), "primary" if self.goal_mode == "board" else "ghost").pack(side="right", padx=(0, 4))
        self._button(toolbar, "列表", lambda: self._set_goal_mode("list"), "primary" if self.goal_mode == "list" else "ghost").pack(side="right", padx=(0, 3))
        tasks = self.db.list_tasks(goal_id=goal_id, include_completed=True, status="all")
        todo = [task for task in tasks if task["status"] == "todo"]
        done = [task for task in tasks if task["status"] == "completed"]
        if self.goal_mode == "board":
            self.render_board(parent, tasks, 3, goal_id)
        else:
            body = tk.Frame(parent, bg=self.BG)
            body.grid(row=3, column=0, sticky="ew")
            self._label(body, f"待办  {len(todo)}", 10, self.TEXT, True, bg=self.BG).pack(anchor="w", pady=(0, 8))
            if todo:
                for task in todo:
                    self.task_row(body, task)
            else:
                self.empty_state(body, "这个目标还没有未完成待办", "新增一个具体动作，让目标开始向前。", lambda gid=goal_id: self.open_new_task(goal_id=gid))
            completed = tk.Frame(body, bg=self.SURFACE_SOFT, highlightthickness=0)
            completed.pack(fill="x", pady=(17, 0))
            self._button(completed, f"{'▾' if self.completed_open else '›'}  已完成  {len(done)}", self.toggle_completed, "ghost").pack(side="left", padx=8, pady=6)
            if self.completed_open:
                for task in done:
                    self.task_row(completed, task, compact=True)
        delete_row = tk.Frame(parent, bg=self.BG)
        delete_row.grid(row=4, column=0, sticky="w", pady=(22, 0))
        self._button(delete_row, "删除目标", lambda gid=goal_id: self.confirm_goal_delete(gid), "danger").pack(side="left")
        self._label(delete_row, "删除前会让你选择如何处理关联待办。", 8, self.TEXT_FAINT, False, bg=self.BG).pack(side="left", padx=9)

    def render_archive(self, parent: tk.Misc) -> None:
        self.page_header(parent, "保留痕迹", "归档", "完成不是删除。把已经做过的事情留在这里，之后仍然可以回看。", (str(len(self.db.list_tasks(include_completed=True, status="completed"))), "完成记录"))
        tabs = tk.Frame(parent, bg=self.BG)
        tabs.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        for value, title in (("tasks", "已完成待办"), ("goals", "已达成目标")):
            self._button(tabs, title, lambda value=value: self._set_archive_tab(value), "primary" if self.archive_tab == value else "ghost").pack(side="left", padx=(0, 4))
        controls = tk.Frame(parent, bg=self.BG)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        query_var = tk.StringVar(value=self.archive_query)
        query_var.trace_add("write", lambda *_args: self._archive_query_changed(query_var.get()))
        ttk.Entry(controls, textvariable=query_var, width=30).pack(side="left")
        category_var = tk.StringVar(value=getattr(self, "archive_category", "all"))
        category = ttk.Combobox(controls, textvariable=category_var, values=["全部分类", "工作", "生活"], state="readonly", width=10)
        category.pack(side="right")
        category.bind("<<ComboboxSelected>>", lambda _event: self._set_archive_category({"全部分类": "all", "工作": "work", "生活": "life"}.get(category_var.get(), "all")))
        self._label(controls, "筛选", 8, self.TEXT_FAINT, True, bg=self.BG).pack(side="right", padx=(0, 7))
        if self.archive_tab == "tasks":
            tasks = self.db.list_tasks(include_completed=True, status="completed", category=getattr(self, "archive_category", "all"), query=self.archive_query)
            if not tasks:
                self.empty_state(parent, "还没有已完成待办", "完成的事项会按实际完成日期出现在这里。")
                return
            for task in tasks:
                self.archive_task_row(parent, task)
        else:
            goals = [goal for goal in self.db.list_goals(status="achieved", category=getattr(self, "archive_category", "all"))]
            if not goals:
                self.empty_state(parent, "还没有已达成目标", "目标达成后会永久保留在这里。")
                return
            for goal in goals:
                self.archive_goal_row(parent, goal)

    def archive_task_row(self, parent: tk.Misc, task: dict[str, Any]) -> None:
        row = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0)
        row.grid(sticky="ew", pady=(0, 8))
        body = tk.Frame(row, bg=self.SURFACE)
        body.pack(fill="x", padx=14, pady=11)
        left = tk.Frame(body, bg=self.SURFACE)
        left.pack(side="left", fill="x", expand=True)
        self._label(left, task["title"], 10, self.TEXT, True, bg=self.SURFACE, anchor="w").pack(fill="x")
        goal_label = f"  ·  {task['goal_title']}" if task.get("goal_title") else "  ·  独立待办"
        self._label(left, f"✓  实际完成 {task['completed_at'][:10] if task.get('completed_at') else '未知日期'}   {goal_label}", 8, self.TEXT_FAINT, False, bg=self.SURFACE, anchor="w").pack(fill="x", pady=(4, 0))
        self.badge(body, "已完成", "#E8F5EE", "#4A9B72").pack(side="right", padx=(10, 0))
        self._button(body, "查看", lambda tid=task["id"]: self.open_task_dialog(tid), "ghost").pack(side="right")

    def archive_goal_row(self, parent: tk.Misc, goal: dict[str, Any]) -> None:
        row = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0)
        row.grid(sticky="ew", pady=(0, 8))
        body = tk.Frame(row, bg=self.SURFACE)
        body.pack(fill="x", padx=14, pady=11)
        left = tk.Frame(body, bg=self.SURFACE)
        left.pack(side="left", fill="x", expand=True)
        self._label(left, goal["title"], 10, self.TEXT, True, bg=self.SURFACE, anchor="w").pack(fill="x")
        self._label(left, f"✓  达成于 {goal['achieved_at'][:10] if goal.get('achieved_at') else '未知日期'}   ·   {goal['completed']} / {goal['total']} 个待办", 8, self.TEXT_FAINT, False, bg=self.SURFACE, anchor="w").pack(fill="x", pady=(4, 0))
        self.badge(body, "已达成", "#E8F5EE", "#4A9B72").pack(side="right")
        self._button(body, "查看", lambda gid=goal["id"]: self.open_goal_detail(gid), "ghost").pack(side="right", padx=(0, 8))

    def render_search(self, parent: tk.Misc, query: str) -> None:
        result_tasks = self.db.list_tasks(include_completed=True, status="all", query=query)
        result_goals = self.db.list_goals(status="all", query=query)
        self.page_header(parent, "全局搜索", f"搜索「{query}」", "搜索标题、备注、标签、目标名称和目标说明。", (str(len(result_tasks) + len(result_goals)), "条结果"))
        row = 1
        if self.selected_task_ids:
            self.render_batch_bar(parent, row)
            row += 1
        self._label(parent, f"待办  {len(result_tasks)}", 10, self.TEXT, True, bg=self.BG).grid(row=row, column=0, sticky="w", pady=(0, 9))
        row += 1
        if result_tasks:
            task_block = tk.Frame(parent, bg=self.BG)
            task_block.grid(row=row, column=0, sticky="ew")
            for task in result_tasks:
                self.task_row(task_block, task, selectable=True)
            row += 1
        else:
            self._label(parent, "没有匹配的待办。", 9, self.TEXT_SOFT, False, bg=self.BG).grid(row=row, column=0, sticky="w", padx=7, pady=(0, 18))
            row += 1
        self._label(parent, f"目标  {len(result_goals)}", 10, self.TEXT, True, bg=self.BG).grid(row=row, column=0, sticky="w", pady=(7, 9))
        row += 1
        if result_goals:
            for goal in result_goals:
                self.goal_card(parent, goal).grid(row=row, column=0, sticky="ew", pady=(0, 8))
                row += 1
        else:
            self._label(parent, "没有匹配的目标。", 9, self.TEXT_SOFT, False, bg=self.BG).grid(row=row, column=0, sticky="w", padx=7)

    def render_rail(self, parent: tk.Misc) -> None:
        for child in parent.winfo_children():
            child.destroy()
        colors = self.colors
        goals_card = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0)
        goals_card.pack(fill="x", pady=(0, 14))
        self._label(goals_card, "🐾  长期目标", 10, self.TEXT, True, bg=self.SURFACE).pack(anchor="w", padx=15, pady=(15, 12))
        active = self.db.list_goals(status="active")[:3]
        if active:
            for goal in active:
                item = tk.Frame(goals_card, bg=self.SURFACE, cursor="hand2")
                item.pack(fill="x", padx=15, pady=(0, 13))
                top = tk.Frame(item, bg=self.SURFACE)
                top.pack(fill="x")
                self._label(top, goal["title"], 9, self.TEXT, True, bg=self.SURFACE, anchor="w").pack(side="left", fill="x", expand=True)
                self._label(top, f"{goal['progress']}%", 9, colors["strong"], True, bg=self.SURFACE).pack(side="right")
                track = tk.Frame(item, bg=self.SURFACE_SOFT, height=6)
                track.pack(fill="x", pady=(6, 0))
                tk.Frame(track, bg=colors["accent"], height=6).place(relwidth=max(0, min(1, goal["progress"] / 100)), relheight=1)
                self._label(item, f"{goal['completed']}/{goal['total']} 个待办 · {'高优先' if goal['priority'] == 'high' else '稳步推进'}", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(anchor="w", pady=(5, 0))
                self._bind_click_recursive(item, lambda gid=goal["id"]: self.open_goal_detail(gid))
        else:
            self._label(goals_card, "还没有进行中的目标。", 8, self.TEXT_SOFT, False, bg=self.SURFACE).pack(anchor="w", padx=15, pady=(0, 7))
            self._button(goals_card, "设定一个长期目标 →", self.open_new_goal, "link").pack(anchor="w", padx=15, pady=(0, 13))
        self._button(goals_card, "查看全部目标 →", lambda: self.navigate("goals"), "link").pack(anchor="w", padx=15, pady=(0, 14))
        stats = self.db.weekly_stats()
        stat_card = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0)
        stat_card.pack(fill="x")
        self._label(stat_card, "📊  本周执行", 10, self.TEXT, True, bg=self.SURFACE).pack(anchor="w", padx=15, pady=(15, 3))
        self._label(stat_card, f"{date_text(start_of_week().isoformat())} – {date_text(end_of_week().isoformat())}", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(anchor="w", padx=15, pady=(0, 13))
        for title, value in (("实际完成", stats["actual"]), ("有效计划", stats["total"]), ("计划完成率", f"{stats['rate']}%")):
            line = tk.Frame(stat_card, bg=self.SURFACE)
            line.pack(fill="x", padx=15, pady=(0, 10))
            self._label(line, title, 8, self.TEXT_SOFT, False, bg=self.SURFACE).pack(side="left")
            self._label(line, str(value), 15 if title == "计划完成率" else 13, colors["strong"] if title == "计划完成率" else self.TEXT, True, bg=self.SURFACE).pack(side="right")
        chart = tk.Frame(stat_card, bg=self.SURFACE, height=76)
        chart.pack(fill="x", padx=15, pady=(4, 15))
        chart.pack_propagate(False)
        max_actual = max(1, max(item["actual"] for item in stats["days"]))
        for index, item in enumerate(stats["days"]):
            col = tk.Frame(chart, bg=self.SURFACE)
            col.place(relx=index / 7, rely=0, relwidth=1 / 7, relheight=1)
            bar = tk.Frame(col, bg=colors["strong"] if item["date"] == today_key() else colors["accent"], width=16)
            bar.place(relx=0.5, rely=0.78, anchor="s", relheight=max(0.05, item["actual"] / max_actual * 0.65), relwidth=0.38)
            self._label(col, "今" if item["date"] == today_key() else item["date"][5:].replace("-", "/"), 7, self.TEXT_FAINT, False, bg=self.SURFACE).place(relx=0.5, rely=0.9, anchor="n")

    def render_settings(self, parent: tk.Misc) -> None:
        self.page_header(parent, "工作方式", "设置", "让软件更贴合你的工作方式；数据和备份始终留在本机。", (APP_VERSION, "本地桌面版"))
        row = 1
        self.settings_card(parent, row, "常规", "默认值和窗口行为")
        general = tk.Frame(parent, bg=self.SURFACE)
        general.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13), padx=0)
        self._settings_line(general, "默认分类", "快速新增时使用的分类", "combo", self.settings.get("default_category", "work"), self._save_default_category)
        self._settings_line(general, "默认启动页", "下次打开软件时进入的页面", "combo_page", self.settings.get("startup_page", "today"), self._save_startup_page)
        self._settings_line(general, "开机自启", "登录 Windows 后自动在后台启动 PiggyPlan", "check", self.settings.get("startup_enabled") == "1", self._save_startup_enabled)
        self._settings_line(general, "启动后最小化", "配合开机自启使用，不抢占前台窗口", "check", self.settings.get("startup_minimized") == "1", self._save_startup_minimized)
        self._settings_line(general, "关闭按钮行为", "关闭窗口时隐藏到托盘，或直接退出软件", "combo_close", self.settings.get("close_to_tray", "1"), self._save_close_mode)
        row += 2
        self.settings_card(parent, row, "外观", "浅色主题与动效偏好")
        appearance = tk.Frame(parent, bg=self.SURFACE)
        appearance.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        theme_line = tk.Frame(appearance, bg=self.SURFACE)
        theme_line.pack(fill="x", padx=14, pady=11)
        self._label(theme_line, "主题色", 9, self.TEXT, True, bg=self.SURFACE).pack(side="left")
        theme_choices = tk.Frame(theme_line, bg=self.SURFACE)
        theme_choices.pack(side="right")
        for key, theme in THEMES.items():
            color = theme["accent"]
            tk.Button(theme_choices, text="  ", bg=color, activebackground=theme["strong"], relief="flat", bd=0, width=4, height=2, command=lambda key=key: self.set_theme(key), cursor="hand2", highlightbackground=theme["strong"] if key == self.theme_key else self.SURFACE, highlightthickness=2).pack(side="left", padx=4)
            self._label(theme_choices, theme["name"], 7, self.TEXT_SOFT, False, bg=self.SURFACE).pack(side="left", padx=(0, 8))
        self._settings_line(appearance, "减少动效", "降低页面变化和弹窗动画", "check", self.settings.get("reduce_motion", "0") == "1", self._save_reduce_motion)
        row += 2
        self.settings_card(parent, row, "快捷键", "窗口内快捷操作；全局快速添加可在其他软件前台使用")
        shortcuts = tk.Frame(parent, bg=self.SURFACE)
        shortcuts.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        self._settings_line(shortcuts, "新建待办", "Ctrl + N", "info", "可用")
        self._settings_line(shortcuts, "快速搜索", "Ctrl + F", "info", "可用")
        hotkey_state = "已注册" if self.integration._hotkey_registered else (self.integration.hotkey_error or "不可用")
        self._settings_line(shortcuts, "全局快速添加", "可修改，例如 Ctrl + Alt + T；冲突时会明确提示", "hotkey", self.settings.get("global_hotkey", HOTKEY_DEFAULT), self._save_global_hotkey)
        self._settings_line(shortcuts, "当前状态", "系统会检测快捷键是否被其他软件占用", "info", hotkey_state)
        row += 2
        self.settings_card(parent, row, "数据与备份", "完整备份包含任务、目标、标签、模板和计划历史")
        data = tk.Frame(parent, bg=self.SURFACE)
        data.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        actions = tk.Frame(data, bg=self.SURFACE)
        actions.pack(fill="x", padx=14, pady=12)
        for text, command in (("导出完整备份", self.export_json), ("导出历史 CSV", self.export_csv), ("从备份恢复", self.import_json), ("清空所有数据", self.clear_all), ("打开数据目录", self.open_data_folder), ("打开日志目录", self.open_log_folder)):
            self._button(actions, text, command, "danger" if text == "清空所有数据" else "outline").pack(side="left", padx=(0, 6))
        self._label(data, f"数据库路径：{self.db.path}", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(anchor="w", padx=14, pady=(0, 12))
        row += 2
        self.settings_card(parent, row, "任务模板", "模板不保存旧的日期和目标")
        templates = tk.Frame(parent, bg=self.SURFACE)
        templates.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        values = self.db.list_templates()
        if values:
            for template in values:
                line = tk.Frame(templates, bg=self.SURFACE)
                line.pack(fill="x", padx=14, pady=7)
                self._label(line, template["title"], 9, self.TEXT, True, bg=self.SURFACE).pack(side="left")
                self._label(line, f"{category_label(template['category'])} · {len(template['subtasks'])} 个子步骤", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(side="left", padx=10)
                self._button(line, "使用", lambda item=template: self.open_new_task(template=item), "ghost").pack(side="right")
                self._button(line, "删除", lambda tid=template["id"]: self.delete_template(tid), "ghost").pack(side="right")
        else:
            self._label(templates, "还没有模板。在待办详情中可以保存为模板。", 8, self.TEXT_SOFT, False, bg=self.SURFACE).pack(anchor="w", padx=14, pady=13)
        row += 2
        self.settings_card(parent, row, "本地优先", "隐私与桌面能力")
        local = tk.Frame(parent, bg=self.SURFACE)
        local.grid(row=row + 1, column=0, sticky="ew", pady=(0, 13))
        tray_status = "已启用" if self.integration.tray_available else "当前环境不可用"
        self._label(local, f"所有核心数据都保存在本机 SQLite，不需要账号或网络。\n原生桌面能力：系统托盘 {tray_status} · 单实例已启用 · 每日自动备份保留最近 14 份。", 9, self.TEXT_SOFT, False, bg=self.SURFACE, justify="left").pack(anchor="w", padx=14, pady=13)

    def settings_card(self, parent: tk.Misc, row: int, title: str, description: str) -> None:
        card = tk.Frame(parent, bg=self.BG)
        card.grid(row=row, column=0, sticky="ew", pady=(7, 5))
        self._label(card, title, 10, self.TEXT, True, bg=self.BG).pack(anchor="w")
        self._label(card, description, 8, self.TEXT_SOFT, False, bg=self.BG).pack(anchor="w", pady=(2, 0))

    def _settings_line(self, parent: tk.Misc, title: str, description: str, kind: str, value: Any, command=None) -> None:
        line = tk.Frame(parent, bg=self.SURFACE, highlightthickness=0)
        line.pack(fill="x", pady=(0, 1))
        copy = tk.Frame(line, bg=self.SURFACE)
        copy.pack(side="left", fill="x", expand=True, padx=15, pady=11)
        self._label(copy, title, 9, self.TEXT, True, bg=self.SURFACE, anchor="w").pack(fill="x")
        self._label(copy, description, 8, self.TEXT_SOFT, False, bg=self.SURFACE, anchor="w").pack(fill="x", pady=(3, 0))
        control = tk.Frame(line, bg=self.SURFACE)
        control.pack(side="right", padx=15, pady=9)
        if kind == "combo":
            var = tk.StringVar(value="工作" if value == "work" else "生活")
            combo = ttk.Combobox(control, textvariable=var, values=["工作", "生活"], state="readonly", width=9)
            combo.pack()
            combo.bind("<<ComboboxSelected>>", lambda _event: command("life" if var.get() == "生活" else "work"))
        elif kind == "combo_page":
            var = tk.StringVar(value={"today": "今天", "upcoming": "之后", "all": "全部"}.get(value, "今天"))
            combo = ttk.Combobox(control, textvariable=var, values=["今天", "之后", "全部"], state="readonly", width=9)
            combo.pack()
            combo.bind("<<ComboboxSelected>>", lambda _event: command({"今天": "today", "之后": "upcoming", "全部": "all"}[var.get()]))
        elif kind == "combo_close":
            var = tk.StringVar(value="隐藏到托盘" if str(value) == "1" else "直接退出")
            combo = ttk.Combobox(control, textvariable=var, values=["隐藏到托盘", "直接退出"], state="readonly", width=11)
            combo.pack()
            combo.bind("<<ComboboxSelected>>", lambda _event: command("1" if var.get() == "隐藏到托盘" else "0"))
        elif kind == "hotkey":
            row = tk.Frame(control, bg=self.SURFACE)
            row.pack()
            var = tk.StringVar(value=display_hotkey(str(value)))
            entry = ttk.Entry(row, textvariable=var, width=16)
            entry.pack(side="left")
            self._button(row, "保存", lambda: command(var.get()), "outline").pack(side="left", padx=(6, 0))
        elif kind == "check":
            var = tk.BooleanVar(value=bool(value))
            tk.Checkbutton(control, variable=var, command=lambda: command(var.get()), bg=self.SURFACE, activebackground=self.SURFACE, selectcolor=self.SURFACE, highlightthickness=0).pack()
        else:
            self._label(control, str(value), 8, self.colors["strong"], True, bg=self.SURFACE).pack()

    def toggle_completed(self) -> None:
        self.completed_open = not self.completed_open
        self.render()

    def _set_all_mode(self, mode: str) -> None:
        self.all_mode = mode
        self.render()

    def _set_goal_mode(self, mode: str) -> None:
        self.goal_mode = mode
        self.render()

    def _set_goal_status(self, status: str) -> None:
        self.goal_status = status
        self.render()

    def _set_goal_category(self, category: str) -> None:
        self.goal_category = category
        self.render()

    def _set_archive_tab(self, tab: str) -> None:
        self.archive_tab = tab
        self.render()

    def _set_archive_category(self, category: str) -> None:
        self.archive_category = category
        self.render()

    def _archive_query_changed(self, value: str) -> None:
        self.archive_query = value
        self.after_idle(self.render)

    def _save_default_category(self, value: str) -> None:
        self.db.set_setting("default_category", value)
        self.settings["default_category"] = value

    def _save_startup_page(self, value: str) -> None:
        self.db.set_setting("startup_page", value)
        self.settings["startup_page"] = value

    def _save_reduce_motion(self, value: bool) -> None:
        self.db.set_setting("reduce_motion", int(value))
        self.settings["reduce_motion"] = "1" if value else "0"

    def _save_startup_enabled(self, value: bool) -> None:
        try:
            set_windows_autostart(bool(value))
            self.db.set_setting("startup_enabled", int(bool(value)))
            self.settings["startup_enabled"] = "1" if value else "0"
            self.show_toast("开机自启已更新")
        except Exception as error:
            log_event("autostart setting failed", error)
            messagebox.showerror("开机自启不可用", "Windows 没有接受这个开机自启设置。", parent=self)
            self.render()

    def _save_startup_minimized(self, value: bool) -> None:
        self.db.set_setting("startup_minimized", int(bool(value)))
        self.settings["startup_minimized"] = "1" if value else "0"
        self.show_toast("启动方式已更新")

    def _save_close_mode(self, value: str) -> None:
        mode = "1" if value == "1" else "0"
        self.db.set_setting("close_to_tray", mode)
        self.settings["close_to_tray"] = mode
        self.show_toast("关闭按钮行为已更新")

    def _save_global_hotkey(self, value: str) -> None:
        normalized = normalize_hotkey(value)
        if not normalized:
            messagebox.showerror("快捷键格式不正确", "请输入类似 Ctrl + Alt + T 的组合键。", parent=self)
            return
        if not self.integration.available:
            messagebox.showerror("快捷键不可用", "当前运行环境没有可用的 Windows 全局快捷键接口。", parent=self)
            return
        if not self.integration.register_hotkey(normalized):
            messagebox.showerror("快捷键冲突", f"{display_hotkey(normalized)} 已被其他软件占用，请换一个组合键。", parent=self)
            return
        self.db.set_setting("global_hotkey", normalized)
        self.settings["global_hotkey"] = normalized
        self.render()
        self.show_toast(f"全局快捷键已设为 {display_hotkey(normalized)}")

    def set_theme(self, theme_key: str) -> None:
        if theme_key in THEMES:
            self.theme_key = theme_key
            self.db.set_setting("theme", theme_key)
            self.render()

    def open_new_task(self, date_key: str | None = None, goal_id: str | None = None, template: dict[str, Any] | None = None) -> None:
        if date_key is None and self.view == "today":
            date_key = today_key()
        self.open_task_dialog(None, preset_date=date_key, goal_id=goal_id, template=template)

    def open_new_goal(self) -> None:
        self.open_goal_dialog()

    def open_goal_detail(self, goal_id: str) -> None:
        self.selected_goal_id = goal_id
        self.view = "goals"
        self.render()

    def open_task_dialog(self, task_id: str | None = None, preset_date: str | None = None, goal_id: str | None = None, template: dict[str, Any] | None = None) -> None:
        task = self.db.get_task(task_id) if task_id else None
        template = template or {}
        dialog = tk.Toplevel(self)
        dialog.title("编辑待办" if task else "新建待办")
        dialog.configure(bg=self.BG)
        dialog.transient(self)
        dialog.grab_set()
        dialog.minsize(470, 520)
        dialog.geometry("540x730")
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)
        head = tk.Frame(dialog, bg=self.SURFACE)
        head.grid(row=0, column=0, sticky="ew")
        self._label(head, "编辑待办" if task else "新建待办", 17, self.TEXT, True, bg=self.SURFACE).pack(anchor="w", padx=22, pady=(19, 3))
        self._label(head, "标题先行，其他信息之后再补也可以。", 9, self.TEXT_SOFT, False, bg=self.SURFACE).pack(anchor="w", padx=22, pady=(0, 16))
        form = tk.Frame(dialog, bg=self.BG)
        form.grid(row=1, column=0, sticky="nsew", padx=20, pady=16)
        form.columnconfigure(0, weight=1)
        title_var = tk.StringVar(value=task["title"] if task else template.get("title", ""))
        note_default = task["note"] if task else template.get("note", "")
        category_value = task["category"] if task else template.get("category", self.settings.get("default_category", "work"))
        priority_value = task["priority"] if task else template.get("priority", "normal")
        category_var = tk.StringVar(value=category_label(category_value))
        priority_var = tk.StringVar(value="高" if priority_value == "high" else "普通")
        date_var = tk.StringVar(value=task["planned_date"] if task and task.get("planned_date") else preset_date or "")
        goal_values = {"独立待办": ""}
        for goal in self.db.list_goals(status="all"):
            goal_values[f"{goal['title']}{'（已达成）' if goal['status'] == 'achieved' else ''}"] = goal["id"]
        goal_current = task.get("goal_id") if task else goal_id
        goal_display = next((name for name, value in goal_values.items() if value == goal_current), "独立待办")
        goal_var = tk.StringVar(value=goal_display)
        tags_var = tk.StringVar(value="、".join(task.get("tags", [])) if task else "、".join(template.get("tags", [])))
        self._form_label(form, "要做什么？", row=0)
        title_entry = ttk.Entry(form, textvariable=title_var, font=("Microsoft YaHei UI", 12))
        title_entry.grid(row=1, column=0, sticky="ew", pady=(0, 14), ipady=3)
        self._form_label(form, "备注详情（可选）", row=2)
        note = tk.Text(form, height=4, wrap="word", bg=self.SURFACE_SOFT, fg=self.TEXT, relief="flat", bd=0, highlightbackground=self.SURFACE_SOFT, highlightcolor=self.colors["strong"], highlightthickness=1, font=("Microsoft YaHei UI", 9))
        note.grid(row=3, column=0, sticky="ew", pady=(0, 13))
        note.insert("1.0", note_default)
        properties = tk.Frame(form, bg=self.BG)
        properties.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        for col in range(2): properties.columnconfigure(col, weight=1)
        self._form_label(properties, "分类", 0, 0)
        self._form_label(properties, "优先级", 0, 1)
        category = ttk.Combobox(properties, textvariable=category_var, values=["工作", "生活"], state="readonly")
        category.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        priority = ttk.Combobox(properties, textvariable=priority_var, values=["普通", "高"], state="readonly")
        priority.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self._form_label(form, "计划日期（可留空）", row=5)
        date_entry = ttk.Entry(form, textvariable=date_var)
        date_entry.grid(row=6, column=0, sticky="ew", pady=(4, 1))
        self._label(form, "格式 YYYY-MM-DD；只保存自然日，不设置截止时刻。", 8, self.TEXT_FAINT, False, bg=self.BG).grid(row=7, column=0, sticky="w", pady=(0, 11))
        self._form_label(form, "所属长期目标", row=8)
        goal_combo = ttk.Combobox(form, textvariable=goal_var, values=list(goal_values), state="readonly")
        goal_combo.grid(row=9, column=0, sticky="ew", pady=(4, 11))
        self._form_label(form, "标签（用逗号或顿号分隔）", row=10)
        ttk.Entry(form, textvariable=tags_var).grid(row=11, column=0, sticky="ew", pady=(4, 11))
        self._form_label(form, "子步骤（每行一个，可选）", row=12)
        step_completion: dict[str, tk.BooleanVar] = {}
        if task and task.get("subtasks"):
            checklist = tk.Frame(form, bg=self.SURFACE_SOFT, highlightthickness=0)
            checklist.grid(row=13, column=0, sticky="ew", pady=(4, 7))
            self._label(checklist, "逐项勾选（不会自动完成主待办）", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(anchor="w", padx=9, pady=(7, 3))
            for step in task["subtasks"][:6]:
                var = tk.BooleanVar(value=bool(step["completed"]))
                step_completion[step["id"]] = var
                tk.Checkbutton(checklist, text=step["title"], variable=var, command=lambda sid=step["id"], current=var: self.db.update_subtask(sid, completed=current.get()), anchor="w", bg=self.SURFACE, fg=self.TEXT, activebackground=self.SURFACE, selectcolor=self.SURFACE, highlightthickness=0, font=("Microsoft YaHei UI", 9)).pack(fill="x", padx=7, pady=1)
            if len(task["subtasks"]) > 6:
                self._label(checklist, f"其余 {len(task['subtasks']) - 6} 项可在下方文本中编辑。", 8, self.TEXT_FAINT, False, bg=self.SURFACE).pack(anchor="w", padx=9, pady=(3, 7))
        steps = tk.Text(form, height=5, wrap="word", bg=self.SURFACE_SOFT, fg=self.TEXT, relief="flat", bd=0, highlightbackground=self.SURFACE_SOFT, highlightcolor=self.colors["strong"], highlightthickness=1, font=("Microsoft YaHei UI", 9))
        steps.grid(row=14, column=0, sticky="ew", pady=(4, 0))
        if task:
            steps.insert("1.0", "\n".join(step["title"] for step in task.get("subtasks", [])))
        elif template.get("subtasks"):
            steps.insert("1.0", "\n".join(template["subtasks"]))
        footer = tk.Frame(dialog, bg=self.SURFACE_SOFT, highlightthickness=0)
        footer.grid(row=2, column=0, sticky="ew")
        error = tk.Label(footer, text="", bg=self.SURFACE, fg=self.HIGH, font=("Microsoft YaHei UI", 9))
        error.pack(side="left", padx=22)
        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=(0, 10), pady=13)

        def save() -> None:
            title_value = title_var.get().strip()
            if not title_value:
                error.configure(text="标题不能为空")
                title_entry.focus_set()
                return
            step_lines = [item.strip() for item in steps.get("1.0", tk.END).splitlines() if item.strip()]
            old_steps = task.get("subtasks", []) if task else []
            steps_value = []
            for index, item in enumerate(step_lines):
                completed = False
                if index < len(old_steps) and old_steps[index]["title"] == item:
                    variable = step_completion.get(old_steps[index]["id"])
                    completed = variable.get() if variable else bool(old_steps[index]["completed"])
                steps_value.append({"title": item, "completed": completed})
            goal_id_value = goal_values.get(goal_var.get()) or None
            values = {"title": title_value, "note": note.get("1.0", tk.END).strip(), "category": "life" if category_var.get() == "生活" else "work", "priority": "high" if priority_var.get() == "高" else "normal", "planned_date": date_var.get().strip() or None, "goal_id": goal_id_value, "tags": split_tags(tags_var.get()), "subtasks": steps_value}
            if values["planned_date"] and not parse_date(values["planned_date"]):
                error.configure(text="计划日期格式应为 YYYY-MM-DD")
                date_entry.focus_set()
                return
            if task:
                self.db.update_task(task["id"], values)
            else:
                self.db.create_task(**values)
            dialog.destroy()
            self.render()
            self.show_toast("待办已保存")

        self._button(footer, "保存待办", save, "primary").pack(side="right", padx=(0, 22), pady=13)
        title_entry.focus_set()

    def _form_label(self, parent: tk.Misc, text: str, row: int | None = None, col: int = 0, color: str | None = None) -> None:
        label = self._label(parent, text, 8, color or self.TEXT_SOFT, True, bg=parent.cget("bg"))
        if row is None:
            label.pack(anchor="w", pady=(0, 5))
        else:
            label.grid(row=row, column=col, sticky="w")

    def open_goal_dialog(self, goal_id: str | None = None) -> None:
        goal = self.db.get_goal(goal_id) if goal_id else None
        dialog = tk.Toplevel(self)
        dialog.title("编辑长期目标" if goal else "新建长期目标")
        dialog.configure(bg=self.BG)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("500x470")
        dialog.columnconfigure(0, weight=1)
        head = tk.Frame(dialog, bg=self.SURFACE)
        head.grid(row=0, column=0, sticky="ew")
        self._label(head, "编辑长期目标" if goal else "新建长期目标", 17, self.TEXT, True, bg=self.SURFACE).pack(anchor="w", padx=22, pady=(19, 3))
        self._label(head, "目标进度由关联待办自动计算，不需要手动维护百分比。", 9, self.TEXT_SOFT, False, bg=self.SURFACE).pack(anchor="w", padx=22, pady=(0, 16))
        form = tk.Frame(dialog, bg=self.BG)
        form.grid(row=1, column=0, sticky="nsew", padx=20, pady=17)
        form.columnconfigure(0, weight=1)
        title_var = tk.StringVar(value=goal["title"] if goal else "")
        category_var = tk.StringVar(value=category_label(goal["category"] if goal else self.settings.get("default_category", "work")))
        priority_var = tk.StringVar(value="高" if goal and goal["priority"] == "high" else "普通")
        date_var = tk.StringVar(value=goal["planned_finish_date"] if goal and goal.get("planned_finish_date") else "")
        self._form_label(form, "目标是什么？", row=0)
        title_entry = ttk.Entry(form, textvariable=title_var, font=("Microsoft YaHei UI", 12))
        title_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15), ipady=3)
        self._form_label(form, "目标说明（可选）", row=2)
        note = tk.Text(form, height=5, wrap="word", bg=self.SURFACE_SOFT, fg=self.TEXT, relief="flat", bd=0, highlightbackground=self.SURFACE_SOFT, highlightcolor=self.colors["strong"], highlightthickness=1, font=("Microsoft YaHei UI", 9))
        note.grid(row=3, column=0, sticky="ew", pady=(4, 14))
        if goal:
            note.insert("1.0", goal.get("note", ""))
        properties = tk.Frame(form, bg=self.BG)
        properties.grid(row=4, column=0, sticky="ew")
        properties.grid_columnconfigure(0, weight=1)
        properties.grid_columnconfigure(1, weight=1)
        self._form_label(properties, "分类", 0, 0)
        self._form_label(properties, "优先级", 0, 1)
        ttk.Combobox(properties, textvariable=category_var, values=["工作", "生活"], state="readonly").grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(4, 0))
        ttk.Combobox(properties, textvariable=priority_var, values=["普通", "高"], state="readonly").grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))
        self._form_label(form, "计划完成日期（可留空）", row=5)
        date_entry = ttk.Entry(form, textvariable=date_var)
        date_entry.grid(row=6, column=0, sticky="ew", pady=(4, 1))
        self._label(form, "只做方向提醒，不会产生强提醒。格式 YYYY-MM-DD。", 8, self.TEXT_FAINT, False, bg=self.BG).grid(row=7, column=0, sticky="w")
        footer = tk.Frame(dialog, bg=self.SURFACE_SOFT, highlightthickness=0)
        footer.grid(row=2, column=0, sticky="ew")
        error = tk.Label(footer, text="", bg=self.SURFACE, fg=self.HIGH, font=("Microsoft YaHei UI", 9))
        error.pack(side="left", padx=22)
        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=(0, 10), pady=13)

        def save() -> None:
            title_value = title_var.get().strip()
            if not title_value:
                error.configure(text="目标标题不能为空")
                title_entry.focus_set()
                return
            if date_var.get().strip() and not parse_date(date_var.get().strip()):
                error.configure(text="日期格式应为 YYYY-MM-DD")
                date_entry.focus_set()
                return
            values = {"title": title_value, "note": note.get("1.0", tk.END).strip(), "category": "life" if category_var.get() == "生活" else "work", "priority": "high" if priority_var.get() == "高" else "normal", "planned_finish_date": date_var.get().strip() or None}
            if goal:
                self.db.update_goal(goal["id"], values)
            else:
                self.db.create_goal(**values)
            dialog.destroy()
            self.render()
            self.show_toast("长期目标已保存")

        self._button(footer, "保存目标", save, "primary").pack(side="right", padx=(0, 22), pady=13)
        title_entry.focus_set()

    def open_filter_dialog(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("筛选待办")
        dialog.configure(bg=self.BG)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("420x410")
        form = tk.Frame(dialog, bg=self.BG)
        form.pack(fill="both", expand=True, padx=20, pady=20)
        self._label(form, "筛选待办", 16, self.TEXT, True, bg=self.BG).pack(anchor="w")
        self._label(form, "临时筛选不会改变任务本身。", 9, self.TEXT_SOFT, False, bg=self.BG).pack(anchor="w", pady=(3, 17))
        variables: dict[str, tk.StringVar] = {}
        choices = [("category", "分类", [("all", "全部分类"), ("work", "工作"), ("life", "生活")]), ("priority", "优先级", [("all", "全部优先级"), ("high", "高优先级"), ("normal", "普通优先级")]), ("goal", "目标关系", [("all", "全部待办"), ("linked", "已关联目标"), ("standalone", "独立待办")]), ("status", "状态", [("todo", "待办"), ("completed", "已完成"), ("all", "全部状态")]), ("tag", "标签", [("all", "全部标签")] + [(tag, f"#{tag}") for tag in self.db.all_tags()])]
        for key, title, values in choices:
            line = tk.Frame(form, bg=self.BG)
            line.pack(fill="x", pady=5)
            self._label(line, title, 9, self.TEXT, True, bg=self.BG).pack(side="left")
            var = tk.StringVar(value=self.filter_values[key])
            variables[key] = var
            display = [label for _value, label in values]
            value_map = {label: value for value, label in values}
            combo = ttk.Combobox(line, values=display, state="readonly", width=20)
            combo.set(next((label for value, label in values if value == self.filter_values[key]), display[0]))
            combo.pack(side="right")
            combo._value_map = value_map  # type: ignore[attr-defined]
            combo._key = key  # type: ignore[attr-defined]
            combo.bind("<<ComboboxSelected>>", lambda _event, combo=combo, key=key: variables[key].set(combo._value_map[combo.get()]))  # type: ignore[attr-defined]
        footer = tk.Frame(dialog, bg=self.SURFACE_SOFT, highlightthickness=0)
        footer.pack(fill="x", side="bottom")
        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=8, pady=10)

        def apply() -> None:
            for key, variable in variables.items():
                self.filter_values[key] = variable.get() or "all"
            dialog.destroy()
            self.render()

        self._button(footer, "应用筛选", apply, "primary").pack(side="right", padx=(0, 18), pady=10)

    def _selected_tasks(self) -> list[dict[str, Any]]:
        values = []
        for task_id in list(self.selected_task_ids):
            task = self.db.get_task(task_id)
            if task and task.get("status") != "deleted":
                values.append(task)
        return values

    def batch_complete(self) -> None:
        tasks = [task for task in self._selected_tasks() if task["status"] == "todo"]
        if not tasks:
            return
        for task in tasks:
            self.db.toggle_task(task["id"])
        ids = [task["id"] for task in tasks]
        self.selected_task_ids.clear()
        self.render()
        self.show_toast(f"已完成 {len(ids)} 项", undo_callback=lambda ids=ids: self._undo_batch_complete(ids))

    def _undo_batch_complete(self, task_ids: list[str]) -> None:
        for task_id in task_ids:
            task = self.db.get_task(task_id)
            if task and task["status"] == "completed":
                self.db.toggle_task(task_id)
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量完成")

    def batch_set(self, field: str, value: str) -> None:
        if field not in {"category", "priority"}:
            return
        tasks = self._selected_tasks()
        if not tasks:
            return
        snapshots = [(task["id"], task[field]) for task in tasks]
        for task in tasks:
            self.db.update_task(task["id"], {field: value})
        self.selected_task_ids.clear()
        self.render()
        label = {"category": category_label(value), "priority": "高优先级" if value == "high" else "普通优先级"}[field]
        self.show_toast(f"已将 {len(tasks)} 项设为{label}", undo_callback=lambda snapshots=snapshots, field=field: self._undo_batch_values(snapshots, field))

    def _undo_batch_values(self, snapshots: list[tuple[str, Any]], field: str) -> None:
        for task_id, value in snapshots:
            if self.db.get_task(task_id):
                self.db.update_task(task_id, {field: value})
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量修改")

    def batch_set_date(self) -> None:
        tasks = self._selected_tasks()
        if not tasks:
            return
        dialog = tk.Toplevel(self)
        dialog.title("批量设置计划日期")
        dialog.configure(bg=self.BG)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("390x205")
        self._label(dialog, "批量设置计划日期", 15, self.TEXT, True, bg=self.BG).pack(anchor="w", padx=20, pady=(19, 3))
        self._label(dialog, f"将修改已选择的 {len(tasks)} 项；未安排不会进入计划完成率。", 8, self.TEXT_SOFT, False, bg=self.BG).pack(anchor="w", padx=20)
        row = tk.Frame(dialog, bg=self.BG)
        row.pack(fill="x", padx=20, pady=16)
        date_var = tk.StringVar()
        ttk.Entry(row, textvariable=date_var, width=15).pack(side="left")
        for label, value in (("今天", today_key()), ("明天", offset_date(1)), ("未安排", "")):
            self._button(row, label, lambda value=value: date_var.set(value), "ghost").pack(side="left", padx=(6, 0))
        error = self._label(dialog, "", 8, self.HIGH, False, bg=self.BG)
        error.pack(anchor="w", padx=20)
        footer = tk.Frame(dialog, bg=self.SURFACE_SOFT, highlightthickness=0)
        footer.pack(fill="x", side="bottom")

        def apply() -> None:
            value = date_var.get().strip() or None
            if value and not parse_date(value):
                error.configure(text="日期格式应为 YYYY-MM-DD")
                return
            snapshots = [(task["id"], task.get("planned_date")) for task in tasks]
            for task in tasks:
                self.db.update_task(task["id"], {"planned_date": value})
            dialog.destroy()
            self.selected_task_ids.clear()
            self.render()
            self.show_toast("批量计划日期已更新", undo_callback=lambda snapshots=snapshots: self._undo_batch_dates(snapshots))

        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=(0, 7), pady=10)
        self._button(footer, "确认修改", apply, "primary").pack(side="right", padx=(0, 20), pady=10)
        dialog.bind("<Return>", lambda _event: apply())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def _undo_batch_dates(self, snapshots: list[tuple[str, str | None]]) -> None:
        for task_id, value in snapshots:
            if self.db.get_task(task_id):
                self.db.update_task(task_id, {"planned_date": value})
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量日期修改")

    def batch_attach_goal(self) -> None:
        goals = self.db.list_goals(status="active")
        if not goals:
            messagebox.showinfo("没有进行中的目标", "请先创建一个进行中的长期目标。", parent=self)
            return
        if len(goals) == 1:
            self._batch_set_goal(goals[0]["id"])
            return
        dialog = tk.Toplevel(self)
        dialog.title("挂载到目标")
        dialog.configure(bg=self.BG)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("390x180")
        self._label(dialog, "挂载到长期目标", 15, self.TEXT, True, bg=self.BG).pack(anchor="w", padx=20, pady=(19, 12))
        values = {goal["title"]: goal["id"] for goal in goals}
        selected = tk.StringVar(value=next(iter(values)))
        ttk.Combobox(dialog, textvariable=selected, values=list(values), state="readonly", width=30).pack(anchor="w", padx=20)
        footer = tk.Frame(dialog, bg=self.SURFACE_SOFT, highlightthickness=0)
        footer.pack(fill="x", side="bottom", pady=(22, 0))

        def apply() -> None:
            dialog.destroy()
            self._batch_set_goal(values[selected.get()])

        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=(0, 7), pady=10)
        self._button(footer, "确认挂载", apply, "primary").pack(side="right", padx=(0, 20), pady=10)

    def _batch_set_goal(self, goal_id: str | None) -> None:
        tasks = self._selected_tasks()
        if not tasks:
            return
        snapshots = [(task["id"], task.get("goal_id")) for task in tasks]
        for task in tasks:
            self.db.update_task(task["id"], {"goal_id": goal_id})
        self.selected_task_ids.clear()
        self.render()
        self.show_toast("目标关联已批量更新", undo_callback=lambda snapshots=snapshots: self._undo_batch_goal(snapshots))

    def _undo_batch_goal(self, snapshots: list[tuple[str, str | None]]) -> None:
        for task_id, value in snapshots:
            if self.db.get_task(task_id):
                self.db.update_task(task_id, {"goal_id": value})
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量目标关联")

    def batch_delete(self) -> None:
        tasks = self._selected_tasks()
        if not tasks:
            return
        if not messagebox.askyesno("批量删除", f"确定删除已选择的 {len(tasks)} 项吗？删除前会保留计划历史。", parent=self):
            return
        for task in tasks:
            self.db.delete_task(task["id"])
        ids = [task["id"] for task in tasks]
        self.selected_task_ids.clear()
        self.render()
        self.show_toast(f"已删除 {len(ids)} 项", undo_callback=lambda ids=ids: self._undo_batch_delete(ids))

    def _undo_batch_delete(self, task_ids: list[str]) -> None:
        for task_id in task_ids:
            self.db.restore_task(task_id)
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.render()
        self.show_toast("已撤回批量删除")

    def goal_decision_dialog(self, goal_id: str, action: str) -> None:
        goal = self.db.get_goal(goal_id)
        if not goal:
            return
        is_achieve = action == "achieve"
        dialog = tk.Toplevel(self)
        dialog.title("达成长期目标" if is_achieve else "删除长期目标")
        dialog.configure(bg=self.BG)
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("480x330" if is_achieve else "480x270")
        title = "标记目标已达成" if is_achieve else "删除长期目标"
        self._label(dialog, title, 15, self.TEXT, True, bg=self.BG).pack(anchor="w", padx=20, pady=(19, 4))
        if is_achieve:
            self._label(dialog, f"「{goal['title']}」还有 {goal['remaining']} 个未完成待办，请选择如何处理。", 9, self.TEXT_SOFT, False, bg=self.BG, wraplength=420, justify="left").pack(anchor="w", padx=20, pady=(0, 13))
            choice = tk.StringVar(value="detach")
            options = [("detach", "转为独立待办", "待办保留，解除与该目标的关联"), ("complete", "全部标记为完成", "写入当前完成时间，并计入实际完成数量"), ("delete", "删除这些待办", "未完成待办移入删除状态，不计入完成数量")]
        else:
            self._label(dialog, f"「{goal['title']}」仍有关联待办，请选择处理方式。", 9, self.TEXT_SOFT, False, bg=self.BG, wraplength=420, justify="left").pack(anchor="w", padx=20, pady=(0, 13))
            choice = tk.StringVar(value="detach")
            options = [("detach", "保留并转为独立待办", "关联待办本身不变，只解除目标关系"), ("delete", "删除未完成关联待办", "已完成待办保留，未完成待办移入删除状态")]
        body = tk.Frame(dialog, bg=self.BG)
        body.pack(fill="x", padx=20)
        for value, label, description in options:
            line = tk.Frame(body, bg=self.BG)
            line.pack(fill="x", pady=4)
            tk.Radiobutton(line, variable=choice, value=value, bg=self.BG, activebackground=self.BG, selectcolor=self.SURFACE, highlightthickness=0).pack(side="left")
            copy = tk.Frame(line, bg=self.BG)
            copy.pack(side="left", padx=4)
            self._label(copy, label, 9, self.TEXT, True, bg=self.BG).pack(anchor="w")
            self._label(copy, description, 8, self.TEXT_SOFT, False, bg=self.BG).pack(anchor="w")
        footer = tk.Frame(dialog, bg=self.SURFACE_SOFT, highlightthickness=0)
        footer.pack(fill="x", side="bottom", pady=(16, 0))

        def confirm() -> None:
            if is_achieve:
                self.db.achieve_goal(goal_id, choice.get())
                message = f"目标「{goal['title']}」已达成"
            else:
                self.db.delete_goal(goal_id, choice.get())
                self.selected_goal_id = None
                message = "长期目标已删除"
            dialog.destroy()
            self.render()
            self.show_toast(message)

        self._button(footer, "取消", dialog.destroy, "ghost").pack(side="right", padx=(0, 7), pady=10)
        self._button(footer, "确认", confirm, "primary").pack(side="right", padx=(0, 20), pady=10)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def toggle_task(self, task_id: str) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        previous = task["status"]
        self.db.toggle_task(task_id)
        self.render()
        self.show_toast("已完成" if previous == "todo" else "已撤销完成", undo_id=task_id, undo_status=previous)

    def show_toast(self, message: str, undo_id: str | None = None, undo_status: str | None = None, undo_callback=None) -> None:
        if self.toast and self.toast.winfo_exists():
            self.toast.destroy()
        self.toast_undo_callback = undo_callback
        toast = tk.Toplevel(self)
        self.toast = toast
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=self.SURFACE)
        width, height = 340, 56
        self.update_idletasks()
        x = self.winfo_x() + max(20, self.winfo_width() - width - 25)
        y = self.winfo_y() + max(20, self.winfo_height() - height - 30)
        toast.geometry(f"{width}x{height}+{x}+{y}")
        outer = tk.Frame(toast, bg=self.SURFACE, highlightthickness=0)
        outer.pack(fill="both", expand=True)
        self._label(outer, "🐾", 13, self.colors["strong"], True, bg=self.SURFACE).pack(side="left", padx=(14, 8))
        self._label(outer, message, 9, self.TEXT_SOFT, False, bg=self.SURFACE).pack(side="left", fill="x", expand=True)
        if undo_id:
            self._button(outer, "撤回", lambda: self._undo_task(undo_id, undo_status), "link").pack(side="right", padx=10)
        elif undo_callback:
            self._button(outer, "撤回", undo_callback, "link").pack(side="right", padx=10)
        toast.after(5200, lambda: toast.destroy() if toast.winfo_exists() else None)

    def _undo_task(self, task_id: str, previous_status: str | None) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        if task["status"] == "deleted":
            self.db.restore_task(task_id)
        elif previous_status == "todo" and task["status"] == "completed":
            self.db.toggle_task(task_id)
        elif previous_status == "completed" and task["status"] == "todo":
            self.db.toggle_task(task_id)
        if self.toast and self.toast.winfo_exists(): self.toast.destroy()
        self.render()
        self.show_toast("已撤回上一步操作")

    def delete_task(self, task_id: str) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        self.db.delete_task(task_id)
        self.render()
        self.show_toast(f"已移除「{task['title']}」", undo_id=task_id, undo_status=task["status"])

    def save_template(self, task_id: str) -> None:
        self.db.create_template(task_id)
        self.show_toast("已保存为任务模板")

    def delete_template(self, template_id: str) -> None:
        if messagebox.askyesno("删除模板", "确定删除这个任务模板吗？", parent=self):
            self.db.delete_template(template_id)
            self.render()
            self.show_toast("模板已删除")

    def open_context_menu(self, task_id: str, event_or_widget: Any) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        menu = tk.Menu(self, tearoff=0, bg=self.SURFACE, fg=self.TEXT, activebackground=self.colors["soft"], activeforeground=self.TEXT, bd=0, relief="flat", font=("Microsoft YaHei UI", 9))
        menu.add_command(label="完成" if task["status"] == "todo" else "撤销完成", command=lambda: self.toggle_task(task_id))
        menu.add_command(label="编辑", command=lambda: self.open_task_dialog(task_id))
        menu.add_separator()
        menu.add_command(label="设为高优" if task["priority"] != "high" else "设为普通", command=lambda: self.set_task_priority(task_id, "high" if task["priority"] != "high" else "normal"))
        menu.add_command(label="安排到今天", command=lambda: self.set_task_date(task_id, today_key()))
        menu.add_command(label="安排到明天", command=lambda: self.set_task_date(task_id, offset_date(1)))
        menu.add_command(label="选择日期…", command=lambda: self.open_task_dialog(task_id))
        menu.add_separator()
        menu.add_command(label="解除目标关联" if task.get("goal_id") else "挂载到目标…", command=lambda: self.toggle_task_goal(task_id))
        menu.add_command(label="保存为模板", command=lambda: self.save_template(task_id))
        menu.add_separator()
        menu.add_command(label="删除", command=lambda: self.delete_task(task_id))
        if isinstance(event_or_widget, tk.Event):
            menu.tk_popup(event_or_widget.x_root, event_or_widget.y_root)
        else:
            widget = event_or_widget
            x = widget.winfo_rootx() + widget.winfo_width() - 10
            y = widget.winfo_rooty() + widget.winfo_height() - 4
            menu.tk_popup(x, y)
        menu.grab_release()

    def set_task_priority(self, task_id: str, priority: str) -> None:
        task = self.db.get_task(task_id)
        if task:
            self.db.update_task(task_id, {"priority": priority})
            self.render()
            self.show_toast("优先级已更新")

    def set_task_date(self, task_id: str, planned_date: str | None) -> None:
        task = self.db.get_task(task_id)
        if task:
            self.db.update_task(task_id, {"planned_date": planned_date})
            self.render()
            self.show_toast("计划日期已更新")

    def toggle_task_goal(self, task_id: str) -> None:
        task = self.db.get_task(task_id)
        if not task:
            return
        if task.get("goal_id"):
            self.db.update_task(task_id, {"goal_id": None})
            self.render()
            self.show_toast("已解除目标关联")
        else:
            active = self.db.list_goals(status="active")
            if len(active) == 1:
                self.db.update_task(task_id, {"goal_id": active[0]["id"]})
                self.render()
                self.show_toast(f"已挂载到「{active[0]['title']}」")
            else:
                self.open_task_dialog(task_id)

    def confirm_goal_achieve(self, goal_id: str) -> None:
        goal = self.db.get_goal(goal_id)
        if not goal:
            return
        if not goal["remaining"]:
            self.db.achieve_goal(goal_id, "detach")
            self.render()
            self.show_toast(f"目标「{goal['title']}」已达成")
            return
        self.goal_decision_dialog(goal_id, "achieve")

    def confirm_goal_delete(self, goal_id: str) -> None:
        goal = self.db.get_goal(goal_id)
        if goal:
            self.goal_decision_dialog(goal_id, "delete")


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    if "--self-test" in arguments:
        run_self_test()
        return 0
    if "--gui-smoke" in arguments:
        run_gui_smoke_test()
        return 0

    instance = SingleInstance()
    if not instance.acquire():
        activate_existing_window()
        return 0
    try:
        app = PiggyPlanApp(start_minimized="--minimized" in arguments)
        app.mainloop()
        return 0
    except Exception as error:
        log_event("application startup failed", error)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("PiggyPlan 启动失败", "软件没有成功启动。请查看日志目录中的 piggyplan.log。", parent=root)
            root.destroy()
        except Exception:
            print("PiggyPlan startup failed; see the application log for details.")
        return 1
    finally:
        instance.release()


if __name__ == "__main__":
    raise SystemExit(main())
