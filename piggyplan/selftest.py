"""数据库层自测与 GUI 冒烟：--self-test / --gui-smoke 的实现。"""

from __future__ import annotations

import tkinter as tk
import json
import sqlite3
import tempfile
from pathlib import Path
from .database import Database
from .util import offset_date, today_key

from .app import PiggyPlanApp


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
    run_design_assertions()
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


def run_design_assertions() -> None:
    """把 spec 的两条硬规则钉死：文字色必须达 AA，且 <=9pt 不得加粗。"""
    from .tokens import NEUTRAL, SEMANTIC, THEMES, contrast, font_rules

    surfaces = {
        "surface": "#FFFFFF",
        "bg": NEUTRAL["bg"],
        "surface_soft": NEUTRAL["surface_soft"],
    }
    for key, theme in THEMES.items():
        for bg_name, bg in surfaces.items():
            ratio = contrast(theme["ink"], bg)
            assert ratio >= 4.5, f"{key}.ink on {bg_name} = {ratio:.2f}, 需 >= 4.5"
        assert contrast(theme["accent"], "#FFFFFF") < 4.5 or theme["accent"] == theme["ink"], \
            f"{key}.accent 不该同时是文字色——两级制要求它只做图形"
    for role, spec in SEMANTIC.items():
        assert contrast(spec["ink"], "#FFFFFF") >= 4.5, f"{role}.ink 未达 AA"
        assert contrast(spec["shape"], "#FFFFFF") < contrast(spec["ink"], "#FFFFFF"), \
            f"{role}.shape 比 .ink 更亮，两级制被破坏"
    for name, (family, size, weight) in font_rules().items():
        if size <= 9:
            # 唯一例外：Microsoft YaHei UI 无 Medium 字族，micro 角色允许 bold。
            assert weight in ("normal", "medium", "Medium") or (name == "micro" and family == "Microsoft YaHei UI"), \
                f"{name} 为 {size}pt 却用了 {weight}：CJK 小字号加粗会糊"
