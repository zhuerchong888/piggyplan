"""数据、备份、日志目录与技术日志。"""

from __future__ import annotations

import os
import traceback
from pathlib import Path

from ..util import now_iso


def app_data_dir() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return base / "PiggyPlan"


def app_backup_dir() -> Path:
    return app_data_dir() / "backups"


def app_log_dir() -> Path:
    return app_data_dir() / "logs"


def log_event(message: str, error: BaseException | None = None) -> None:
    """Write technical diagnostics without recording task content."""

    try:
        folder = app_log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "piggyplan.log"
        if path.exists() and path.stat().st_size > 1024 * 1024:
            old = folder / "piggyplan.log.1"
            if old.exists():
                old.unlink()
            path.replace(old)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{now_iso()} {message}\n")
            if error:
                handle.write("".join(traceback.format_exception(type(error), error, error.__traceback__)))
    except OSError:
        # Logging must never prevent the application from opening.
        pass
