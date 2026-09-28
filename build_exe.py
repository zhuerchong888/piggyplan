"""Build the standalone Windows executable with the project-local toolchain."""

from __future__ import annotations

import sys
import shutil
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
BUILD_TOOLS = PROJECT_DIR / ".build-tools"
PYTHON_ROOT = Path(sys.base_prefix)
TCL_ROOT = PYTHON_ROOT / "tcl"
PACKAGING_RUNTIME = PROJECT_DIR / "build" / "packaging-runtime"
PACKAGED_TCL = PACKAGING_RUNTIME / "tcl8.6"
PACKAGED_TK = PACKAGING_RUNTIME / "tk8.6"


def prepare_tcl_tk_runtime() -> None:
    """Copy and repair Tcl/Tk scripts for this relocated one-file build."""

    shutil.copytree(TCL_ROOT / "tcl8.6", PACKAGED_TCL, dirs_exist_ok=True)
    shutil.copytree(TCL_ROOT / "tk8.6", PACKAGED_TK, dirs_exist_ok=True)

    init_path = PACKAGED_TCL / "init.tcl"
    init_text = init_path.read_text(encoding="utf-8")
    init_marker = "package require -exact Tcl 8.6.15"
    if init_marker not in init_text:
        raise SystemExit("Unsupported Tcl init.tcl: expected version marker is missing.")
    init_text = init_text.replace(
        init_marker,
        "if {![info exists ::tcl_library]} {\n"
        "    set ::tcl_library [file dirname [info script]]\n"
        "}\n"
        + init_marker,
        1,
    )
    init_path.write_text(init_text, encoding="utf-8", newline="\n")

    tk_path = PACKAGED_TK / "tk.tcl"
    tk_text = tk_path.read_text(encoding="utf-8")
    tk_marker = "# Verify that we have Tk binary and script components from the same release"
    if tk_marker not in tk_text:
        raise SystemExit("Unsupported Tk tk.tcl: expected marker is missing.")
    tk_text = tk_text.replace(
        tk_marker,
        "# Repair relocated Windows runtimes that do not initialize this variable.\n"
        "if {![info exists ::tk_library]} {\n"
        "    set ::tk_library [file dirname [info script]]\n"
        "}\n\n"
        + tk_marker,
        1,
    )
    tk_path.write_text(tk_text, encoding="utf-8", newline="\n")

if not (BUILD_TOOLS / "PyInstaller").is_dir():
    raise SystemExit("PyInstaller is missing. Run: python -m pip install --target .build-tools pyinstaller")

sys.path.insert(0, str(BUILD_TOOLS))

from PyInstaller.__main__ import run  # noqa: E402


if __name__ == "__main__":
    prepare_tcl_tk_runtime()
    run(
        [
            "--noconfirm",
            "--clean",
            "--onedir",
            "--windowed",
            "--name=PiggyPlan",
            f"--additional-hooks-dir={PROJECT_DIR / 'packaging_hooks'}",
            f"--runtime-hook={PROJECT_DIR / 'packaging_hooks' / 'pyi_rth_piggyplan_tk.py'}",
            "--hidden-import=tkinter",
            "--hidden-import=tkinter.ttk",
            "--hidden-import=tkinter.filedialog",
            "--hidden-import=tkinter.messagebox",
            f"--add-binary={PYTHON_ROOT / 'DLLs' / '_tkinter.pyd'};.",
            f"--add-binary={PYTHON_ROOT / 'DLLs' / 'tcl86t.dll'};.",
            f"--add-binary={PYTHON_ROOT / 'DLLs' / 'tk86t.dll'};.",
            f"--add-data={PACKAGED_TCL};_tcl_data",
            f"--add-data={PACKAGED_TK};_tk_data",
            f"--add-data={TCL_ROOT / 'tcl8'};tcl8",
            f"--version-file={PROJECT_DIR / 'version_info.txt'}",
            f"--distpath={PROJECT_DIR / 'dist'}",
            f"--workpath={PROJECT_DIR / 'build'}",
            f"--specpath={PROJECT_DIR}",
            str(PROJECT_DIR / "piggyplan_desktop.py"),
        ]
    )
    shutil.copy2(PROJECT_DIR / "便携版使用说明.txt", PROJECT_DIR / "dist" / "PiggyPlan" / "使用说明.txt")
