# PiggyPlan 视觉重构与模块化 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 3185 行单文件 Tkinter 应用拆成多文件包，并在零功能变更的前提下重建其视觉层（自绘圆角组件、对比度达标的两级强调色、以用户提供的猪图为源的品牌层）。

**Architecture:** 纯标准库。工具/数据/运行时层为真模块；页面与对话框以 Mixin 混入 `PiggyPlanApp`（`self.` 调用点零改动）；视觉层由 `tokens.py`（设计变量）→ `ui/shape.py`（Canvas 圆角与假抗锯齿）→ `ui/widgets.py`（组件）三层构成，页面只消费组件不直接画。

**Tech Stack:** Python 3.12 标准库、Tkinter/Tk 8.6、SQLite、ctypes/win32 API、PyInstaller（构建期）。

**Spec:** `docs/superpowers/specs/2026-09-28-piggyplan-visual-refactor-design.md`

## Global Constraints

每个任务都隐含遵守以下条目，数值逐字取自 spec：

- **零第三方依赖**：运行时与构建期只用 Python 标准库。不得 `pip install`（含 pytest、Pillow）。
- **测试载体**：断言写进 `piggyplan/selftest.py` 的 `run_self_test()`，沿用现有 `assert` 风格（本机无 pytest）。
- **入口文件名不变**：根目录 `piggyplan_desktop.py` 必须继续存在且可直接 `python piggyplan_desktop.py` 运行（`.bat`、开机自启注册表值、PyInstaller spec 都指向它）。
- **对比度下限**：任何用于文字的 `*Ink` 色，在其所处背景上 WCAG 对比度 ≥ 4.5:1。由 selftest 强制。
- **字号下限**：≤9pt 不得使用 `bold`（`Microsoft YaHei UI` 回退下的 micro 角色是唯一例外）。
- **间距取值只允许**：`4 8 12 16 24 32 48`；圆角只允许 `4 10 14 22`。
- **文案**：空状态是行动的邀请；存钱罐隐喻全局只用 2 处。
- **阶段纪律**：Task 2–4 为纯搬迁，验收标准是截图与 Task 1 基线一致；任何视觉变化只能出现在 Task 7–11。
- **每任务一提交**，提交前 `--self-test` 与 `--gui-smoke` 必须通过。

## 关于计划中的代码量

Task 2–4 是机械搬迁，计划给出**精确行区间 + 转换规则 + 验收命令**，不把既有 3000 行复制进本文档——那不会增加任何信息。Task 5–11 是**新写**的代码（token、圆角算法、组件、资产管线、断言），计划给出完整可用实现。

## 文件结构（终态）

| 文件 | 职责 | 来源 |
|---|---|---|
| `piggyplan_desktop.py` | 薄入口：`_prepare_tcl_runtime` + `main()` | 改造 1–64 / 3153–3185 |
| `piggyplan/constants.py` | `APP_NAME` `APP_VERSION` `DAY_FORMAT` `HOTKEY_DEFAULT` | 搬 75–81 |
| `piggyplan/util.py` | 日期/文本/uid/热键规范化/开机自启 | 搬 90–247 |
| `piggyplan/database.py` | `Database` | 搬 248–790 |
| `piggyplan/png.py` | PNG 解码/编码/抠底/缩放/裁切 | 新写 |
| `piggyplan/tokens.py` | 色板、两级强调色、字号阶、间距阶、圆角阶、字族解析 | 新写 |
| `piggyplan/assets.py` | 构建期生成的 base64 图像 | 生成 |
| `piggyplan/runtime/paths.py` | 数据/备份/日志目录与 `log_event` | 搬 96–125, 909–913 |
| `piggyplan/runtime/tcl.py` | Tcl 运行时修复 | 搬 26–64 |
| `piggyplan/runtime/single_instance.py` | 单实例与已有窗口激活 | 搬 914–1009 |
| `piggyplan/runtime/windows_integration.py` | 托盘/全局热键/窗口消息 | 搬 1010–1211 |
| `piggyplan/ui/shape.py` | 圆角矩形、假抗锯齿、颜色混合、描边壳 | 新写 |
| `piggyplan/ui/widgets.py` | `Card` `PillButton` `Chip` `HeartMark` `SnoutBullet` `Field` `StatBlock` `SegmentedControl` `Switch` | 新写 |
| `piggyplan/ui/mascot.py` | `PigMark` 各尺寸档 | 新写 |
| `piggyplan/ui/primitives.py` | `page_header` `section_title` `card` `badge` `empty_state` `task_row` 等原语（Mixin） | 搬 1754–1918 |
| `piggyplan/ui/toast.py` | `show_toast` | 搬 3023–3060 |
| `piggyplan/ui/menu.py` | `open_context_menu` | 搬 3079–3104 |
| `piggyplan/pages/*.py` | 8 个页面 Mixin | 搬 1919–2463 |
| `piggyplan/dialogs/*.py` | 5 个对话框 Mixin | 搬 1497–1567, 2552–2792, 2964–3013 |
| `piggyplan/features/batch.py` | 批量操作与撤销 Mixin | 搬 2793–2963 |
| `piggyplan/features/tasks.py` | 单任务操作与撤销 Mixin | 搬 3014–3152 剩余部分 |
| `piggyplan/app.py` | `PiggyPlanApp` 外壳与路由 | 搬 1212–1446, 1568–1753, 2464–2551 |
| `piggyplan/selftest.py` | `run_self_test` `run_gui_smoke_test` + 设计断言 | 搬 791–908 并扩展 |
| `tools/build_assets.py` | 生成 `assets.py` 与 `icon.ico` | 新写 |
| `tools/shoot.py` | 六页 + 一对话框的截图夹具 | 新写 |
| `legacy/` | 旧 PWA 七个文件 | 移动 |

---

## Task 1: 截图基线夹具（重构前必须先有"之前"）

**Files:**
- Create: `tools/shoot.py`
- Create: `shots/.gitignore`

**Interfaces:**
- Consumes: `piggyplan_desktop.py` 的 `PiggyPlanApp`（尚未拆分，从根模块导入）
- Produces: `shots/<label>/{today,upcoming,all,goals,archive,settings,dialog-task}.png`；`label` 为 `before` 或 `after`。后续每个 Task 的验收命令都调用它。

- [ ] **Step 1: 写 `tools/shoot.py`**

抓窗口用 PowerShell 的 `Graphics.CopyFromScreen`（本仓库 `verify.ps1` 已有同类用法，本会话已验证可用），不在 Python 里手写 GDI 结构体——后者容易在 `BITMAPINFOHEADER` 打包上出错且无收益。窗口矩形由 `ctypes` 的 `GetWindowRect` 取得。

```python
"""截图夹具：以固定窗口几何渲染每个页面，再抓窗口矩形存 PNG。

只依赖标准库 + 系统自带 PowerShell。用于重构前后逐张肉眼比对。
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CAPTURES = ["today", "upcoming", "all", "goals", "archive", "settings"]


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def window_rect(app) -> tuple[int, int, int, int]:
    app.update_idletasks()
    app.lift()
    app.focus_force()
    app.update()
    hwnd = int(app.frame(), 16) if app.frame().startswith("0x") else int(app.frame())
    rect = RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def grab(app, destination: Path) -> None:
    left, top, width, height = window_rect(app)
    script = (
        "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
        f"$b=New-Object System.Drawing.Bitmap {width},{height};"
        "$g=[System.Drawing.Graphics]::FromImage($b);"
        f"$g.CopyFromScreen({left},{top},0,0,$b.Size);"
        f"$b.Save('{destination.as_posix()}')"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
    print(f"  {destination.name} {width}x{height}")


def run(label: str) -> None:
    import piggyplan_desktop

    out = ROOT / "shots" / label
    out.mkdir(parents=True, exist_ok=True)
    app = piggyplan_desktop.PiggyPlanApp()
    app.geometry("1160x760+60+40")
    for name in CAPTURES:
        app.navigate(name)
        grab(app, out / f"{name}.png")
    app.open_task_dialog()
    grab(app, out / "dialog-task.png")
    app.destroy_top_level()
    app.destroy()
    print(f"shots/{label}: {len(CAPTURES) + 1} images")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "before")
```

`tk.Tk.frame()` 返回的是十六进制字符串窗口 id，即 Win32 HWND，可直接交给 `GetWindowRect`。

- [ ] **Step 2: 生成基线并逐张肉眼确认**

Run: `python tools/shoot.py before`
Expected: `shots/before: 7 images`，七张图都能看清对应页面（不是黑屏/不是别的窗口）。若截到别的窗口，说明 `SetForegroundWindow` 未生效——在 `grab` 前先 `app.lift(); app.focus_force(); update()`。

- [ ] **Step 3: 让 `shots/` 不进版本库**

Create `shots/.gitignore`:

```
*
!.gitignore
```

- [ ] **Step 4: 提交**

```bash
git add tools/shoot.py shots/.gitignore
git commit -m "test: 增加六页一对话框的截图夹具，用于重构前后比对"
```

---

## Task 2: 包骨架与纯逻辑层搬迁

**Files:**
- Create: `piggyplan/__init__.py`, `piggyplan/constants.py`, `piggyplan/util.py`, `piggyplan/database.py`, `piggyplan/runtime/__init__.py`, `piggyplan/runtime/paths.py`
- Modify: `piggyplan_desktop.py`（删除已搬出的段落，改为 import）

**Interfaces:**
- Consumes: 无
- Produces: `constants.{APP_NAME,APP_VERSION,DAY_FORMAT,APP_MUTEX_NAME,AUTOSTART_KEY,AUTOSTART_VALUE,HOTKEY_DEFAULT}`；`util.{today_text,today_key,offset_date,parse_date,date_text,category_label,split_tags,uid,now_iso,start_of_week,end_of_week,normalize_hotkey,display_hotkey,autostart_command,set_windows_autostart}`；`database.Database`；`runtime.paths.{app_data_dir,app_backup_dir,app_log_dir,log_event}`

- [ ] **Step 1: 按行区间原样搬出**

| 目标 | 源行区间（`piggyplan_desktop.py`） |
|---|---|
| `piggyplan/constants.py` | 75–81（`APP_NAME` … `HOTKEY_DEFAULT`） |
| `piggyplan/util.py` | 90–247 |
| `piggyplan/database.py` | 248–790 |
| `piggyplan/runtime/paths.py` | 96–125 与 909–913 |

搬动时**不改一行逻辑**，只补 import。`util.py` 头部：

```python
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from .constants import DAY_FORMAT

try:
    import winreg
except ImportError:
    winreg = None
```

`database.py` 头部：

```python
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .constants import APP_VERSION
from .runtime.paths import log_event
from .util import now_iso, offset_date, split_tags, today_key, uid
```

- [ ] **Step 2: 处理 `THEMES` 的临时归属**

`THEMES`(82–87) 此刻同时被 `PiggyPlanApp` 和（Task 5 之前的）`selftest` 引用。**先搬到 `piggyplan/constants.py`**，Task 5 再迁进 `tokens.py`。不要跳过这一步去提前建 `tokens.py`。

- [ ] **Step 3: 根模块改为导入**

`piggyplan_desktop.py` 保留 `_prepare_tcl_runtime`(26–64)、`PiggyPlanApp`、`run_self_test`、`run_gui_smoke_test`、`SingleInstance`、`activate_existing_window`、`WindowsIntegration`、`main`，其余替换为：

```python
from piggyplan.constants import (APP_MUTEX_NAME, APP_NAME, APP_VERSION, AUTOSTART_KEY,
                                 AUTOSTART_VALUE, DAY_FORMAT, HOTKEY_DEFAULT, THEMES)
from piggyplan.database import Database
from piggyplan.runtime.paths import app_backup_dir, app_data_dir, app_log_dir, log_event
from piggyplan.util import (category_label, date_text, display_hotkey, normalize_hotkey,
                            now_iso, offset_date, parse_date, split_tags, start_of_week,
                            end_of_week, today_key, today_text, uid)
```

- [ ] **Step 4: 跑测试**

Run: `python piggyplan_desktop.py --self-test && python piggyplan_desktop.py --gui-smoke`
Expected: `desktop-database-self-test: ok` 与现有 gui-smoke 通过输出。若报 `NameError`，说明根模块仍有对已搬出符号的引用——按报错补 import，不要改逻辑。

- [ ] **Step 5: 截图比对基线**

Run: `python tools/shoot.py after-task2`
Expected: 七张图与 `shots/before/` 视觉一致（此任务不应有任何像素差异）。

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "refactor: 抽出 constants/util/database/runtime.paths 为独立模块

纯搬迁，无行为变更；为后续组件层与视觉 token 建立落点。"
```

---

## Task 3: 运行时层与 Tcl 修复搬迁

**Files:**
- Create: `piggyplan/runtime/tcl.py`, `piggyplan/runtime/single_instance.py`, `piggyplan/runtime/windows_integration.py`
- Modify: `piggyplan_desktop.py`

**Interfaces:**
- Consumes: `runtime.paths`（Task 2）、`constants`、`util.normalize_hotkey`
- Produces: `runtime.tcl.prepare()`；`runtime.single_instance.{SingleInstance,activate_existing_window}`；`runtime.windows_integration.WindowsIntegration`

- [ ] **Step 1: 搬 `runtime/tcl.py`**（源 26–64）

函数改名 `_prepare_tcl_runtime` → `prepare`，模块内**不要**在 import 时执行（原文件靠 import 副作用调用，搬后由入口显式调用）。

- [ ] **Step 2: 搬 `runtime/single_instance.py`**（源 914–1009）

`APP_MUTEX_NAME` 改为从 `.constants` 导入。

- [ ] **Step 3: 搬 `runtime/windows_integration.py`**（源 1010–1211）

`WindowsIntegration` 引用 `PiggyPlanApp` 只用于类型标注与方法调用，改为字符串标注并加注释：

```python
class WindowsIntegration:
    """Owns the tray icon, the global hotkey and the message pump.

    `app` is duck-typed: this module calls show_tray_menu / open_quick_add /
    show_main_window on it and reads .settings / .db.  Keeping it untyped here
    is what lets runtime/ stay importable without the UI layer.
    """

    def __init__(self, app: "Any") -> None: ...
```

- [ ] **Step 4: 根模块显式调用 Tcl 修复**

`piggyplan_desktop.py` 顶部：

```python
from piggyplan.runtime.tcl import prepare as _prepare_tcl

_prepare_tcl()

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
```

**顺序是关键**：`_prepare_tcl()` 必须在 `import tkinter` 之前执行，否则 PyInstaller 打包版的 Tcl 路径修复失效（原文件正是靠 import 副作用保证这一点的）。

**连带约束**：`runtime/tcl.py` 自身**不得 import tkinter**，`piggyplan/__init__.py` 与 `piggyplan/constants.py` 也不得——否则 `from piggyplan.runtime.tcl import prepare` 这一行就会间接把 tkinter 拉进来，修复时机作废。`piggyplan/__init__.py` 保持空文件。

- [ ] **Step 5: 跑测试 + 截图比对**

Run: `python piggyplan_desktop.py --self-test && python piggyplan_desktop.py --gui-smoke && python tools/shoot.py after-task3`
Expected: 测试通过；截图与 `before` 一致。

- [ ] **Step 6: 提交**

```bash
git commit -aqm "refactor: 抽出 Tcl 运行时修复、单实例与托盘/热键集成到 runtime/

Tcl 修复改为入口显式调用，顺序仍在 import tkinter 之前。"
```

---

## Task 4: UI 层按 Mixin 拆分

**Files:**
- Create: `piggyplan/ui/__init__.py`, `piggyplan/ui/primitives.py`, `piggyplan/ui/toast.py`, `piggyplan/ui/menu.py`
- Create: `piggyplan/pages/__init__.py` + `today.py` `upcoming.py` `all.py` `goals.py` `archive.py` `search.py` `rail.py` `settings.py`
- Create: `piggyplan/dialogs/__init__.py` + `task.py` `goal.py` `filter.py` `quick_add.py` `goal_decision.py`
- Create: `piggyplan/features/__init__.py` `batch.py` `tasks.py`
- Create: `piggyplan/app.py`
- Modify: `piggyplan_desktop.py` → 变成薄入口

**Interfaces:**
- Consumes: Task 2–3 全部
- Produces: `piggyplan.app.PiggyPlanApp`（继承顺序见 Step 3）；`piggyplan_desktop.main()` 与 `piggyplan_desktop.PiggyPlanApp`（**必须继续可从根模块取到**，`tools/shoot.py` 依赖它）

- [ ] **Step 1: 按行区间把 `PiggyPlanApp` 方法搬进 Mixin**

转换规则（对每个方法**只做这三处替换**，不改任何逻辑）：
1. `class PiggyPlanApp(tk.Tk)` 的方法 → `class XxxMixin:` 的方法，签名不变（`self` 保留）。
2. 删除方法体里对已搬出模块符号的直接引用 → 改为 `from ..constants import ...` 等模块级 import。
3. `super().__init__()` 只留在 `app.py`。

| 目标文件 | 类名 | 源行（方法名） |
|---|---|---|
| `ui/primitives.py` | `PrimitivesMixin` | 1754–1918：`page_header` `section_title` `card` `badge` `_scrollable_task_holder` `task_row` `_drag_start` `_drag_motion` `_drag_release` `_bind_right_click` `_toggle_selection` `empty_state` |
| `ui/toast.py` | `ToastMixin` | 3023–3046：`show_toast`（`_undo_task` 属撤销语义，归 `features/tasks.py`） |
| `ui/menu.py` | `MenuMixin` | 3079–3104：`open_context_menu` |
| `pages/today.py` | `TodayMixin` | 1919–1971 |
| `pages/upcoming.py` | `UpcomingMixin` | 1972–1998 |
| `pages/all.py` | `AllMixin` | 1999–2094：`render_all` `_apply_task_filters` `_filter_summary` `render_batch_bar` `render_board` |
| `pages/goals.py` | `GoalsMixin` | 2095–2225：`render_goals` `goal_card` `_bind_click_recursive` `render_goal_detail` |
| `pages/archive.py` | `ArchiveMixin` | 2226–2281 |
| `pages/search.py` | `SearchMixin` | 2282–2309 |
| `pages/rail.py` | `RailMixin` | 2310–2355 |
| `pages/settings.py` | `SettingsMixin` | 2356–2463 |
| `dialogs/quick_add.py` | `QuickAddMixin` | 1497–1567 |
| `dialogs/task.py` | `TaskDialogMixin` | 2552–2685：`open_new_task` `open_task_dialog` `_form_label` |
| `dialogs/goal.py` | `GoalDialogMixin` | 2686–2753 |
| `dialogs/filter.py` | `FilterDialogMixin` | 2754–2792 |
| `dialogs/goal_decision.py` | `GoalDecisionMixin` | 2964–3013 |
| `features/batch.py` | `BatchMixin` | 2793–2963 |
| `features/tasks.py` | `TaskActionsMixin` | 3014–3022, 3047–3078, 3105–3152 |
| `app.py` | `PiggyPlanApp` | 1212–1496, 1568–1753, 2464–2551 |

- [ ] **Step 2: 每个新文件加统一头注释**

例：`piggyplan/pages/today.py`

```python
"""今日清单页：逾期、今天、已完成三段。

页面只负责排布与调用，绘制一律走 PrimitivesMixin 的 card/section_title/task_row，
数据一律走 self.db。任何颜色/字号只能来自 tokens（Task 5 之后）。
"""
```

- [ ] **Step 3: `app.py` 组装继承顺序**

```python
from ..dialogs.filter import FilterDialogMixin
from ..dialogs.goal import GoalDialogMixin
from ..dialogs.goal_decision import GoalDecisionMixin
from ..dialogs.quick_add import QuickAddMixin
from ..dialogs.task import TaskDialogMixin
from ..features.batch import BatchMixin
from ..features.tasks import TaskActionsMixin
from ..pages.all import AllMixin
from ..pages.archive import ArchiveMixin
from ..pages.goals import GoalsMixin
from ..pages.rail import RailMixin
from ..pages.search import SearchMixin
from ..pages.settings import SettingsMixin
from ..pages.today import TodayMixin
from ..pages.upcoming import UpcomingMixin
from ..ui.menu import MenuMixin
from ..ui.primitives import PrimitivesMixin
from ..ui.toast import ToastMixin


class PiggyPlanApp(
    SettingsMixin, ArchiveMixin, GoalsMixin, AllMixin, UpcomingMixin, TodayMixin,
    SearchMixin, RailMixin,
    TaskDialogMixin, GoalDialogMixin, FilterDialogMixin, QuickAddMixin, GoalDecisionMixin,
    BatchMixin, TaskActionsMixin,
    MenuMixin, ToastMixin, PrimitivesMixin,
    tk.Tk,
):
    ...
```

`tk.Tk` 必须在最右（基类链末端），`__init__` 里的 `super().__init__()` 才会命中它。

- [ ] **Step 4: 根模块变薄入口**

`piggyplan_desktop.py` 最终只保留：

```python
"""PiggyPlan 桌面版入口。

保留此文件与这些 re-export 是硬要求：启动 .bat、开机自启注册表值、
PyInstaller spec 和 tools/shoot.py 都按 `piggyplan_desktop` 这个名字引用它。
"""
from __future__ import annotations

import sys

from piggyplan.runtime.tcl import prepare as _prepare_tcl

_prepare_tcl()

from piggyplan.app import PiggyPlanApp            # noqa: E402  (re-export：见模块 docstring)
from piggyplan.selftest import run_gui_smoke_test, run_self_test  # noqa: E402
from piggyplan.runtime.single_instance import SingleInstance, activate_existing_window  # noqa: E402
from piggyplan.runtime.paths import log_event     # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ...  # 原 3153–3181 逐字搬来


if __name__ == "__main__":
    raise SystemExit(main())
```

`run_self_test` / `run_gui_smoke_test` 从 `piggyplan_desktop.py` 791–908 搬到 `piggyplan/selftest.py`。

- [ ] **Step 5: 跑测试 + 截图比对**

Run: `python piggyplan_desktop.py --self-test && python piggyplan_desktop.py --gui-smoke && python tools/shoot.py after-task4`
Expected: 全绿；截图与 `before` 一致。此任务结束时根模块应 < 80 行，`wc -l piggyplan/*.py piggyplan/*/*.py` 总和约等于原 3185。

- [ ] **Step 6: 提交**

```bash
git commit -aqm "refactor: PiggyPlanApp 按页面/对话框/批量操作拆为 Mixin 模块

单文件 3185 行拆为 22 个文件。用 Mixin 而非 render(app, parent) 函数是为零调用点
改动：搬迁与换肤的风险因此可以分开归因。代价是页面仍经 self 共享状态。"
```

---

## Task 5: `tokens.py` 与对比度断言

**Files:**
- Create: `piggyplan/tokens.py`
- Modify: `piggyplan/selftest.py`（新增 `run_design_assertions`）
- Modify: `piggyplan/constants.py`（删除 `THEMES`）

**Interfaces:**
- Consumes: 无
- Produces:
  - `tokens.THEME_KEYS: tuple[str, ...]`、`tokens.THEMES: dict[str, Theme]`，`Theme` 含 `name accent accentDeep ink soft wash shell`
  - `tokens.NEUTRAL: dict` 含 `bg surface surface_soft line line_strong ink ink_soft ink_faint`
  - `tokens.SEMANTIC: dict` 含 `high success warning`，每项 `{"shape": hex, "ink": hex}`
  - `tokens.SPACE: dict[str,int]`、`tokens.RADIUS: dict[str,int]`
  - `tokens.resolve_family(root) -> str`、`tokens.resolve_fonts(root) -> dict[str, tuple]`、`tokens.font_rules(root=None) -> dict[str, tuple[str,int,str]]`
  - `tokens.contrast(a: str, b: str) -> float`
  - `tokens.palette(theme_key: str) -> dict[str, str]` — 展平成 `app.colors` 需要的键（含向后兼容键 `strong/accent/soft/bg/surface/text/text_soft/text_faint/high/warning/success`）

- [ ] **Step 1: 先写失败断言**

在 `piggyplan/selftest.py` 追加，并在 `run_self_test()` 末尾调用：

```python
def run_design_assertions() -> None:
    """把 spec 的两条硬规则钉死：文字色必须达 AA，且 ≤9pt 不得加粗。"""
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
            assert weight in ("normal", "medium", "Medium"), \
                f"{name} 为 {size}pt 却用了 {weight}：CJK 小字号加粗会糊"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python piggyplan_desktop.py --self-test`
Expected: `ModuleNotFoundError: No module named 'piggyplan.tokens'`

- [ ] **Step 3: 写 `tokens.py`**

```python
"""设计 token：唯一的颜色、字号、间距、圆角来源。

页面与组件一律从这里取值；本文件之外的模块不得出现字面量色号。
色值来源与两级强调色规则见 docs/superpowers/specs/
2026-09-28-piggyplan-visual-refactor-design.md 第 3 节。
"""
from __future__ import annotations

import tkinter.font as tkfont

# --- 中性色：与主题无关 ---
NEUTRAL = {
    "bg": "#FFF9F8",
    "surface": "#FFFFFF",
    "surface_soft": "#FFF1F5",
    "line": "#F7E8ED",
    "line_strong": "#EEC6D4",
    "ink": "#2E2126",          # 15.4:1 on surface
    "ink_soft": "#7A666D",     # 5.32:1 on surface, 4.67:1 on pink.soft
    "ink_faint": "#A9969D",    # 仅装饰性大字号，禁止用于正文
}

# --- 四套浅色主题 ---
# accent/accentDeep 只做图形；ink 才允许做文字；shell 是"墨线只在壳上"的描边色。
THEMES = {
    "pink":     {"name": "小猪粉",   "accent": "#F8CEDB", "accentDeep": "#F2B4C7", "ink": "#B8405F", "soft": "#FDECF1", "wash": "#FFF8FA"},
    "peach":    {"name": "蜜桃橘",   "accent": "#F9D3C5", "accentDeep": "#F3BDA9", "ink": "#B4522F", "soft": "#FFF0EA", "wash": "#FFF9F6"},
    "mint":     {"name": "薄荷绿",   "accent": "#C7E5DB", "accentDeep": "#A8D6C7", "ink": "#2E7A68", "soft": "#EAF7F2", "wash": "#F7FCFA"},
    "lavender": {"name": "薰衣草",   "accent": "#DDD2EE", "accentDeep": "#C6B4E4", "ink": "#6A4E9E", "soft": "#F3EFFB", "wash": "#FAF8FD"},
}
THEME_KEYS = tuple(THEMES)
SHELL = NEUTRAL["ink"]  # 墨线只画在壳上：对话框、侧边栏卡、空状态、Toast

SEMANTIC = {
    "high":    {"shape": "#F86870", "ink": "#B8405F"},  # 心形色取自猪图 #F86870
    "success": {"shape": "#55A781", "ink": "#2E7A68"},
    "warning": {"shape": "#CB8750", "ink": "#A85A22"},
}

SPACE = {"0": 0, "1": 4, "2": 8, "3": 12, "4": 16, "5": 24, "6": 32, "7": 48}
# 自绘假抗锯齿的外圈两环各占 1px，故半径最小取 6（chip 原为 4，因此上调）。
RADIUS = {"chip": 6, "control": 10, "card": 14, "pill": 22}

# --- 字族解析：按角色映射，避免小字号加粗 ---
FONT_PREFERENCE = ("Noto Sans SC", "Microsoft YaHei UI")
FONT_TABLE = {
    "Noto Sans SC": {
        "display": ("Noto Sans SC Medium", 22), "title": ("Noto Sans SC Medium", 13),
        "body": ("Noto Sans SC", 11), "meta": ("Noto Sans SC", 9),
        "micro": ("Noto Sans SC Medium", 8),
    },
    "Microsoft YaHei UI": {
        "display": ("Microsoft YaHei UI", 22, "bold"), "title": ("Microsoft YaHei UI", 13, "bold"),
        "body": ("Microsoft YaHei UI", 11), "meta": ("Microsoft YaHei UI", 9),
        "micro": ("Microsoft YaHei UI", 8, "bold"),
    },
}
DEFAULT_FAMILY = "Microsoft YaHei UI"


def resolve_family(root) -> str:
    installed = set(tkfont.families(root))
    for family in FONT_PREFERENCE:
        if family in installed:
            return family
    return DEFAULT_FAMILY


def resolve_fonts(root) -> dict:
    return dict(FONT_TABLE[resolve_family(root)])


def font_rules(root=None) -> dict:
    """归一化成 (family, size, weight) 三元组，供断言检查。"""
    table = resolve_fonts(root) if root is not None else FONT_TABLE[DEFAULT_FAMILY]
    return {name: (spec[0], spec[1], spec[2] if len(spec) > 2 else "normal")
            for name, spec in table.items()}


def contrast(a: str, b: str) -> float:
    def luminance(hex_value: str) -> float:
        channels = [int(hex_value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def palette(theme_key: str) -> dict[str, str]:
    theme = THEMES.get(theme_key) or THEMES["pink"]
    colors = {**NEUTRAL, **theme}
    for role, values in SEMANTIC.items():
        colors[role] = values["shape"]
        colors[f"{role}_ink"] = values["ink"]
    # 向后兼容：Task 7 之前页面仍在读 strong/text/high 等旧键。
    colors["strong"] = theme["ink"]
    colors["text"] = colors["ink"]
    colors["text_soft"] = colors["ink_soft"]
    colors["text_faint"] = colors["ink_faint"]
    colors["shell"] = SHELL
    return colors
```

**注意**：`strong` 旧键被重新指向 `ink`（≥4.5:1），这一步就让现存所有"用 strong 写的文字"自动达标——这是把兼容性代价压到最低的迁移动作。

- [ ] **Step 4: `app.colors` 改为委托 `tokens.palette`**

`piggyplan/app.py`：

```python
from .tokens import SHELL, THEME_KEYS, palette

    @property
    def colors(self) -> dict[str, str]:
        return palette(self.theme_key)
```

删除 `app.py` 里的 `BG/SURFACE/…/HIGH/WARNING/SUCCESS` 类常量与旧 `THEMES` 引用，全部改走 `palette()` 返回的键。`set_theme` 里的 `in THEMES` 判断改为 `in THEME_KEYS`。

- [ ] **Step 5: 跑测试确认通过**

Run: `python piggyplan_desktop.py --self-test`
Expected: `desktop-database-self-test: ok`（含设计断言）。若 `pink.ink on surface_soft = 4.69` 之类的数值与 spec 不符，以代码计算结果为准并回写 spec。

- [ ] **Step 6: 截图（此时允许出现差异）**

Run: `python tools/shoot.py after-task5`
Expected: 与 `before` 相比，**只有文字颜色变深**（`strong` 从 `#D96288`→`#B8405F`），布局无变化。

- [ ] **Step 7: 提交**

```bash
git commit -aqm "feat: 引入设计 token 与两级强调色，并加对比度回归断言

原 strong/success/warning 在白底仅 3.47/2.90/2.95:1，被用在文字上；现拆为
shape(图形)与 ink(文字)两级，ink 全部 >=4.5:1 并由 selftest 钉死。"
```

---

## Task 6: `png.py` 与 `tools/build_assets.py`（猪资产管线）

**Files:**
- Create: `piggyplan/png.py`, `tools/build_assets.py`
- Create: `piggyplan/assets.py`（生成物）

**Interfaces:**
- Consumes: `assets_src/piggy.png`
- Produces:
  - `png.decode(data: bytes) -> tuple[int, int, bytearray]`（RGBA）
  - `png.encode(width: int, height: int, rgba: bytes) -> bytes`
  - `png.white_to_alpha(width, height, rgba, low=232, high=250) -> bytearray`
  - `png.resize(width, height, rgba, new_w, new_h) -> bytearray`
  - `png.crop(width, height, rgba, box) -> tuple[int, int, bytearray]`
  - `assets.RAW: dict[str, bytes]`，键为 `"logo" "mascot" "mascot_head" "tray"`，值为 PNG 字节

- [ ] **Step 1: 先写失败测试**

`piggyplan/selftest.py`：

```python
def run_png_assertions() -> None:
    from . import assets, png

    payload = assets.RAW["mascot"]
    assert payload[:8] == b"\x89PNG\r\n\x1a\n", "assets 里存的必须是 PNG 字节"
    width, height, rgba = png.decode(payload)
    assert width == 120, f"mascot 宽度应为 120，实际 {width}"
    assert rgba[3] == 0, "左上角应透明——白底没抠净就是这里抓到"
    assert any(rgba[i] == 255 for i in range(3, len(rgba), 4)), "整张图不该全透明"

    small_width, small_height = 16, max(1, round(16 * height / width))
    shrunk = png.resize(width, height, rgba, small_width, small_height)
    assert len(shrunk) == small_width * small_height * 4

    encoded = png.encode(width, height, bytes(rgba))
    back_width, back_height, back = png.decode(encoded)
    assert (back_width, back_height) == (width, height)
    assert bytes(back) == bytes(rgba), "encode/decode 必须无损往返"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python piggyplan_desktop.py --self-test`
Expected: `ImportError: cannot import name 'png'` 或 `ModuleNotFoundError: piggyplan.assets`

- [ ] **Step 3: 写 `piggyplan/png.py`**

```python
"""最小 PNG 实现：仅覆盖本项目的资产管线所需。

只支持 8bit RGB/RGBA、无隔行；只写 RGBA。存在的意义是让 tools/build_assets.py
保持零第三方依赖——不引入 Pillow 也能抠底与缩放。
"""
from __future__ import annotations

import struct
import zlib

_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def decode(data: bytes) -> tuple[int, int, bytearray]:
    """返回 (width, height, RGBA 字节)。调色板与灰度输入一律展开为 RGBA。"""
    assert data[:8] == _SIGNATURE, "不是 PNG"
    offset = 8
    palette: bytes | None = None
    idat = bytearray()
    width = height = 0
    depth = color_type = 0
    while offset < len(data):
        length, kind = struct.unpack(">I4s", data[offset : offset + 8])
        body = data[offset + 8 : offset + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color_type = struct.unpack(">IIBB", body[:10])
        elif kind == b"PLTE":
            palette = body
        elif kind == b"IDAT":
            idat += body
        offset += 12 + length
    assert depth == 8, f"仅支持 8bit，实际 {depth}"
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    stride = width * channels
    raw = zlib.decompress(bytes(idat))
    rows = bytearray(height * stride)
    previous = bytearray(stride)
    cursor = 0
    for y in range(height):
        filter_type = raw[cursor]
        cursor += 1
        line = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        for x in range(stride):
            left = line[x - channels] if x >= channels else 0
            up = previous[x]
            up_left = previous[x - channels] if x >= channels else 0
            value = line[x]
            if filter_type == 1:
                value += left
            elif filter_type == 2:
                value += up
            elif filter_type == 3:
                value += (left + up) >> 1
            elif filter_type == 4:
                predictor = left + up - up_left
                distances = (abs(predictor - left), abs(predictor - up), abs(predictor - up_left))
                value += left if distances[0] <= min(distances[1:]) else (up if distances[1] <= distances[2] else up_left)
            line[x] = value & 255
        rows[y * stride : (y + 1) * stride] = line
        previous = line
    rgba = bytearray(width * height * 4)
    for index in range(width * height):
        if color_type == 6:
            rgba[index * 4 : index * 4 + 4] = rows[index * 4 : index * 4 + 4]
        elif color_type == 2:
            rgb = rows[index * 3 : index * 3 + 3]
            rgba[index * 4 : index * 4 + 3] = rgb
            rgba[index * 4 + 3] = 255
        elif color_type == 3:
            entry = palette[rows[index] * 3 : rows[index] * 3 + 3]
            rgba[index * 4 : index * 4 + 3] = entry
            rgba[index * 4 + 3] = 255
        else:  # 灰度 / 灰度+alpha
            grey = rows[index * channels]
            alpha = rows[index * channels + 1] if channels == 2 else 255
            rgba[index * 4 : index * 4 + 3] = bytes((grey, grey, grey))
            rgba[index * 4 + 3] = alpha
    return width, height, rgba


def encode(width: int, height: int, rgba: bytes) -> bytes:
    stride = width * 4

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (struct.pack(">I", len(body)) + kind + body
                + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))

    scanlines = b"".join(b"\x00" + bytes(rgba[y * stride : (y + 1) * stride]) for y in range(height))
    return (_SIGNATURE
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanlines, 9))
            + chunk(b"IEND", b""))


def white_to_alpha(width: int, height: int, rgba: bytearray, low: int = 232, high: int = 250) -> bytearray:
    """近白 -> 透明，中间线性渐变，避免硬边锯齿。"""
    for index in range(width * height):
        at = index * 4
        lightest = min(rgba[at], rgba[at + 1], rgba[at + 2])
        if lightest >= high:
            alpha = 0
        elif lightest <= low:
            alpha = 255
        else:
            alpha = int(255 * (high - lightest) / (high - low))
        rgba[at + 3] = alpha
    return rgba


def resize(width: int, height: int, rgba: bytes, new_width: int, new_height: int) -> bytearray:
    """预乘 alpha 的双线性缩放。不预乘会让透明像素的黑色边缘渗进可见像素。"""
    out = bytearray(new_width * new_height * 4)
    for y in range(new_height):
        gy = (y + 0.5) * height / new_height - 0.5
        y0 = min(max(int(gy), 0), height - 1)
        y1 = min(y0 + 1, height - 1)
        fy = min(max(gy - y0, 0.0), 1.0)
        for x in range(new_width):
            gx = (x + 0.5) * width / new_width - 0.5
            x0 = min(max(int(gx), 0), width - 1)
            x1 = min(x0 + 1, width - 1)
            fx = min(max(gx - x0, 0.0), 1.0)
            total = [0.0, 0.0, 0.0, 0.0]
            for row, weight_y in ((y0, 1 - fy), (y1, fy)):
                for column, weight_x in ((x0, 1 - fx), (x1, fx)):
                    at = (row * width + column) * 4
                    alpha = rgba[at + 3]
                    weight = weight_y * weight_x
                    for channel in range(3):
                        total[channel] += rgba[at + channel] * alpha * weight
                    total[3] += alpha * weight
            at = (y * new_width + x) * 4
            coverage = total[3]
            for channel in range(3):
                out[at + channel] = int(round(total[channel] / coverage)) if coverage else 0
            out[at + 3] = int(round(coverage))
    return out


def crop(width: int, height: int, rgba: bytes, box: tuple[int, int, int, int]) -> tuple[int, int, bytearray]:
    left, top, right, bottom = box
    cropped_width, cropped_height = right - left, bottom - top
    out = bytearray(cropped_width * cropped_height * 4)
    for y in range(cropped_height):
        src = ((top + y) * width + left) * 4
        dst = y * cropped_width * 4
        out[dst : dst + cropped_width * 4] = rgba[src : src + cropped_width * 4]
    return cropped_width, cropped_height, out
```

- [ ] **Step 4: 写 `tools/build_assets.py`**

```python
"""构建期：assets_src/piggy.png -> piggyplan/assets.py + icon.ico

不参与运行时。生成物提交进版本库，因此打包不需要 Python 之外的工具。
"""
from __future__ import annotations

import base64
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from piggy import png  # noqa: E402

SOURCE = ROOT / "assets_src" / "piggy.png"
TARGET = ROOT / "piggyplan" / "assets.py"
ICON = ROOT / "icon.ico"

# 头部裁切框：小尺寸下全身会糊，只保留头与心形（165x138 原图上目测标定）。
HEAD_BOX = (28, 8, 140, 108)
SIZES = {"logo": 40, "mascot": 120, "mascot_head": 28, "tray": 16}


def build() -> dict[str, bytes]:
    width, height, rgba = png.decode(SOURCE.read_bytes())
    png.white_to_alpha(width, height, rgba)
    images: dict[str, bytes] = {}
    for name, size in SIZES.items():
        if name.endswith("_head") or name == "tray":
            crop_width, crop_height, source = png.crop(width, height, rgba, HEAD_BOX)
        else:
            crop_width, crop_height, source = width, height, rgba
        target_height = max(1, round(size * crop_height / crop_width))
        images[name] = png.encode(size, target_height, png.resize(crop_width, crop_height, source, size, target_height))
    return images


def ico(images: dict[str, bytes]) -> bytes:
    """把已生成的 PNG 原样封进 ICO（Vista+ 允许 PNG 负载，无需 BMP+AND 掩码）。"""
    entries = [("tray", 16), ("mascot_head", 28), ("logo", 40), ("mascot", 120)]
    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory = bytearray()
    payloads = bytearray()
    for key, size in entries:
        payload = images[key]
        dimension = 0 if size >= 256 else size
        directory += struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(payload), offset)
        offset += len(payload)
        payloads += payload
    return header + bytes(directory) + bytes(payloads)


def main() -> None:
    images = build()
    lines = [
        '"""构建期生成，请勿手改：tools/build_assets.py。"""',
        "from __future__ import annotations",
        "",
        "RAW: dict[str, bytes] = {",
    ]
    for name, payload in images.items():
        encoded = base64.b64encode(payload).decode()
        lines.append(f'    "{name}": __import__("base64").b64decode(')
        for index in range(0, len(encoded), 96):
            lines.append(f'        "{encoded[index : index + 96]}"')
        lines.append("    ),")
    lines += ["}", ""]
    TARGET.write_text("\n".join(lines), encoding="utf-8")
    ICON.write_bytes(ico(images))
    for name, payload in images.items():
        print(f"{name:12} {len(payload):>7} bytes")


if __name__ == "__main__":
    main()
```

`assets.py` 里用 `__import__("base64")` 是为了让生成的文件不额外依赖 import 位置；若你更偏好显式 import，把 `import base64` 加进 `lines` 头部并改写为 `base64.b64decode(...)`——两种写法对 PyInstaller 等价。

- [ ] **Step 5: 生成并跑测试**

Run: `python tools/build_assets.py && python piggyplan_desktop.py --self-test`
Expected: 打印四个尺寸字节数；测试通过。

- [ ] **Step 6: 肉眼验证抠底**

Run: `python -c "from piggyplan import png, assets; import pathlib; pathlib.Path('/tmp/check.png').write_bytes(assets.RAW['mascot'])"`，然后打开 `/tmp/check.png`。
Expected: 棋盘格/透明背景，猪的边缘**无白边残留、无黑边渗入**（预乘 alpha 生效）。若出现深色描边，把 `white_to_alpha` 的 `high` 从 250 降到 245 再试。

- [ ] **Step 7: 提交**

```bash
git commit -aqm "feat: 加入标准库 PNG 管线与猪形象资产生成

抠白底 + 预乘 alpha 双线性缩放 + 头部裁切；16px 托盘用头部而非全身。"
```

---

## Task 7: `ui/shape.py` 圆角与假抗锯齿

**Files:**
- Create: `piggyplan/ui/shape.py`
- Create: `tests_shape` 断言并入 `piggyplan/selftest.py`

**Interfaces:**
- Consumes: `tokens.contrast`
- Produces:
  - `shape.mix(color_a: str, color_b: str, ratio: float) -> str`
  - `shape.round_rect(canvas, x1, y1, x2, y2, radius, **style) -> int`
  - `shape.soft_round_rect(canvas, x1, y1, x2, y2, radius, fill, *, backdrop, stroke=None, stroke_width=2) -> list[int]`
  - `shape.heart(canvas, cx, cy, size, fill) -> int`
  - `shape.snout(canvas, cx, cy, width, fill, hole) -> int`

- [ ] **Step 1: 写 `shape.py`**

```python
"""Canvas 自绘原语。Tk 的 Canvas 没有圆角、没有抗锯齿，这里补上。

假抗锯齿的做法：在 backdrop 与 fill 之间画两圈 1px 中间色环，越靠外越接近
backdrop。实测半径 >=6 时肉眼已看不出锯齿，因此 RADIUS 最小值定为 6。
"""
from __future__ import annotations

import tkinter as tk

# (向外扩张像素, 与 backdrop 的混合比)：外环更淡、内环更浓，形成渐变边。
HALO = ((2, 0.35), (1, 0.70))


def _rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))


def mix(color_a: str, color_b: str, ratio: float) -> str:
    """ratio=0 得 color_a，ratio=1 得 color_b。"""
    a, b = _rgb(color_a), _rgb(color_b)
    return "#%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * ratio) for i in range(3))


def round_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **style) -> int:
    """用 smooth 多边形逼近圆角矩形。四角各给三个控制点，避免贝塞尔外凸。"""
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)
    points = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **style)


def soft_round_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int,
                    fill: str, *, backdrop: str, stroke: str | None = None,
                    stroke_width: int = 2) -> list[int]:
    """画一块带圆角、边缘平滑的色块；stroke 非空时在其内缘描墨线。"""
    ids = [
        round_rect(canvas, x1 - grow, y1 - grow, x2 + grow, y2 + grow, radius + grow,
                   fill=mix(backdrop, fill, ratio), outline="")
        for grow, ratio in HALO
    ]
    ids.append(round_rect(canvas, x1, y1, x2, y2, radius, fill=fill, outline=""))
    if stroke:
        # Tk 的描边多边形是锯齿的 1px 线；改用"外圈实心描边色 + 内实心填充色"
        # 两层叠出平滑墨线，这也是"墨线只在壳上"的唯一实现方式。
        ids.append(round_rect(canvas, x1 + 1, y1 + 1, x2 - 1, y2 - 1, max(1, radius - 1),
                              fill=stroke, outline=""))
        ids.append(round_rect(canvas, x1 + stroke_width, y1 + stroke_width,
                              x2 - stroke_width, y2 - stroke_width, max(1, radius - stroke_width),
                              fill=fill, outline=""))
    return ids


def heart(canvas: tk.Canvas, center_x: int, center_y: int, size: int, fill: str) -> int:
    """高优先级标记：取自猪图头顶那颗心，替代红字"高"。"""
    points = [
        center_x, center_y + size * 0.35,
        center_x - size * 0.5, center_y - size * 0.05,
        center_x - size * 0.25, center_y - size * 0.35,
        center_x, center_y - size * 0.1,
        center_x + size * 0.25, center_y - size * 0.35,
        center_x + size * 0.5, center_y - size * 0.05,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, fill=fill, outline="")


def snout(canvas: tk.Canvas, center_x: int, center_y: int, width: int,
          fill: str, hole: str) -> list[int]:
    """分节标记：猪鼻轮廓 + 两个鼻孔。全应用统一标点。"""
    height = round(width * 0.72)
    ids = [canvas.create_oval(center_x - width / 2, center_y - height / 2,
                              center_x + width / 2, center_y + height / 2,
                              fill=fill, outline="")]
    nose = max(1, round(width * 0.16))
    for offset in (-width * 0.2, width * 0.2):
        ids.append(canvas.create_oval(center_x + offset - nose / 2, center_y - nose,
                                      center_x + offset + nose / 2, center_y + nose,
                                      fill=hole, outline=""))
    return ids
```

- [ ] **Step 2: 加形状断言**

`selftest.py`：

```python
def run_shape_assertions() -> None:
    from .ui.shape import mix

    assert mix("#FFFFFF", "#000000", 0.5) == "#808080"
    assert mix("#FDECF1", "#FFFFFF", 0.0) == "#FFFFFF"
    assert mix("#FDECF1", "#FFFFFF", 1.0) == "#FDECF1"
```

- [ ] **Step 3: 跑测试**

Run: `python piggyplan_desktop.py --self-test`
Expected: ok

- [ ] **Step 4: 提交**

```bash
git commit -aqm "feat: 加入 Canvas 圆角、假抗锯齿与心形/猪鼻形状原语"
```

---

## Task 8: `ui/widgets.py` 组件层

**Files:**
- Create: `piggyplan/ui/widgets.py`, `piggyplan/ui/mascot.py`
- Modify: `piggyplan/ui/primitives.py`（`card`/`badge` 改为委托组件，签名不变）

**Interfaces:**
- Consumes: `tokens`、`ui.shape`、`assets.RAW`
- Produces:
  - `widgets.Card(parent, *, app, tone="surface", radius=14, padding=(16,14), stroke=False, hoverable=False)` → `.body`（子控件容器）、`.hover(bool)`
  - `widgets.PillButton(parent, *, app, text, command=None, kind="primary", size="md")` → `.set_text(str)`、`.invoke()`
  - `widgets.Chip(parent, *, app, text, tone="category")`
  - `widgets.HeartIcon(parent, *, app, size=12)` / `widgets.SnoutIcon(parent, *, app, size=14)`
  - `widgets.Field(parent, *, app, label, hint="", width=None)` → `.var`、`.entry`、`.set_error(str)`
  - `widgets.StatBlock(parent, *, app, value, caption)`
  - `widgets.SegmentedControl(parent, *, app, options, value, command)`
  - `widgets.Switch(parent, *, app, variable, command=None)`
  - `mascot.PigMark(parent, *, app, variant="logo")`

- [ ] **Step 0: `widgets.py` 与 `mascot.py` 的模块头**

```python
# piggyplan/ui/widgets.py
from __future__ import annotations

import tkinter as tk

from ..tokens import RADIUS, SEMANTIC, SPACE
from ..tokens import SHELL
from .shape import heart, mix, round_rect, snout, soft_round_rect
```

```python
# piggyplan/ui/mascot.py
from __future__ import annotations

import tkinter as tk

from ..assets import RAW


class PigMark(tk.Label):
    """品牌图。用 Label 承载 PhotoImage：Tk 的 Label 原生支持 RGBA PNG。"""

    def __init__(self, parent, *, app, variant: str = "logo") -> None:
        self._image = tk.PhotoImage(data=RAW[variant])   # 必须持有引用，否则被 GC 后图消失
        super().__init__(parent, image=self._image, bd=0,
                         highlightthickness=0,
                         bg=parent.cget("bg") or app.colors["bg"])
```

- [ ] **Step 1: 写 `Card`（关键实现：Canvas 包 create_window）**

```python
class Card(tk.Canvas):
    """圆角卡片。对外仍是一个普通控件，可 grid/pack，子控件放进 .body。

    用 Canvas 而不是 Frame：Tk 的 Frame 无法画圆角。用 create_window 把
    真正的子容器嵌进来，Entry/Combobox 等交互控件因此保持原生行为。
    """

    def __init__(self, parent, *, app, tone: str = "surface", radius: int = 14,
                 padding: tuple[int, int] = (16, 14), stroke: bool = False,
                 hoverable: bool = False) -> None:
        self.app = app
        self.radius = radius
        self.padding_x, self.padding_y = padding
        self.tone = tone
        self.stroke = stroke
        self.backdrop = parent.cget("bg") or app.colors["bg"]
        super().__init__(parent, bg=self.backdrop, highlightthickness=0, bd=0)
        self.body = tk.Frame(self, bg=self._fill())
        self._window = self.create_window(self.padding_x, self.padding_y,
                                          window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._follow_body)
        self.bind("<Configure>", self._follow_canvas)
        if hoverable:
            self.body.bind("<Enter>", lambda _e: self.hover(True), add="+")
            self.body.bind("<Leave>", lambda _e: self.hover(False), add="+")

    def _fill(self, hovered: bool = False) -> str:
        colors = self.app.colors
        table = {"surface": colors["surface"], "soft": colors["soft"],
                 "accent": colors["accent"], "wash": colors["wash"],
                 "bg": colors["bg"], "shell": colors["surface"]}
        base = table.get(self.tone, colors["surface"])
        return mix(base, colors["accent"], 0.35) if hovered and self.tone == "surface" else base

    def hover(self, on: bool) -> None:
        self.body.configure(bg=self._fill(on))
        self.redraw(self._fill(on))

    def redraw(self, fill: str | None = None) -> None:
        for item in self.find_all():
            if item != self._window:
                self.delete(item)
        width, height = int(self["width"]), int(self["height"])
        soft_round_rect(self, 2, 2, width - 2, height - 2, self.radius,
                        fill or self._fill(), backdrop=self.backdrop,
                        stroke=self.app.colors["shell"] if self.stroke else None)
        self.tag_lower(*[i for i in self.find_all() if i != self._window])
        self.tag_raise(self._window)

    def _follow_body(self, event) -> None:
        wanted_width = event.width + 2 * self.padding_x
        wanted_height = event.height + 2 * self.padding_y
        if (int(self["width"]), int(self["height"])) != (wanted_width, wanted_height):
            self.configure(width=wanted_width, height=wanted_height)
            self.redraw()

    def _follow_canvas(self, event) -> None:
        # 被 grid(sticky="ew") 拉伸时，让 body 跟随宽度，从而支持 wraplength 自适应。
        tk.after("idle", lambda: self.itemconfigure(
            self._window, width=max(1, event.width - 2 * self.padding_x)))
```

- [ ] **Step 2: 写 `PillButton`**

```python
class PillButton(tk.Canvas):
    """胶囊按钮。Tk 的 Button 画不出圆角，因此自绘并自己接管键盘/鼠标语义。"""

    _KINDS = ("primary", "soft", "ghost", "danger")

    def __init__(self, parent, *, app, text: str, command=None,
                 kind: str = "primary", size: str = "md") -> None:
        self.app = app
        self.kind = kind
        self.size = size
        self.command = command
        height = {"sm": 28, "md": 36, "lg": 44}[size]
        self.backdrop = parent.cget("bg") or app.colors["bg"]
        super().__init__(parent, bg=self.backdrop, height=height,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._text = self.create_text(0, 0, anchor="center", text=text)
        self._pressed = False
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Button-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.configure(takefocus=True, highlightthickness=0)
        self.bind("<Return>", lambda _e: self.invoke())
        self.bind("<space>", lambda _e: self.invoke())

    def _palette(self, hovered: bool) -> tuple[str, str]:
        colors = self.app.colors
        if self.kind == "primary":
            fill = mix(colors["accentDeep"], "#000000", 0.06 if hovered else 0.0)
            return fill, "#FFFFFF"
        if self.kind == "soft":
            return (colors["soft"] if not hovered else mix(colors["soft"], colors["accent"], 0.6),
                    colors["ink"])
        if self.kind == "danger":
            return ("#FFF0F0" if not hovered else "#FBE0E0"), "#C9575B"
        return (colors["bg"] if not hovered else colors["surface_soft"]), colors["ink_soft"]

    def redraw(self) -> None:
        for item in self.find_all():
            if item != self._text:
                self.delete(item)
        width, height = int(self["width"]), int(self["height"])
        fill, foreground = self._palette(self._pressed)
        soft_round_rect(self, 2, 2, width - 2, height - 2, min(RADIUS["pill"], height // 2),
                        fill, backdrop=self.backdrop)
        self.itemconfigure(self._text, fill=foreground, font=self.app.font("micro" if self.size == "sm" else "body"))
        self.tag_raise(self._text)

    def _set_hover(self, on: bool) -> None:
        self._pressed = False
        self.redraw()

    def _press(self, _event) -> None:
        self._pressed = True
        self.focus_set()
        self.redraw()

    def _release(self, event) -> None:
        if self._pressed:
            self._pressed = False
            self.redraw()
            self.invoke()

    def invoke(self) -> None:
        if self.command:
            self.command()

    def set_text(self, text: str) -> None:
        self.itemconfigure(self._text, text=text)
```

- [ ] **Step 3: `app.font(role)` 辅助**

`app.py`：

```python
    def font(self, role: str):
        if not hasattr(self, "_fonts"):
            self._fonts = resolve_fonts(self)
        return self._fonts[role]
```

- [ ] **Step 4: `PrimitivesMixin.card` 委托（签名不变）**

```python
    def card(self, parent: tk.Misc, padx: int = 16, pady: int = 14) -> tk.Frame:
        box = Card(parent, app=self, tone=self._card_tone, radius=RADIUS["card"],
                   padding=(padx, pady), stroke=self._card_stroke, hoverable=self._card_hover)
        box.pack(fill="x", pady=(0, SPACE["2"]))
        return box.body
```

`_card_tone/_card_stroke/_card_hover` 由调用方通过上下文管理器式开关设置，默认 `("surface", False, True)`——**内容区因此自动零描边**，外壳处显式开启描边。这就是"墨线只在壳上"的实现落点。

- [ ] **Step 5: 跑测试 + 截图**

Run: `python piggyplan_desktop.py --self-test && python piggyplan_desktop.py --gui-smoke && python tools/shoot.py after-task8`
Expected: 测试通过；截图开始出现圆角卡片（此时尚未全面换组件，只有 `card()` 走到的地方变化）。

- [ ] **Step 6: 提交**

```bash
git commit -aqm "feat: 自绘 Card/PillButton 等组件层，card() 签名保持兼容

Card 用 Canvas + create_window 包裹真实子容器，Entry/Combobox 保持原生交互。
_card_stroke 默认关闭，实现"墨线只在壳上"。"
```

---

## Task 9: 外壳换肤

**Files:**
- Modify: `piggyplan/app.py`（`_build_shell` `_build_header` `_build_sidebar` `_pig_mark` `_label` `_configure_styles`）
- Modify: `piggyplan/ui/primitives.py`（`page_header` `section_title` `empty_state`）
- Modify: `piggyplan/ui/toast.py`, `piggyplan/dialogs/*.py`

**Interfaces:**
- Consumes: Task 5–8
- Produces: 外壳（侧边栏、头部、对话框、Toast、空状态）全部走组件层并带墨线

- [ ] **Step 1: 侧边栏**

`_build_sidebar` 改动清单：
- `self._pig_mark(brand)` → `PigMark(brand, app=self, variant="logo")`
- 品牌副标题 `"PIGGYPLAN · LOCAL FIRST"` 字号 7→`micro`，颜色 `TEXT_FAINT`→`ink_soft`（2.35:1 不达标）
- 底部"本地优先"卡片：`Card(..., stroke=True, tone="surface")`，文案改 `你的事都装在这只猪身上，只写本机，不联网`
- `sidebar_new` 按钮 → `PillButton(kind="primary", size="lg")`
- `_nav_button` 选中态：由"整条换色"改为"左侧 3px 圆角胶囊 + `soft` 底"，用 `shape.round_rect` 画

- [ ] **Step 2: 头部**

`_build_header`：`new_button` → `PillButton`；搜索框保持 `ttk.Entry` 但由 `tokens` 统一圆角内边距；`header_title` 用 `app.font("display")`。

- [ ] **Step 3: 空状态去 emoji**

`empty_state` 第 1911 行的 `self._label(box, "🐷", 27, ...)` 替换为 `PigMark(box, app=self, variant="mascot")`，并把 `box` 换成 `Card(..., stroke=True, tone="soft")`。文案：`今天还空着` / `放进第一件事`。

- [ ] **Step 4: `section_title` 换猪鼻**

`dot = tk.Frame(...)` → `SnoutIcon(left, app=self, size=14)`。

- [ ] **Step 5: 对话框与 Toast 上墨线**

`dialogs/*.py` 五处 `tk.Toplevel` 统一改为经 `Dialog` 基类（`ui/dialog.py`，本任务新建）：`body` 用 `Card(stroke=True)` 包裹，页脚用 `line` 分隔，按钮一律 `PillButton`。`show_toast` 同样上墨线。

- [ ] **Step 6: 跑测试 + 截图 + 逐张确认**

Run: `python piggyplan_desktop.py --self-test && python piggyplan_desktop.py --gui-smoke && python tools/shoot.py after-task9`
Expected: 六页截图里侧边栏出现真猪图、空状态出现 120px 猪、对话框有墨线；**内容区任务卡仍无描边**。

- [ ] **Step 7: 提交**

```bash
git commit -aqm "feat: 外壳换肤——侧边栏/头部/对话框/Toast/空状态接入组件与猪形象

空状态的 🐷 emoji 换成真实形象图；副标题与提示文字对比度升到 AA。"
```

---

## Task 10: 内容区换肤

**Files:**
- Modify: `piggyplan/ui/primitives.py`（`task_row` `badge`）
- Modify: `piggyplan/pages/*.py`

**Interfaces:**
- Consumes: Task 5–9
- Produces: 任务卡零描边、心形=高优先级、语义色全部走 `*ink`

- [ ] **Step 1: `task_row` 改造**

- 删除 3px 左侧色条（1803–1804）——它属于"边框无处不在"
- `check` 按钮（1811，用 `✓`/`·` 文本字符）→ 自绘圆形勾选：`shape.round_rect` 画圆 + 两条线段画勾
- 高优先级：`badge("高")` → `HeartIcon(size=12)`，颜色 `SEMANTIC["high"]["shape"]`
- 卡片：`Card(tone="surface", stroke=False, hoverable=True)`
- 逾期文字色：`warning` → `warning_ink`

- [ ] **Step 2: 页面语义色替换**

逐页把 `colors["high"]`/`colors["strong"]` 用于**文字**处改为 `colors["high_ink"]`/`colors["ink"]`；用于**色块/进度条**处保持 `accent`/`shape`。涉及 `render_rail` 的完成率数字、`render_goals` 的进度条、`render_settings` 的主题名。

- [ ] **Step 3: 字号角色化**

全量把 `("Microsoft YaHei UI", N, "bold")` 字面量替换为 `self.font(role)`。这是"字体难看"的主因修复点：≤9pt 不再加粗。

- [ ] **Step 4: 间距归一**

`padx/pady` 魔法数按 `SPACE` 就近归档：`2→4`、`6→8`、`10→8 或 12`、`13→12`、`18→16`、`22→24`、`26→24`、`34→32`。

- [ ] **Step 5: 性能检查（本任务的风险点）**

组件层把每个任务卡变成一个 Canvas，200 条任务就是 200 个 Canvas + 每卡 5 个多边形。实测确认没有把滚动拖死：

```python
# tools/perf_check.py —— 一次性测量，不进版本库
import sys, time, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import piggyplan_desktop as m
from piggyplan.database import Database
from piggyplan.util import today_key

with tempfile.TemporaryDirectory() as folder:
    db = Database(Path(folder) / "perf.db")
    for index in range(200):
        db.create_task(f"压测任务 {index}", planned_date=today_key())
    app = m.PiggyPlanApp(database=db)
    app.navigate("all")
    start = time.perf_counter()
    app.render()
    app.update()
    print(f"render 200 tasks: {(time.perf_counter() - start) * 1000:.0f} ms")
    app.destroy()
```

Run: `python tools/perf_check.py`
Expected: `< 400 ms`。若超标，按此顺序排查：
1. `Card.redraw()` 是否在每次 `<Configure>` 都全量重建——加尺寸/填充缓存，仅在变化时重画。
2. `soft_round_rect` 每卡 5 个多边形是否必要——hover 态可只改前景色不重画形状。
3. 仍超标则给 `task_row` 走 `tone="surface"` 且 `stroke=False` 的**快速路径**（跳过外圈两环，只画 1 个多边形）。

- [ ] **Step 6: 跑测试 + 截图 + 确认**

Run: `python piggyplan_desktop.py --self-test && python piggyplan_desktop.py --gui-smoke && python tools/shoot.py after-task10`

- [ ] **Step 7: 提交**

```bash
git commit -aqm "feat: 内容区换肤——零描边卡片、心形优先级标记与 AA 语义色

去掉任务卡左侧色条与 emoji 勾选符；文字一律用 *ink 级颜色，色块用 shape 级。"
```

---

## Task 11: 图标、打包、legacy 归档与文档

**Files:**
- Modify: `PiggyPlan.spec`、`build_exe.py`、`package.json`、`README.md`、`便携版使用说明.txt`
- Move: `app.js` `styles.css` `server.mjs` `sw.js` `manifest.json` `index.html` `icon.svg` → `legacy/`
- Create: `icon.ico`（Task 6 已生成）

- [ ] **Step 1: 归档旧 PWA**

```bash
mkdir -p legacy && git mv app.js styles.css server.mjs sw.js manifest.json index.html icon.svg legacy/
```

- [ ] **Step 2: `package.json` 同步**

```json
{
  "scripts": {
    "start": "python piggyplan_desktop.py",
    "desktop": "python piggyplan_desktop.py",
    "test": "python piggyplan_desktop.py --self-test",
    "test:gui": "python piggyplan_desktop.py --gui-smoke",
    "assets": "python tools/build_assets.py",
    "shots": "python tools/shoot.py",
    "web": "node legacy/server.mjs"
  }
}
```

- [ ] **Step 3: PyInstaller 配置**

`PiggyPlan.spec` 与 `build_exe.py` 里：
- `Analysis(['.../piggyplan_desktop.py'], pathex=['G:/Desktop/piggyplan'], ...)` — `pathex` 必须含仓库根，否则找不到 `piggyplan` 包
- `hiddenimports` 补 `piggyplan.pages.*` 等（Mixin 是显式 import，PyInstaller 能静态发现；仅对动态导入项补）
- `EXE(..., icon='G:/Desktop/piggyplan/icon.ico', ...)` — **当前 spec 完全没有 `icon=`，exe 无图标**

- [ ] **Step 4: 构建并验证 exe 图标与运行**

Run: `python build_exe.py`
Expected: `dist/PiggyPlan/PiggyPlan.exe` 存在；双击后任务栏与窗口标题栏显示猪图标；`--self-test` 在 exe 下同样通过（`PiggyPlan.exe --self-test`）。

- [ ] **Step 5: README 更新**

改：目录结构一节（新增包布局）、"已实现"补一条"品牌视觉层与猪形象图标"、验证命令补 `npm run assets`、末尾旧 PWA 路径改为 `legacy/`。删除"四套浅色主题"里已过时的描述并说明两级强调色。

- [ ] **Step 6: 提交**

```bash
git commit -aqm "build: exe 图标接入、打包适配多文件包，旧 PWA 归档到 legacy/

原 spec 无 icon= 参数，exe 一直没有图标；打包路径需含仓库根才能发现 piggyplan 包。"
```

---

## Task 12: 终检

- [ ] **Step 1: 全量回归**

Run: `python piggyplan_desktop.py --self-test && python piggyplan_desktop.py --gui-smoke && powershell -ExecutionPolicy Bypass -File .\verify.ps1`
Expected: 全绿

- [ ] **Step 2: 键盘可达性**

Tab 走完侧边栏与一个任务卡的所有可交互元素；`PillButton` 在 Return 与 Space 下都触发；焦点位置肉眼可辨。

- [ ] **Step 3: 四套主题逐一截图**

Run: `python tools/shoot.py after-theme-pink`（改 `settings` 里主题后重复四次）
Expected: 四套下 `ink` 文字均清晰；selftest 的对比度断言覆盖此保证。

- [ ] **Step 4: `reduce_motion` 与窄窗口**

设置里开"减少动效"后 hover 不产生过渡；窗口 <1080px 时概览栏隐藏仍生效。

- [ ] **Step 5: 前后对比图交付**

把 `shots/before/today.png` 与 `shots/after/today.png` 一并展示给用户确认。

- [ ] **Step 6: 打 tag**

```bash
git tag v1.1.0-visual && git log --oneline | head -15
```
