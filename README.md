# 日常 · PiggyPlan

PiggyPlan 是一款可在 Windows 本机运行的个人待办与长期目标管理软件。主程序使用原生桌面窗口和 SQLite 数据库，不需要浏览器、账号、网络连接或后台数据库服务。

## 直接启动

双击项目目录中的 `启动 PiggyPlan.bat`。

已构建的绿色便携版位于 `dist\PiggyPlan`，也可以直接双击其中的
`PiggyPlan.exe`。便携版不需要安装 Python，不需要浏览器，也不会联网。

也可以在 PowerShell 中运行：

```powershell
python piggyplan_desktop.py
```

源码运行环境为 Windows 10/11 和 Python 3.10+；绿色便携版不需要 Python。
软件仅使用 Python 标准库，不需要执行 `pip install`。

首次启动为空白数据，不会自动写入示例任务。数据库默认保存在：

```text
%APPDATA%\PiggyPlan\piggyplan.db
```

每日快照位于 `%APPDATA%\PiggyPlan\backups`，最近保留 14 份；技术日志位于 `%APPDATA%\PiggyPlan\logs`，日志不记录任务标题或备注。

## 已实现

- 原生 Windows 桌面窗口、SQLite 本地持久化和单实例保护
- 今天 / 之后 / 全部，逾期不自动顺延，未安排不进入计划完成率
- 待办新增、编辑、完成、撤回、删除、右键操作、拖拽排序和批量修改
- 工作 / 生活分类，高 / 普通优先级，日期、标签、子步骤和任务模板
- 长期目标、自动进度、目标—待办联动、目标达成与恢复
- 列表 / 两栏看板、全局搜索、筛选、待办与目标归档
- 实际完成数量、有效计划、按计划日完成率和最近 7 天图表
- JSON 完整备份与恢复、CSV 历史导出、每日 SQLite 自动快照
- 四套浅色主题、窗口尺寸记忆、窄窗口隐藏概览栏、跨午夜刷新
- 系统托盘、关闭到托盘、开机自启和全局快捷添加
- 窗口内快捷键：`Ctrl + N`、`Ctrl + F`、`Ctrl + 1/2/3`

默认全局快捷键为 `Ctrl + Alt + T`。如果它被其他软件占用，设置页会明确显示冲突，可改为例如 `Ctrl + Alt + F12`。

## 验证

```powershell
python -m py_compile piggyplan_desktop.py
python piggyplan_desktop.py --self-test
python piggyplan_desktop.py --gui-smoke
```

也可以运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\verify.ps1
```

旧的浏览器/PWA实现仍保留作界面参考，需要时可用 `npm run web` 启动；正式本地桌面版入口是 `piggyplan_desktop.py`。
