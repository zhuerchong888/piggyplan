"""Regression coverage for real editing, navigation and archive workflows.

All databases are temporary; Windows integration and automatic backups are
disabled so this suite cannot touch the user's data or global shortcuts.
"""
from __future__ import annotations

import csv
import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from piggyplan.runtime.tcl import prepare

prepare()

import tkinter as tk
from tkinter import ttk

from piggyplan.app import PiggyPlanApp
from piggyplan.database import Database
from piggyplan.util import split_tags


class InactiveIntegration:
    available = False
    tray_available = False
    _hotkey_registered = False
    hotkey_error = None

    def __init__(self, app):
        pass

    def destroy(self):
        pass


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def button_text(widget):
    if isinstance(widget, tk.Canvas) and hasattr(widget, "_text"):
        return widget.itemcget(widget._text, "text")
    try:
        return widget.cget("text")
    except tk.TclError:
        return ""


def click_button(parent, text):
    button = next(widget for widget in descendants(parent)
                  if button_text(widget) == text and hasattr(widget, "invoke"))
    button.invoke()


class DataWorkflowTests(unittest.TestCase):
    def test_tags_accept_all_promised_separators(self):
        self.assertEqual(split_tags("工作、复盘，工作,沟通"), ["工作", "复盘", "沟通"])

    def test_csv_preserves_full_natural_date(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "tasks.db")
            try:
                task_id = db.create_task("历史记录", planned_date="2025-08-12")
                db.toggle_task(task_id)
                target = Path(folder) / "history.csv"
                db.export_csv(target)
                with target.open(encoding="utf-8-sig", newline="") as handle:
                    row = list(csv.DictReader(handle))[0]
                self.assertEqual(row["计划日期"], "2025-08-12")
            finally:
                db.close()

    def test_invalid_backup_nested_data_cannot_replace_existing_data(self):
        invalid_changes = [
            ("template null subtasks", lambda data: data["templates"][0].update(subtasks=None)),
            ("template wrong subtasks", lambda data: data["templates"][0].update(subtasks=[42])),
            ("template null tags", lambda data: data["templates"][0].update(tags=None)),
            ("template wrong tags", lambda data: data["templates"][0].update(tags={"tag": "bad"})),
            ("task date", lambda data: data["tasks"][0].update(planned_date="2026-02-30")),
            ("goal date", lambda data: data["goals"][0].update(planned_finish_date="next week")),
            ("task null subtasks", lambda data: data["tasks"][0].update(subtasks=None)),
            ("task step wrong title", lambda data: data["tasks"][0]["subtasks"][0].update(title=["bad"])),
            ("task wrong tags", lambda data: data["tasks"][0].update(tags={"tag": "bad"})),
            ("task sort order", lambda data: data["tasks"][0].update(sort_rank="not a number")),
            ("task completion time", lambda data: data["tasks"][0].update(completed_at="not a date")),
            ("plan history date", lambda data: data["tasks"][0]["plan_history"][0].update(planned_date="2026-13-01")),
            ("plan history flag", lambda data: data["tasks"][0]["plan_history"][0].update(fulfilled_on_time="yes")),
            ("settings shape", lambda data: data.update(settings=[])),
            ("nested settings value", lambda data: data["settings"].update(geometry={"bad": "shape"})),
        ]
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "tasks.db")
            try:
                goal_id = db.create_goal("原目标")
                task_id = db.create_task("原任务", planned_date="2026-10-02", goal_id=goal_id, tags=["原标签"], subtasks=["原步骤"])
                db.create_template(task_id)
                db.set_setting("theme", "pink")
                before = db.backup_payload()
                before.pop("exported_at")
                baseline = Path(folder) / "baseline.json"
                baseline.write_text(json.dumps(before, ensure_ascii=False), encoding="utf-8")
                for label, change in invalid_changes:
                    with self.subTest(label=label):
                        db.import_json(baseline)
                        invalid = copy.deepcopy(before)
                        change(invalid)
                        source = Path(folder) / "invalid.json"
                        source.write_text(json.dumps(invalid, ensure_ascii=False), encoding="utf-8")
                        try:
                            db.import_json(source)
                        except ValueError:
                            pass
                        except Exception as error:
                            self.fail(f"Malformed backup should report validation failure, not {type(error).__name__}")
                        else:
                            self.fail(f"Accepted malformed backup: {label}")
                        after = db.backup_payload()
                        after.pop("exported_at")
                        self.assertEqual(after, before)
            finally:
                db.close()

    def test_complete_export_restore_keeps_nested_data(self):
        with tempfile.TemporaryDirectory() as folder:
            original = Database(Path(folder) / "original.db")
            restored = Database(Path(folder) / "restored.db")
            try:
                goal_id = original.create_goal("目标", planned_finish_date="2026-11-01")
                task_id = original.create_task("待办", goal_id=goal_id, planned_date="2026-10-02", tags=["甲", "乙"], subtasks=["步骤一", "步骤二"])
                original.update_subtask(original.get_task(task_id)["subtasks"][0]["id"], completed=True)
                original.create_template(task_id)
                original.set_setting("geometry", "1160x760")
                original.toggle_task(task_id)
                source = Path(folder) / "backup.json"
                original.export_json(source)
                restored.import_json(source)
                before = original.backup_payload()
                after = restored.backup_payload()
                before.pop("exported_at")
                after.pop("exported_at")
                self.assertEqual(after, before)
            finally:
                original.close()
                restored.close()

    def test_minimal_wrapped_backup_remains_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "tasks.db")
            try:
                source = Path(folder) / "backup.json"
                source.write_text(json.dumps({"data": {"tasks": [{"id": "old-task", "title": "历史任务"}], "goals": []}}), encoding="utf-8")
                db.import_json(source)
                self.assertEqual(db.get_task("old-task")["title"], "历史任务")
                self.assertEqual(db.get_task("old-task")["subtasks"], [])
            finally:
                db.close()

    def test_import_rejects_unknown_source_and_newer_versions(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "tasks.db")
            try:
                task_id = db.create_task("原任务", planned_date="2026-10-02")
                before = db.backup_payload()
                for label, payload in (
                    ("newer version", {**before, "version": 2}),
                    ("string version", {**before, "version": "1"}),
                    ("other app", {**before, "app": "not-piggyplan"}),
                ):
                    with self.subTest(label=label):
                        source = Path(folder) / "rejected.json"
                        source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                        with self.assertRaises(ValueError):
                            db.import_json(source)
                        self.assertIsNotNone(db.get_task(task_id))
            finally:
                db.close()


class InterfaceWorkflowTests(unittest.TestCase):
    def setUp(self):
        prepare()
        self.folder = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.folder.name) / "tasks.db")
        self.integration_patch = patch("piggyplan.app.WindowsIntegration", InactiveIntegration)
        self.backup_patch = patch.object(PiggyPlanApp, "create_daily_backup", lambda app: None)
        self.integration_patch.start()
        self.backup_patch.start()
        self.app = PiggyPlanApp(database=self.db)
        self.app.withdraw()
        self.app.show_toast = lambda *args, **kwargs: None
        self.app.navigate("all")

    def tearDown(self):
        if self.app.winfo_exists():
            self.app._exiting = True
            self.app.on_close()
        self.integration_patch.stop()
        self.backup_patch.stop()
        self.folder.cleanup()

    def dialog(self):
        return next(child for child in self.app.winfo_children()
                    if isinstance(child, tk.Toplevel))

    def task_texts(self, dialog):
        return [widget for widget in descendants(dialog) if isinstance(widget, tk.Text)]

    def test_more_options_keep_entered_details_after_collapsing_and_saving(self):
        self.app.open_new_task()
        dialog = self.dialog()
        self.assertIn("更多选项", [button_text(widget) for widget in descendants(dialog)])
        click_button(dialog, "更多选项")
        note, steps = self.task_texts(dialog)
        note.insert("1.0", "补充说明")
        steps.insert("1.0", "阅读资料\n整理笔记")
        title = next(widget for widget in descendants(dialog) if isinstance(widget, ttk.Entry))
        title.insert(0, "精简表单待办")
        category = next(widget for widget in descendants(dialog)
                        if isinstance(widget, ttk.Combobox) and "学习" in widget.cget("values"))
        category.set("学习")
        priority = next(widget for widget in descendants(dialog)
                        if isinstance(widget, ttk.Combobox) and "高" in widget.cget("values"))
        priority.set("高")
        click_button(dialog, "收起选项")
        click_button(dialog, "更多选项")
        self.assertEqual(note.get("1.0", "end-1c"), "补充说明")
        click_button(dialog, "收起选项")
        click_button(dialog, "保存待办")
        saved = next(task for task in self.db.list_tasks() if task["title"] == "精简表单待办")
        self.assertEqual(saved["note"], "补充说明")
        self.assertEqual(saved["category"], "life")
        self.assertEqual(saved["priority"], "high")
        self.assertEqual([step["title"] for step in saved["subtasks"]], ["阅读资料", "整理笔记"])

    def test_editing_core_fields_preserves_collapsed_optional_details(self):
        task_id = self.db.create_task("原待办", note="原备注", priority="high",
                                      tags=["课程"], subtasks=["已完成步骤", "下一步"])
        self.db.update_subtask(self.db.get_task(task_id)["subtasks"][0]["id"], completed=True)
        self.app.open_task_dialog(task_id)
        dialog = self.dialog()
        self.assertIn("更多选项", [button_text(widget) for widget in descendants(dialog)])
        title = next(widget for widget in descendants(dialog) if isinstance(widget, ttk.Entry))
        title.delete(0, tk.END)
        title.insert(0, "修改后的待办")
        click_button(dialog, "保存待办")
        saved = self.db.get_task(task_id)
        self.assertEqual(saved["title"], "修改后的待办")
        self.assertEqual(saved["note"], "原备注")
        self.assertEqual(saved["priority"], "high")
        self.assertEqual(saved["tags"], ["课程"])
        self.assertEqual([(step["title"], bool(step["completed"])) for step in saved["subtasks"]],
                         [("已完成步骤", True), ("下一步", False)])

    def test_keyboard_expansion_tabs_into_optional_details(self):
        self.app.deiconify()
        self.app.open_new_task()
        dialog = self.dialog()
        dialog.update()
        more = next(widget for widget in descendants(dialog)
                    if button_text(widget) == "更多选项" and hasattr(widget, "invoke"))
        more.focus_force()
        more.event_generate("<Return>")
        dialog.update()
        note = self.task_texts(dialog)[0]
        self.assertTrue(note.winfo_viewable())
        self.assertEqual(more.tk_focusNext(), note)

    def test_high_priority_goal_detail_opens(self):
        goal_id = self.db.create_goal("重要目标", priority="high")
        try:
            self.app.open_goal_detail(goal_id)
        except NameError as error:
            self.fail(f"Opening a high-priority goal crashed: {error}")
        self.assertIn("重要目标", [button_text(widget) for widget in descendants(self.app.center)])

    def test_goal_board_keeps_own_tasks_after_all_page_filtering(self):
        goal_id = self.db.create_goal("生活目标", category="life")
        self.db.create_task("目标内待办", goal_id=goal_id, category="life", tags=["健康"])
        done = self.db.create_task("目标内完成", goal_id=goal_id, category="life", tags=["健康"])
        self.db.toggle_task(done)
        outsider = self.db.create_task("目标外完成", category="work")
        self.db.toggle_task(outsider)
        self.app.filter_values.update(category="work", priority="high", tag="其他", goal="standalone")
        self.app.goal_mode = "board"
        self.app.open_goal_detail(goal_id)
        texts = [button_text(widget) for widget in descendants(self.app.center)]
        self.assertIn("目标内待办", texts)
        self.assertIn("目标内完成", texts)
        self.assertNotIn("目标外完成", texts)

    def test_restoring_legacy_backup_keeps_data_and_migrates_theme(self):
        task_id = self.db.create_task("备份待办")
        self.db.set_setting("theme", "mint")
        source = Path(self.folder.name) / "legacy.json"
        self.db.export_json(source)
        self.db.clear_all()
        with patch("piggyplan.app.filedialog.askopenfilename", return_value=str(source)), \
             patch("piggyplan.app.messagebox.askyesno", return_value=True), \
             patch("piggyplan.app.messagebox.showerror") as show_error:
            self.app.import_json()
        self.assertIsNotNone(self.db.get_task(task_id))
        self.assertEqual(self.db.settings()["theme"], "pink")
        self.assertEqual(self.app.theme_key, "pink")
        show_error.assert_not_called()
        self.assertTrue(list((Path(self.folder.name) / "backups").glob("before-import-*.db")))

    def test_refresh_error_after_restore_reports_that_data_is_restored(self):
        task_id = self.db.create_task("已恢复待办")
        source = Path(self.folder.name) / "backup.json"
        self.db.export_json(source)
        self.db.clear_all()
        with patch("piggyplan.app.filedialog.askopenfilename", return_value=str(source)), \
             patch("piggyplan.app.messagebox.askyesno", return_value=True), \
             patch("piggyplan.app.log_event"), \
             patch.object(self.app, "render", side_effect=RuntimeError("refresh failed")), \
             patch("piggyplan.app.messagebox.showerror") as show_error:
            self.app.import_json()
        self.assertIsNotNone(self.db.get_task(task_id))
        self.assertIn("数据已恢复", show_error.call_args.args[1])
        self.assertNotIn("未被覆盖", show_error.call_args.args[1])

    def test_goal_search_result_opens_detail(self):
        goal_id = self.db.create_goal("匹配目标")
        self.app.search_var.set("匹配")
        self.app.render()
        self.app.open_goal_detail(goal_id)
        self.assertEqual(self.app.search_var.get(), "")
        self.assertIn("匹配目标", [button_text(widget) for widget in descendants(self.app.center)])

    def test_search_from_goal_detail_creates_a_standalone_task(self):
        goal_id = self.db.create_goal("旧目标")
        self.app.open_goal_detail(goal_id)
        self.app.search_var.set("查找")
        self.app.render()
        self.assertEqual(self.app.header_title.cget("text"), "搜索")
        self.app.new_button.invoke()
        dialog = self.dialog()
        next(widget for widget in descendants(dialog) if isinstance(widget, ttk.Entry)).insert(0, "查找中新建")
        click_button(dialog, "保存待办")
        task = next(task for task in self.db.list_tasks() if task["title"] == "查找中新建")
        self.assertIsNone(task["goal_id"])
        self.app.search_var.set("")
        self.app.render()
        self.assertEqual(self.app.selected_goal_id, goal_id)
        self.assertEqual(self.app.header_title.cget("text"), "目标详情")

    def test_cancel_discards_substep_completion_edits(self):
        task_id = self.db.create_task("步骤任务", subtasks=["第一步"])
        self.app.open_task_dialog(task_id)
        dialog = self.dialog()
        checkbox = next(widget for widget in descendants(dialog) if isinstance(widget, tk.Checkbutton))
        checkbox.invoke()
        click_button(dialog, "取消")
        self.assertFalse(self.db.get_task(task_id)["subtasks"][0]["completed"])

    def test_save_commits_substep_completion_edits(self):
        task_id = self.db.create_task("步骤任务", subtasks=["第一步"])
        self.app.open_task_dialog(task_id)
        dialog = self.dialog()
        next(widget for widget in descendants(dialog) if isinstance(widget, tk.Checkbutton)).invoke()
        self.assertFalse(self.db.get_task(task_id)["subtasks"][0]["completed"])
        click_button(dialog, "保存待办")
        self.assertTrue(self.db.get_task(task_id)["subtasks"][0]["completed"])

    def test_reordering_substeps_preserves_completion(self):
        task_id = self.db.create_task("步骤任务", subtasks=["第一步", "第二步"])
        self.db.update_subtask(self.db.get_task(task_id)["subtasks"][0]["id"], completed=True)
        self.app.open_task_dialog(task_id)
        dialog = self.dialog()
        steps = self.task_texts(dialog)[-1]
        steps.delete("1.0", tk.END)
        steps.insert("1.0", "第二步\n第一步")
        click_button(dialog, "保存待办")
        self.assertEqual([(step["title"], bool(step["completed"])) for step in self.db.get_task(task_id)["subtasks"]],
                         [("第二步", False), ("第一步", True)])

    def test_renaming_substep_preserves_completion(self):
        task_id = self.db.create_task("步骤任务", subtasks=["第一步", "第二步"])
        self.db.update_subtask(self.db.get_task(task_id)["subtasks"][0]["id"], completed=True)
        self.app.open_task_dialog(task_id)
        dialog = self.dialog()
        steps = self.task_texts(dialog)[-1]
        steps.delete("1.0", tk.END)
        steps.insert("1.0", "第一步的补充说明\n第二步")
        click_button(dialog, "保存待办")
        self.assertTrue(self.db.get_task(task_id)["subtasks"][0]["completed"])

    def test_inserting_substep_preserves_existing_completion(self):
        task_id = self.db.create_task("步骤任务", subtasks=["第一步", "第二步"])
        self.db.update_subtask(self.db.get_task(task_id)["subtasks"][1]["id"], completed=True)
        self.app.open_task_dialog(task_id)
        dialog = self.dialog()
        steps = self.task_texts(dialog)[-1]
        steps.insert("1.0", "新增步骤\n")
        click_button(dialog, "保存待办")
        self.assertEqual([bool(step["completed"]) for step in self.db.get_task(task_id)["subtasks"]],
                         [False, False, True])

    def test_more_than_six_substeps_can_be_completed(self):
        task_id = self.db.create_task("长清单", subtasks=[f"步骤 {index}" for index in range(8)])
        self.app.open_task_dialog(task_id)
        checkboxes = [widget for widget in descendants(self.dialog()) if isinstance(widget, tk.Checkbutton)]
        self.assertEqual(len(checkboxes), 8)

    def test_saving_other_fields_keeps_separate_tags(self):
        task_id = self.db.create_task("带标签", tags=["工作", "复盘"])
        self.app.open_task_dialog(task_id)
        click_button(self.dialog(), "保存待办")
        self.assertEqual(self.db.get_task(task_id)["tags"], ["复盘", "工作"])

    def test_duplicate_goal_titles_are_individually_selectable(self):
        goal_ids = {self.db.create_goal("同名目标", category="work"),
                    self.db.create_goal("同名目标", category="life")}
        attached = set()
        for index in range(2):
            self.app.open_new_task()
            dialog = self.dialog()
            combos = [widget for widget in descendants(dialog) if isinstance(widget, ttk.Combobox)]
            goals = next(combo for combo in combos if "独立待办" in combo.cget("values"))
            choices = [value for value in goals.cget("values") if value != "独立待办"]
            self.assertEqual(len(choices), 2)
            goals.set(choices[index])
            next(widget for widget in descendants(dialog) if isinstance(widget, ttk.Entry)).insert(0, f"新任务 {index}")
            click_button(dialog, "保存待办")
            attached.add(next(task for task in self.db.list_tasks() if task["title"] == f"新任务 {index}")["goal_id"])
        self.assertEqual(attached, goal_ids)

    def test_batch_can_choose_each_duplicate_goal_title(self):
        goal_ids = {self.db.create_goal("同名目标", category="work"),
                    self.db.create_goal("同名目标", category="life")}
        task_id = self.db.create_task("批量任务")
        attached = set()
        for index in range(2):
            self.app.selected_task_ids.add(task_id)
            self.app.batch_attach_goal()
            dialog = self.dialog()
            goals = next(widget for widget in descendants(dialog) if isinstance(widget, ttk.Combobox))
            choices = list(goals.cget("values"))
            self.assertEqual(len(choices), 2)
            goals.set(choices[index])
            click_button(dialog, "确认挂载")
            attached.add(self.db.get_task(task_id)["goal_id"])
        self.assertEqual(attached, goal_ids)

    def test_batch_date_rejects_invalid_input_then_updates_and_can_undo(self):
        task_id = self.db.create_task("改期待办", planned_date="2026-10-01")
        self.app.selected_task_ids.add(task_id)
        self.app.batch_set_date()
        dialog = self.dialog()
        entry = next(widget for widget in descendants(dialog) if isinstance(widget, ttk.Entry))
        entry.insert(0, "2026-02-30")
        click_button(dialog, "确认修改")
        self.assertEqual(self.db.get_task(task_id)["planned_date"], "2026-10-01")
        self.assertTrue(dialog.winfo_exists())
        entry.delete(0, tk.END)
        entry.insert(0, "2026-10-03")
        click_button(dialog, "确认修改")
        self.assertEqual(self.db.get_task(task_id)["planned_date"], "2026-10-03")
        self.assertFalse(self.app.selected_task_ids)
        self.app._undo_batch_dates([(task_id, "2026-10-01")])
        self.assertEqual(self.db.get_task(task_id)["planned_date"], "2026-10-01")

    def test_batch_date_rejects_invalid_input_then_updates_and_can_undo(self):
        task_id = self.db.create_task("改期待办", planned_date="2026-10-01")
        self.app.selected_task_ids.add(task_id)
        self.app.batch_set_date()
        dialog = self.dialog()
        entry = next(widget for widget in descendants(dialog) if isinstance(widget, ttk.Entry))
        entry.insert(0, "2026-02-30")
        click_button(dialog, "确认修改")
        self.assertEqual(self.db.get_task(task_id)["planned_date"], "2026-10-01")
        self.assertTrue(dialog.winfo_exists())
        entry.delete(0, tk.END)
        entry.insert(0, "2026-10-03")
        click_button(dialog, "确认修改")
        self.assertEqual(self.db.get_task(task_id)["planned_date"], "2026-10-03")
        self.assertFalse(self.app.selected_task_ids)
        self.app._undo_batch_dates([(task_id, "2026-10-01")])
        self.assertEqual(self.db.get_task(task_id)["planned_date"], "2026-10-01")

    def test_archived_goal_search_filters_results(self):
        first = self.db.create_goal("苹果项目")
        second = self.db.create_goal("香蕉项目")
        self.db.achieve_goal(first)
        self.db.achieve_goal(second)
        self.app.archive_tab = "goals"
        self.app.archive_query = "苹果"
        self.app.navigate("archive")
        titles = [button_text(widget) for widget in descendants(self.app.center)]
        self.assertIn("苹果项目", titles)
        self.assertNotIn("香蕉项目", titles)

    def test_removed_tag_filter_applies_the_displayed_all_tags_choice(self):
        self.db.create_task("旧待办", tags=["旧标签"])
        self.app.filter_values["tag"] = "旧标签"
        self.db.clear_all()
        self.db.create_task("改标签待办")
        self.app.open_filter_dialog()
        dialog = self.dialog()
        combo = [widget for widget in descendants(dialog) if isinstance(widget, ttk.Combobox)][-1]
        self.assertEqual(combo.get(), "全部标签")
        click_button(dialog, "应用筛选")
        self.assertEqual(self.app.filter_values["tag"], "all")
        self.assertIn("改标签待办", [button_text(widget) for widget in descendants(self.app.center)])

    def test_archive_typing_keeps_the_same_entry_and_cursor(self):
        self.app.navigate("archive")
        entry = next(widget for widget in descendants(self.app.center) if isinstance(widget, ttk.Entry))
        entry.insert(0, "连续输入")
        entry.icursor(2)
        deadline = time.monotonic() + 0.3
        while time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        self.assertTrue(entry.winfo_exists(), "Typing rebuilt and destroyed the active search field")
        self.assertEqual(entry.get(), "连续输入")
        self.assertEqual(entry.index(tk.INSERT), 2)


if __name__ == "__main__":
    unittest.main()
