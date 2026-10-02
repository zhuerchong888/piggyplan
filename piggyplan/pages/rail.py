"""Contextual progress beside the continuous daily list."""
from __future__ import annotations
import tkinter as tk
from ..util import date_text, end_of_week, start_of_week, today_key


class RailMixin:
    def render_rail(self, parent: tk.Misc) -> None:
        self.clear(parent)
        c = self.colors
        bg = parent.cget("bg")
        parent.grid_columnconfigure(1, weight=1)
        tk.Frame(parent, bg=c["line"], width=1).grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 22))
        goals = tk.Frame(parent, bg=bg)
        goals.grid(row=0, column=1, sticky="new", pady=(0, 28))
        self._label(goals, "正在推进", 11, c["text"], True, bg=bg).pack(anchor="w", pady=(0, 17))
        active = self.db.list_goals(status="active")[:3]
        for goal in active:
            item = tk.Frame(goals, bg=bg, cursor="hand2")
            item.pack(fill="x", pady=(0, 20))
            title = self._label(item, goal["title"], 10, c["text"], bg=bg, anchor="w", justify="left", width=1)
            title.pack(fill="x")
            title.bind("<Configure>", lambda e, label=title: label.configure(wraplength=max(100, e.width)))
            track = tk.Frame(item, bg=c["line"], height=3)
            track.pack(fill="x", pady=(10, 7))
            tk.Frame(track, bg=c["accentDeep"], height=3).place(relwidth=goal["progress"] / 100, relheight=1)
            self._label(item, f"{goal['completed']}/{goal['total']} 待办完成    {goal['progress']}%", 9, c["text_soft"], bg=bg).pack(anchor="w")
            self._bind_click_recursive(item, lambda gid=goal["id"]: self.open_goal_detail(gid))
        if not active:
            self._label(goals, "还没有进行中的目标", 10, c["text_soft"], bg=bg).pack(anchor="w")
        self._button(goals, "查看长期目标", lambda: self.navigate("goals"), "link").pack(anchor="w")
        stats = self.db.weekly_stats()
        week = tk.Frame(parent, bg=bg)
        week.grid(row=1, column=1, sticky="new")
        self._label(week, "本周", 11, c["text"], True, bg=bg).pack(anchor="w")
        self._label(week, f"{date_text(start_of_week().isoformat())} — {date_text(end_of_week().isoformat())}", 9, c["text_soft"], bg=bg).pack(anchor="w", pady=(7, 19))
        for title, value in (("实际完成", stats["actual"]), ("有效计划", stats["total"]), ("按计划完成", f"{stats['rate']}%")):
            line = tk.Frame(week, bg=bg)
            line.pack(fill="x", pady=(0, 13))
            self._label(line, title, 9, c["text_soft"], bg=bg).pack(side="left")
            self._label(line, str(value), 11, c["text"], bg=bg).pack(side="right")
        chart = tk.Frame(week, bg=bg, height=74)
        chart.pack(fill="x", pady=(6, 0))
        chart.pack_propagate(False)
        maximum = max(1, max(day["actual"] for day in stats["days"]))
        for index, day in enumerate(stats["days"]):
            column = tk.Frame(chart, bg=bg)
            column.place(relx=index / 7, rely=0, relwidth=1 / 7, relheight=1)
            tk.Frame(column, bg=c["accentDeep"] if day["date"] == today_key() else c["accent"], width=10).place(relx=0.5, rely=0.72, anchor="s", relheight=max(0.025, day["actual"] / maximum * 0.65), relwidth=0.25)
            self._label(column, "今" if day["date"] == today_key() else day["date"][8:], 9, c["text_soft"], bg=bg).place(relx=0.5, rely=1, y=-1, anchor="s")
