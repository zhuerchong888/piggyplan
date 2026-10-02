"""概览侧栏：本周执行统计与长期目标进度。"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from ..util import date_text, end_of_week, start_of_week, today_key


class RailMixin:
    def render_rail(self, parent: tk.Misc) -> None:
        for child in parent.winfo_children():
            child.destroy()
        colors = self.colors
        goals_card = tk.Frame(parent, bg=self.colors["surface"], highlightthickness=0)
        goals_card.pack(fill="x", pady=(0, 14))
        self._label(goals_card, "🐾  长期目标", 10, self.colors["text"], True, bg=self.colors["surface"]).pack(anchor="w", padx=15, pady=(15, 12))
        active = self.db.list_goals(status="active")[:3]
        if active:
            for goal in active:
                item = tk.Frame(goals_card, bg=self.colors["surface"], cursor="hand2")
                item.pack(fill="x", padx=15, pady=(0, 13))
                top = tk.Frame(item, bg=self.colors["surface"])
                top.pack(fill="x")
                self._label(top, goal["title"], 9, self.colors["text"], True, bg=self.colors["surface"], anchor="w").pack(side="left", fill="x", expand=True)
                self._label(top, f"{goal['progress']}%", 9, colors["strong"], True, bg=self.colors["surface"]).pack(side="right")
                track = tk.Frame(item, bg=self.colors["surface_soft"], height=6)
                track.pack(fill="x", pady=(6, 0))
                tk.Frame(track, bg=colors["accent"], height=6).place(relwidth=max(0, min(1, goal["progress"] / 100)), relheight=1)
                self._label(item, f"{goal['completed']}/{goal['total']} 个待办 · {'高优先' if goal['priority'] == 'high' else '稳步推进'}", 8, self.colors["text_faint"], False, bg=self.colors["surface"]).pack(anchor="w", pady=(5, 0))
                self._bind_click_recursive(item, lambda gid=goal["id"]: self.open_goal_detail(gid))
        else:
            self._label(goals_card, "还没有进行中的目标。", 8, self.colors["text_soft"], False, bg=self.colors["surface"]).pack(anchor="w", padx=15, pady=(0, 7))
            self._button(goals_card, "设定一个长期目标 →", self.open_new_goal, "link").pack(anchor="w", padx=15, pady=(0, 13))
        self._button(goals_card, "查看全部目标 →", lambda: self.navigate("goals"), "link").pack(anchor="w", padx=15, pady=(0, 14))
        stats = self.db.weekly_stats()
        stat_card = tk.Frame(parent, bg=self.colors["surface"], highlightthickness=0)
        stat_card.pack(fill="x")
        self._label(stat_card, "📊  本周执行", 10, self.colors["text"], True, bg=self.colors["surface"]).pack(anchor="w", padx=15, pady=(15, 3))
        self._label(stat_card, f"{date_text(start_of_week().isoformat())} – {date_text(end_of_week().isoformat())}", 8, self.colors["text_faint"], False, bg=self.colors["surface"]).pack(anchor="w", padx=15, pady=(0, 13))
        for title, value in (("实际完成", stats["actual"]), ("有效计划", stats["total"]), ("计划完成率", f"{stats['rate']}%")):
            line = tk.Frame(stat_card, bg=self.colors["surface"])
            line.pack(fill="x", padx=15, pady=(0, 10))
            self._label(line, title, 8, self.colors["text_soft"], False, bg=self.colors["surface"]).pack(side="left")
            self._label(line, str(value), 15 if title == "计划完成率" else 13, colors["strong"] if title == "计划完成率" else self.colors["text"], True, bg=self.colors["surface"]).pack(side="right")
        chart = tk.Frame(stat_card, bg=self.colors["surface"], height=76)
        chart.pack(fill="x", padx=15, pady=(4, 15))
        chart.pack_propagate(False)
        max_actual = max(1, max(item["actual"] for item in stats["days"]))
        for index, item in enumerate(stats["days"]):
            col = tk.Frame(chart, bg=self.colors["surface"])
            col.place(relx=index / 7, rely=0, relwidth=1 / 7, relheight=1)
            bar = tk.Frame(col, bg=colors["strong"] if item["date"] == today_key() else colors["accent"], width=16)
            bar.place(relx=0.5, rely=0.78, anchor="s", relheight=max(0.05, item["actual"] / max_actual * 0.65), relwidth=0.38)
            self._label(col, "今" if item["date"] == today_key() else item["date"][5:].replace("-", "/"), 7, self.colors["text_faint"], False, bg=self.colors["surface"]).place(relx=0.5, rely=0.9, anchor="n")
