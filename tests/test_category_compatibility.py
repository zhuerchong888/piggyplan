"""Category display changes must preserve existing SQLite and backup values.

Only temporary databases are opened; this suite never imports the application
or starts a GUI.
"""
from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from piggyplan.database import Database
from piggyplan.util import category_label, goal_choice_labels


class CategoryCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.directory = Path(self.folder.name)

    def legacy_database(self) -> Path:
        """Build the old on-disk records without current creation helpers."""
        path = self.directory / "legacy.db"
        with closing(sqlite3.connect(path)) as conn:
            conn.executescript("""
                CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO schema_meta VALUES ('schema_version', '1');
                CREATE TABLE goals (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'work' CHECK(category IN ('work','life')),
                    priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('high','normal')),
                    planned_finish_date TEXT,
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','achieved')),
                    sort_rank REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL, achieved_at TEXT
                );
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'work' CHECK(category IN ('work','life')),
                    priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('high','normal')),
                    planned_date TEXT,
                    status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','completed','deleted')),
                    goal_id TEXT REFERENCES goals(id) ON DELETE SET NULL,
                    sort_rank REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, completed_at TEXT, deleted_at TEXT,
                    deleted_previous_status TEXT
                );
                CREATE TABLE task_templates (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT 'work',
                    priority TEXT NOT NULL DEFAULT 'normal',
                    tags_json TEXT NOT NULL DEFAULT '[]', subtasks_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            conn.execute(
                "INSERT INTO goals(id,title,note,category,created_at) VALUES(?,?,?,?,?)",
                ("legacy-goal", "旧目标", "保持生活节奏", "life", "2026-09-01T08:00:00"),
            )
            conn.execute(
                """INSERT INTO tasks(id,title,note,category,status,goal_id,
                   created_at,updated_at,completed_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                ("legacy-task", "旧待办", "生活节奏", "life", "completed", "legacy-goal",
                 "2026-09-01T08:00:00", "2026-09-02T08:00:00", "2026-09-02T08:00:00"),
            )
            conn.execute(
                "INSERT INTO task_templates(id,title,note,category,created_at) VALUES(?,?,?,?,?)",
                ("legacy-template", "旧模板", "生活节奏", "life", "2026-09-01T08:00:00"),
            )
            conn.execute("INSERT INTO app_settings VALUES('default_category','life')")
            conn.commit()
        return path

    @staticmethod
    def category_schema(path: Path) -> dict[str, str]:
        with closing(sqlite3.connect(path)) as conn:
            return dict(conn.execute(
                """SELECT name,sql FROM sqlite_master WHERE type='table'
                   AND name IN ('schema_meta','goals','tasks','task_templates','app_settings')"""
            ))

    def open_database(self, path: Path) -> Database:
        database = Database(path)
        self.addCleanup(database.close)
        return database

    def test_reopen_legacy_sqlite_keeps_stored_category_and_displays_learning(self):
        path = self.legacy_database()
        original_schema = self.category_schema(path)
        database = self.open_database(path)

        tasks = database.list_tasks(include_completed=True, category="life")
        goals = database.list_goals(category="life")
        self.assertEqual([task["id"] for task in tasks], ["legacy-task"])
        self.assertEqual([goal["id"] for goal in goals], ["legacy-goal"])
        self.assertEqual(database.list_templates()[0]["category"], "life")
        self.assertEqual(database.get_setting("default_category"), "life")
        self.assertEqual(database.conn.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()[0], "1")
        self.assertEqual(self.category_schema(path), original_schema)
        self.assertEqual(tasks[0]["note"], "生活节奏")
        self.assertEqual(category_label(tasks[0]["category"]), "学习")
        self.assertEqual(category_label(goals[0]["category"]), "学习")
        self.assertEqual(category_label(database.get_setting("default_category")), "学习")
        self.assertEqual(category_label("work"), "工作")

    def test_completed_csv_uses_learning_label_without_rewriting_free_text(self):
        database = self.open_database(self.legacy_database())
        work_task = database.create_task("工作记录", category="work")
        database.toggle_task(work_task)
        database.create_task("尚未完成", category="life")
        target = self.directory / "completed.csv"
        database.export_csv(target)

        with target.open(encoding="utf-8-sig", newline="") as handle:
            rows = {row["标题"]: row for row in csv.DictReader(handle)}
        self.assertEqual(set(rows), {"旧待办", "工作记录"})
        self.assertEqual(rows["旧待办"]["分类"], "学习")
        self.assertEqual(rows["旧待办"]["备注"], "生活节奏")
        self.assertEqual(rows["工作记录"]["分类"], "工作")
        self.assertEqual(database.get_task("legacy-task")["category"], "life")

    def test_json_round_trip_keeps_life_values_and_restores_learning_display(self):
        original = self.open_database(self.legacy_database())
        backup = self.directory / "backup.json"
        original.export_json(backup)
        payload = json.loads(backup.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["settings"]["default_category"], "life")
        self.assertEqual(payload["tasks"][0]["category"], "life")
        self.assertEqual(payload["goals"][0]["category"], "life")
        self.assertEqual(payload["templates"][0]["category"], "life")
        self.assertEqual(payload["tasks"][0]["note"], "生活节奏")

        restored_path = self.directory / "restored.db"
        restored = Database(restored_path)
        try:
            restored.import_json(backup)
        finally:
            restored.close()
        reopened = self.open_database(restored_path)
        task = reopened.get_task("legacy-task")
        self.assertEqual(task["category"], "life")
        self.assertEqual(task["note"], "生活节奏")
        self.assertEqual(reopened.get_goal("legacy-goal")["category"], "life")
        self.assertEqual(reopened.list_templates()[0]["category"], "life")
        self.assertEqual(reopened.get_setting("default_category"), "life")
        self.assertEqual(category_label(task["category"]), "学习")
        self.assertEqual(category_label(reopened.get_setting("default_category")), "学习")

    def test_duplicate_goal_choices_use_learning_suffix_and_keep_both_ids(self):
        database = self.open_database(self.directory / "duplicates.db")
        work_goal = database.create_goal("同名目标", category="work")
        learning_goal = database.create_goal("同名目标", category="life")
        choices = goal_choice_labels(database.list_goals())
        self.assertEqual(set(choices.values()), {work_goal, learning_goal})
        learning_label = next(label for label, goal_id in choices.items() if goal_id == learning_goal)
        work_label = next(label for label, goal_id in choices.items() if goal_id == work_goal)
        self.assertIn(" · 学习 · ", learning_label)
        self.assertIn(" · 工作 · ", work_label)


if __name__ == "__main__":
    unittest.main()
