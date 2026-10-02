"""Tcl/Tk 库搜索路径修复：必须在 `import tkinter` 之前由入口显式调用。

本模块以及 piggyplan/__init__.py、constants.py 都不得 import tkinter——
`from piggyplan.runtime.tcl import prepare` 这一行若把 tkinter 间接拉进来，
修复时机就作废了。
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


def prepare() -> None:
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
