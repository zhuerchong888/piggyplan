"""Pure SQLite coverage for goal deletion, plan history and task recovery.

Every case uses a temporary database; no application, GUI or runtime data path
is imported or opened.
"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from piggyplan.database import Database


class GoalDeletionRulesTests(unittest.TestCase):
    def setUp(self):
        self.day_patch = patch("piggyplan.database.today_key", return_value="2026-10-02")
        self.today = self.day_patch.start()
        self.addCleanup(self.day_patch.stop)
        timestamp_patch = patch("piggyplan.database.now_iso", return_value="2026-10-02T12:00:00")
        timestamp_patch.start()
        self.addCleanup(timestamp_patch.stop)

    @contextmanager
    def database_case(self):
        self.today.return_value = "2026-10-02"
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "goal-rules.db")
            try:
                yield db, db.create_goal("临时目标")
            finally:
                db.close()

    @staticmethod
    def delete_through_goal(db, goal_id, operation):
        if operation == "achieve":
            db.achieve_goal(goal_id, "delete")
        else:
            db.delete_goal(goal_id, "delete")

    @staticmethod
    def history(db, task_id):
        return [dict(row) for row in db.conn.execute(
            "SELECT * FROM task_plan_history WHERE task_id=? ORDER BY planned_date,id", (task_id,)
        )]

    def test_future_goal_deletion_cancels_plan_before_it_becomes_due(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                task_id = db.create_task("未来待办", planned_date="2026-10-03", goal_id=goal_id)
                plan_id = self.history(db, task_id)[0]["id"]
                self.delete_through_goal(db, goal_id, operation)
                task = db.get_task(task_id)
                self.assertEqual(task["status"], "deleted")
                self.assertEqual(task["deleted_previous_status"], "todo")
                self.assertEqual(task["goal_id"], goal_id if operation == "achieve" else None)
                history = self.history(db, task_id)
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["id"], plan_id)
                self.assertEqual(history[0]["cancelled_before_due"], 1)
                self.assertEqual(history[0]["superseded_at"], "2026-10-02T12:00:00")
                self.today.return_value = "2026-10-03"
                self.assertEqual(db.plan_stats("2026-10-03", "2026-10-03"),
                                 {"total": 0, "on_time": 0, "rate": 0})

    def test_today_and_overdue_goal_deletion_keep_due_plan_history(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                tasks = [db.create_task("到期待办", planned_date=day, goal_id=goal_id)
                         for day in ("2026-10-01", "2026-10-02")]
                before = {task_id: self.history(db, task_id) for task_id in tasks}
                self.delete_through_goal(db, goal_id, operation)
                for task_id in tasks:
                    self.assertEqual(db.get_task(task_id)["status"], "deleted")
                    self.assertEqual(self.history(db, task_id), before[task_id])
                self.assertEqual(db.plan_stats("2026-10-01", "2026-10-02"),
                                 {"total": 2, "on_time": 0, "rate": 0})

    def test_undated_goal_task_deletion_does_not_create_plan_history(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                task_id = db.create_task("未安排日期", goal_id=goal_id)
                self.delete_through_goal(db, goal_id, operation)
                self.assertEqual(db.get_task(task_id)["status"], "deleted")
                self.assertEqual(self.history(db, task_id), [])

    def test_goal_deletion_cancels_current_future_plan_and_keeps_old_due_plan(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                task_id = db.create_task("改期待办", planned_date="2026-10-01", goal_id=goal_id)
                db.update_task(task_id, {"planned_date": "2026-10-03"})
                old_plan = self.history(db, task_id)[0]
                self.delete_through_goal(db, goal_id, operation)
                history = self.history(db, task_id)
                self.assertEqual(history[0], old_plan)
                self.assertEqual(history[1]["cancelled_before_due"], 1)
                self.today.return_value = "2026-10-03"
                self.assertEqual(db.plan_stats("2026-10-01", "2026-10-03"),
                                 {"total": 1, "on_time": 0, "rate": 0})
                db.restore_task(task_id)
                self.assertEqual(self.history(db, task_id)[0], old_plan)
                self.assertEqual(db.plan_stats("2026-10-01", "2026-10-03"),
                                 {"total": 2, "on_time": 0, "rate": 0})

    def test_restoring_future_goal_deleted_task_reactivates_same_plan(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                task_id = db.create_task("未来待办", planned_date="2026-10-03", goal_id=goal_id)
                plan_id = self.history(db, task_id)[0]["id"]
                self.delete_through_goal(db, goal_id, operation)
                db.restore_task(task_id)
                db.restore_task(task_id)
                task = db.get_task(task_id)
                self.assertEqual(task["status"], "todo")
                self.assertIsNone(task["deleted_at"])
                self.assertIsNone(task["deleted_previous_status"])
                self.assertEqual(task["goal_id"], goal_id if operation == "achieve" else None)
                history = self.history(db, task_id)
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["id"], plan_id)
                self.assertEqual(history[0]["cancelled_before_due"], 0)
                self.assertIsNone(history[0]["superseded_at"])
                self.assertEqual(history[0]["became_due"], 0)
                self.assertIsNone(history[0]["fulfilled_on_time"])
                self.today.return_value = "2026-10-03"
                self.assertEqual(db.plan_stats("2026-10-03", "2026-10-03"),
                                 {"total": 1, "on_time": 0, "rate": 0})

    def test_restoring_goal_deleted_task_after_due_reinstates_due_plan(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                task_id = db.create_task("未来待办", planned_date="2026-10-03", goal_id=goal_id)
                plan_id = self.history(db, task_id)[0]["id"]
                self.delete_through_goal(db, goal_id, operation)
                self.today.return_value = "2026-10-04"
                db.restore_task(task_id)
                history = self.history(db, task_id)
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["id"], plan_id)
                self.assertEqual(history[0]["cancelled_before_due"], 0)
                self.assertEqual(history[0]["became_due"], 1)
                self.assertIsNone(history[0]["superseded_at"])
                self.assertEqual(db.plan_stats("2026-10-03", "2026-10-03"),
                                 {"total": 1, "on_time": 0, "rate": 0})

    def test_restoring_due_goal_deleted_task_keeps_existing_plan(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                task_id = db.create_task("逾期待办", planned_date="2026-10-01", goal_id=goal_id)
                before = self.history(db, task_id)
                self.delete_through_goal(db, goal_id, operation)
                db.restore_task(task_id)
                self.assertEqual(db.get_task(task_id)["status"], "todo")
                self.assertEqual(self.history(db, task_id), before)
                self.assertEqual(db.plan_stats("2026-10-01", "2026-10-01"),
                                 {"total": 1, "on_time": 0, "rate": 0})

    def test_goal_deletion_leaves_completed_tasks_and_their_plans_intact(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                task_id = db.create_task("已完成事项", planned_date="2026-10-02", goal_id=goal_id)
                db.toggle_task(task_id)
                before = self.history(db, task_id)
                self.delete_through_goal(db, goal_id, operation)
                task = db.get_task(task_id)
                self.assertEqual(task["status"], "completed")
                self.assertEqual(task["completed_at"], "2026-10-02T12:00:00")
                self.assertEqual(task["goal_id"], goal_id if operation == "achieve" else None)
                self.assertEqual(self.history(db, task_id), before)
                self.assertEqual(db.plan_stats("2026-10-02", "2026-10-02"),
                                 {"total": 1, "on_time": 1, "rate": 100})

    def test_goal_deletion_does_not_touch_an_unrelated_future_task(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                db.create_task("关联待办", planned_date="2026-10-03", goal_id=goal_id)
                task_id = db.create_task("无关待办", planned_date="2026-10-03")
                before = db.get_task(task_id), self.history(db, task_id)
                self.delete_through_goal(db, goal_id, operation)
                self.assertEqual((db.get_task(task_id), self.history(db, task_id)), before)

    def test_failed_goal_operation_rolls_back_all_task_and_history_changes(self):
        for operation in ("achieve", "delete"):
            with self.subTest(operation=operation), self.database_case() as (db, goal_id):
                tasks = [db.create_task("未来待办", planned_date=day, goal_id=goal_id)
                         for day in ("2026-10-03", "2026-10-04")]
                before_goal = db.get_goal(goal_id)
                before_tasks = {task_id: db.get_task(task_id) for task_id in tasks}
                before_history = {task_id: self.history(db, task_id) for task_id in tasks}
                action = "UPDATE OF status" if operation == "achieve" else "DELETE"
                db.conn.execute(f"""CREATE TEMP TRIGGER reject_goal_action
                    BEFORE {action} ON goals BEGIN
                    SELECT RAISE(ABORT, 'injected goal failure'); END""")
                db.conn.commit()
                with self.assertRaisesRegex(sqlite3.IntegrityError, "injected goal failure"):
                    self.delete_through_goal(db, goal_id, operation)
                self.assertEqual(db.get_goal(goal_id), before_goal)
                for task_id in tasks:
                    self.assertEqual(db.get_task(task_id), before_tasks[task_id])
                    self.assertEqual(self.history(db, task_id), before_history[task_id])
                self.assertFalse(db.conn.in_transaction)

    def test_direct_task_deletion_retains_the_same_date_and_recovery_policy(self):
        for day, cancelled in (("2026-10-01", 0), ("2026-10-02", 0), ("2026-10-03", 1)):
            with self.subTest(day=day), self.database_case() as (db, goal_id):
                task_id = db.create_task("单独删除待办", planned_date=day, goal_id=goal_id)
                plan_id = self.history(db, task_id)[0]["id"]
                db.delete_task(task_id)
                db.delete_task(task_id)
                self.assertEqual(self.history(db, task_id)[0]["cancelled_before_due"], cancelled)
                self.assertEqual(db.get_task(task_id)["deleted_previous_status"], "todo")
                db.restore_task(task_id)
                history = self.history(db, task_id)
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0]["id"], plan_id)
                self.assertEqual(history[0]["cancelled_before_due"], 0)
                self.assertIsNone(history[0]["superseded_at"])
                self.assertEqual(db.get_task(task_id)["status"], "todo")

    def test_direct_completed_task_deletion_restores_completed_status(self):
        with self.database_case() as (db, goal_id):
            task_id = db.create_task("已完成事项", planned_date="2026-10-02", goal_id=goal_id)
            db.toggle_task(task_id)
            before = self.history(db, task_id)
            db.delete_task(task_id)
            self.assertEqual(db.get_task(task_id)["deleted_previous_status"], "completed")
            db.restore_task(task_id)
            self.assertEqual(db.get_task(task_id)["status"], "completed")
            self.assertEqual(db.get_task(task_id)["completed_at"], "2026-10-02T12:00:00")
            self.assertEqual(self.history(db, task_id), before)
            self.assertEqual(db.plan_stats("2026-10-02", "2026-10-02"),
                             {"total": 1, "on_time": 1, "rate": 100})


if __name__ == "__main__":
    unittest.main()
