"""SQLite repository and concentrated application rules."""

from __future__ import annotations

import csv
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from .util import date_text, end_of_week, now_iso, offset_date, split_tags, start_of_week, today_key, uid


class Database:
    """SQLite repository and concentrated application rules."""

    def __init__(self, path: str | Path, seed: bool = False):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._migrate()
        if seed and self._is_empty():
            self.seed_demo()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT OR IGNORE INTO schema_meta(key,value) VALUES('schema_version','1');
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'work' CHECK(category IN ('work','life')),
                priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('high','normal')),
                planned_finish_date TEXT,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','achieved')),
                sort_rank REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                achieved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'work' CHECK(category IN ('work','life')),
                priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('high','normal')),
                planned_date TEXT,
                status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','completed','deleted')),
                goal_id TEXT REFERENCES goals(id) ON DELETE SET NULL,
                sort_rank REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                deleted_at TEXT,
                deleted_previous_status TEXT
            );
            CREATE TABLE IF NOT EXISTS subtasks (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                sort_rank REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS task_tags (
                task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY(task_id, tag_id)
            );
            CREATE TABLE IF NOT EXISTS task_templates (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'work',
                priority TEXT NOT NULL DEFAULT 'normal',
                tags_json TEXT NOT NULL DEFAULT '[]',
                subtasks_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS task_plan_history (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                planned_date TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                superseded_at TEXT,
                became_due INTEGER NOT NULL DEFAULT 0,
                fulfilled_on_time INTEGER,
                cancelled_before_due INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_planned_date ON tasks(planned_date);
            CREATE INDEX IF NOT EXISTS idx_tasks_completed_at ON tasks(completed_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_goal_id ON tasks(goal_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
            CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
            CREATE INDEX IF NOT EXISTS idx_plan_history_date ON task_plan_history(planned_date);
            """
        )
        self.conn.commit()

    def _is_empty(self) -> bool:
        return self.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0 and self.conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0] == 0

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return str(row[0]) if row else default

    def set_setting(self, key: str, value: Any) -> None:
        self.conn.execute("INSERT INTO app_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
        self.conn.commit()

    def settings(self) -> dict[str, str]:
        return {row["key"]: row["value"] for row in self.conn.execute("SELECT key,value FROM app_settings")}

    def _attach_task_details(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        task = dict(row)
        task["tags"] = [r[0] for r in self.conn.execute("SELECT tags.name FROM tags JOIN task_tags ON task_tags.tag_id=tags.id WHERE task_tags.task_id=? ORDER BY tags.name", (task["id"],))]
        task["subtasks"] = [dict(r) for r in self.conn.execute("SELECT * FROM subtasks WHERE task_id=? ORDER BY sort_rank,created_at", (task["id"],))]
        goal = self.conn.execute("SELECT title,status FROM goals WHERE id=?", (task.get("goal_id"),)).fetchone()
        task["goal_title"] = goal["title"] if goal else None
        task["goal_status"] = goal["status"] if goal else None
        return task

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        return self._attach_task_details(self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

    @staticmethod
    def _task_sort_key(task: dict[str, Any], mode: str = "default") -> tuple:
        priority = 0 if task["priority"] == "high" else 1
        planned = task.get("planned_date") or "9999-99-99"
        if mode == "upcoming":
            return (planned, priority, task["sort_rank"], task["created_at"])
        if mode == "all":
            if not task.get("planned_date"):
                date_rank = 3
            elif task["planned_date"] < today_key():
                date_rank = 0
            elif task["planned_date"] == today_key():
                date_rank = 1
            else:
                date_rank = 2
            return (priority, date_rank, planned, task["sort_rank"], task["created_at"])
        return (priority, planned, task["sort_rank"], task["created_at"])

    def list_tasks(self, include_completed: bool = False, mode: str = "default", goal_id: str | None = None, category: str = "all", priority: str = "all", status: str = "all", query: str = "") -> list[dict[str, Any]]:
        clauses = ["status != 'deleted'"]
        params: list[Any] = []
        if not include_completed:
            clauses.append("status='todo'")
        elif status == "todo":
            clauses.append("status='todo'")
        elif status == "completed":
            clauses.append("status='completed'")
        if goal_id:
            clauses.append("goal_id=?")
            params.append(goal_id)
        if category in ("work", "life"):
            clauses.append("category=?")
            params.append(category)
        if priority in ("high", "normal"):
            clauses.append("priority=?")
            params.append(priority)
        where = " AND ".join(clauses)
        rows = [self._attach_task_details(row) for row in self.conn.execute(f"SELECT * FROM tasks WHERE {where}", params)]
        if query.strip():
            needle = query.strip().lower()
            rows = [task for task in rows if needle in " ".join([task["title"], task["note"], task.get("goal_title") or "", *task["tags"]]).lower()]
        return sorted([task for task in rows if task], key=lambda task: self._task_sort_key(task, mode))

    def completed_on(self, day: str) -> list[dict[str, Any]]:
        rows = [self._attach_task_details(row) for row in self.conn.execute("SELECT * FROM tasks WHERE status='completed' AND substr(completed_at,1,10)=? ORDER BY completed_at DESC", (day,))]
        return [row for row in rows if row]

    def all_tags(self) -> list[str]:
        return [row[0] for row in self.conn.execute("SELECT name FROM tags ORDER BY name")]

    def _sync_tags(self, task_id: str, tags: Iterable[str]) -> None:
        self.conn.execute("DELETE FROM task_tags WHERE task_id=?", (task_id,))
        for name in split_tags(tags):
            tag_id = self.conn.execute("SELECT id FROM tags WHERE name=?", (name,)).fetchone()
            if tag_id:
                tag_id = tag_id[0]
            else:
                tag_id = uid("tag")
                self.conn.execute("INSERT INTO tags(id,name) VALUES(?,?)", (tag_id, name))
            self.conn.execute("INSERT OR IGNORE INTO task_tags(task_id,tag_id) VALUES(?,?)", (task_id, tag_id))

    def _insert_plan(self, task_id: str, planned_date: str, assigned_at: str | None = None) -> None:
        self.conn.execute("INSERT INTO task_plan_history(id,task_id,planned_date,assigned_at) VALUES(?,?,?,?)", (uid("plan"), task_id, planned_date, assigned_at or now_iso()))

    def create_task(self, title: str, note: str = "", category: str = "work", priority: str = "normal", planned_date: str | None = None, goal_id: str | None = None, tags: Iterable[str] | str | None = None, subtasks: Iterable[str | dict[str, Any]] | None = None) -> str:
        title = title.strip()
        if not title:
            raise ValueError("标题不能为空")
        task_id = uid("task")
        timestamp = now_iso()
        task_subtasks = list(subtasks or [])
        with self.conn:
            self.conn.execute("INSERT INTO tasks(id,title,note,category,priority,planned_date,status,goal_id,sort_rank,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (task_id, title, note.strip(), category if category in ("work", "life") else "work", priority if priority in ("high", "normal") else "normal", planned_date or None, "todo", goal_id or None, datetime.now().timestamp(), timestamp, timestamp))
            self._sync_tags(task_id, tags or [])
            for index, item in enumerate(task_subtasks):
                step_title = item.get("title", "") if isinstance(item, dict) else str(item)
                if step_title.strip():
                    self.conn.execute("INSERT INTO subtasks(id,task_id,title,completed,sort_rank,created_at) VALUES(?,?,?,?,?,?)", (uid("step"), task_id, step_title.strip(), 0, index, timestamp))
            if planned_date:
                self._insert_plan(task_id, planned_date, timestamp)
        return task_id

    def update_task(self, task_id: str, values: dict[str, Any]) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        planned_date = values.get("planned_date", task["planned_date"]) or None
        old_date = task["planned_date"] or None
        timestamp = now_iso()
        with self.conn:
            if planned_date != old_date:
                current = self.conn.execute("SELECT id,planned_date FROM task_plan_history WHERE task_id=? AND planned_date=? AND superseded_at IS NULL ORDER BY assigned_at DESC LIMIT 1", (task_id, old_date)).fetchone() if old_date else None
                if current:
                    due = current["planned_date"] <= today_key()
                    self.conn.execute("UPDATE task_plan_history SET superseded_at=?,became_due=?,fulfilled_on_time=CASE WHEN ? THEN COALESCE(fulfilled_on_time,0) ELSE fulfilled_on_time END,cancelled_before_due=? WHERE id=?", (timestamp, int(due), int(due), int(not due), current["id"]))
                if planned_date:
                    self._insert_plan(task_id, planned_date, timestamp)
            fields = {"title": values.get("title", task["title"]).strip(), "note": values.get("note", task["note"]).strip(), "category": values.get("category", task["category"]), "priority": values.get("priority", task["priority"]), "planned_date": planned_date, "goal_id": values.get("goal_id", task["goal_id"]) or None, "updated_at": timestamp}
            self.conn.execute("UPDATE tasks SET title=:title,note=:note,category=:category,priority=:priority,planned_date=:planned_date,goal_id=:goal_id,updated_at=:updated_at WHERE id=:id", {**fields, "id": task_id})
            if "tags" in values:
                self._sync_tags(task_id, values["tags"])
            if "subtasks" in values:
                self.conn.execute("DELETE FROM subtasks WHERE task_id=?", (task_id,))
                for index, step in enumerate(values["subtasks"]):
                    step_title = step.get("title", "") if isinstance(step, dict) else str(step)
                    if step_title.strip():
                        self.conn.execute("INSERT INTO subtasks(id,task_id,title,completed,sort_rank,created_at) VALUES(?,?,?,?,?,?)", (uid("step"), task_id, step_title.strip(), int(bool(step.get("completed"))) if isinstance(step, dict) else 0, index, timestamp))

    def update_subtask(self, step_id: str, completed: bool | None = None, title: str | None = None) -> None:
        if completed is not None:
            self.conn.execute("UPDATE subtasks SET completed=? WHERE id=?", (int(completed), step_id))
        if title is not None:
            self.conn.execute("UPDATE subtasks SET title=? WHERE id=?", (title.strip(), step_id))
        self.conn.commit()

    def add_subtask(self, task_id: str, title: str) -> None:
        if title.strip():
            rank = self.conn.execute("SELECT COALESCE(MAX(sort_rank),0)+1 FROM subtasks WHERE task_id=?", (task_id,)).fetchone()[0]
            self.conn.execute("INSERT INTO subtasks(id,task_id,title,sort_rank,created_at) VALUES(?,?,?,?,?)", (uid("step"), task_id, title.strip(), rank, now_iso()))
            self.conn.commit()

    def delete_subtask(self, step_id: str) -> None:
        self.conn.execute("DELETE FROM subtasks WHERE id=?", (step_id,))
        self.conn.commit()

    def _mark_plan_completion(self, task: dict[str, Any], completed_at: str) -> None:
        completed_day = completed_at[:10]
        for row in self.conn.execute("SELECT id,planned_date,cancelled_before_due FROM task_plan_history WHERE task_id=?", (task["id"],)).fetchall():
            if row["cancelled_before_due"]:
                continue
            if row["planned_date"] == completed_day:
                self.conn.execute("UPDATE task_plan_history SET became_due=1,fulfilled_on_time=1 WHERE id=?", (row["id"],))
            elif row["planned_date"] < completed_day:
                self.conn.execute("UPDATE task_plan_history SET became_due=1,fulfilled_on_time=0 WHERE id=?", (row["id"],))
            else:
                self.conn.execute("UPDATE task_plan_history SET fulfilled_on_time=0 WHERE id=?", (row["id"],))

    def toggle_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if not task or task["status"] == "deleted":
            return
        with self.conn:
            if task["status"] == "completed":
                self.conn.execute("UPDATE tasks SET status='todo',completed_at=NULL,updated_at=? WHERE id=?", (now_iso(), task_id))
                self.conn.execute(
                    """
                    UPDATE task_plan_history
                    SET became_due=CASE WHEN planned_date<=? THEN 1 ELSE 0 END,
                        fulfilled_on_time=CASE WHEN planned_date<? THEN 0 ELSE NULL END
                    WHERE task_id=? AND cancelled_before_due=0
                    """,
                    (today_key(), today_key(), task_id),
                )
            else:
                completed_at = now_iso()
                self.conn.execute("UPDATE tasks SET status='completed',completed_at=?,updated_at=? WHERE id=?", (completed_at, completed_at, task_id))
                self._mark_plan_completion(task, completed_at)

    def delete_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if not task or task["status"] == "deleted":
            return
        with self.conn:
            self.conn.execute("UPDATE tasks SET status='deleted',deleted_at=?,deleted_previous_status=?,updated_at=? WHERE id=?", (now_iso(), task["status"], now_iso(), task_id))
            if task["planned_date"] and task["planned_date"] > today_key():
                self.conn.execute("UPDATE task_plan_history SET cancelled_before_due=1,superseded_at=? WHERE task_id=? AND planned_date=? AND superseded_at IS NULL", (now_iso(), task_id, task["planned_date"]))

    def restore_task(self, task_id: str) -> None:
        with self.conn:
            self.conn.execute("UPDATE tasks SET status=COALESCE(deleted_previous_status,'todo'),deleted_at=NULL,deleted_previous_status=NULL,updated_at=? WHERE id=? AND status='deleted'", (now_iso(), task_id))
            task = self.conn.execute("SELECT planned_date FROM tasks WHERE id=? AND status!='deleted'", (task_id,)).fetchone()
            if task and task["planned_date"]:
                active = self.conn.execute("SELECT id FROM task_plan_history WHERE task_id=? AND planned_date=? AND cancelled_before_due=0 AND superseded_at IS NULL ORDER BY assigned_at DESC LIMIT 1", (task_id, task["planned_date"])).fetchone()
                if not active:
                    cancelled = self.conn.execute("SELECT id FROM task_plan_history WHERE task_id=? AND planned_date=? AND cancelled_before_due=1 ORDER BY assigned_at DESC LIMIT 1", (task_id, task["planned_date"])).fetchone()
                    if cancelled:
                        self.conn.execute("UPDATE task_plan_history SET cancelled_before_due=0,superseded_at=NULL,became_due=?,fulfilled_on_time=NULL WHERE id=?", (int(task["planned_date"] <= today_key()), cancelled["id"]))
                    else:
                        self._insert_plan(task_id, task["planned_date"])

    def reorder_tasks(self, task_ids: Iterable[str]) -> None:
        with self.conn:
            for rank, task_id in enumerate(task_ids):
                self.conn.execute("UPDATE tasks SET sort_rank=?,updated_at=? WHERE id=?", (rank, now_iso(), task_id))

    def create_goal(self, title: str, note: str = "", category: str = "work", priority: str = "normal", planned_finish_date: str | None = None) -> str:
        title = title.strip()
        if not title:
            raise ValueError("目标标题不能为空")
        goal_id = uid("goal")
        timestamp = now_iso()
        self.conn.execute("INSERT INTO goals(id,title,note,category,priority,planned_finish_date,status,sort_rank,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (goal_id, title, note.strip(), category if category in ("work", "life") else "work", priority if priority in ("high", "normal") else "normal", planned_finish_date or None, "active", datetime.now().timestamp(), timestamp))
        self.conn.commit()
        return goal_id

    def get_goal(self, goal_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
        if not row:
            return None
        goal = dict(row)
        goal.update(self.goal_stats(goal_id))
        return goal

    def list_goals(self, status: str = "all", category: str = "all", query: str = "") -> list[dict[str, Any]]:
        clauses = ["1=1"]
        params: list[str] = []
        if status in ("active", "achieved"):
            clauses.append("status=?")
            params.append(status)
        if category in ("work", "life"):
            clauses.append("category=?")
            params.append(category)
        goals = []
        for row in self.conn.execute(f"SELECT * FROM goals WHERE {' AND '.join(clauses)}", params):
            goal = dict(row)
            goal.update(self.goal_stats(goal["id"]))
            if query.strip() and query.strip().lower() not in f"{goal['title']} {goal['note']}".lower():
                continue
            goals.append(goal)
        return sorted(goals, key=lambda item: (0 if item["priority"] == "high" else 1, item["sort_rank"], item["created_at"]))

    def update_goal(self, goal_id: str, values: dict[str, Any]) -> None:
        self.conn.execute("UPDATE goals SET title=?,note=?,category=?,priority=?,planned_finish_date=? WHERE id=?", (values.get("title", "").strip(), values.get("note", "").strip(), values.get("category", "work"), values.get("priority", "normal"), values.get("planned_finish_date") or None, goal_id))
        self.conn.commit()

    def goal_stats(self, goal_id: str) -> dict[str, int]:
        row = self.conn.execute("SELECT COUNT(*) AS total,COALESCE(SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END),0) AS completed FROM tasks WHERE goal_id=? AND status!='deleted'", (goal_id,)).fetchone()
        total = int(row["total"])
        completed = int(row["completed"])
        goal_status = self.conn.execute("SELECT status FROM goals WHERE id=?", (goal_id,)).fetchone()
        status = goal_status[0] if goal_status else "active"
        progress = 100 if total == 0 and status == "achieved" else (0 if total == 0 else round(completed / total * 100))
        return {"total": total, "completed": completed, "remaining": total - completed, "progress": progress}

    def achieve_goal(self, goal_id: str, option: str = "detach") -> None:
        remaining = self.conn.execute("SELECT id,status FROM tasks WHERE goal_id=? AND status='todo'", (goal_id,)).fetchall()
        with self.conn:
            for row in remaining:
                if option == "detach":
                    self.conn.execute("UPDATE tasks SET goal_id=NULL,updated_at=? WHERE id=?", (now_iso(), row["id"]))
                elif option == "complete":
                    completed_at = now_iso()
                    task = self.get_task(row["id"])
                    self.conn.execute("UPDATE tasks SET status='completed',completed_at=?,updated_at=? WHERE id=?", (completed_at, completed_at, row["id"]))
                    if task:
                        self._mark_plan_completion(task, completed_at)
                elif option == "delete":
                    self.conn.execute("UPDATE tasks SET status='deleted',deleted_at=?,deleted_previous_status='todo',updated_at=? WHERE id=?", (now_iso(), now_iso(), row["id"]))
            self.conn.execute("UPDATE goals SET status='achieved',achieved_at=? WHERE id=?", (now_iso(), goal_id))

    def restore_goal(self, goal_id: str) -> None:
        self.conn.execute("UPDATE goals SET status='active',achieved_at=NULL WHERE id=?", (goal_id,))
        self.conn.commit()

    def delete_goal(self, goal_id: str, option: str = "detach") -> None:
        tasks = self.conn.execute("SELECT id,status FROM tasks WHERE goal_id=? AND status!='deleted'", (goal_id,)).fetchall()
        with self.conn:
            for row in tasks:
                if option == "delete" and row["status"] == "todo":
                    self.conn.execute("UPDATE tasks SET status='deleted',deleted_at=?,deleted_previous_status='todo',goal_id=NULL,updated_at=? WHERE id=?", (now_iso(), now_iso(), row["id"]))
                else:
                    self.conn.execute("UPDATE tasks SET goal_id=NULL,updated_at=? WHERE id=?", (now_iso(), row["id"]))
            self.conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))

    def create_template(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if not task:
            return
        self.conn.execute("INSERT INTO task_templates(id,title,note,category,priority,tags_json,subtasks_json,created_at) VALUES(?,?,?,?,?,?,?,?)", (uid("template"), task["title"], task["note"], task["category"], task["priority"], json.dumps(task["tags"], ensure_ascii=False), json.dumps([step["title"] for step in task["subtasks"]], ensure_ascii=False), now_iso()))
        self.conn.commit()

    def list_templates(self) -> list[dict[str, Any]]:
        templates = []
        for row in self.conn.execute("SELECT * FROM task_templates ORDER BY created_at DESC"):
            item = dict(row)
            item["tags"] = json.loads(item.pop("tags_json") or "[]")
            item["subtasks"] = json.loads(item.pop("subtasks_json") or "[]")
            templates.append(item)
        return templates

    def delete_template(self, template_id: str) -> None:
        self.conn.execute("DELETE FROM task_templates WHERE id=?", (template_id,))
        self.conn.commit()

    def actual_count(self, start: str, end: str) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM tasks WHERE status='completed' AND substr(completed_at,1,10) BETWEEN ? AND ?", (start, end)).fetchone()[0])

    def plan_stats(self, start: str, end: str) -> dict[str, int]:
        rows = self.conn.execute("SELECT planned_date,fulfilled_on_time,cancelled_before_due FROM task_plan_history WHERE planned_date BETWEEN ? AND ? AND cancelled_before_due=0", (start, end)).fetchall()
        valid = [row for row in rows if row["fulfilled_on_time"] is not None or row["planned_date"] <= today_key()]
        on_time = sum(1 for row in valid if row["fulfilled_on_time"] == 1)
        return {"total": len(valid), "on_time": on_time, "rate": round(on_time / len(valid) * 100) if valid else 0}

    def weekly_stats(self) -> dict[str, Any]:
        start = start_of_week().isoformat()
        end = end_of_week().isoformat()
        values = self.plan_stats(start, end)
        values["actual"] = self.actual_count(start, end)
        values["days"] = []
        for index in range(7):
            day_value = (start_of_week() + timedelta(days=index)).isoformat()
            stats = self.plan_stats(day_value, day_value)
            values["days"].append({"date": day_value, "actual": self.actual_count(day_value, day_value), "rate": stats["rate"] if stats["total"] else None})
        return values

    def backup_payload(self) -> dict[str, Any]:
        tasks = []
        for row in self.conn.execute("SELECT * FROM tasks"):
            task = self._attach_task_details(row)
            task["plan_history"] = [dict(item) for item in self.conn.execute("SELECT * FROM task_plan_history WHERE task_id=? ORDER BY assigned_at", (task["id"],))]
            tasks.append(task)
        return {
            "app": "piggyplan",
            "version": 1,
            "exported_at": now_iso(),
            "settings": self.settings(),
            "tasks": tasks,
            "goals": [dict(row) for row in self.conn.execute("SELECT * FROM goals")],
            "templates": self.list_templates(),
        }

    def export_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.backup_payload(), ensure_ascii=False, indent=2), encoding="utf-8")

    def backup_database(self, path: str | Path) -> None:
        """Create a consistent SQLite snapshot, including WAL contents."""

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            self.conn.commit()
            backup = sqlite3.connect(temporary)
            try:
                self.conn.backup(backup)
                backup.commit()
            finally:
                backup.close()
            temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()

    def export_csv(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["标题", "状态", "分类", "优先级", "计划日期", "实际完成日期", "所属目标", "标签", "备注"])
            for task in self.list_tasks(include_completed=True, status="completed"):
                writer.writerow([task["title"], "已完成", "生活" if task["category"] == "life" else "工作", "高" if task["priority"] == "high" else "普通", date_text(task["planned_date"]), task["completed_at"][:10] if task["completed_at"] else "", task.get("goal_title") or "独立待办", "、".join(task["tags"]), task["note"]])

    def import_json(self, path: str | Path) -> None:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        data = payload.get("data", payload)
        if not isinstance(data, dict) or not isinstance(data.get("tasks"), list) or not isinstance(data.get("goals"), list):
            raise ValueError("备份结构不正确")
        tasks = data["tasks"]
        goals = data["goals"]
        if any(not isinstance(item, dict) or not str(item.get("id", "")).strip() or not str(item.get("title", "")).strip() for item in [*tasks, *goals]):
            raise ValueError("备份中存在缺少 ID 或标题的记录")
        task_ids = [str(item["id"]) for item in tasks]
        goal_ids = [str(item["id"]) for item in goals]
        if len(task_ids) != len(set(task_ids)) or len(goal_ids) != len(set(goal_ids)):
            raise ValueError("备份中存在重复 ID")
        known_goals = set(goal_ids)
        if any(task.get("goal_id") and task.get("goal_id") not in known_goals for task in tasks):
            raise ValueError("备份中存在无效的目标关联")
        with self.conn:
            for table in ("task_tags", "tags", "subtasks", "task_plan_history", "tasks", "goals", "task_templates", "app_settings"):
                self.conn.execute(f"DELETE FROM {table}")
            for goal in goals:
                self.conn.execute("INSERT INTO goals(id,title,note,category,priority,planned_finish_date,status,sort_rank,created_at,achieved_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (goal["id"], goal.get("title", ""), goal.get("note", ""), goal.get("category", "work"), goal.get("priority", "normal"), goal.get("planned_finish_date"), goal.get("status", "active"), goal.get("sort_rank", 0), goal.get("created_at", now_iso()), goal.get("achieved_at")))
            for task in tasks:
                self.conn.execute("INSERT INTO tasks(id,title,note,category,priority,planned_date,status,goal_id,sort_rank,created_at,updated_at,completed_at,deleted_at,deleted_previous_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (task["id"], task.get("title", ""), task.get("note", ""), task.get("category", "work"), task.get("priority", "normal"), task.get("planned_date"), task.get("status", "todo"), task.get("goal_id"), task.get("sort_rank", 0), task.get("created_at", now_iso()), task.get("updated_at", now_iso()), task.get("completed_at"), task.get("deleted_at"), task.get("deleted_previous_status")))
                self._sync_tags(task["id"], task.get("tags", []))
                for index, step in enumerate(task.get("subtasks", [])):
                    self.conn.execute("INSERT INTO subtasks(id,task_id,title,completed,sort_rank,created_at) VALUES(?,?,?,?,?,?)", (step.get("id", uid("step")), task["id"], step.get("title", ""), int(bool(step.get("completed"))), step.get("sort_rank", index), step.get("created_at", now_iso())))
                for record in task.get("plan_history", []):
                    self.conn.execute("INSERT INTO task_plan_history(id,task_id,planned_date,assigned_at,superseded_at,became_due,fulfilled_on_time,cancelled_before_due) VALUES(?,?,?,?,?,?,?,?)", (record.get("id", uid("plan")), task["id"], record["planned_date"], record.get("assigned_at", now_iso()), record.get("superseded_at"), int(bool(record.get("became_due"))), record.get("fulfilled_on_time"), int(bool(record.get("cancelled_before_due")))))
            for template in data.get("templates", []):
                self.conn.execute("INSERT INTO task_templates(id,title,note,category,priority,tags_json,subtasks_json,created_at) VALUES(?,?,?,?,?,?,?,?)", (template.get("id", uid("template")), template.get("title", ""), template.get("note", ""), template.get("category", "work"), template.get("priority", "normal"), json.dumps(template.get("tags", []), ensure_ascii=False), json.dumps(template.get("subtasks", []), ensure_ascii=False), template.get("created_at", now_iso())))
            for key, value in data.get("settings", {}).items():
                self.conn.execute("INSERT INTO app_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    def clear_all(self) -> None:
        with self.conn:
            self.conn.executescript("DELETE FROM task_tags; DELETE FROM tags; DELETE FROM subtasks; DELETE FROM task_plan_history; DELETE FROM tasks; DELETE FROM goals; DELETE FROM task_templates;")

    def seed_demo(self) -> None:
        product = self.create_goal("完成产品季度复盘", "把用户反馈、数据和下一步行动整理成一份能推动决策的复盘。", "work", "high", offset_date(24))
        movement = self.create_goal("建立每周运动习惯", "让运动成为轻量、可持续的生活节奏。", "life", "normal", offset_date(48))
        old = offset_date(-2)
        yesterday = offset_date(-1)
        self.create_task("整理上周项目会议结论", "把决策、负责人和下一步行动补进项目文档。", "work", "high", old, product, ["项目", "复盘"])
        feedback = self.create_task("完成用户反馈整理", "已提炼出三条需要进入下个版本的产品机会。", "work", "normal", yesterday, product, ["用户", "复盘"])
        self.toggle_task(feedback)
        self.create_task("给客户发出版本确认邮件", "确认体验优化清单和本周交付范围。", "work", "high", today_key(), product, ["沟通"])
        self.create_task("补齐复盘分享的大纲", "先完成结构，不追求一次写完。", "work", "high", today_key(), product, ["输出"])
        self.create_task("完成 30 分钟轻松跑", "", "life", "normal", today_key(), movement, ["健康"])
        self.create_task("准备周五产品演示", "挑 3 个最能说明变化的场景，配上前后对比。", "work", "high", offset_date(2), product, ["演示"])
        self.create_task("安排本周下一次拉伸时间", "", "life", "normal", offset_date(4), movement, ["健康"])
        self.create_task("购买新的收纳盒", "量一下书桌抽屉，再决定尺寸。", "life", "normal", None, None, ["采购"])
        archived = self.create_task("发布新版帮助中心首页", "", "work", "normal", offset_date(-8), None, ["发布"])
        self.toggle_task(archived)
        self.create_template_from_values("每周复盘", "回顾本周完成情况，留下下周最重要的三个动作。", "work", "normal", ["复盘"], ["回顾已完成事项", "记录阻塞点", "选出下周三个动作"])

    def create_template_from_values(self, title: str, note: str, category: str, priority: str, tags: list[str], subtasks: list[str]) -> None:
        self.conn.execute("INSERT INTO task_templates(id,title,note,category,priority,tags_json,subtasks_json,created_at) VALUES(?,?,?,?,?,?,?,?)", (uid("template"), title, note, category, priority, json.dumps(tags, ensure_ascii=False), json.dumps(subtasks, ensure_ascii=False), now_iso()))
        self.conn.commit()
