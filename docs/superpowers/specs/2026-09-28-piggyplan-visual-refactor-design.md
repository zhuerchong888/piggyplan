# PiggyPlan 视觉重构与模块化 · 设计文档

日期：2026-09-28 · 状态：已与用户逐节确认

## 0. 决策记录（用户已选定）

| 议题 | 决定 |
|---|---|
| 优化重心 | 外观与猪形象 + 代码结构与可维护性。**不做**功能新增、不做性能专项 |
| 技术栈 | 保留 Tkinter + 纯 Python 标准库，自绘组件层。**不引入** pywebview/WebView2 |
| 猪的角色 | 品牌装饰（logo / 窗口与托盘图标 / 空状态插画）。**不做**情绪反应、不做桌宠 |
| 视觉基调 | 折中：外壳软萌、内容克制 |
| 拆分尺度 | 拆成多文件包，根目录保留薄入口 |
| 旧 PWA | 移入 `legacy/`，不删除 |
| 保底 | 先 `git init` 建立基线（已完成 `bdbf7ab`） |

## 1. 现状与问题定位

主程序 `piggyplan_desktop.py` 3185 行单文件，Tkinter + SQLite，职责分布：

- 26–64 Tcl 运行时修复；90–247 工具函数；248–790 `Database`；791–908 自测
- 909–1211 数据目录 / 单实例 / `WindowsIntegration`（托盘、全局热键）
- 1212–3152 `PiggyPlanApp`（外壳 + 6 个页面 + 6 个对话框 + 批量操作 + Toast）

用户反馈"边框难看、配色难看、字体难看、整体粗糙"。可量化的根因：

1. **对比度不达标**：`STRONG #D96288` 白底 3.47:1、`SUCCESS #55A781` 2.90:1、`WARNING #CB8750` 2.95:1、`TEXT_FAINT #B8A4AC` 2.35:1，却都被用在**文字**上。
2. **描边无层次**：边框出现在所有层级，导致没有视觉主次。
3. **小字号加粗**：8/9pt 大量 `bold`，CJK 笔画糊成一团。
4. **间距魔法数**：34 / 22 / 26 / 13 / 10 散落各处，无节奏。
5. **无组件层**：`tk.Button` / `tk.Frame` 在 60+ 处各自手写样式，改一处外观要改全文件。
6. **猪形象缺失**：`_pig_mark` 用 Canvas 几何图形拼出一张与品牌图无关的脸。

## 2. 目录结构

```
piggyplan/
  __init__.py
  constants.py     APP_NAME / APP_VERSION / HOTKEY_DEFAULT / DAY_FORMAT
  tokens.py        设计 token：色板、字号阶、间距阶、圆角阶、字族解析
  png.py           纯标准库 PNG 解码 / 编码 / 抠白底 / 双线性缩放 / 裁切
  assets.py        构建期生成的 base64 图像（运行时零外部文件依赖）
  util.py          日期 / 文本 / uid / 热键规范化 / 开机自启
  database.py      Database
  runtime/
    paths.py       app_data_dir / app_backup_dir / app_log_dir / log_event
    tcl.py         _prepare_tcl_runtime
    single_instance.py   SingleInstance / activate_existing_window
    windows_integration.py  托盘 / 全局热键 / 窗口消息
  ui/
    shape.py       round_rect / 双色环假抗锯齿 / 颜色混合
    widgets.py     Card / PillButton / Chip / HeartMark / SnoutBullet / Field / StatBlock / SegmentedControl / Switch
    mascot.py      PigMark（按用途提供尺寸档）
    scroll.py      ScrollArea
    dialog.py      Dialog 基类
    toast.py       show_toast
    menu.py        上下文菜单
  pages/           today / upcoming / all / goals / archive / search / rail / settings
  dialogs/         task / goal / filter / quick_add / goal_decision
  features/        batch（批量操作与撤销）/ tasks（单任务操作与撤销）
  app.py           PiggyPlanApp 外壳：窗口、侧边栏、头部、路由、渲染循环
  selftest.py      run_self_test / run_gui_smoke_test
piggyplan_desktop.py    薄入口（保持 .bat、开机自启注册表、exe 路径不变）
tools/build_assets.py   构建期资产生成
assets_src/piggy.png    猪形象原图（不参与运行时）
legacy/                 旧 PWA：app.js / styles.css / server.mjs / sw.js / manifest.json / index.html / icon.svg
```

`piggyplan_desktop.py` 与旧 PWA 之间没有代码耦合（桌面版不读取 `index.html`），因此 `legacy/` 搬迁只需同步 `package.json` 的 `web` 脚本路径与 README 说明。

### 2.1 页面为何用 Mixin 而不是函数 + 上下文对象

页面类以 Mixin 形式混入 `PiggyPlanApp`：

```python
class PiggyPlanApp(ArchivePageMixin, SettingsPageMixin, GoalsPageMixin,
                   AllPageMixin, UpcomingPageMixin, TodayPageMixin, tk.Tk): ...
```

**收益**：`self.` 调用点零改动，3000 行搬迁的回归风险降到最低；每个页面成为可独立阅读、独立编辑的文件。

**代价（明确承认）**：Mixin 之间仍通过 `self` 共享状态，这不是真正的模块隔离。退出坡道：日后若要把某页拆成独立进程/独立渲染器，只需把该 Mixin 的方法改成 `render(app, parent)` 并注入一个只读 view model——文件边界已经先划好，届时不必再拆一次。

**真正隔离的部分**是 `tokens.py` / `ui/` / `database.py` / `runtime/`：它们不依赖 `PiggyPlanApp`，可单独测试。

## 3. 视觉系统

### 3.1 取色来源

程序化统计 `assets_src/piggy.png` 色频：身体 `#F8C8D0`(14.0%)、腮红 `#F8C8C8`(3.6%)、心形 `#F86870`(1.3%)、描边纯黑、白底 65.7%。现有 pink 主题 accent `#F8CEDB` 与猪身体 `#F8C8D0` 基本同色，故**色相方向保留，改的是用法**。

### 3.2 强调色两级制（硬规则）

- **`accent`**（图形级，2.5–3:1）：色块、进度条、心形、选中底。**禁止**用于文字。
- **`accentInk`**（文字级，≥4.5:1，已对各主题 `soft` 底验算）：

| 主题 | accent | accentInk | vs 白 | vs soft |
|---|---|---|---|---|
| pink 小猪粉 | `#F8CEDB` | `#B8405F` | 5.33 | 4.69 |
| peach 蜜桃橘 | `#F9D3C5` | `#B4522F` | 5.01 | 4.51 |
| mint 薄荷绿 | `#C7E5DB` | `#2E7A68` | 5.12 | 4.66 |
| lavender 薰衣草 | `#DDD2EE` | `#6A4E9E` | 6.57 | 5.80 |

中性色修正：`TEXT #34272C`→`#2E2126`（15.4:1）；`TEXT_SOFT #806A72`→`#7A666D`（soft 上 4.37→4.67）；`TEXT_FAINT #B8A4AC`（2.35:1）**降级为仅装饰性大字号可用**，正文提示一律改用 `TEXT_SOFT`。

语义色同样拆两级：`HIGH #D95F73`→图形 `#F86870` / 文字 `#B8405F`；`SUCCESS`→图形 `#55A781` / 文字 `#2E7A68`；`WARNING`→图形 `#CB8750` / 文字 `#A85A22`。

### 3.3 字族与字号

启动时探测已安装字族，按优先级解析：`Noto Sans SC` → `Microsoft YaHei UI`。字族差异映射到角色，避免小字号加粗：

| 角色 | pt | Noto Sans SC | YaHei 回退 |
|---|---|---|---|
| display | 22 | Medium 500 | Bold |
| title | 13 | Medium 500 | Bold |
| body | 11 | Regular 400 | Regular |
| meta | 9 | Regular 400 | Regular |
| micro | 8 | Medium 500 | Bold |

规则：**≤9pt 不使用 Bold**（YaHei 回退时 micro 例外，因该字族无 Medium）。小字号的层级由颜色承担。

### 3.4 间距与圆角

- 间距（4 为基）：`4 8 12 16 24 32 48`
- 圆角：`chip 4 · 控件 10 · 卡片 14 · 胶囊 22`
- 自绘假抗锯齿的外圈两环各占 1px，故最小可用半径为 6。

### 3.5 签名元素（三处，均取自形象本身）

1. **心形 = 高优先级**：用 `#F86870` 实心心形替代现有红字"高"标签。既编码信息又是品牌。
2. **猪鼻 = 分节标记**：`section_title` 的方块 bullet 换成微缩猪鼻（椭圆 + 两孔），成为全应用统一标点。
3. **墨线只画在壳上**（本次唯一的美学冒险）：粗描边只出现在外壳——侧边栏卡片、对话框、空状态、Toast；内容区任务卡**零描边**，靠 `#FFFFFF` / `#FFF9F8` / `#FDECF1` 三级色阶分层。这条规则同时落实"外壳软萌、内容克制"，并直接治掉"边框无处不在"。

```
┌─ 壳：墨线描边 ─────┬─ 内容：无描边，靠色阶 ─────────
│ ▒▒ 猪鼻 日常       │  今天                    2 项  │
│ ▒▒ PIGGYPLAN      │  ┌──────────────────────────┐  │
│  ( ˘ᴗ˘ ) 新建待办  │  │ ○ 取快递        生活      │  │  ← 白底无框
│ ○ 今日清单    ●●●  │  ├──────────────────────────┤  │
│ ○ 之后安排         │  │ ♥ 写周报   工作 · 逾期 2天 │  │  ← 心形=高优先级
│ 本地优先 ▒墨线卡  │  └──────────────────────────┘  │
└───────────────────┴────────────────────────────────┘
```

## 4. 猪形象资产管线

`tools/build_assets.py`（构建期，纯标准库）读 `assets_src/piggy.png` → 抠白底（`min(r,g,b)` 在 232–250 之间做线性 alpha 渐变，避免硬边）→ 生成变体 → 写出 `piggyplan/assets.py`（base64 常量）与 `icon.ico`。运行时用 `tk.PhotoImage(data=base64)` 解码，Tk 8.6 原生支持 RGBA PNG 透明。

| 用途 | 尺寸 | 处理 |
|---|---|---|
| 侧边栏 logo | 40px 高 | 全身 |
| 窗口 / 任务栏图标 | 16/24/32/48 `.ico` | 全身 |
| 托盘图标 | 16px | **裁头部**（16px 全身会糊，原型已验证） |
| 空状态插画 | 120px | 全身，三处空状态共用 |
| 对话框角标 | 28px | 裁头部 |

已验证：抠底后在 `#FDECF1`、`#F8CEDB`、`#D96288` 三种底上均无白边残留。

## 5. 组件层 API

`ui/widgets.py` 的 `Card` 与 `PillButton` **保持与现有 `self.card()`(1783) 和 `self._button()`(1407) 兼容的签名**，使"换组件实现"与"改页面布局"成为两次独立提交。

| 组件 | 替代 | 关键能力 |
|---|---|---|
| `Card(tone, radius, padding)` → `.body` | `self.card()` | 真圆角、色调分层、`hover(bool)` |
| `PillButton(text, command, kind, size)` | `self._button()` | hover/press 变色、键盘 Return/Space 触发、焦点可见 |
| `Chip(kind, label)` | `self.badge()` | 分类 / 优先级 / 标签统一形态 |
| `HeartMark` / `SnoutBullet` | 红字"高"、方块 bullet | 品牌化语义标记 |
| `Field(label, hint, error)` | 对话框手写 label+Entry | 表单一致性 |
| `Dialog(title, subtitle)` → `.body/.footer` | 6 处复制粘贴的 Toplevel | 统一 Escape / 回车 / 错误位 |
| `ScrollArea` | `render` 手搭 Canvas+Scrollbar | 滚轮、边界 |

## 6. 文案

按"空态是行动的邀请"重写，存钱罐隐喻只用 2 处：

- `今天没有安排事项` → `今天还空着 · 放进第一件事`
- `数据只保存在本机 SQLite\n不联网，也能安心使用` → `你的事都装在这只猪身上，只写本机，不联网`

动词一致性：按钮"保存待办"→ Toast"待办已保存"（现状已是，保持）。

## 7. 实施阶段与回滚点

每阶段一次提交，且都必须 `--self-test` 通过 + 截图肉眼确认后才进入下一阶段。

| # | 阶段 | 回滚方式 |
|---|---|---|
| 1 | 建基线 | ✅ `bdbf7ab` |
| 2 | 机械拆分：`constants/util/database/runtime` 成模块，行为零变化 | revert 单次提交 |
| 3 | Mixin 拆分：pages / dialogs / features / ui 原语 | revert 单次提交 |
| 4 | 资产管线 + 猪形象接入 | revert 单次提交 |
| 5 | `tokens.py` + `ui/shape.py` + `ui/widgets.py`（签名兼容，实现替换） | revert 单次提交 |
| 6 | 外壳换组件：侧边栏 / 头部 / 对话框 / Toast / 空状态 + 墨线规则 | revert 单次提交 |
| 7 | 内容区换组件 + 心形优先级 + 猪鼻标记 + 对比度修正 | revert 单次提交 |
| 8 | 图标 / PyInstaller spec / README / 便携版说明 | revert 单次提交 |

阶段 2、3 是**纯搬迁**，验收标准是"截图与基线像素级一致"；视觉变化全部集中在 5–7。这样任何一步出现行为回归，都能立刻定位是搬迁引入的还是换肤引入的。

## 8. 验证策略

- `python piggyplan_desktop.py --self-test`：数据库层断言，每阶段必跑。
- `python piggyplan_desktop.py --gui-smoke`：GUI 冒烟，每阶段必跑。
- **截图对比**：脚本化启动应用、截取 6 个页面（今天/之后/全部/目标/归档/设置）+ 1 个对话框，阶段 2–3 与基线逐张比对；阶段 5–7 人工确认视觉改进落地且无布局破损。
- **对比度回归**：`tokens.py` 内置断言，任何 `*Ink` 色在其对应背景上 < 4.5:1 即 self-test 失败——把这条规则钉死在测试里，防止日后改主题时回退。
- 键盘可达性：Tab 顺序、`PillButton` 的 Return/Space、焦点可见；`reduce_motion` 设置项必须继续生效。

## 9. 明确不做

- 不新增功能（周/月视图、习惯打卡、番茄钟、提醒等一律不在本次范围）
- 不做性能专项（但若阶段 5–7 出现可感知卡顿，属本次必须解决）
- 不做深色模式（四套浅色主题保持四套）
- 不做猪的情绪反应 / 桌宠 / 拖拽互动
- 不引入任何第三方依赖
