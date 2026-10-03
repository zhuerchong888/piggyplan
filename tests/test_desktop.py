"""Desktop interactions exercised against a disposable local database."""
from pathlib import Path
import tempfile
import unittest
import time
from piggyplan.util import today_key, offset_date

import piggyplan_desktop
import tkinter as tk
from piggyplan.database import Database


class DesktopTests(unittest.TestCase):
    def setUp(self):
        from piggyplan.runtime.tcl import prepare
        prepare()
        self.temp = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp.name) / 'tasks.db', seed=False)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.database.close)
        self.database.set_setting('theme', 'peach')
        self.database.set_setting('startup_page', 'all')
        for index in range(28):
            self.database.create_task(f'待办 {index}', category='life' if index == 0 else 'work')
        self.app = piggyplan_desktop.PiggyPlanApp(database=self.database)
        self.app.withdraw()
        self.app.update()

    def tearDown(self):
        self.app._exiting = True
        self.app.on_close()
        self.temp.cleanup()

    def test_legacy_theme_is_migrated_to_pink(self):
        self.assertEqual(self.app.theme_key, 'pink')
        self.assertEqual(self.database.settings()['theme'], 'pink')

    def test_task_update_keeps_scroll_position(self):
        self.app.canvas.yview_moveto(0.5)
        self.app.update()
        before = self.app.canvas.yview()[0]
        self.app.render()
        self.app.update()
        self.assertGreater(before, 0.1)
        self.assertAlmostEqual(self.app.canvas.yview()[0], before, delta=0.04)

    def test_mouse_wheel_scrolls_task_content(self):
        self.app.canvas.yview_moveto(0)
        self.app.canvas.event_generate('<MouseWheel>', delta=-120)
        self.app.update()
        self.assertGreater(self.app.canvas.yview()[0], 0)

    def test_hidden_selection_is_cleared_after_filtering(self):
        task = self.database.list_tasks(category='life')[0]
        self.app.selected_task_ids.add(task['id'])
        self.app.filter_values['category'] = 'work'
        self.app.render()
        self.assertNotIn(task['id'], self.app.selected_task_ids)

    def test_today_count_excludes_future_and_unscheduled_tasks(self):
        tasks = self.database.list_tasks()
        self.database.update_task(tasks[0]['id'], {'planned_date': today_key()})
        self.database.update_task(tasks[1]['id'], {'planned_date': offset_date(-1)})
        self.database.update_task(tasks[2]['id'], {'planned_date': offset_date(1)})
        self.app.render()
        self.assertEqual(self.app.nav_buttons['today']._count_label.cget('text'), '2')

    def test_goal_board_stacks_columns_after_resizing_narrow(self):
        goal_id = self.database.create_goal('响应式目标')
        self.database.create_task('目标内待办', goal_id=goal_id)
        completed_id = self.database.create_task('目标内完成', goal_id=goal_id)
        self.database.toggle_task(completed_id)
        self.app.attributes('-alpha', 0)
        self.app.geometry('1320x820')
        self.app.deiconify()
        self.app.update()
        self.app.goal_mode = 'board'
        self.app.open_goal_detail(goal_id)
        self.app.update()

        def headings():
            def visit(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from visit(child)
            return {widget.cget('text'): widget for widget in visit(self.app.center)
                    if isinstance(widget, tk.Label) and widget.cget('text') in ('待办', '已完成')}

        labels = headings()
        self.assertEqual(labels['待办'].winfo_rooty(), labels['已完成'].winfo_rooty())
        self.app.geometry('860x680')
        deadline = time.monotonic() + 0.3
        while time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        labels = headings()
        self.assertGreater(labels['已完成'].winfo_rooty(), labels['待办'].winfo_rooty())
        self.assertEqual(labels['已完成'].winfo_rootx(), labels['待办'].winfo_rootx())


if __name__ == '__main__':
    unittest.main()
