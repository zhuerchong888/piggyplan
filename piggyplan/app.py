"""PiggyPlanApp 外壳：窗口、侧边栏、头部、路由与设置状态；Mixin 在此组装。

tk.Tk 位于基类链最右，__init__ 里的 super().__init__() 才会命中它。"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import sys
from datetime import date, datetime
from .constants import APP_NAME, APP_VERSION, HOTKEY_DEFAULT
from .tokens import THEME_KEYS, palette, resolve_fonts
from .ui.mascot import PigMark
from .ui.shape import round_rect
from .ui.widgets import Card, PillButton
from .database import Database
from .runtime.paths import app_backup_dir, app_data_dir, app_log_dir, log_event
from .runtime.windows_integration import WindowsIntegration
from .util import date_text, display_hotkey, normalize_hotkey, set_windows_autostart, today_key, today_text

from .dialogs.filter import FilterDialogMixin
from .dialogs.goal import GoalDialogMixin
from .dialogs.goal_decision import GoalDecisionMixin
from .dialogs.quick_add import QuickAddMixin
from .dialogs.task import TaskDialogMixin
from .features.batch import BatchMixin
from .features.tasks import TaskActionsMixin
from .pages.all import AllMixin
from .pages.archive import ArchiveMixin
from .pages.goals import GoalsMixin
from .pages.rail import RailMixin
from .pages.search import SearchMixin
from .pages.settings import SettingsMixin
from .pages.today import TodayMixin
from .pages.upcoming import UpcomingMixin
from .ui.menu import MenuMixin
from .ui.primitives import PrimitivesMixin
from .ui.toast import ToastMixin


class PiggyPlanApp(
    SettingsMixin, ArchiveMixin, GoalsMixin, AllMixin, UpcomingMixin, TodayMixin,
    SearchMixin, RailMixin,
    TaskDialogMixin, GoalDialogMixin, FilterDialogMixin, QuickAddMixin, GoalDecisionMixin,
    BatchMixin, TaskActionsMixin,
    MenuMixin, ToastMixin, PrimitivesMixin,
    tk.Tk,
):
    """Native desktop UI.  All writes go through Database."""

    def __init__(self, database: Database | None = None, start_minimized: bool = False):
        super().__init__()
        self.db = database or Database(app_data_dir() / "piggyplan.db")
        self.settings = self.db.settings()
        defaults = {
            "theme": "pink",
            "default_category": "work",
            "startup_page": "today",
            "close_to_tray": "1",
            "startup_enabled": "0",
            "startup_minimized": "0",
            "global_hotkey": HOTKEY_DEFAULT,
            "reduce_motion": "0",
        }
        for key, value in defaults.items():
            if key not in self.settings:
                self.db.set_setting(key, value)
                self.settings[key] = value
        self.theme_key = self.settings.get("theme", "pink") if self.settings.get("theme", "pink") in THEME_KEYS else THEME_KEYS[0]
        startup_page = self.settings.get("startup_page", self.settings.get("last_view", "today"))
        self.view = startup_page if startup_page in {"today", "upcoming", "all", "goals", "archive", "settings"} else "today"
        self.selected_goal_id: str | None = None
        self.completed_open = False
        self.all_mode = "list"
        self.goal_mode = "list"
        self.archive_tab = "tasks"
        self.selected_task_ids: set[str] = set()
        self.filter_values = {"category": "all", "priority": "all", "goal": "all", "status": "todo", "tag": "all"}
        self.archive_query = ""
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._search_changed)
        self._search_after: str | None = None
        self.toast: tk.Toplevel | None = None
        self.toast_undo_callback = None
        self.tray_menu: tk.Menu | None = None
        self._exiting = False
        self._compact_window = False
        self._resize_after: str | None = None
        self._natural_day = today_key()
        self._drag_task_id: str | None = None
        self._drag_widget: tk.Widget | None = None
        self._drag_start_y = 0
        self.start_minimized = start_minimized or self.settings.get("startup_minimized") == "1"
        self.configure(bg=self.colors["bg"])
        self.title(APP_NAME)
        self.minsize(860, 600)
        geometry = self.settings.get("geometry", "1160x760")
        try:
            self.geometry(geometry)
        except tk.TclError:
            self.geometry("1160x760")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Configure>", self._window_resized)
        self._configure_styles()
        self._build_shell()
        self._bind_shortcuts()
        self.integration = WindowsIntegration(self)
        self.create_daily_backup()
        self.render()
        self.after(60_000, self._check_natural_day)
        if self.start_minimized and self.integration.tray_available:
            self.after(10, self.withdraw)

    @property
    def colors(self) -> dict[str, str]:
        """按当前主题返回展平的 token 色表；结果按主题缓存（调用方只读）。"""
        if not hasattr(self, "_colors_cache"):
            self._colors_cache: dict[str, dict[str, str]] = {}
        cached = self._colors_cache.get(self.theme_key)
        if cached is None:
            cached = palette(self.theme_key)
            self._colors_cache[self.theme_key] = cached
        return cached

    def font(self, role: str):
        """按角色返回 (family, size, weight)；字族在首次调用时解析一次。"""
        if not hasattr(self, "_fonts"):
            self._fonts = resolve_fonts(self)
        return self._fonts[role]

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        colors = self.colors
        style.configure("TEntry", padding=(11, 9), fieldbackground=colors["soft"], background=colors["soft"], foreground=colors["text"], bordercolor=colors["soft"], lightcolor=colors["soft"], darkcolor=colors["soft"], font=self.font("body"))
        style.map("TEntry", bordercolor=[("focus", colors["strong"])], lightcolor=[("focus", colors["strong"])], darkcolor=[("focus", colors["strong"])])
        style.configure("TCombobox", padding=(10, 8), fieldbackground=colors["soft"], background=colors["soft"], foreground=colors["text"], bordercolor=colors["soft"], lightcolor=colors["soft"], darkcolor=colors["soft"], arrowcolor=colors["strong"], font=self.font("body"))
        style.map("TCombobox", bordercolor=[("focus", colors["strong"])], lightcolor=[("focus", colors["strong"])], darkcolor=[("focus", colors["strong"])])
        style.configure("Vertical.TScrollbar", troughcolor=colors["bg"], background=colors["line"], arrowcolor=colors["text_soft"], bordercolor=colors["bg"], lightcolor=colors["bg"], darkcolor=colors["bg"])

    def _build_shell(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.sidebar = tk.Frame(self, width=248, bg=self.colors["soft_surface"], highlightthickness=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.main = tk.Frame(self, bg=self.colors["bg"])
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)
        self.header = tk.Frame(self.main, bg=self.colors["bg"], height=76)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(2, weight=1)
        self.body = tk.Frame(self.main, bg=self.colors["bg"])
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self.body, bg=self.colors["bg"], highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self.body, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.page = tk.Frame(self.canvas, bg=self.colors["bg"])
        self.page_window = self.canvas.create_window((0, 0), window=self.page, anchor="nw")
        self.page.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.page_window, width=event.width))
        self.page.grid_columnconfigure(0, weight=1)
        self.page.grid_columnconfigure(1, minsize=266)
        self.center = tk.Frame(self.page, bg=self.colors["bg"])
        self.center.grid(row=0, column=0, sticky="nsew", padx=(34, 22), pady=(30, 40))
        self.rail = tk.Frame(self.page, bg=self.colors["bg"], width=266)
        self.rail.grid(row=0, column=1, sticky="nsew", padx=(0, 34), pady=(30, 40))
        self._build_header()
        self._build_sidebar()

    def _build_header(self) -> None:
        self.header.grid_columnconfigure(0, weight=0)
        self.header.grid_columnconfigure(1, weight=0)
        self.header.grid_columnconfigure(2, weight=1)
        self.header.grid_columnconfigure(3, weight=0)
        self.header_title = tk.Label(self.header, text="今天", bg=self.colors["bg"], fg=self.colors["text"], font=self.font("display"))
        self.header_title.grid(row=0, column=0, sticky="w", padx=(34, 10), pady=(22, 0))
        self.header_caption = tk.Label(self.header, text=today_text(), bg=self.colors["bg"], fg=self.colors["text_soft"], font=self.font("body"))
        self.header_caption.grid(row=1, column=0, sticky="w", padx=(34, 10), pady=(2, 18))
        search_wrap = tk.Frame(self.header, bg=self.colors["bg"])
        search_wrap.grid(row=0, column=2, rowspan=2, sticky="ew", padx=26, pady=23)
        search_wrap.grid_columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(search_wrap, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky="ew", ipady=3)
        self.search_entry.insert(0, "")
        self.search_entry.configure(width=32)
        self.new_button = PillButton(self.header, app=self, text="+  新建待办", command=self.open_new_task, kind="primary", size="md")
        self.new_button.grid(row=0, column=3, rowspan=2, padx=(0, 34), pady=23, sticky="e")

    def _build_sidebar(self) -> None:
        self.sidebar.grid_rowconfigure(10, weight=1)
        brand = tk.Frame(self.sidebar, bg=self.colors["soft_surface"])
        brand.grid(row=0, column=0, sticky="ew", padx=20, pady=(26, 22))
        PigMark(brand, app=self, variant="logo").pack(side="left")
        brand_text = tk.Frame(brand, bg=self.colors["soft_surface"])
        brand_text.pack(side="left", padx=10)
        tk.Label(brand_text, text="日常", bg=self.colors["soft_surface"], fg=self.colors["text"], font=self.font("title")).pack(anchor="w")
        tk.Label(brand_text, text="PIGGYPLAN · LOCAL FIRST", bg=self.colors["soft_surface"], fg=self.colors["ink_soft"], font=self.font("micro")).pack(anchor="w", pady=(1, 0))
        self.sidebar_new = PillButton(self.sidebar, app=self, text="+  新建待办", command=self.open_new_task, kind="primary", size="lg")
        self.sidebar_new.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 20))
        self.nav_frame = tk.Frame(self.sidebar, bg=self.colors["soft_surface"])
        self.nav_frame.grid(row=2, column=0, sticky="new", padx=10)
        self.nav_buttons: dict[str, tk.Button] = {}
        self._nav_button("today", "今日清单", 0)
        self._nav_button("upcoming", "之后安排", 1)
        self._nav_button("all", "全部待办", 2, True)
        tk.Frame(self.nav_frame, bg=self.colors["line"], height=1).grid(row=3, column=0, sticky="ew", padx=10, pady=(13, 10))
        self._nav_button("goals", "长期目标", 4, True)
        self._nav_button("archive", "完成归档", 5)
        tk.Frame(self.nav_frame, bg=self.colors["line"], height=1).grid(row=6, column=0, sticky="ew", padx=10, pady=(13, 10))
        self._nav_button("settings", "偏好设置", 7)
        footer = tk.Frame(self.sidebar, bg=self.colors["soft_surface"])
        footer.grid(row=11, column=0, sticky="sew", padx=16, pady=17)
        footer_card = Card(footer, app=self, tone="surface", stroke=True, padding=(14, 12))
        footer_card.pack(fill="x")
        card_bg = footer_card.body.cget("bg")
        tk.Label(footer_card.body, text="你的事都装在这只猪身上", bg=card_bg, fg=self.colors["ink"], font=self.font("body")).pack(anchor="w")
        tk.Label(footer_card.body, text="只写本机，不联网", justify="left", bg=card_bg, fg=self.colors["ink_soft"], font=self.font("meta")).pack(anchor="w", pady=(2, 0))
        tk.Label(footer, text=f"版本 {APP_VERSION}", bg=self.colors["soft_surface"], fg=self.colors["ink_soft"], font=self.font("micro")).pack(anchor="w", pady=(9, 0))

    def _nav_button(self, view: str, text: str, row: int, show_count: bool = False) -> None:
        colors = self.colors
        frame = tk.Frame(self.nav_frame, bg=colors["soft_surface"])
        frame.grid(row=row, column=0, sticky="ew", pady=2)
        frame.grid_columnconfigure(1, weight=1)
        indicator = tk.Canvas(frame, width=4, height=20, bg=colors["soft_surface"], highlightthickness=0, bd=0)
        indicator.grid(row=0, column=0, padx=(2, 9))
        button = tk.Button(frame, text=text, command=lambda v=view: self.navigate(v), anchor="w", relief="flat", bd=0, padx=14, pady=10, font=self.font("body"), cursor="hand2", bg=colors["soft_surface"], fg=colors["text_soft"], activebackground=colors["soft_surface"])
        button.grid(row=0, column=1, sticky="ew")
        if show_count:
            count = tk.Label(frame, text="", width=4, font=self.font("micro"), padx=4, pady=2, bg=colors["soft_surface"])
            count.grid(row=0, column=2, padx=(0, 8))
            button._count_label = count  # type: ignore[attr-defined]
        button._indicator = indicator  # type: ignore[attr-defined]
        self.nav_buttons[view] = button

    def _button(self, parent: tk.Misc, text: str, command, kind: str = "ghost", width: int | None = None) -> tk.Button:
        colors = self.colors
        palettes = {
            "primary": (colors["strong"], "#FFFFFF", colors["accent"]),
            "ghost": (colors["soft_surface"], colors["text_soft"], colors["soft"]),
            "outline": (colors["soft"], colors["strong"], colors["accent"]),
            "danger": ("#FFF0F0", "#C9575B", "#F3D4D4"),
            "link": (colors["bg"], colors["strong"], colors["soft"]),
        }
        bg, fg, active = palettes.get(kind, palettes["ghost"])
        button = tk.Button(parent, text=text, command=command, relief="flat", bd=0, bg=bg, fg=fg, activebackground=active, activeforeground=fg, font=("Microsoft YaHei UI", 9, "bold" if kind in ("primary", "link") else "normal"), cursor="hand2", padx=13, pady=8)
        if width:
            button.configure(width=width)
        return button

    def _label(self, parent: tk.Misc, text: str, size: int = 10, color: str | None = None, bold: bool = False, **kwargs) -> tk.Label:
        if size <= 9:
            # CJK 小字号加粗会糊；层级交给颜色承担（micro 角色的 YaHei 例外仅限组件层）。
            bold = False
            size = max(size, 8)
        family = self.font("meta")[0]
        return tk.Label(parent, text=text, bg=kwargs.pop("bg", self.colors["bg"]), fg=color or self.colors["text"], font=(family, size, "bold" if bold else "normal"), **kwargs)

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-n>", lambda _event: self.open_new_task())
        self.bind_all("<Control-f>", lambda _event: self.focus_search())
        self.bind_all("<Control-Key-1>", lambda _event: self.navigate("today"))
        self.bind_all("<Control-Key-2>", lambda _event: self.navigate("upcoming"))
        self.bind_all("<Control-Key-3>", lambda _event: self.navigate("all"))
        self.bind_all("<Escape>", lambda _event: self.destroy_top_level())

    def _search_changed(self, *_args) -> None:
        if self._search_after:
            self.after_cancel(self._search_after)
        self._search_after = self.after(150, self.render)

    def focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, tk.END)

    def destroy_top_level(self) -> None:
        for child in self.winfo_children():
            if isinstance(child, tk.Toplevel):
                child.destroy()
                return

    def show_main_window(self) -> None:
        self.deiconify()
        try:
            self.state("normal")
        except tk.TclError:
            pass
        self.lift()
        self.focus_force()

    def show_tray_menu(self) -> None:
        if not self.integration.tray_available:
            self.show_main_window()
            return
        if self.tray_menu and self.tray_menu.winfo_exists():
            self.tray_menu.destroy()
        remaining = len(self.db.list_tasks())
        startup_label = "开机自启  ✓" if self.settings.get("startup_enabled") == "1" else "开机自启"
        menu = tk.Menu(self, tearoff=0, bg=self.colors["surface"], fg=self.colors["text"], activebackground=self.colors["soft"], activeforeground=self.colors["text"], bd=0, relief="flat", font=self.font("meta"))
        menu.add_command(label="快速添加待办", command=self.open_quick_add)
        menu.add_command(label="打开主界面", command=self.show_main_window)
        menu.add_command(label=f"今天剩余 {remaining} 项", command=lambda: self.show_main_window() or self.navigate("today"))
        menu.add_separator()
        menu.add_command(label=startup_label, command=lambda: self._save_startup_enabled(self.settings.get("startup_enabled") != "1"))
        menu.add_separator()
        menu.add_command(label="退出", command=self.quit_from_tray)
        self.tray_menu = menu
        x, y = self.integration.cursor_position()
        menu.tk_popup(x, y)
        menu.grab_release()

    def quit_from_tray(self) -> None:
        self._exiting = True
        self.on_close()

    def create_daily_backup(self) -> None:
        """Keep one SQLite snapshot per day and retain the latest 14 snapshots."""

        try:
            folder = app_backup_dir()
            folder.mkdir(parents=True, exist_ok=True)
            destination = folder / f"{date.today().isoformat()}.db"
            if not destination.exists():
                self.db.backup_database(destination)
            snapshots = sorted(folder.glob("*.db"), key=lambda item: item.stat().st_mtime, reverse=True)
            for old in snapshots[14:]:
                old.unlink()
        except Exception as error:
            log_event("daily backup failed", error)

    def export_json(self) -> None:
        path = filedialog.asksaveasfilename(title="导出完整备份", defaultextension=".json", initialfile=f"piggyplan-backup-{date.today().strftime('%Y%m%d')}.json", filetypes=[("JSON 备份", "*.json"), ("所有文件", "*.*")])
        if path:
            try:
                self.db.export_json(path)
                self.show_toast("完整备份已导出")
            except Exception as error:
                log_event("JSON export failed", error)
                messagebox.showerror("导出失败", "完整备份没有成功导出。", parent=self)

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(title="导出历史 CSV", defaultextension=".csv", initialfile=f"piggyplan-history-{date.today().strftime('%Y%m%d')}.csv", filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")])
        if path:
            try:
                self.db.export_csv(path)
                self.show_toast("历史 CSV 已导出")
            except Exception as error:
                log_event("CSV export failed", error)
                messagebox.showerror("导出失败", "历史 CSV 没有成功导出。", parent=self)

    def import_json(self) -> None:
        path = filedialog.askopenfilename(title="从备份恢复", filetypes=[("JSON 备份", "*.json"), ("所有文件", "*.*")])
        if not path:
            return
        if not messagebox.askyesno("覆盖当前数据", "恢复备份会覆盖当前任务、目标、标签和模板。是否继续？", parent=self):
            return
        try:
            before = app_backup_dir() / f"before-import-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            self.db.backup_database(before)
            self.db.import_json(path)
            self.settings = self.db.settings()
            self.theme_key = self.settings.get("theme", "pink") if self.settings.get("theme", "pink") in THEME_KEYS else THEME_KEYS[0]
            self.selected_goal_id = None
            self.selected_task_ids.clear()
            if self.integration.available:
                self.integration.register_hotkey(self.settings.get("global_hotkey", HOTKEY_DEFAULT))
            self.render()
            self.show_toast("备份已恢复")
        except Exception as error:
            log_event("JSON import failed", error)
            messagebox.showerror("恢复失败", "备份文件无效或无法恢复；当前数据未被覆盖。", parent=self)

    def clear_all(self) -> None:
        if not messagebox.askyesno("清空所有数据", "确定清空全部任务、目标、标签和模板吗？这一步可以通过恢复备份找回。", parent=self):
            return
        try:
            before = app_backup_dir() / f"before-clear-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            self.db.backup_database(before)
            self.db.clear_all()
            self.selected_goal_id = None
            self.selected_task_ids.clear()
            self.render()
            self.show_toast("数据已清空，清空前快照已保留")
        except Exception as error:
            log_event("clear data failed", error)
            messagebox.showerror("操作失败", "数据没有成功清空。", parent=self)

    def open_data_folder(self) -> None:
        folder = self.db.path.parent
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(folder))

    def open_log_folder(self) -> None:
        folder = app_log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(folder))

    def navigate(self, view: str) -> None:
        self.view = view
        self.selected_goal_id = None
        self.selected_task_ids.clear()
        self.search_var.set("")
        self.render()

    def _window_resized(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        compact = int(event.width) < 1080
        if compact == self._compact_window:
            return
        self._compact_window = compact
        if self._resize_after:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(80, self.render)

    def _check_natural_day(self) -> None:
        current = today_key()
        if current != self._natural_day:
            self._natural_day = current
            if self.state() != "withdrawn":
                self.render()
        if self.winfo_exists():
            self.after(60_000, self._check_natural_day)

    def on_close(self) -> None:
        if not self._exiting and self.settings.get("close_to_tray", "1") == "1" and self.integration.tray_available:
            self.withdraw()
            return
        self._exiting = True
        self.db.set_setting("geometry", self.geometry())
        self.db.set_setting("last_view", self.view)
        self.db.set_setting("theme", self.theme_key)
        self.integration.destroy()
        self.db.close()
        self.destroy()

    def clear(self, parent: tk.Misc) -> None:
        for child in parent.winfo_children():
            child.destroy()

    def render(self) -> None:
        self._configure_styles()
        self._refresh_sidebar()
        query = self.search_var.get().strip()
        if self.selected_goal_id:
            title, caption = "目标详情", "把目标落到每一个可以执行的动作上"
            show_rail = False
        elif query:
            title, caption = "搜索", f"正在查找「{query}」"
            show_rail = False
        else:
            title_map = {"today": "今天", "upcoming": "之后", "all": "全部", "goals": "长期目标", "archive": "归档", "settings": "设置"}
            caption_map = {"today": date_text(today_key(), True), "upcoming": "把未来安排看得清楚", "all": "所有未完成事项的全局视图", "goals": "让长期方向有清晰的下一步", "archive": "回看已经完成的事情", "settings": "让软件更贴合你的工作方式"}
            title, caption = title_map.get(self.view, "今天"), caption_map.get(self.view, date_text(today_key(), True))
            show_rail = self.view in {"today", "upcoming", "all"} and not self._compact_window
        self.header_title.configure(text=title)
        self.header_caption.configure(text=caption)
        self.clear(self.center)
        self.clear(self.rail)
        if query:
            self.render_search(self.center, query)
        elif self.selected_goal_id:
            self.render_goal_detail(self.center, self.selected_goal_id)
        elif self.view == "today":
            self.render_today(self.center)
        elif self.view == "upcoming":
            self.render_upcoming(self.center)
        elif self.view == "all":
            self.render_all(self.center)
        elif self.view == "goals":
            self.render_goals(self.center)
        elif self.view == "archive":
            self.render_archive(self.center)
        else:
            self.render_settings(self.center)
        if show_rail:
            self.page.grid_columnconfigure(1, minsize=250)
            self.render_rail(self.rail)
            self.rail.grid()
        else:
            self.page.grid_columnconfigure(1, minsize=0)
            self.rail.grid_remove()
        self.canvas.yview_moveto(0)

    def _refresh_sidebar(self) -> None:
        colors = self.colors
        for view, button in self.nav_buttons.items():
            active = (view == "goals" and self.selected_goal_id) or (view == self.view and not self.search_var.get().strip() and not self.selected_goal_id)
            button.configure(bg=colors["soft"] if active else colors["soft_surface"], fg=colors["ink"] if active else colors["text_soft"], activebackground=colors["soft"] if active else colors["soft_surface"], font=("Microsoft YaHei UI", 10, "bold" if active else "normal"))
            indicator = getattr(button, "_indicator", None)
            if indicator is not None:
                indicator.delete("all")
                if active:
                    round_rect(indicator, 0, 1, 3, max(4, indicator.winfo_height() - 1), 2, fill=colors["accentDeep"], outline="")
            count_label = getattr(button, "_count_label", None)
            if count_label:
                if view == "today":
                    count_label.configure(text=str(len(self.db.list_tasks(mode="default"))))
                elif view == "all":
                    count_label.configure(text=str(len(self.db.list_tasks())))
                elif view == "goals":
                    count_label.configure(text=str(len(self.db.list_goals(status="active"))))
                count_label.configure(bg=colors["soft"] if active else colors["soft_surface"], fg=colors["ink_soft"])

    def toggle_completed(self) -> None:
        self.completed_open = not self.completed_open
        self.render()

    def _set_all_mode(self, mode: str) -> None:
        self.all_mode = mode
        self.render()

    def _set_goal_mode(self, mode: str) -> None:
        self.goal_mode = mode
        self.render()

    def _set_goal_status(self, status: str) -> None:
        self.goal_status = status
        self.render()

    def _set_goal_category(self, category: str) -> None:
        self.goal_category = category
        self.render()

    def _set_archive_tab(self, tab: str) -> None:
        self.archive_tab = tab
        self.render()

    def _set_archive_category(self, category: str) -> None:
        self.archive_category = category
        self.render()

    def _archive_query_changed(self, value: str) -> None:
        self.archive_query = value
        self.after_idle(self.render)

    def _save_default_category(self, value: str) -> None:
        self.db.set_setting("default_category", value)
        self.settings["default_category"] = value

    def _save_startup_page(self, value: str) -> None:
        self.db.set_setting("startup_page", value)
        self.settings["startup_page"] = value

    def _save_reduce_motion(self, value: bool) -> None:
        self.db.set_setting("reduce_motion", int(value))
        self.settings["reduce_motion"] = "1" if value else "0"

    def _save_startup_enabled(self, value: bool) -> None:
        try:
            set_windows_autostart(bool(value))
            self.db.set_setting("startup_enabled", int(bool(value)))
            self.settings["startup_enabled"] = "1" if value else "0"
            self.show_toast("开机自启已更新")
        except Exception as error:
            log_event("autostart setting failed", error)
            messagebox.showerror("开机自启不可用", "Windows 没有接受这个开机自启设置。", parent=self)
            self.render()

    def _save_startup_minimized(self, value: bool) -> None:
        self.db.set_setting("startup_minimized", int(bool(value)))
        self.settings["startup_minimized"] = "1" if value else "0"
        self.show_toast("启动方式已更新")

    def _save_close_mode(self, value: str) -> None:
        mode = "1" if value == "1" else "0"
        self.db.set_setting("close_to_tray", mode)
        self.settings["close_to_tray"] = mode
        self.show_toast("关闭按钮行为已更新")

    def _save_global_hotkey(self, value: str) -> None:
        normalized = normalize_hotkey(value)
        if not normalized:
            messagebox.showerror("快捷键格式不正确", "请输入类似 Ctrl + Alt + T 的组合键。", parent=self)
            return
        if not self.integration.available:
            messagebox.showerror("快捷键不可用", "当前运行环境没有可用的 Windows 全局快捷键接口。", parent=self)
            return
        if not self.integration.register_hotkey(normalized):
            messagebox.showerror("快捷键冲突", f"{display_hotkey(normalized)} 已被其他软件占用，请换一个组合键。", parent=self)
            return
        self.db.set_setting("global_hotkey", normalized)
        self.settings["global_hotkey"] = normalized
        self.render()
        self.show_toast(f"全局快捷键已设为 {display_hotkey(normalized)}")

    def set_theme(self, theme_key: str) -> None:
        if theme_key in THEME_KEYS:
            self.theme_key = theme_key
            self.db.set_setting("theme", theme_key)
            self.render()
