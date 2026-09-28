/*
 * PiggyPlan - a dependency-free local-first prototype.
 *
 * The UI is intentionally kept separate from the business rules below so the
 * storage layer can later be replaced by a Tauri command + SQLite repository.
 */

const STORAGE_KEY = "piggyplan-state-v1";
const APP_VERSION = "0.1.0";
const DAY_MS = 24 * 60 * 60 * 1000;

const ICON_PATHS = {
  spark: '<path d="M12 2l1.45 5.55L19 9l-5.55 1.45L12 16l-1.45-5.55L5 9l5.55-1.45L12 2Z"/><path d="M19 15l.62 2.38L22 18l-2.38.62L19 21l-.62-2.38L16 18l2.38-.62L19 15Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  check: '<path d="m5 12 4.2 4.2L19.5 6"/>',
  calendar: '<rect x="3" y="4.5" width="18" height="17" rx="2"/><path d="M16 2.5v4M8 2.5v4M3 9h18"/>',
  search: '<circle cx="10.8" cy="10.8" r="6.7"/><path d="m16 16 4.5 4.5"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  chevronRight: '<path d="m9 5 7 7-7 7"/>',
  chevronDown: '<path d="m5 9 7 7 7-7"/>',
  arrowLeft: '<path d="m15 18-6-6 6-6M9 12h11"/>',
  arrowUpRight: '<path d="M7 17 17 7M8 7h9v9"/>',
  inbox: '<path d="M4 4.5h16v15H4z"/><path d="M4 14h4l1.6 2h4.8L16 14h4"/>',
  clock: '<circle cx="12" cy="12" r="8.8"/><path d="M12 7v5l3.2 2"/>',
  list: '<path d="M8 6h12M8 12h12M8 18h12"/><path d="M4.5 6h.01M4.5 12h.01M4.5 18h.01"/>',
  target: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.3"/><circle cx="12" cy="12" r="1"/>',
  archive: '<path d="M4 7h16v13H4zM3 4h18v3H3z"/><path d="M9 12h6"/>',
  settings: '<path d="M12 8.2a3.8 3.8 0 1 0 0 7.6 3.8 3.8 0 0 0 0-7.6Z"/><path d="m19.4 15 .1.1 1.1.9-1.8 3.1-1.3-.6-.1-.1a8 8 0 0 1-1.8 1l-.1.2-.2 1.4h-3.6l-.2-1.4-.1-.2a8 8 0 0 1-1.8-1l-.1.1-1.3.6-1.8-3.1 1.1-.9.1-.1a7.5 7.5 0 0 1 0-2l-.1-.1-1.1-.9 1.8-3.1 1.3.6.1.1a8 8 0 0 1 1.8-1l.1-.2.2-1.4h3.6l.2 1.4.1.2a8 8 0 0 1 1.8 1l.1-.1 1.3-.6 1.8 3.1-1.1.9-.1.1a7.5 7.5 0 0 1 0 2Z"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  edit: '<path d="m4 16.5-.7 3.7 3.7-.7L18.7 7.8a2.6 2.6 0 0 0-3.7-3.7L4 16.5Z"/><path d="m13.5 5.5 3.7 3.7"/>',
  trash: '<path d="M4 7h16M10 11v5M14 11v5M6.5 7l.8 13h9.4l.8-13M9 7l.6-3h4.8l.6 3"/>',
  undo: '<path d="M9 7 4 12l5 5"/><path d="M4 12h10a5 5 0 0 1 0 10h-1"/>',
  filter: '<path d="M4 5h16l-6.2 7v5l-3.6 2v-7L4 5Z"/>',
  board: '<rect x="4" y="4" width="6" height="16" rx="1"/><rect x="14" y="4" width="6" height="10" rx="1"/>',
  drag: '<path d="M9 5h.01M9 12h.01M9 19h.01M15 5h.01M15 12h.01M15 19h.01"/>',
  note: '<path d="M5 3.5h10l4 4v13H5z"/><path d="M15 3.5v4h4M8 12h8M8 16h6"/>',
  tag: '<path d="m4 5 .5 7.3L13 21l7.5-7.5L12 4.5 4 5Z"/><circle cx="8.5" cy="8.5" r="1"/>',
  link: '<path d="M9.5 14.5 8 16a4 4 0 0 1-5.7-5.7l3-3A4 4 0 0 1 11 7M14.5 9.5 16 8a4 4 0 1 1 5.7 5.7l-3 3A4 4 0 0 1 13 17"/><path d="m8 12 8-2"/>',
  unlink: '<path d="m3 3 18 18M9.5 14.5 8 16a4 4 0 0 1-5.7-5.7l3-3A4 4 0 0 1 9 6.8M14.5 9.5 16 8a4 4 0 0 1 5.1.4"/>',
  steps: '<path d="M9 6h11M9 12h11M9 18h11"/><path d="m4 6 .8.8L6.5 5M4 12l.8.8 1.7-1.8M4 18l.8.8 1.7-1.8"/>',
  keyboard: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M6 10h.01M9 10h.01M12 10h.01M15 10h.01M18 10h.01M6 14h12"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M4 20h16"/>',
  upload: '<path d="M12 15V3M7 8l5-5 5 5M4 20h16"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  sparkles: '<path d="M12 3 13.4 8.6 19 10l-5.6 1.4L12 17l-1.4-5.6L5 10l5.6-1.4L12 3ZM19 16l.7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z"/>',
  alert: '<path d="M12 4 21 20H3L12 4Z"/><path d="M12 10v4M12 17h.01"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m7.5 12 3 3 6-6"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-14.6-4L4 9"/><path d="M4 4v5h5M4 13a8 8 0 0 0 14.6 4L20 15"/><path d="M20 20v-5h-5"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5"/>',
  leaf: '<path d="M20 4C11 4 5 7.4 5 13c0 3 2.2 5 5 5 5.7 0 8.8-6 10-14Z"/><path d="M4 21c2.5-4.7 6.1-7.5 11-9.5"/>',
  pig: '<path d="M7.5 8.5 6 4.5l4.4 2.3M16.5 8.5 18 4.5l-4.4 2.3"/><circle cx="12" cy="13" r="7.5"/><circle cx="9.5" cy="11.5" r=".7" fill="currentColor"/><circle cx="14.5" cy="11.5" r=".7" fill="currentColor"/><ellipse cx="12" cy="15.5" rx="3.3" ry="2.3"/><path d="M10.8 15.5h.01M13.2 15.5h.01"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.8 9a2.4 2.4 0 1 1 3.7 2c-.9.6-1.5 1-1.5 2.2M12 16h.01"/>',
  crosshair: '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v3M12 17.5v3M3.5 12h3M17.5 12h3"/>',
  book: '<path d="M4 5.5a2 2 0 0 1 2-2h5v16H6a2 2 0 0 0-2 2zM20 5.5a2 2 0 0 0-2-2h-5v16h5a2 2 0 0 1 2 2z"/>',
  home: '<path d="m4 11 8-7 8 7"/><path d="M6 10v10h12V10M10 20v-6h4v6"/>',
};

function icon(name, className = "") {
  return `<svg class="icon ${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_PATHS[name] || ICON_PATHS.spark}</svg>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function makeId(prefix = "id") {
  if (globalThis.crypto?.randomUUID) return `${prefix}-${crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function nowIso() {
  return new Date().toISOString();
}

function dateKey(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function localDate(key) {
  if (!key) return null;
  const [year, month, day] = key.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function offsetDate(days, from = new Date()) {
  const result = new Date(from.getFullYear(), from.getMonth(), from.getDate());
  result.setDate(result.getDate() + days);
  return dateKey(result);
}

function dateDistance(key, reference = dateKey()) {
  if (!key) return null;
  const a = localDate(key);
  const b = localDate(reference);
  return Math.round((a - b) / DAY_MS);
}

function formatDate(key, long = false) {
  if (!key) return "未安排";
  const value = localDate(key);
  if (long) {
    const weekdays = ["日", "一", "二", "三", "四", "五", "六"];
    return `${value.getFullYear()}年${value.getMonth() + 1}月${value.getDate()}日 周${weekdays[value.getDay()]}`;
  }
  return `${value.getMonth() + 1}月${value.getDate()}日`;
}

function relativeDate(key) {
  if (!key) return "未安排";
  const distance = dateDistance(key);
  if (distance === 0) return "今天";
  if (distance === 1) return "明天";
  if (distance === -1) return "昨天";
  return formatDate(key);
}

function dateTone(key) {
  if (!key) return "";
  const distance = dateDistance(key);
  if (distance < 0) return "overdue";
  if (distance === 0) return "today";
  if (distance === 1) return "soon";
  return "";
}

function startOfWeek(key = dateKey()) {
  const value = localDate(key);
  const day = value.getDay() || 7;
  value.setDate(value.getDate() - day + 1);
  return dateKey(value);
}

function endOfWeek(key = dateKey()) {
  return offsetDate(6, localDate(startOfWeek(key)));
}

function formatCount(value) {
  return new Intl.NumberFormat("zh-CN").format(value);
}

function categoryLabel(category) {
  return category === "life" ? "生活" : "工作";
}

function priorityLabel(priority) {
  return priority === "high" ? "高优先级" : "普通优先级";
}

function statusLabel(status) {
  return status === "completed" ? "已完成" : status === "achieved" ? "已达成" : "待办";
}

function todayText() {
  return formatDate(dateKey(), true);
}

function createPlanRecord(plannedDate, assignedAt = nowIso()) {
  return {
    id: makeId("plan"),
    plannedDate,
    assignedAt,
    supersededAt: null,
    becameDue: false,
    fulfilledOnTime: null,
    cancelledBeforeDue: false
  };
}

function makeTask(input = {}) {
  const createdAt = input.createdAt || nowIso();
  const plannedDate = input.plannedDate || null;
  const task = {
    id: input.id || makeId("task"),
    title: input.title || "",
    note: input.note || "",
    category: input.category === "life" ? "life" : "work",
    priority: input.priority === "high" ? "high" : "normal",
    plannedDate,
    status: input.status || "todo",
    goalId: input.goalId || null,
    sortRank: Number.isFinite(input.sortRank) ? input.sortRank : Date.now(),
    createdAt,
    updatedAt: input.updatedAt || createdAt,
    completedAt: input.completedAt || null,
    deletedAt: input.deletedAt || null,
    tags: Array.isArray(input.tags) ? input.tags.filter(Boolean) : [],
    subtasks: Array.isArray(input.subtasks) ? input.subtasks.map((step, index) => ({
      id: step.id || makeId("step"),
      title: step.title || "",
      completed: Boolean(step.completed),
      sortRank: Number.isFinite(step.sortRank) ? step.sortRank : index,
      createdAt: step.createdAt || createdAt
    })).filter((step) => step.title.trim()) : [],
    planHistory: Array.isArray(input.planHistory) ? input.planHistory : (plannedDate ? [createPlanRecord(plannedDate, createdAt)] : [])
  };
  return task;
}

function makeGoal(input = {}) {
  const createdAt = input.createdAt || nowIso();
  return {
    id: input.id || makeId("goal"),
    title: input.title || "",
    note: input.note || "",
    category: input.category === "life" ? "life" : "work",
    priority: input.priority === "high" ? "high" : "normal",
    plannedFinishDate: input.plannedFinishDate || null,
    status: input.status === "achieved" ? "achieved" : "active",
    sortRank: Number.isFinite(input.sortRank) ? input.sortRank : Date.now(),
    createdAt,
    achievedAt: input.achievedAt || null
  };
}

function createDemoState() {
  const productGoal = makeGoal({
    id: "goal-product-review",
    title: "完成产品季度复盘",
    note: "把本季度的用户反馈、数据和下一步行动整理成一份能推动决策的复盘。",
    category: "work",
    priority: "high",
    plannedFinishDate: offsetDate(24),
    sortRank: 1
  });
  const lifeGoal = makeGoal({
    id: "goal-movement",
    title: "建立每周运动习惯",
    note: "让运动成为轻量、可持续的生活节奏。",
    category: "life",
    priority: "normal",
    plannedFinishDate: offsetDate(48),
    sortRank: 2
  });
  const createSeedTask = (input) => makeTask(input);
  const tasks = [
    createSeedTask({ id: "task-meeting", title: "整理上周项目会议结论", note: "把决策、负责人和下一步行动补进项目文档。", category: "work", priority: "high", plannedDate: offsetDate(-2), goalId: productGoal.id, sortRank: 1, tags: ["项目", "复盘"] }),
    createSeedTask({ id: "task-feedback", title: "完成用户反馈整理", note: "已提炼出三条需要进入下个版本的产品机会。", category: "work", priority: "normal", plannedDate: offsetDate(-1), goalId: productGoal.id, status: "completed", completedAt: new Date(new Date().setDate(new Date().getDate() - 1)).toISOString(), sortRank: 2, tags: ["用户", "复盘"] }),
    createSeedTask({ id: "task-email", title: "给客户发出版本确认邮件", note: "确认体验优化清单和本周交付范围。", category: "work", priority: "high", plannedDate: dateKey(), goalId: productGoal.id, sortRank: 3, tags: ["沟通"] }),
    createSeedTask({ id: "task-outline", title: "补齐复盘分享的大纲", note: "先完成结构，不追求一次写完。", category: "work", priority: "high", plannedDate: dateKey(), goalId: productGoal.id, sortRank: 4, tags: ["输出"] }),
    createSeedTask({ id: "task-run", title: "完成 30 分钟轻松跑", category: "life", priority: "normal", plannedDate: dateKey(), goalId: lifeGoal.id, sortRank: 5, tags: ["健康"] }),
    createSeedTask({ id: "task-demo", title: "准备周五产品演示", note: "挑 3 个最能说明变化的场景，配上前后对比。", category: "work", priority: "high", plannedDate: offsetDate(2), goalId: productGoal.id, sortRank: 6, tags: ["演示"] }),
    createSeedTask({ id: "task-stretch", title: "安排本周下一次拉伸时间", category: "life", priority: "normal", plannedDate: offsetDate(4), goalId: lifeGoal.id, sortRank: 7, tags: ["健康"] }),
    createSeedTask({ id: "task-storage", title: "购买新的收纳盒", note: "量一下书桌抽屉，再决定尺寸。", category: "life", priority: "normal", plannedDate: null, sortRank: 8, tags: ["采购"] }),
    createSeedTask({ id: "task-archive", title: "发布新版帮助中心首页", category: "work", priority: "normal", plannedDate: offsetDate(-8), status: "completed", completedAt: new Date(new Date().setDate(new Date().getDate() - 6)).toISOString(), sortRank: 9, tags: ["发布"] })
  ];
  tasks.forEach((task) => {
    task.planHistory.forEach((record) => {
      const completedDate = task.completedAt ? dateKey(new Date(task.completedAt)) : null;
      if (completedDate && record.plannedDate === completedDate) {
        record.becameDue = true;
        record.fulfilledOnTime = true;
      } else if (completedDate && record.plannedDate < completedDate) {
        record.becameDue = true;
        record.fulfilledOnTime = false;
      }
    });
  });
  return {
    version: 1,
    tasks,
    goals: [productGoal, lifeGoal],
    templates: [
      {
        id: "template-weekly-review",
        title: "每周复盘",
        note: "回顾本周完成情况，留下下周最重要的三个动作。",
        category: "work",
        priority: "normal",
        tags: ["复盘"],
        subtasks: ["回顾已完成事项", "记录阻塞点", "选出下周三个动作"],
        createdAt: nowIso()
      }
    ],
    settings: {
      theme: "blue",
      defaultCategory: "work",
      startupPage: "today",
      startMinimized: false,
      startupEnabled: false,
      closeToTray: true,
      reduceMotion: false,
      shortcut: "Ctrl + Alt + T"
    },
    meta: { demo: true, lastBackupDate: null }
  };
}

function createEmptyState() {
  const state = createDemoState();
  state.tasks = [];
  state.goals = [];
  state.templates = [];
  state.meta.demo = false;
  return state;
}

function normalizeState(raw) {
  const source = raw && typeof raw === "object" ? raw : createDemoState();
  const normalized = {
    version: 1,
    tasks: Array.isArray(source.tasks) ? source.tasks.map(makeTask) : [],
    goals: Array.isArray(source.goals) ? source.goals.map(makeGoal) : [],
    templates: Array.isArray(source.templates) ? source.templates.map((template) => ({
      id: template.id || makeId("template"),
      title: template.title || "未命名模板",
      note: template.note || "",
      category: template.category === "life" ? "life" : "work",
      priority: template.priority === "high" ? "high" : "normal",
      tags: Array.isArray(template.tags) ? template.tags.filter(Boolean) : [],
      subtasks: Array.isArray(template.subtasks) ? template.subtasks.filter(Boolean) : [],
      createdAt: template.createdAt || nowIso()
    })) : [],
    settings: {
      theme: ["blue", "green", "orange", "purple"].includes(source.settings?.theme) ? source.settings.theme : "blue",
      defaultCategory: source.settings?.defaultCategory === "life" ? "life" : "work",
      startupPage: ["today", "upcoming", "all"].includes(source.settings?.startupPage) ? source.settings.startupPage : "today",
      startMinimized: Boolean(source.settings?.startMinimized),
      startupEnabled: Boolean(source.settings?.startupEnabled),
      closeToTray: source.settings?.closeToTray !== false,
      reduceMotion: Boolean(source.settings?.reduceMotion),
      shortcut: source.settings?.shortcut || "Ctrl + Alt + T"
    },
    meta: { demo: Boolean(source.meta?.demo), lastBackupDate: source.meta?.lastBackupDate || null }
  };
  normalized.tasks.forEach((task) => {
    if (!task.planHistory.length && task.plannedDate) task.planHistory.push(createPlanRecord(task.plannedDate, task.createdAt));
    if (task.status === "completed" && !task.completedAt) task.completedAt = task.updatedAt;
  });
  return normalized;
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? normalizeState(JSON.parse(raw)) : createDemoState();
  } catch {
    return createDemoState();
  }
}

let state = loadState();
state.ui = {
  view: state.settings.startupPage || "today",
  selectedGoalId: null,
  drawerTaskId: null,
  modal: null,
  searchQuery: "",
  filterOpen: false,
  filters: { category: "all", priority: "all", goal: "all", status: "todo", tag: "all" },
  goalsStatus: "active",
  goalsCategory: "all",
  archiveTab: "tasks",
  archiveCategory: "all",
  archiveQuery: "",
  allViewMode: "list",
  goalViewMode: "list",
  completedOpen: false,
  selectedTaskIds: [],
  contextMenu: null,
  sidebarOpen: false,
  mobileMenuOpen: false
};

const undoActions = new Map();
let toastSequence = 0;

function persist() {
  try {
    const serializable = clone(state);
    delete serializable.ui;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serializable));
  } catch {
    // Storage can be unavailable in strict/private browser contexts. The UI
    // remains usable for the current session.
  }
}

function getTask(id) {
  return state.tasks.find((task) => task.id === id);
}

function getGoal(id) {
  return state.goals.find((goal) => goal.id === id);
}

function visibleTasks({ includeCompleted = false, includeDeleted = false } = {}) {
  return state.tasks.filter((task) => {
    if (!includeDeleted && task.status === "deleted") return false;
    if (!includeCompleted && task.status !== "todo") return false;
    return true;
  });
}

function tasksForGoal(goalId, includeCompleted = true) {
  return state.tasks.filter((task) => task.goalId === goalId && task.status !== "deleted" && (includeCompleted || task.status === "todo"));
}

function goalStats(goal) {
  const tasks = tasksForGoal(goal.id, true);
  const completed = tasks.filter((task) => task.status === "completed").length;
  const total = tasks.length;
  const progress = total === 0 ? (goal.status === "achieved" ? 100 : 0) : Math.round((completed / total) * 100);
  return { total, completed, remaining: total - completed, progress };
}

function activeCount() {
  return visibleTasks().length;
}

function todayTasks() {
  return visibleTasks().filter((task) => task.plannedDate === dateKey());
}

function overdueTasks() {
  return visibleTasks().filter((task) => task.plannedDate && task.plannedDate < dateKey());
}

function completedOn(day) {
  return state.tasks.filter((task) => task.status === "completed" && task.completedAt && dateKey(new Date(task.completedAt)) === day);
}

function taskSort(a, b, mode = "default") {
  if (mode === "upcoming") {
    const aDate = a.plannedDate || "9999-99-99";
    const bDate = b.plannedDate || "9999-99-99";
    if (aDate !== bDate) return aDate.localeCompare(bDate);
  }
  if (a.priority !== b.priority) return a.priority === "high" ? -1 : 1;
  if (mode === "all") {
    const stateRank = (task) => {
      if (!task.plannedDate) return 3;
      if (task.plannedDate < dateKey()) return 0;
      if (task.plannedDate === dateKey()) return 1;
      return 2;
    };
    const rankDiff = stateRank(a) - stateRank(b);
    if (rankDiff !== 0) return rankDiff;
    if (a.plannedDate && b.plannedDate && a.plannedDate !== b.plannedDate) return a.plannedDate.localeCompare(b.plannedDate);
  }
  if (a.plannedDate && b.plannedDate && a.plannedDate !== b.plannedDate && mode !== "all") return a.plannedDate.localeCompare(b.plannedDate);
  if (a.plannedDate && !b.plannedDate) return -1;
  if (!a.plannedDate && b.plannedDate) return 1;
  return (a.sortRank - b.sortRank) || a.createdAt.localeCompare(b.createdAt);
}

function goalSort(a, b) {
  if (a.priority !== b.priority) return a.priority === "high" ? -1 : 1;
  return (a.sortRank - b.sortRank) || a.createdAt.localeCompare(b.createdAt);
}

function currentPlanHistory(task) {
  return [...(task.planHistory || [])].reverse().find((record) => record.plannedDate === task.plannedDate && !record.supersededAt);
}

function setTaskPlanDate(task, plannedDate) {
  const nextDate = plannedDate || null;
  if (task.plannedDate === nextDate) return;
  const current = currentPlanHistory(task);
  if (current) {
    const due = current.plannedDate <= dateKey();
    current.supersededAt = nowIso();
    current.becameDue = due;
    current.cancelledBeforeDue = !due;
    if (due && current.fulfilledOnTime === null) current.fulfilledOnTime = false;
  }
  task.plannedDate = nextDate;
  if (nextDate) task.planHistory.push(createPlanRecord(nextDate));
  task.updatedAt = nowIso();
}

function markPlanCompletion(task) {
  if (!task.completedAt) return;
  const completedDate = dateKey(new Date(task.completedAt));
  task.planHistory.forEach((record) => {
    if (record.cancelledBeforeDue) return;
    if (record.plannedDate === completedDate) {
      record.becameDue = true;
      record.fulfilledOnTime = true;
    } else if (record.plannedDate < completedDate) {
      record.becameDue = true;
      record.fulfilledOnTime = false;
    } else if (record.plannedDate > completedDate && record.fulfilledOnTime === null) {
      record.fulfilledOnTime = false;
    }
  });
}

function toggleTask(id) {
  const task = getTask(id);
  if (!task || task.status === "deleted") return;
  const snapshot = clone(task);
  if (task.status === "completed") {
    task.status = "todo";
    task.completedAt = null;
    task.updatedAt = nowIso();
    task.planHistory.forEach((record) => {
      if (record.fulfilledOnTime === true && record.plannedDate >= dateKey()) record.fulfilledOnTime = null;
    });
    pushToast("已撤销完成", "撤回", () => restoreTask(id, snapshot));
  } else {
    task.status = "completed";
    task.completedAt = nowIso();
    task.updatedAt = nowIso();
    markPlanCompletion(task);
    pushToast(`已完成「${task.title}」`, "撤回", () => restoreTask(id, snapshot));
  }
  state.ui.selectedTaskIds = state.ui.selectedTaskIds.filter((selectedId) => selectedId !== id);
  persist();
  render();
}

function restoreTask(id, snapshot) {
  const index = state.tasks.findIndex((task) => task.id === id);
  if (index === -1) return;
  state.tasks[index] = clone(snapshot);
  persist();
  render();
  pushToast("已恢复上一步操作", null);
}

function deleteTask(id) {
  const task = getTask(id);
  if (!task || task.status === "deleted") return;
  const snapshot = clone(task);
  task.status = "deleted";
  task.deletedAt = nowIso();
  task.updatedAt = nowIso();
  const current = currentPlanHistory(task);
  if (current && current.plannedDate > dateKey()) {
    current.cancelledBeforeDue = true;
    current.supersededAt = nowIso();
  }
  state.ui.selectedTaskIds = state.ui.selectedTaskIds.filter((selectedId) => selectedId !== id);
  persist();
  render();
  pushToast(`已移除「${task.title}」`, "撤回", () => restoreTask(id, snapshot));
}

function updateTask(task, changes) {
  Object.entries(changes).forEach(([key, value]) => {
    if (key === "plannedDate") setTaskPlanDate(task, value);
    else if (key in task) task[key] = value;
  });
  task.updatedAt = nowIso();
  persist();
  render();
}

function actualCompletionCount(start, end) {
  return state.tasks.filter((task) => {
    if (task.status !== "completed" || !task.completedAt) return false;
    const day = dateKey(new Date(task.completedAt));
    return day >= start && day <= end;
  }).length;
}

function validPlanRecords(start, end) {
  const records = [];
  state.tasks.forEach((task) => {
    (task.planHistory || []).forEach((record) => {
      if (!record.plannedDate || record.plannedDate < start || record.plannedDate > end || record.cancelledBeforeDue) return;
      records.push({ task, record });
    });
  });
  return records;
}

function planStats(start = startOfWeek(), end = endOfWeek()) {
  const records = validPlanRecords(start, end);
  const valid = records.filter(({ record }) => {
    if (record.fulfilledOnTime !== null) return true;
    return record.plannedDate <= dateKey();
  });
  const onTime = valid.filter(({ record }) => record.fulfilledOnTime === true).length;
  return { total: valid.length, onTime, rate: valid.length ? Math.round((onTime / valid.length) * 100) : 0 };
}

function lastSevenDays() {
  return Array.from({ length: 7 }, (_, index) => {
    const day = offsetDate(index - 6);
    const label = index === 6 ? "今" : `${localDate(day).getMonth() + 1}/${localDate(day).getDate()}`;
    const actual = actualCompletionCount(day, day);
    const plan = planStats(day, day);
    return { day, label, actual, rate: plan.total ? plan.rate : null };
  });
}

function saveTemplate(task) {
  const template = {
    id: makeId("template"),
    title: task.title,
    note: task.note,
    category: task.category,
    priority: task.priority,
    tags: [...task.tags],
    subtasks: task.subtasks.map((step) => step.title),
    createdAt: nowIso()
  };
  state.templates.unshift(template);
  persist();
  render();
  pushToast("已保存为任务模板", null);
}

function deleteTemplate(id) {
  state.templates = state.templates.filter((template) => template.id !== id);
  persist();
  render();
  pushToast("模板已删除", null);
}

function pushToast(message, actionLabel = null, action = null, type = "success") {
  const id = `toast-${++toastSequence}`;
  if (action) undoActions.set(id, action);
  state.ui.toasts = [...(state.ui.toasts || []), { id, message, actionLabel, type }].slice(-4);
  render();
  window.setTimeout(() => {
    state.ui.toasts = (state.ui.toasts || []).filter((toast) => toast.id !== id);
    undoActions.delete(id);
    render();
  }, 5200);
}

function runUndo(id) {
  const action = undoActions.get(id);
  undoActions.delete(id);
  state.ui.toasts = (state.ui.toasts || []).filter((toast) => toast.id !== id);
  if (action) action();
  else render();
}

function navigate(view) {
  state.ui.view = view;
  state.ui.searchQuery = "";
  state.ui.selectedGoalId = null;
  state.ui.drawerTaskId = null;
  state.ui.modal = null;
  state.ui.contextMenu = null;
  state.ui.selectedTaskIds = [];
  state.ui.sidebarOpen = false;
  state.ui.mobileMenuOpen = false;
  render();
}

function openTaskDrawer(id) {
  if (!getTask(id)) return;
  state.ui.drawerTaskId = id;
  state.ui.contextMenu = null;
  render();
}

function closeOverlays() {
  state.ui.modal = null;
  state.ui.drawerTaskId = null;
  state.ui.contextMenu = null;
  state.ui.sidebarOpen = false;
  render();
}

function openTaskModal(taskId = null, options = {}) {
  const task = taskId ? getTask(taskId) : null;
  state.ui.modal = {
    type: "task",
    taskId,
    quick: Boolean(options.quick),
    presetDate: options.presetDate !== undefined ? options.presetDate : (state.ui.view === "today" ? dateKey() : null),
    goalId: options.goalId || task?.goalId || null,
    templateId: options.templateId || null,
    quickPriority: options.quickPriority || task?.priority || "normal",
    quickCategory: options.quickCategory || task?.category || state.settings.defaultCategory
  };
  state.ui.contextMenu = null;
  state.ui.drawerTaskId = null;
  render();
  window.setTimeout(() => {
    const input = document.querySelector(state.ui.modal?.quick ? ".quick-add-input" : ".title-field-input");
    input?.focus();
  }, 0);
}

function openGoalModal(goalId = null) {
  state.ui.modal = { type: "goal", goalId };
  state.ui.contextMenu = null;
  render();
  window.setTimeout(() => document.querySelector(".goal-title-input")?.focus(), 0);
}

function openBatchModal(operation) {
  state.ui.modal = { type: "batch", operation };
  render();
}

function openGoalAchieveModal(goalId) {
  state.ui.modal = { type: "goal-achieve", goalId, option: "detach" };
  render();
}

function openGoalDeleteModal(goalId) {
  state.ui.modal = { type: "goal-delete", goalId, option: "detach" };
  render();
}

function achieveGoal(goalId, option = "detach") {
  const goal = getGoal(goalId);
  if (!goal) return;
  const related = tasksForGoal(goalId, false);
  if (option === "detach") {
    related.forEach((task) => {
      task.goalId = null;
      task.updatedAt = nowIso();
    });
  } else if (option === "complete") {
    related.forEach((task) => {
      task.status = "completed";
      task.completedAt = nowIso();
      task.updatedAt = nowIso();
      markPlanCompletion(task);
    });
  } else if (option === "delete") {
    related.forEach((task) => {
      task.status = "deleted";
      task.deletedAt = nowIso();
      task.updatedAt = nowIso();
    });
  }
  goal.status = "achieved";
  goal.achievedAt = nowIso();
  state.ui.modal = null;
  persist();
  render();
  pushToast(`目标「${goal.title}」已达成`, null);
}

function restoreGoal(goalId) {
  const goal = getGoal(goalId);
  if (!goal) return;
  goal.status = "active";
  goal.achievedAt = null;
  persist();
  render();
  pushToast("目标已恢复为进行中", null);
}

function deleteGoal(goalId, option = "detach") {
  const goal = getGoal(goalId);
  if (!goal) return;
  const related = tasksForGoal(goalId, true);
  if (option === "detach") related.forEach((task) => { task.goalId = null; task.updatedAt = nowIso(); });
  if (option === "delete") related.forEach((task) => {
    if (task.status === "todo") {
      task.status = "deleted";
      task.deletedAt = nowIso();
    } else {
      task.goalId = null;
    }
    task.updatedAt = nowIso();
  });
  state.goals = state.goals.filter((item) => item.id !== goalId);
  state.ui.selectedGoalId = null;
  state.ui.modal = null;
  persist();
  render();
  pushToast(`目标「${goal.title}」已删除`, null, null, "warning");
}

function filterTaskList(tasks, filters = state.ui.filters) {
  return tasks.filter((task) => {
    if (filters.category !== "all" && task.category !== filters.category) return false;
    if (filters.priority !== "all" && task.priority !== filters.priority) return false;
    if (filters.goal === "linked" && !task.goalId) return false;
    if (filters.goal === "standalone" && task.goalId) return false;
    if (filters.status === "todo" && task.status !== "todo") return false;
    if (filters.status === "completed" && task.status !== "completed") return false;
    if (filters.tag !== "all" && !task.tags.includes(filters.tag)) return false;
    return true;
  });
}

function allTags() {
  return [...new Set(state.tasks.flatMap((task) => task.tags))].sort((a, b) => a.localeCompare(b, "zh-CN"));
}

function searchData(query) {
  const needle = query.trim().toLocaleLowerCase();
  if (!needle) return { tasks: [], goals: [] };
  const tasks = state.tasks.filter((task) => {
    if (task.status === "deleted") return false;
    const goal = getGoal(task.goalId);
    const text = [task.title, task.note, ...task.tags, goal?.title || ""].join(" ").toLocaleLowerCase();
    return text.includes(needle);
  });
  const goals = state.goals.filter((goal) => [goal.title, goal.note, categoryLabel(goal.category)].join(" ").toLocaleLowerCase().includes(needle));
  return { tasks, goals };
}

function render() {
  document.documentElement.dataset.theme = state.settings.theme;
  document.documentElement.classList.toggle("reduce-motion", state.settings.reduceMotion);
  const root = document.querySelector("#app");
  if (!root) return;
  const showRail = !state.ui.selectedGoalId && !state.ui.searchQuery.trim() && ["today", "upcoming", "all"].includes(state.ui.view);
  const page = state.ui.selectedGoalId ? renderGoalDetail() : state.ui.searchQuery.trim() ? renderSearchPage() : renderView();
  root.innerHTML = `
    <div class="app-shell">
      ${renderSidebar()}
      <main class="main-shell">
        ${renderTopbar()}
        <div class="content-grid ${showRail ? "" : "single-column"}">
          <section class="primary-content">${page}</section>
          ${showRail ? `<aside class="right-rail">${renderRightRail()}</aside>` : ""}
        </div>
      </main>
      ${renderModal()}
      ${renderDrawer()}
      ${renderContextMenu()}
      ${renderToasts()}
    </div>`;
  bindDynamicFocus();
}

function renderSidebar() {
  const currentView = state.ui.selectedGoalId ? "goals" : state.ui.searchQuery.trim() ? "search" : state.ui.view;
  const todayRemaining = todayTasks().length;
  const overdue = overdueTasks().length;
  const navItem = (view, label, iconName, count = null) => `
    <button class="nav-item ${currentView === view ? "active" : ""}" data-action="navigate" data-view="${view}" aria-current="${currentView === view ? "page" : "false"}">
      <span class="nav-icon">${icon(iconName)}</span><span class="nav-label">${label}</span>${count !== null ? `<span class="nav-count">${count}</span>` : ""}
    </button>`;
  return `
    <aside class="sidebar ${state.ui.sidebarOpen ? "open" : ""}">
      <div class="brand">
        <span class="brand-mark">${icon("pig")}</span>
        <div><div class="brand-name">日常</div><div class="brand-subtitle">PIGGYPLAN</div></div>
      </div>
      <button class="sidebar-new" data-action="open-new-task">${icon("plus")}<span>新建待办</span><span class="spacer"></span><kbd>Ctrl N</kbd></button>
      <nav class="nav-list" aria-label="主导航">
        ${navItem("today", "今天", "sun", todayRemaining)}
        ${navItem("upcoming", "之后", "clock")}
        ${navItem("all", "全部", "inbox", activeCount())}
        <div class="nav-separator"></div>
        ${navItem("goals", "长期目标", "target", state.goals.filter((goal) => goal.status === "active").length)}
        ${navItem("archive", "归档", "archive")}
        <div class="nav-separator"></div>
        ${navItem("settings", "设置", "settings")}
      </nav>
      <div class="sidebar-footer">
        <div class="sidebar-note">${icon("sparkles")}<strong>${overdue ? `有 ${overdue} 项逾期` : "节奏保持得不错"}</strong><span>${overdue ? "今天先看清楚，再决定下一步。" : "记录要快，查看要清楚。"}</span></div>
        <div class="faint" style="margin: 12px 10px 0; font-size: 10px;">本地优先 · 无强提醒 · v${APP_VERSION}</div>
      </div>
    </aside>`;
}

function pageTitle() {
  if (state.ui.selectedGoalId) return "目标详情";
  if (state.ui.searchQuery.trim()) return "搜索";
  return { today: "今天", upcoming: "之后", all: "全部", goals: "长期目标", archive: "归档", settings: "设置" }[state.ui.view] || "今天";
}

function pageCaption() {
  if (state.ui.selectedGoalId) return "把目标落到每一个可以执行的动作上";
  if (state.ui.searchQuery.trim()) return `正在查找「${state.ui.searchQuery.trim()}」`;
  return { today: todayText(), upcoming: "把未来安排看得清楚", all: "所有未完成事项的全局视图", goals: "让长期愿望有清晰的下一步", archive: "回看已经完成的事情", settings: "让日常工作方式更贴合你" }[state.ui.view] || todayText();
}

function renderTopbar() {
  return `
    <header class="topbar">
      <button class="mobile-menu" data-action="toggle-sidebar" aria-label="打开导航">${icon("menu")}</button>
      <div class="topbar-title-wrap"><h1 class="topbar-title">${pageTitle()}</h1><div class="topbar-caption">${pageCaption()}</div></div>
      <label class="search-box"><span class="sr-only">搜索待办或目标</span>${icon("search")}<input data-search-input type="search" value="${escapeHtml(state.ui.searchQuery)}" placeholder="搜索待办、目标、标签…" autocomplete="off" />${state.ui.searchQuery ? `<button class="search-clear" data-action="clear-search" aria-label="清除搜索">${icon("close")}</button>` : ""}</label>
      <div class="topbar-actions">
        ${state.ui.selectedGoalId ? `<button class="icon-button" data-action="edit-goal" data-id="${state.ui.selectedGoalId}" aria-label="编辑目标">${icon("edit")}</button>` : ""}
        <div class="date-stamp">${icon("calendar")} ${formatDate(dateKey())}</div>
        <button class="primary-button" data-action="open-new-task">${icon("plus")}<span>新建待办</span></button>
      </div>
    </header>`;
}

function renderView() {
  switch (state.ui.view) {
    case "upcoming": return renderUpcoming();
    case "all": return renderAll();
    case "goals": return renderGoals();
    case "archive": return renderArchive();
    case "settings": return renderSettings();
    case "today":
    default: return renderToday();
  }
}

function renderHero(eyebrowText, title, description, stat = null) {
  return `
    <div class="content-hero">
      <div><div class="eyebrow">${icon(stat ? "sparkles" : "sun")} ${eyebrowText}</div><h2>${title}</h2><p>${description}</p></div>
      ${stat ? `<div class="hero-stat"><div class="hero-stat-ring" style="--progress:${stat.progress}%"><span>${stat.progress}%</span></div><div><strong>${stat.primary}</strong><small>${stat.secondary}</small></div></div>` : ""}
    </div>`;
}

function renderToolbar({ showFilters = false, viewMode = null, onViewMode = "allViewMode" } = {}) {
  const mode = state.ui[onViewMode] || "list";
  return `
    <div class="toolbar-row">
      <div class="toolbar-left">
        ${showFilters ? `<button class="filter-button ${state.ui.filterOpen ? "active" : ""}" data-action="toggle-filters">${icon("filter")} 筛选 ${activeFilterCount() ? `<span class="nav-count">${activeFilterCount()}</span>` : ""}</button>${renderFilterChips()}` : ""}
      </div>
      <div class="toolbar-right">
        ${viewMode ? `<div class="segmented"><button class="${mode === "list" ? "active" : ""}" data-action="set-view-mode" data-view-mode="list" data-mode-key="${onViewMode}">${icon("list")} 列表</button><button class="${mode === "board" ? "active" : ""}" data-action="set-view-mode" data-view-mode="board" data-mode-key="${onViewMode}">${icon("board")} 看板</button></div>` : ""}
      </div>
    </div>`;
}

function activeFilterCount() {
  return Object.entries(state.ui.filters).filter(([key, value]) => value !== "all" && !(key === "status" && value === "todo")).length;
}

function renderFilterChips() {
  const chips = [];
  if (state.ui.filters.category !== "all") chips.push(["category", categoryLabel(state.ui.filters.category)]);
  if (state.ui.filters.priority !== "all") chips.push(["priority", priorityLabel(state.ui.filters.priority)]);
  if (state.ui.filters.goal !== "all") chips.push(["goal", state.ui.filters.goal === "linked" ? "已关联目标" : "独立待办"]);
  if (state.ui.filters.status !== "todo") chips.push(["status", state.ui.filters.status === "completed" ? "已完成" : "全部状态"]);
  if (state.ui.filters.tag !== "all") chips.push(["tag", `#${state.ui.filters.tag}`]);
  return chips.map(([key, label]) => `<span class="filter-chip">${escapeHtml(label)}<button data-action="clear-filter" data-filter-key="${key}" aria-label="清除${escapeHtml(label)}">${icon("close")}</button></span>`).join("");
}

function renderFilterPanel() {
  if (!state.ui.filterOpen) return "";
  const tags = allTags();
  return `
    <div class="filter-panel">
      <div class="filter-field"><label for="filter-category">分类</label><select id="filter-category" data-filter-key="category"><option value="all" ${state.ui.filters.category === "all" ? "selected" : ""}>全部分类</option><option value="work" ${state.ui.filters.category === "work" ? "selected" : ""}>工作</option><option value="life" ${state.ui.filters.category === "life" ? "selected" : ""}>生活</option></select></div>
      <div class="filter-field"><label for="filter-priority">优先级</label><select id="filter-priority" data-filter-key="priority"><option value="all" ${state.ui.filters.priority === "all" ? "selected" : ""}>全部优先级</option><option value="high" ${state.ui.filters.priority === "high" ? "selected" : ""}>高优先级</option><option value="normal" ${state.ui.filters.priority === "normal" ? "selected" : ""}>普通优先级</option></select></div>
      <div class="filter-field"><label for="filter-goal">目标关系</label><select id="filter-goal" data-filter-key="goal"><option value="all" ${state.ui.filters.goal === "all" ? "selected" : ""}>全部待办</option><option value="linked" ${state.ui.filters.goal === "linked" ? "selected" : ""}>已关联目标</option><option value="standalone" ${state.ui.filters.goal === "standalone" ? "selected" : ""}>独立待办</option></select></div>
      <div class="filter-field"><label for="filter-status">状态</label><select id="filter-status" data-filter-key="status"><option value="todo" ${state.ui.filters.status === "todo" ? "selected" : ""}>待办</option><option value="completed" ${state.ui.filters.status === "completed" ? "selected" : ""}>已完成</option><option value="all" ${state.ui.filters.status === "all" ? "selected" : ""}>全部状态</option></select></div>
      ${tags.length ? `<div class="filter-field"><label for="filter-tag">标签</label><select id="filter-tag" data-filter-key="tag"><option value="all" ${state.ui.filters.tag === "all" ? "selected" : ""}>全部标签</option>${tags.map((tag) => `<option value="${escapeHtml(tag)}" ${state.ui.filters.tag === tag ? "selected" : ""}>#${escapeHtml(tag)}</option>`).join("")}</select></div>` : ""}
      <button class="ghost-button" data-action="reset-filters">重置筛选</button>
    </div>`;
}

function renderTaskRow(task, { selectable = false, showDate = true, compact = false } = {}) {
  const goal = getGoal(task.goalId);
  const completed = task.status === "completed";
  const subtaskDone = task.subtasks.filter((step) => step.completed).length;
  const tone = showDate ? dateTone(task.plannedDate) : "";
  const selected = state.ui.selectedTaskIds.includes(task.id);
  const metaDate = task.plannedDate
    ? `${icon("calendar")}<span>${relativeDate(task.plannedDate)}</span>`
    : `${icon("calendar")}<span>未安排</span>`;
  return `
    <article class="task-row priority-${task.priority} ${completed ? "completed" : ""} ${selectable ? "selectable" : ""}" draggable="${completed ? "false" : "true"}" data-task-row data-id="${task.id}" aria-label="${escapeHtml(task.title)}">
      ${selectable ? `<input class="select-check" type="checkbox" data-batch-select data-id="${task.id}" ${selected ? "checked" : ""} aria-label="选择${escapeHtml(task.title)}" />` : ""}
      <button class="task-check ${completed ? "checked" : ""}" data-action="toggle-task" data-id="${task.id}" aria-label="${completed ? "撤销完成" : "标记完成"}">${completed ? icon("check") : ""}</button>
      <div class="task-main" role="button" tabindex="0" data-action="open-task" data-id="${task.id}">
        <div class="task-title-line"><span class="task-title">${escapeHtml(task.title)}</span>${goal ? `<span class="goal-badge">${icon("target")} ${escapeHtml(goal.title)}</span>` : ""}</div>
        ${task.note && !compact ? `<div class="task-note-preview">${escapeHtml(task.note)}</div>` : ""}
        <div class="task-meta">
          ${showDate ? `<span class="task-meta-item ${tone}">${metaDate}</span>` : ""}
          <span class="task-meta-item"><span class="category-badge ${task.category}">${categoryLabel(task.category)}</span></span>
          ${task.tags.slice(0, compact ? 1 : 2).map((tag) => `<span class="tag-badge">#${escapeHtml(tag)}</span>`).join("")}
          ${subtaskDone || task.subtasks.length ? `<span class="task-meta-item">${icon("steps")} ${subtaskDone}/${task.subtasks.length}</span>` : ""}
        </div>
      </div>
      <div class="task-extra">
        ${task.plannedDate && task.plannedDate < dateKey() && !completed ? `<span class="priority-badge high">逾期</span>` : ""}
        ${task.priority === "high" ? `<span class="priority-badge high">高</span>` : ""}
        <div class="task-actions"><button class="task-action" data-action="open-task" data-id="${task.id}" aria-label="查看详情">${icon("chevronRight")}</button><button class="task-action" data-action="open-context" data-id="${task.id}" aria-label="更多操作">${icon("more")}</button></div>
      </div>
    </article>`;
}

function renderTaskList(tasks, options = {}) {
  if (!tasks.length) return `<div class="section-drop-zone" data-drop-priority="${options.priority || ""}">${renderEmpty(options.emptyTitle || "这里还没有待办", options.emptyDescription || "创建一条具体的小行动，让目标开始向前。", options.emptyAction !== false)}</div>`;
  return `<div class="task-list section-drop-zone" data-drop-priority="${options.priority || ""}">${tasks.map((task) => renderTaskRow(task, options)).join("")}</div>`;
}

function renderEmpty(title, description, showAction = true, iconName = "inbox") {
  return `<div class="empty-state"><div><div class="empty-illustration">${icon(iconName)}</div><strong>${escapeHtml(title)}</strong><span>${escapeHtml(description)}</span>${showAction ? `<button class="text-button" style="margin-top: 11px;" data-action="open-new-task">+ 新建第一条</button>` : ""}</div></div>`;
}

function renderPriorityGroup(title, tasks, options = {}) {
  return `
    <section class="section-block">
      <div class="section-heading priority-heading"><div class="section-heading-main"><span class="priority-dot ${options.priority === "high" ? "high" : ""}"></span><h3>${title}</h3><span class="count">${tasks.length}</span></div></div>
      ${renderTaskList(tasks, { ...options, priority: options.priority, emptyTitle: `没有${title}待办`, emptyDescription: "这一组暂时是空的。", emptyAction: false })}
    </section>`;
}

function renderToday() {
  const overdue = overdueTasks().sort((a, b) => taskSort(a, b));
  const today = todayTasks().sort((a, b) => taskSort(a, b));
  const completed = completedOn(dateKey()).sort((a, b) => (b.completedAt || "").localeCompare(a.completedAt || ""));
  const plannedTodayTotal = today.length + completed.filter((task) => task.plannedDate === dateKey()).length;
  const todayProgress = plannedTodayTotal ? Math.round((completed.filter((task) => task.plannedDate === dateKey()).length / plannedTodayTotal) * 100) : 0;
  return `
    ${renderHero("执行焦点", "今天要做的事", "逾期不会自动消失，今天只保留真正需要你决定的下一步。", { progress: todayProgress, primary: `${today.length} 项`, secondary: "今天待办" })}
    ${overdue.length ? `<div class="notice-bar"><div class="notice-main">${icon("alert")}<span>有 <strong>${overdue.length}</strong> 项逾期，原计划日期会保留。先处理最重要的一件。</span></div><button class="text-button" data-action="focus-overdue">查看逾期</button></div>` : ""}
    ${overdue.length ? `<section class="section-block"><div class="section-heading"><div class="section-heading-main"><h3 style="color: var(--high);">逾期</h3><span class="count">${overdue.length}</span></div><span class="faint" style="font-size:10px;">按原计划从早到晚</span></div>${renderTaskList(overdue, { showDate: true, emptyAction: false })}</section>` : ""}
    <section class="section-block"><div class="section-heading"><div class="section-heading-main"><h3>今天</h3><span class="count">${today.length}</span></div><button class="section-action" data-action="open-new-task" data-preset-date="${dateKey()}">${icon("plus")} 添加到今天</button></div>
      ${today.length ? `${renderPriorityGroup("高优先级", today.filter((task) => task.priority === "high"), { priority: "high", showDate: false })}${renderPriorityGroup("普通优先级", today.filter((task) => task.priority !== "high"), { priority: "normal", showDate: false })}` : renderEmpty("今天没有安排事项", "需要做的事可以先放到之后或未安排。", true, "sun")}
    </section>
    <section class="section-block"><div class="completed-collapse"><button class="completed-toggle ${state.ui.completedOpen ? "open" : ""}" data-action="toggle-completed"><span class="completed-toggle-main">${icon("chevronRight")}<span>已完成 <strong>${completed.length}</strong></span></span><span class="faint">今天实际完成</span></button>${state.ui.completedOpen && completed.length ? `<div class="completed-list">${completed.map((task) => renderTaskRow(task, { showDate: true, compact: true })).join("")}</div>` : state.ui.completedOpen ? `<div class="completed-list">${renderEmpty("今天还没有完成记录", "完成的事项会在这里留下痕迹。", false, "checkCircle")}</div>` : ""}</div></section>`;
}

function renderUpcoming() {
  const tasks = visibleTasks().filter((task) => task.plannedDate > dateKey() || !task.plannedDate).sort((a, b) => taskSort(a, b, "upcoming"));
  const grouped = new Map();
  tasks.forEach((task) => {
    const key = task.plannedDate || "unplanned";
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(task);
  });
  const groups = [...grouped.entries()].sort(([a], [b]) => {
    if (a === "unplanned") return 1;
    if (b === "unplanned") return -1;
    return a.localeCompare(b);
  });
  return `
    ${renderHero("轻量规划", "之后", "未来按日期展开，未安排的想法留在最底部，不占用计划完成率。", null)}
    <div class="toolbar-row"><div class="toolbar-left"><span class="faint" style="font-size:11px;">${tasks.length} 项未来安排</span></div><div class="toolbar-right"><button class="outline-button" data-action="open-new-task" data-preset-date="${offsetDate(1)}">${icon("plus")} 添加到明天</button></div></div>
    ${groups.length ? groups.map(([key, items]) => `<section class="date-group"><div class="date-group-title"><span class="date-accent">${key === "unplanned" ? "未安排" : relativeDate(key)}</span><span>${key === "unplanned" ? "先记录，之后再决定" : formatDate(key)}</span><span>${items.length} 项</span><button class="section-action" data-action="open-new-task" data-preset-date="${key === "unplanned" ? "" : key}">${icon("plus")} 添加</button></div>${renderTaskList(items, { showDate: false })}</section>`).join("") : renderEmpty("之后还没有安排", "把想法记录下来，或为待办选一个未来日期。", true, "clock")}`;
}

function renderAll() {
  const base = filterTaskList(visibleTasks({ includeCompleted: state.ui.filters.status !== "todo" }), state.ui.filters).sort((a, b) => taskSort(a, b, "all"));
  const completedForBoard = state.ui.allViewMode === "board" ? filterTaskList(visibleTasks({ includeCompleted: true }).filter((task) => task.status === "completed"), { ...state.ui.filters, status: "completed" }).sort((a, b) => (b.completedAt || "").localeCompare(a.completedAt || "")) : [];
  const todoForBoard = base.filter((task) => task.status === "todo");
  return `
    ${renderHero("全局掌握", "全部待办", "工作与生活放在同一条执行线上，日期通过显式操作调整。", null)}
    ${renderToolbar({ showFilters: true, viewMode: true, onViewMode: "allViewMode" })}
    ${renderFilterPanel()}
    ${state.ui.selectedTaskIds.length ? renderBatchBar() : ""}
    ${state.ui.allViewMode === "board" ? renderBoard(todoForBoard, completedForBoard) : (base.length ? `<div class="all-list">${renderPriorityGroup("高优先级", base.filter((task) => task.priority === "high"), { priority: "high", selectable: true, showDate: true })}${renderPriorityGroup("普通优先级", base.filter((task) => task.priority !== "high"), { priority: "normal", selectable: true, showDate: true })}</div>` : renderEmpty("没有符合条件的待办", "试试清除筛选，或者新建一条待办。", true, "search"))}`;
}

function renderBoard(todoTasks, completedTasks) {
  return `<div class="board-grid"><section class="board-column" data-board-status="todo"><div class="board-column-title"><span>待办</span><span>${todoTasks.length}</span></div><div class="board-list section-drop-zone" data-drop-status="todo">${todoTasks.length ? todoTasks.map((task) => renderTaskRow(task, { selectable: true, showDate: true, compact: true })).join("") : renderEmpty("没有待办", "这一栏暂时是空的。", false)}</div></section><section class="board-column" data-board-status="completed"><div class="board-column-title"><span>已完成</span><span>${completedTasks.length}</span></div><div class="board-list section-drop-zone" data-drop-status="completed">${completedTasks.length ? completedTasks.map((task) => renderTaskRow(task, { selectable: true, showDate: true, compact: true })).join("") : renderEmpty("还没有完成记录", "完成后的事项会归档到这里。", false, "checkCircle")}</div></section></div>`;
}

function renderBatchBar() {
  return `<div class="batch-bar"><div class="batch-count">已选择 ${state.ui.selectedTaskIds.length} 项</div><div class="batch-actions"><button data-action="batch-complete">标记完成</button><button data-action="batch-priority" data-value="high">设为高优</button><button data-action="batch-priority" data-value="normal">设为普通</button><button data-action="batch-category" data-value="work">工作</button><button data-action="batch-category" data-value="life">生活</button><button data-action="batch-date">设置日期</button><button data-action="batch-goal">挂载目标</button><button data-action="batch-delete">删除</button><button data-action="clear-selection">清除</button></div></div>`;
}

function renderGoals() {
  const goals = state.goals.filter((goal) => {
    if (state.ui.goalsStatus !== "all" && goal.status !== state.ui.goalsStatus) return false;
    if (state.ui.goalsCategory !== "all" && goal.category !== state.ui.goalsCategory) return false;
    return true;
  }).sort(goalSort);
  const active = state.goals.filter((goal) => goal.status === "active");
  const average = active.length ? Math.round(active.reduce((sum, goal) => sum + goalStats(goal).progress, 0) / active.length) : 0;
  return `
    ${renderHero("长期方向", "长期目标", "目标只负责承载成果，真正推进它的，是一件件进入待办的具体动作。", { progress: average, primary: `${active.length} 个`, secondary: "进行中目标" })}
    <div class="toolbar-row"><div class="toolbar-left"><div class="segmented"><button class="${state.ui.goalsStatus === "active" ? "active" : ""}" data-action="set-goals-status" data-value="active">进行中</button><button class="${state.ui.goalsStatus === "all" ? "active" : ""}" data-action="set-goals-status" data-value="all">全部</button><button class="${state.ui.goalsStatus === "achieved" ? "active" : ""}" data-action="set-goals-status" data-value="achieved">已达成</button></div><div class="segmented"><button class="${state.ui.goalsCategory === "all" ? "active" : ""}" data-action="set-goals-category" data-value="all">全部</button><button class="${state.ui.goalsCategory === "work" ? "active" : ""}" data-action="set-goals-category" data-value="work">工作</button><button class="${state.ui.goalsCategory === "life" ? "active" : ""}" data-action="set-goals-category" data-value="life">生活</button></div></div><div class="toolbar-right"><button class="primary-button compact" data-action="open-new-goal">${icon("plus")} 新建目标</button></div></div>
    ${goals.length ? `<div class="goal-page-grid">${goals.map(renderGoalCard).join("")}</div>` : renderEmpty(state.ui.goalsStatus === "achieved" ? "还没有已达成目标" : "还没有长期目标", "设定一个长期目标，把它拆成具体待办。", true, "target")}`;
}

function renderGoalCard(goal) {
  const stats = goalStats(goal);
  return `<article class="goal-card ${goal.priority === "high" ? "high" : ""} ${goal.status === "achieved" ? "achieved" : ""}" data-action="open-goal" data-id="${goal.id}" role="button" tabindex="0"><div class="goal-card-top"><div><h3 class="goal-card-title">${escapeHtml(goal.title)}</h3><div style="margin-top:7px; display:flex; gap:5px;"><span class="category-badge ${goal.category}">${categoryLabel(goal.category)}</span>${goal.priority === "high" ? `<span class="priority-badge high">高</span>` : ""}</div></div><span class="status-badge ${goal.status === "achieved" ? "archived" : ""}">${statusLabel(goal.status)}</span></div><p class="goal-card-note">${escapeHtml(goal.note || "还没有目标说明，把它拆成下一步就好。")}</p><div class="goal-card-progress"><div class="goal-card-progress-row"><strong>${stats.progress}%</strong><span>${stats.completed} / ${stats.total} 个待办完成</span></div><div class="progress-track"><div class="progress-fill ${goal.status === "achieved" ? "success" : ""}" style="width:${stats.progress}%"></div></div></div><div class="goal-card-footer"><span>${goal.plannedFinishDate ? `${icon("calendar")} 计划 ${formatDate(goal.plannedFinishDate)}` : `${icon("calendar")} 暂无计划日期`}</span>${icon("chevronRight")}</div></article>`;
}

function renderGoalDetail() {
  const goal = getGoal(state.ui.selectedGoalId);
  if (!goal) {
    state.ui.selectedGoalId = null;
    return renderGoals();
  }
  const relatedTodo = tasksForGoal(goal.id, false).sort(taskSort);
  const relatedCompleted = tasksForGoal(goal.id, true).filter((task) => task.status === "completed").sort((a, b) => (b.completedAt || "").localeCompare(a.completedAt || ""));
  const stats = goalStats(goal);
  const relatedContent = state.ui.goalViewMode === "board"
    ? renderBoard(relatedTodo, relatedCompleted)
    : `<section class="section-block"><div class="section-heading"><div class="section-heading-main"><h3>待办</h3><span class="count">${relatedTodo.length}</span></div></div>${relatedTodo.length ? `${renderPriorityGroup("高优先级", relatedTodo.filter((task) => task.priority === "high"), { priority: "high", showDate: true })}${renderPriorityGroup("普通优先级", relatedTodo.filter((task) => task.priority !== "high"), { priority: "normal", showDate: true })}` : renderEmpty("这个目标还没有未完成待办", "新增一个具体动作，让目标开始向前。", true, "target")}</section><section class="section-block"><div class="completed-collapse"><button class="completed-toggle ${state.ui.completedOpen ? "open" : ""}" data-action="toggle-completed"><span class="completed-toggle-main">${icon("chevronRight")}<span>已完成 <strong>${relatedCompleted.length}</strong></span></span><span class="faint">关联待办</span></button>${state.ui.completedOpen && relatedCompleted.length ? `<div class="completed-list">${relatedCompleted.map((task) => renderTaskRow(task, { compact: true, showDate: true })).join("")}</div>` : ""}</div></section>`;
  return `
    <div class="goal-detail-head"><button class="back-link" data-action="back-to-goals">${icon("arrowLeft")} 返回长期目标</button><div class="goal-detail-summary"><div><div class="goal-detail-title-row"><h2>${escapeHtml(goal.title)}</h2><span class="category-badge ${goal.category}">${categoryLabel(goal.category)}</span>${goal.priority === "high" ? `<span class="priority-badge high">高优先级</span>` : ""}<span class="status-badge ${goal.status === "achieved" ? "archived" : ""}">${statusLabel(goal.status)}</span></div><p class="goal-detail-note">${escapeHtml(goal.note || "这个目标还没有说明。")}</p><div class="goal-detail-meta"><span class="goal-detail-meta-item">${icon("calendar")} ${goal.plannedFinishDate ? `计划完成 ${formatDate(goal.plannedFinishDate)}` : "暂未设置计划完成日期"}</span><span class="goal-detail-meta-item">${icon("checkCircle")} ${stats.completed} / ${stats.total} 个待办</span><span class="goal-detail-meta-item">${icon("calendar")} 创建于 ${formatDate(dateKey(new Date(goal.createdAt)))}</span></div></div><div class="goal-detail-progress"><div class="big-progress-circle" style="--progress:${stats.progress}%"><div><strong>${stats.progress}%</strong><small>自动进度</small></div></div><div class="goal-detail-actions"><button class="outline-button small-button" data-action="edit-goal" data-id="${goal.id}">${icon("edit")} 编辑</button>${goal.status === "active" ? `<button class="primary-button compact" data-action="achieve-goal" data-id="${goal.id}">${icon("checkCircle")} 达成</button>` : `<button class="outline-button small-button" data-action="restore-goal" data-id="${goal.id}">${icon("refresh")} 恢复</button>`}</div></div></div></div>
    <div class="toolbar-row"><div class="toolbar-left"><span class="muted" style="font-size:11px;">关联待办 · ${stats.total} 项</span></div><div class="toolbar-right"><div class="segmented"><button class="${state.ui.goalViewMode === "list" ? "active" : ""}" data-action="set-view-mode" data-view-mode="list" data-mode-key="goalViewMode">${icon("list")} 列表</button><button class="${state.ui.goalViewMode === "board" ? "active" : ""}" data-action="set-view-mode" data-view-mode="board" data-mode-key="goalViewMode">${icon("board")} 看板</button></div><button class="outline-button" data-action="open-new-task" data-goal-id="${goal.id}" data-preset-date="">${icon("plus")} 新增关联待办</button></div></div>
    ${relatedContent}
    <div class="drawer-danger-zone" style="margin-top:27px; padding-top:16px; border-top:1px solid var(--line);"><button class="danger-button" data-action="delete-goal" data-id="${goal.id}">${icon("trash")} 删除目标</button><span class="faint" style="margin-left:10px; font-size:10px;">删除前会让你选择如何处理关联待办</span></div>`;
}

function renderArchive() {
  const completedTasks = state.tasks.filter((task) => task.status === "completed" && task.completedAt).filter((task) => {
    if (state.ui.archiveCategory !== "all" && task.category !== state.ui.archiveCategory) return false;
    const query = state.ui.archiveQuery.trim().toLocaleLowerCase();
    if (query && ![task.title, task.note, ...task.tags].join(" ").toLocaleLowerCase().includes(query)) return false;
    return true;
  }).sort((a, b) => (b.completedAt || "").localeCompare(a.completedAt || ""));
  const achievedGoals = state.goals.filter((goal) => goal.status === "achieved").filter((goal) => state.ui.archiveCategory === "all" || goal.category === state.ui.archiveCategory).sort((a, b) => (b.achievedAt || "").localeCompare(a.achievedAt || ""));
  return `
    ${renderHero("保留痕迹", "归档", "完成不是删除。把已经做过的事情留在这里，之后仍然可以回看。", null)}
    <div class="archive-tabs"><button class="archive-tab ${state.ui.archiveTab === "tasks" ? "active" : ""}" data-action="set-archive-tab" data-value="tasks">已完成待办 <span class="faint">${state.tasks.filter((task) => task.status === "completed").length}</span></button><button class="archive-tab ${state.ui.archiveTab === "goals" ? "active" : ""}" data-action="set-archive-tab" data-value="goals">已达成目标 <span class="faint">${state.goals.filter((goal) => goal.status === "achieved").length}</span></button></div>
    <div class="toolbar-row"><div class="toolbar-left"><label class="search-box" style="max-width:260px; min-width:180px;"><span class="sr-only">筛选归档</span>${icon("search")}<input data-archive-search type="search" value="${escapeHtml(state.ui.archiveQuery)}" placeholder="筛选归档…" /></label></div><div class="toolbar-right"><select data-archive-category style="padding:8px 9px; font-size:11px;"><option value="all" ${state.ui.archiveCategory === "all" ? "selected" : ""}>全部分类</option><option value="work" ${state.ui.archiveCategory === "work" ? "selected" : ""}>工作</option><option value="life" ${state.ui.archiveCategory === "life" ? "selected" : ""}>生活</option></select></div></div>
    ${state.ui.archiveTab === "tasks" ? (completedTasks.length ? completedTasks.map((task) => renderArchiveTask(task)).join("") : renderEmpty("还没有已完成待办", "完成的事项会按实际完成日期出现在这里。", false, "archive")) : (achievedGoals.length ? achievedGoals.map(renderArchiveGoal).join("") : renderEmpty("还没有已达成目标", "目标达成后会永久保留在这里。", false, "target"))}`;
}

function renderArchiveTask(task) {
  const goal = getGoal(task.goalId);
  return `<div class="archive-item"><div class="archive-item-main"><div class="archive-item-title">${escapeHtml(task.title)}</div><div class="archive-item-sub"><span>${icon("checkCircle")} 实际完成 ${formatDate(dateKey(new Date(task.completedAt)))}</span><span class="category-badge ${task.category}">${categoryLabel(task.category)}</span>${goal ? `<span>${icon("target")} ${escapeHtml(goal.title)}</span>` : ""}${task.tags.map((tag) => `<span>#${escapeHtml(tag)}</span>`).join("")}</div></div><div class="archive-item-right"><span class="status-badge">已完成</span><button class="icon-button" data-action="open-task" data-id="${task.id}" aria-label="查看详情">${icon("chevronRight")}</button></div></div>`;
}

function renderArchiveGoal(goal) {
  const stats = goalStats(goal);
  return `<div class="archive-item"><div class="archive-item-main"><div class="archive-item-title">${escapeHtml(goal.title)}</div><div class="archive-item-sub"><span>${icon("checkCircle")} 达成于 ${goal.achievedAt ? formatDate(dateKey(new Date(goal.achievedAt))) : "未知日期"}</span><span class="category-badge ${goal.category}">${categoryLabel(goal.category)}</span><span>${stats.completed}/${stats.total} 个待办</span></div></div><div class="archive-item-right"><span class="status-badge archived">已达成</span><button class="outline-button small-button" data-action="open-goal" data-id="${goal.id}">查看目标</button></div></div>`;
}

function renderSettings() {
  return `
    ${renderHero("工作方式", "设置", "把软件调成更安静、更贴近你每天节奏的样子。", null)}
    <div class="settings-grid">
      <section class="settings-card"><h3>常规</h3><p class="settings-card-description">应用行为与默认值</p>
        ${settingSwitch("startupEnabled", "开机后自动启动", "桌面版接入后会在 Windows 启动时运行。", state.settings.startupEnabled)}
        ${settingSwitch("startMinimized", "启动后最小化", "启动时直接留在后台，不抢占当前窗口。", state.settings.startMinimized)}
        ${settingSwitch("closeToTray", "关闭窗口时转入托盘", "浏览器预览中只记录偏好；桌面版会真正隐藏主窗口。", state.settings.closeToTray)}
        <div class="setting-row"><div class="setting-copy"><strong>默认分类</strong><span>快速新增时使用的分类</span></div><div class="setting-control"><select data-setting="defaultCategory"><option value="work" ${state.settings.defaultCategory === "work" ? "selected" : ""}>工作</option><option value="life" ${state.settings.defaultCategory === "life" ? "selected" : ""}>生活</option></select></div></div>
        <div class="setting-row"><div class="setting-copy"><strong>默认启动页</strong><span>下次打开软件时显示</span></div><div class="setting-control"><select data-setting="startupPage"><option value="today" ${state.settings.startupPage === "today" ? "selected" : ""}>今天</option><option value="upcoming" ${state.settings.startupPage === "upcoming" ? "selected" : ""}>之后</option><option value="all" ${state.settings.startupPage === "all" ? "selected" : ""}>全部</option></select></div></div>
      </section>
      <section class="settings-card"><h3>外观</h3><p class="settings-card-description">四套浅色主题与低干扰动效</p><div class="theme-options">${["blue", "green", "orange", "purple"].map((theme) => `<button class="theme-option ${state.settings.theme === theme ? "active" : ""}" data-action="set-theme" data-value="${theme}"><span class="theme-swatch ${theme}"></span>${{ blue: "沉静蓝", green: "清新绿", orange: "活力橙", purple: "优雅紫" }[theme]}</button>`).join("")}</div>${settingSwitch("reduceMotion", "减少动效", "降低完成、拖拽和进度变化的动画。", state.settings.reduceMotion)}</section>
      <section class="settings-card"><h3>快捷键</h3><p class="settings-card-description">在软件内快速打开输入窗口；桌面端可注册为全局快捷键。</p><div class="setting-row"><div class="setting-copy"><strong>快速添加待办</strong><span>当前快捷键：${escapeHtml(state.settings.shortcut)}</span></div><div class="setting-control"><button class="outline-button" data-action="edit-shortcut">${icon("keyboard")} 修改</button></div></div><div class="setting-row"><div class="setting-copy"><strong>内置快捷键</strong><span>Ctrl + N 新增 · Ctrl + F 搜索 · Ctrl + 1/2/3 切换视图 · Esc 关闭</span></div><div class="setting-control"><span class="status-badge">可用</span></div></div></section>
      <section class="settings-card"><h3>数据与备份</h3><p class="settings-card-description">数据留在当前设备。完整备份包含任务、目标、标签、模板和计划历史。</p><div class="data-actions"><button class="outline-button" data-action="export-json">${icon("download")} 导出完整备份</button><button class="outline-button" data-action="export-csv">${icon("download")} 导出历史 CSV</button><button class="outline-button" data-action="import-json">${icon("upload")} 从备份恢复</button><button class="ghost-button" data-action="backup-now">${icon("lock")} 生成本地备份</button><button class="ghost-button" data-action="load-demo">${icon("sparkles")} 载入示例数据</button></div><input id="import-input" class="sr-only" type="file" accept="application/json,.json" /><div class="rail-divider"></div><div class="setting-row"><div class="setting-copy"><strong>浏览器版数据</strong><span>保存在此浏览器的 localStorage；未来接入 Tauri 后切换到 SQLite。</span></div><div class="setting-control"><button class="danger-button" data-action="reset-data">清空数据</button></div></div></section>
      <section class="settings-card"><h3>任务模板</h3><p class="settings-card-description">模板只保存内容与结构，不保存旧的日期和目标。</p>${state.templates.length ? `<div class="template-list">${state.templates.map((template) => `<div class="template-item"><div><strong>${escapeHtml(template.title)}</strong><span>${categoryLabel(template.category)} · ${template.subtasks.length} 个子步骤</span></div><div style="display:flex; gap:5px;"><button class="small-button" data-action="use-template" data-id="${template.id}">使用</button><button class="icon-button" data-action="delete-template" data-id="${template.id}" aria-label="删除模板">${icon("trash")}</button></div></div>`).join("")}</div>` : `<div class="faint" style="font-size:11px; padding:7px 0;">还没有模板。在待办的更多操作中可以保存模板。</div>`}</section>
      <section class="settings-card"><h3>关于日常</h3><p class="settings-card-description">一个把长期方向落到今天行动的个人执行工具。</p><div class="setting-row"><div class="setting-copy"><strong>版本</strong><span>浏览器本地优先预览版</span></div><div class="setting-control"><span class="status-badge">v${APP_VERSION}</span></div></div><div class="setting-row"><div class="setting-copy"><strong>产品原则</strong><span>记录要快，查看要清楚，统计要真实，软件本身不要成为新的管理负担。</span></div><div class="setting-control">${icon("leaf")}</div></div></section>
    </div>`;
}

function settingSwitch(key, title, description, checked) {
  return `<div class="setting-row"><div class="setting-copy"><strong>${title}</strong><span>${description}</span></div><label class="switch setting-control"><input type="checkbox" data-setting="${key}" ${checked ? "checked" : ""} /><span></span></label></div>`;
}

function renderRightRail() {
  const activeGoals = state.goals.filter((goal) => goal.status === "active").sort(goalSort);
  const stats = planStats();
  const actual = actualCompletionCount(startOfWeek(), endOfWeek());
  const chart = lastSevenDays();
  const maxActual = Math.max(1, ...chart.map((item) => item.actual));
  return `
    <section class="rail-card"><div class="rail-card-heading"><h3>长期目标</h3><button class="rail-link" data-action="navigate" data-view="goals">全部目标 ${icon("arrowUpRight")}</button></div>${activeGoals.length ? `<div class="mini-goal-list">${activeGoals.slice(0, 3).map((goal) => { const item = goalStats(goal); return `<div class="mini-goal" data-action="open-goal" data-id="${goal.id}" role="button" tabindex="0"><div class="mini-goal-top"><span class="mini-goal-title">${escapeHtml(goal.title)}</span><span class="mini-goal-percent">${item.progress}%</span></div><div class="progress-track"><div class="progress-fill" style="width:${item.progress}%"></div></div><div class="mini-goal-meta">${item.completed}/${item.total} 个待办 · ${goal.priority === "high" ? "高优先" : "稳步推进"}</div></div>`; }).join("")}</div>` : `<div class="faint" style="font-size:11px;">还没有进行中的目标。<br /><button class="text-button" data-action="open-new-goal">设定一个长期目标 →</button></div>`}</section>
    <section class="rail-card"><div class="rail-card-heading"><h3>本周执行</h3><span>${formatDate(startOfWeek())} – ${formatDate(endOfWeek())}</span></div><div class="stat-stack"><div class="stat-line"><span>实际完成</span><strong>${actual}</strong></div><div class="stat-line"><span>有效计划</span><strong>${stats.total}</strong></div><div class="stat-line rate"><span>计划完成率</span><strong>${stats.rate}%</strong></div></div><div class="rail-divider"></div><div class="faint" style="font-size:10px;">最近 7 天实际完成</div><div class="chart">${chart.every((item) => item.actual === 0) ? `<div class="chart-empty">完成的事项会在这里形成节奏</div>` : chart.map((item) => `<div class="chart-bar-wrap" title="${item.label} · ${item.actual} 项"><div class="chart-bar ${item.day === dateKey() ? "today" : ""}" style="height:${Math.max(6, Math.round((item.actual / maxActual) * 53))}px"></div><small>${item.label}</small></div>`).join("")}</div></section>`;
}

function renderSearchPage() {
  const result = searchData(state.ui.searchQuery);
  return `
    ${renderHero("全局搜索", `搜索「${escapeHtml(state.ui.searchQuery.trim())}」`, "搜索标题、备注、标签、目标名称和目标说明。", null)}
    ${state.ui.selectedTaskIds.length ? renderBatchBar() : ""}
    <div class="search-results-group"><h3>${icon("inbox")} 待办 <span>${result.tasks.length} 条结果</span></h3>${result.tasks.length ? result.tasks.map((task) => renderTaskRow(task, { selectable: task.status === "todo", showDate: true })).join("") : `<div class="empty-state" style="min-height:140px;"><div><strong>没有匹配的待办</strong><span>可以换个关键词，或搜索目标名称。</span></div></div>`}</div>
    <div class="search-results-group"><h3>${icon("target")} 目标 <span>${result.goals.length} 条结果</span></h3>${result.goals.length ? result.goals.map((goal) => `<div class="search-target-card" data-action="open-goal" data-id="${goal.id}" role="button" tabindex="0"><div class="search-target-main"><div class="search-target-title">${escapeHtml(goal.title)}</div><div class="search-target-sub">${categoryLabel(goal.category)} · ${statusLabel(goal.status)} · ${goalStats(goal).progress}% 自动进度</div></div>${icon("chevronRight")}</div>`).join("") : `<div class="empty-state" style="min-height:120px;"><div><strong>没有匹配的目标</strong><span>暂时没有找到对应的长期目标。</span></div></div>`}</div>`;
}

function renderDrawer() {
  const task = state.ui.drawerTaskId ? getTask(state.ui.drawerTaskId) : null;
  if (!task) return "";
  const goal = getGoal(task.goalId);
  const doneSteps = task.subtasks.filter((step) => step.completed).length;
  return `
    <div class="drawer-backdrop" data-action="close-drawer" role="presentation">
      <aside class="drawer" role="dialog" aria-modal="true" aria-label="待办详情" data-drawer-content>
        <div class="drawer-header"><div><h3>${escapeHtml(task.title)}</h3><p>${task.status === "completed" ? `已完成于 ${task.completedAt ? formatDate(dateKey(new Date(task.completedAt))) : ""}` : `创建于 ${formatDate(dateKey(new Date(task.createdAt)))}`}</p></div><button class="close-button" data-action="close-drawer" aria-label="关闭详情">${icon("close")}</button></div>
        <div class="drawer-body">
          <div class="drawer-section"><div class="drawer-section-title"><span>状态</span><span class="status-badge ${task.status === "completed" ? "" : "archived"}">${statusLabel(task.status)}</span></div><button class="outline-button" style="width:100%; justify-content:flex-start;" data-action="toggle-task" data-id="${task.id}">${task.status === "completed" ? icon("undo") : icon("checkCircle")} ${task.status === "completed" ? "撤销完成" : "标记为已完成"}</button></div>
          <div class="drawer-section"><div class="drawer-section-title"><span>任务属性</span><button class="text-button" data-action="open-task-edit" data-id="${task.id}">打开完整编辑</button></div><div class="drawer-field-list"><div class="drawer-field"><label for="drawer-category">分类</label><select id="drawer-category" data-inline-field="category" data-id="${task.id}"><option value="work" ${task.category === "work" ? "selected" : ""}>工作</option><option value="life" ${task.category === "life" ? "selected" : ""}>生活</option></select></div><div class="drawer-field"><label for="drawer-priority">优先级</label><select id="drawer-priority" data-inline-field="priority" data-id="${task.id}"><option value="normal" ${task.priority === "normal" ? "selected" : ""}>普通</option><option value="high" ${task.priority === "high" ? "selected" : ""}>高</option></select></div><div class="drawer-field"><label for="drawer-date">计划日期</label><input id="drawer-date" type="date" value="${task.plannedDate || ""}" data-inline-field="plannedDate" data-id="${task.id}" /></div><div class="drawer-field"><label for="drawer-goal">所属目标</label><select id="drawer-goal" data-inline-field="goalId" data-id="${task.id}"><option value="">独立待办</option>${state.goals.map((item) => `<option value="${item.id}" ${task.goalId === item.id ? "selected" : ""}>${escapeHtml(item.title)}${item.status === "achieved" ? "（已达成）" : ""}</option>`).join("")}</select></div></div></div>
          <div class="drawer-section"><div class="drawer-section-title"><span>备注</span></div><textarea class="drawer-note" data-inline-field="note" data-id="${task.id}" aria-label="任务备注">${escapeHtml(task.note)}</textarea></div>
          <div class="drawer-section"><div class="drawer-section-title"><span>标签</span><button class="text-button" data-action="open-task-edit" data-id="${task.id}">编辑标签</button></div><div class="drawer-tags">${task.tags.length ? task.tags.map((tag) => `<span class="tag-badge">#${escapeHtml(tag)}</span>`).join("") : `<span class="faint" style="font-size:11px;">还没有标签</span>`}</div></div>
          <div class="drawer-section"><div class="drawer-section-title"><span>子步骤</span><span class="faint">${doneSteps}/${task.subtasks.length}</span></div><div class="drawer-subtasks">${task.subtasks.length ? task.subtasks.sort((a, b) => a.sortRank - b.sortRank).map((step) => `<div class="subtask-row"><button class="task-check ${step.completed ? "checked" : ""}" data-action="toggle-subtask" data-task-id="${task.id}" data-id="${step.id}" aria-label="${step.completed ? "撤销子步骤" : "完成子步骤"}">${step.completed ? icon("check") : ""}</button><span class="subtask-title ${step.completed ? "done" : ""}">${escapeHtml(step.title)}</span><button class="subtask-delete" data-action="delete-subtask" data-task-id="${task.id}" data-id="${step.id}" aria-label="删除子步骤">${icon("trash")}</button></div>`).join("") : `<span class="faint" style="font-size:11px;">把一个较大的事项拆成几个轻量步骤。</span>`}</div><form class="subtask-form" data-form="subtask" data-task-id="${task.id}"><input name="title" placeholder="添加一个子步骤" aria-label="子步骤" /><button class="small-button" type="submit">${icon("plus")} 添加</button></form></div>
          <div class="drawer-section"><div class="drawer-danger-zone"><button class="outline-button" data-action="save-template" data-id="${task.id}">${icon("copy")} 保存为模板</button><button class="danger-button" style="margin-left:7px;" data-action="delete-task" data-id="${task.id}">${icon("trash")} 删除待办</button></div></div>
        </div>
      </aside>
    </div>`;
}

function renderModal() {
  const modal = state.ui.modal;
  if (!modal) return "";
  if (modal.type === "task") return modal.quick ? renderQuickAddModal() : renderTaskModal();
  if (modal.type === "goal") return renderGoalModal();
  if (modal.type === "batch") return renderBatchModal();
  if (modal.type === "goal-achieve") return renderGoalAchieveModal();
  if (modal.type === "goal-delete") return renderGoalDeleteModal();
  return "";
}

function renderTaskModal() {
  const modal = state.ui.modal;
  const task = modal.taskId ? getTask(modal.taskId) : null;
  const template = modal.templateId ? state.templates.find((item) => item.id === modal.templateId) : null;
  const selectedPlan = task ? task.plannedDate || "" : modal.presetDate || "";
  const selectedGoal = task ? task.goalId || "" : modal.goalId || "";
  const selectedCategory = task ? task.category : template?.category || modal.quickCategory || state.settings.defaultCategory;
  const selectedPriority = task ? task.priority : template?.priority || modal.quickPriority || "normal";
  const title = task ? task.title : template?.title || "";
  const note = task ? task.note : template?.note || "";
  const tags = task ? task.tags : template?.tags || [];
  return `
    <div class="modal-backdrop" data-action="close-modal" role="presentation"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="task-modal-title"><div class="modal-header"><div><h3 id="task-modal-title">${task ? "编辑待办" : "新建待办"}</h3><p>${task ? "把属性调整到当前真实状态。" : "标题先行，其他信息之后再补也可以。"}</p></div><button class="close-button" data-action="close-modal" aria-label="关闭">${icon("close")}</button></div><form class="modal-body" data-form="task" data-task-id="${task?.id || ""}"><div class="form-grid"><div class="form-field full title-field"><label for="task-title">要做什么？</label><input id="task-title" class="title-field-input" name="title" value="${escapeHtml(title)}" placeholder="写下一件具体的事" maxlength="120" required /></div><div class="form-error" data-form-error>标题不能为空</div><div class="form-field full"><label for="task-note">备注详情 <span class="faint">（可选）</span></label><textarea id="task-note" name="note" placeholder="补充背景、下一步或完成标准">${escapeHtml(note)}</textarea></div><div class="form-field"><label for="task-category">分类</label><select id="task-category" name="category"><option value="work" ${selectedCategory === "work" ? "selected" : ""}>工作</option><option value="life" ${selectedCategory === "life" ? "selected" : ""}>生活</option></select></div><div class="form-field"><label for="task-priority">优先级</label><select id="task-priority" name="priority"><option value="normal" ${selectedPriority === "normal" ? "selected" : ""}>普通</option><option value="high" ${selectedPriority === "high" ? "selected" : ""}>高</option></select></div><div class="form-field"><label for="task-date">计划日期</label><input id="task-date" type="date" name="plannedDate" value="${selectedPlan}" /><span class="form-help">只保存自然日，不设置截止时刻。</span></div><div class="form-field"><label for="task-goal">所属长期目标</label><select id="task-goal" name="goalId"><option value="">独立待办</option>${state.goals.map((goal) => `<option value="${goal.id}" ${selectedGoal === goal.id ? "selected" : ""}>${escapeHtml(goal.title)}${goal.status === "achieved" ? "（已达成）" : ""}</option>`).join("")}</select></div><div class="form-field full"><label for="task-tags">标签 <span class="faint">（用逗号分隔）</span></label><input id="task-tags" name="tags" value="${escapeHtml(tags.join(", "))}" placeholder="例如：论文，沟通，采购" /></div>${!task && state.templates.length ? `<div class="form-field full"><label for="task-template">从模板填充 <span class="faint">（不覆盖日期和目标）</span></label><select id="task-template" data-action="apply-template"><option value="">不使用模板</option>${state.templates.map((item) => `<option value="${item.id}">${escapeHtml(item.title)}</option>`).join("")}</select></div>` : ""}</div><div class="form-help" style="margin-top:14px;">按 Enter 提交标题也可以；完成后仍可在右侧详情中补充子步骤。</div></form><div class="modal-footer"><button class="ghost-button" data-action="close-modal">取消</button><button class="primary-button" data-action="submit-form" data-form-target="task">${icon("check")} ${task ? "保存修改" : "添加待办"}</button></div></section></div>`;
}

function renderQuickAddModal() {
  const modal = state.ui.modal;
  return `<div class="modal-backdrop" data-action="close-modal" role="presentation"><section class="modal quick-add-modal" role="dialog" aria-modal="true" aria-labelledby="quick-add-title"><div class="modal-header"><div><h3 id="quick-add-title">${icon("plus")} 快速添加待办</h3><p>先把想法放下来，计划日期默认保持未安排。</p></div><button class="close-button" data-action="close-modal" aria-label="关闭">${icon("close")}</button></div><form class="modal-body" data-form="quick-task"><input class="quick-add-input" name="title" placeholder="例如：明天修改论文第三章" maxlength="120" autocomplete="off" required /><div class="quick-add-options"><button type="button" class="quick-option ${!modal.presetDate ? "active" : ""}" data-action="quick-date" data-value="">未安排</button><button type="button" class="quick-option ${modal.presetDate === dateKey() ? "active" : ""}" data-action="quick-date" data-value="${dateKey()}">今天</button><button type="button" class="quick-option ${modal.presetDate === offsetDate(1) ? "active" : ""}" data-action="quick-date" data-value="${offsetDate(1)}">明天</button><button type="button" class="quick-option ${modal.presetDate && ![dateKey(), offsetDate(1)].includes(modal.presetDate) ? "active" : ""}" data-action="quick-date-custom">选择日期</button><input type="hidden" name="plannedDate" value="${modal.presetDate || ""}" /><span class="quick-option" style="margin-left:auto;">${categoryLabel(modal.quickCategory)} · ${modal.quickPriority === "high" ? "高优" : "普通"}</span></div></form><div class="modal-footer"><span class="faint" style="font-size:10px;">Enter 保存 · Esc 取消</span><button class="primary-button" data-action="submit-form" data-form-target="quick-task">${icon("check")} 添加</button></div></section></div>`;
}

function renderGoalModal() {
  const modal = state.ui.modal;
  const goal = modal.goalId ? getGoal(modal.goalId) : null;
  return `<div class="modal-backdrop" data-action="close-modal" role="presentation"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="goal-modal-title"><div class="modal-header"><div><h3 id="goal-modal-title">${goal ? "编辑长期目标" : "新建长期目标"}</h3><p>目标进度只由关联待办自动计算，不需要手动维护百分比。</p></div><button class="close-button" data-action="close-modal" aria-label="关闭">${icon("close")}</button></div><form class="modal-body" data-form="goal" data-goal-id="${goal?.id || ""}"><div class="form-grid"><div class="form-field full title-field"><label for="goal-title">目标是什么？</label><input id="goal-title" class="goal-title-input" name="title" value="${escapeHtml(goal?.title || "")}" placeholder="例如：完成毕业论文" maxlength="120" required /></div><div class="form-error" data-form-error>目标标题不能为空</div><div class="form-field full"><label for="goal-note">目标说明 <span class="faint">（可选）</span></label><textarea id="goal-note" name="note" placeholder="描述你想交付的成果">${escapeHtml(goal?.note || "")}</textarea></div><div class="form-field"><label for="goal-category">分类</label><select id="goal-category" name="category"><option value="work" ${goal?.category !== "life" ? "selected" : ""}>工作</option><option value="life" ${goal?.category === "life" ? "selected" : ""}>生活</option></select></div><div class="form-field"><label for="goal-priority">优先级</label><select id="goal-priority" name="priority"><option value="normal" ${goal?.priority !== "high" ? "selected" : ""}>普通</option><option value="high" ${goal?.priority === "high" ? "selected" : ""}>高</option></select></div><div class="form-field"><label for="goal-date">计划完成日期</label><input id="goal-date" type="date" name="plannedFinishDate" value="${goal?.plannedFinishDate || ""}" /><span class="form-help">只作为方向提醒，不会产生强提醒。</span></div></div></form><div class="modal-footer"><button class="ghost-button" data-action="close-modal">取消</button><button class="primary-button" data-action="submit-form" data-form-target="goal">${icon("check")} ${goal ? "保存修改" : "创建目标"}</button></div></section></div>`;
}

function renderBatchModal() {
  const operation = state.ui.modal.operation;
  const labels = { priority: "修改优先级", category: "修改分类", date: "设置计划日期", goal: "挂载长期目标" };
  const content = operation === "priority" ? `<select name="value"><option value="high">高优先级</option><option value="normal">普通优先级</option></select>` : operation === "category" ? `<select name="value"><option value="work">工作</option><option value="life">生活</option></select>` : operation === "date" ? `<input type="date" name="value" value="${dateKey()}" /><span class="form-help">批量修改日期会写入每一条待办的计划历史。</span>` : `<select name="value"><option value="">解除目标关联</option>${state.goals.filter((goal) => goal.status === "active").map((goal) => `<option value="${goal.id}">${escapeHtml(goal.title)}</option>`).join("")}</select>`;
  return `<div class="modal-backdrop" data-action="close-modal" role="presentation"><section class="modal small" role="dialog" aria-modal="true"><div class="modal-header"><div><h3>${labels[operation]}</h3><p>将应用到已选择的 ${state.ui.selectedTaskIds.length} 项待办。</p></div><button class="close-button" data-action="close-modal" aria-label="关闭">${icon("close")}</button></div><form class="modal-body" data-form="batch" data-operation="${operation}"><div class="form-field">${content}</div></form><div class="modal-footer"><button class="ghost-button" data-action="close-modal">取消</button><button class="primary-button" data-action="submit-form" data-form-target="batch">${icon("check")} 应用修改</button></div></section></div>`;
}

function renderGoalAchieveModal() {
  const goal = getGoal(state.ui.modal.goalId);
  const remaining = goal ? goalStats(goal).remaining : 0;
  if (!goal) return "";
  return `<div class="modal-backdrop" data-action="close-modal" role="presentation"><section class="modal small" role="dialog" aria-modal="true"><div class="modal-header"><div><h3>达成这个目标？</h3><p>「${escapeHtml(goal.title)}」还有 ${remaining} 个未完成待办，请选择如何处理。</p></div><button class="close-button" data-action="close-modal" aria-label="关闭">${icon("close")}</button></div><form class="modal-body" data-form="goal-achieve"><div class="inline-choice-list"><label class="choice-card"><input type="radio" name="option" value="detach" ${state.ui.modal.option === "detach" ? "checked" : ""} /><span><strong>转为独立待办</strong><span>保留任务、日期和优先级，解除目标关联。</span></span></label><label class="choice-card"><input type="radio" name="option" value="complete" ${state.ui.modal.option === "complete" ? "checked" : ""} /><span><strong>全部标记为完成</strong><span>现在统一完成，并计入实际完成数量。</span></span></label><label class="choice-card"><input type="radio" name="option" value="delete" ${state.ui.modal.option === "delete" ? "checked" : ""} /><span><strong>删除这些待办</strong><span>任务将被移除，不计入完成统计。</span></span></label></div></form><div class="modal-footer"><button class="ghost-button" data-action="close-modal">取消</button><button class="primary-button" data-action="submit-form" data-form-target="goal-achieve">${icon("checkCircle")} 确认达成</button></div></section></div>`;
}

function renderGoalDeleteModal() {
  const goal = getGoal(state.ui.modal.goalId);
  const remaining = goal ? goalStats(goal).remaining : 0;
  if (!goal) return "";
  return `<div class="modal-backdrop" data-action="close-modal" role="presentation"><section class="modal small" role="dialog" aria-modal="true"><div class="modal-header"><div><h3>删除目标</h3><p>「${escapeHtml(goal.title)}」${remaining ? `还有 ${remaining} 个未完成关联待办。` : "没有未完成关联待办。"}</p></div><button class="close-button" data-action="close-modal" aria-label="关闭">${icon("close")}</button></div><form class="modal-body" data-form="goal-delete"><div class="inline-choice-list"><label class="choice-card"><input type="radio" name="option" value="detach" ${state.ui.modal.option === "detach" ? "checked" : ""} /><span><strong>转为独立待办</strong><span>保留关联待办，不再归属于这个目标。</span></span></label><label class="choice-card"><input type="radio" name="option" value="delete" ${state.ui.modal.option === "delete" ? "checked" : ""} /><span><strong>同时删除关联待办</strong><span>只删除未完成的关联待办，完成历史仍然保留。</span></span></label></div></form><div class="modal-footer"><button class="ghost-button" data-action="close-modal">取消</button><button class="danger-button" data-action="submit-form" data-form-target="goal-delete">${icon("trash")} 确认删除</button></div></section></div>`;
}

function renderContextMenu() {
  const menu = state.ui.contextMenu;
  if (!menu) return "";
  const task = getTask(menu.taskId);
  if (!task || task.status === "deleted") return "";
  const attachLabel = task.goalId ? "解除目标关联" : "挂载到目标";
  const attachIcon = task.goalId ? "unlink" : "link";
  return `<div class="context-menu" style="left:${menu.x}px; top:${menu.y}px" data-context-menu><button data-action="toggle-task" data-id="${task.id}">${icon(task.status === "completed" ? "undo" : "checkCircle")} ${task.status === "completed" ? "撤销完成" : "完成"}</button><button data-action="open-task-edit" data-id="${task.id}">${icon("edit")} 编辑</button><div class="context-divider"></div>${task.priority === "high" ? `<button data-action="set-priority" data-id="${task.id}" data-value="normal">${icon("sparkles")} 设为普通</button>` : `<button data-action="set-priority" data-id="${task.id}" data-value="high">${icon("sparkles")} 设为高优</button>`}<button data-action="set-task-date" data-id="${task.id}" data-value="${dateKey()}">${icon("sun")} 安排到今天</button><button data-action="set-task-date" data-id="${task.id}" data-value="${offsetDate(1)}">${icon("clock")} 安排到明天</button><button data-action="open-task-date" data-id="${task.id}">${icon("calendar")} 选择日期</button><div class="context-divider"></div><button data-action="toggle-task-goal" data-id="${task.id}">${icon(attachIcon)} ${attachLabel}</button><button data-action="save-template" data-id="${task.id}">${icon("copy")} 保存为模板</button><div class="context-divider"></div><button class="danger" data-action="delete-task" data-id="${task.id}">${icon("trash")} 删除</button></div>`;
}

function renderToasts() {
  return `<div class="toast-stack">${(state.ui.toasts || []).map((toast) => `<div class="toast ${toast.type}" data-toast-id="${toast.id}">${icon(toast.type === "warning" ? "alert" : "checkCircle")}<span class="toast-text">${escapeHtml(toast.message)}</span>${toast.actionLabel ? `<button class="toast-action" data-action="undo-toast" data-id="${toast.id}">${escapeHtml(toast.actionLabel)}</button>` : ""}</div>`).join("")}</div>`;
}

function bindDynamicFocus() {
  const searchInput = document.querySelector("[data-search-input]");
  if (state.ui.focusSearch && searchInput) {
    searchInput.focus();
    searchInput.setSelectionRange(searchInput.value.length, searchInput.value.length);
    state.ui.focusSearch = false;
  }
  const archiveSearch = document.querySelector("[data-archive-search]");
  if (state.ui.focusArchiveSearch && archiveSearch) {
    archiveSearch.focus();
    archiveSearch.setSelectionRange(archiveSearch.value.length, archiveSearch.value.length);
    state.ui.focusArchiveSearch = false;
  }
  const modalInput = document.querySelector(state.ui.modal?.quick ? ".quick-add-input" : state.ui.modal?.type === "task" ? ".title-field-input" : state.ui.modal?.type === "goal" ? ".goal-title-input" : "");
  if (state.ui.modal && modalInput && document.activeElement === document.body) modalInput.focus();
}

function selectedTaskObjects() {
  return state.ui.selectedTaskIds.map(getTask).filter((task) => task && task.status !== "deleted");
}

function toggleSelection(id, checked) {
  if (checked && !state.ui.selectedTaskIds.includes(id)) state.ui.selectedTaskIds.push(id);
  if (!checked) state.ui.selectedTaskIds = state.ui.selectedTaskIds.filter((selectedId) => selectedId !== id);
  render();
}

function batchComplete() {
  const tasks = selectedTaskObjects();
  if (!tasks.length) return;
  const snapshots = tasks.map((task) => [task.id, clone(task)]);
  tasks.forEach((task) => {
    if (task.status === "todo") {
      task.status = "completed";
      task.completedAt = nowIso();
      task.updatedAt = nowIso();
      markPlanCompletion(task);
    }
  });
  state.ui.selectedTaskIds = [];
  persist();
  render();
  pushToast(`已完成 ${tasks.length} 项待办`, "撤回", () => {
    snapshots.forEach(([id, snapshot]) => restoreTaskWithoutToast(id, snapshot));
    persist();
    render();
  });
}

function batchDelete() {
  const tasks = selectedTaskObjects();
  if (!tasks.length) return;
  const snapshots = tasks.map((task) => [task.id, clone(task)]);
  tasks.forEach((task) => {
    task.status = "deleted";
    task.deletedAt = nowIso();
    task.updatedAt = nowIso();
    const current = currentPlanHistory(task);
    if (current && current.plannedDate > dateKey()) {
      current.cancelledBeforeDue = true;
      current.supersededAt = nowIso();
    }
  });
  state.ui.selectedTaskIds = [];
  persist();
  render();
  pushToast(`已移除 ${tasks.length} 项待办`, "撤回", () => {
    snapshots.forEach(([id, snapshot]) => restoreTaskWithoutToast(id, snapshot));
    persist();
    render();
  }, "warning");
}

function restoreTaskWithoutToast(id, snapshot) {
  const index = state.tasks.findIndex((task) => task.id === id);
  if (index >= 0) state.tasks[index] = clone(snapshot);
}

function applyBatch(operation, value) {
  const tasks = selectedTaskObjects();
  if (!tasks.length) return;
  const snapshots = tasks.map((task) => [task.id, clone(task)]);
  tasks.forEach((task) => {
    if (operation === "priority") task.priority = value === "high" ? "high" : "normal";
    if (operation === "category") task.category = value === "life" ? "life" : "work";
    if (operation === "date") setTaskPlanDate(task, value);
    if (operation === "goal") task.goalId = value || null;
    task.updatedAt = nowIso();
  });
  state.ui.selectedTaskIds = [];
  state.ui.modal = null;
  persist();
  render();
  pushToast(`已更新 ${tasks.length} 项待办`, "撤回", () => {
    snapshots.forEach(([id, snapshot]) => restoreTaskWithoutToast(id, snapshot));
    persist();
    render();
  });
}

function submitTaskForm(form, quick = false) {
  const formData = new FormData(form);
  const title = String(formData.get("title") || "").trim();
  const error = form.querySelector("[data-form-error]");
  if (!title) {
    error?.classList.add("visible");
    form.querySelector("[name=title]")?.focus();
    return;
  }
  const modal = state.ui.modal;
  if (quick) {
    const task = makeTask({
      title,
      category: modal.quickCategory,
      priority: modal.quickPriority,
      plannedDate: String(formData.get("plannedDate") || "") || null
    });
    state.tasks.unshift(task);
    state.ui.modal = null;
    persist();
    render();
    pushToast("已快速添加待办", null);
    return;
  }
  const taskId = form.dataset.taskId;
  const task = taskId ? getTask(taskId) : null;
  const tags = String(formData.get("tags") || "").split(/[，,]/).map((tag) => tag.trim()).filter(Boolean).filter((tag, index, list) => list.indexOf(tag) === index);
  const changes = {
    title,
    note: String(formData.get("note") || "").trim(),
    category: formData.get("category") === "life" ? "life" : "work",
    priority: formData.get("priority") === "high" ? "high" : "normal",
    plannedDate: String(formData.get("plannedDate") || "") || null,
    goalId: String(formData.get("goalId") || "") || null,
    tags
  };
  if (task) {
    updateTask(task, changes);
    state.ui.modal = null;
    state.ui.drawerTaskId = task.id;
    render();
    pushToast("待办已更新", null);
  } else {
    const template = modal.templateId ? state.templates.find((item) => item.id === modal.templateId) : null;
    const newTask = makeTask({ ...changes, subtasks: template?.subtasks?.map((step, index) => ({ title: step, sortRank: index })) || [] });
    state.tasks.unshift(newTask);
    state.ui.modal = null;
    persist();
    render();
    pushToast("待办已添加", null);
  }
}

function submitGoalForm(form) {
  const formData = new FormData(form);
  const title = String(formData.get("title") || "").trim();
  const error = form.querySelector("[data-form-error]");
  if (!title) {
    error?.classList.add("visible");
    form.querySelector("[name=title]")?.focus();
    return;
  }
  const goalId = form.dataset.goalId;
  const goal = goalId ? getGoal(goalId) : null;
  const changes = {
    title,
    note: String(formData.get("note") || "").trim(),
    category: formData.get("category") === "life" ? "life" : "work",
    priority: formData.get("priority") === "high" ? "high" : "normal",
    plannedFinishDate: String(formData.get("plannedFinishDate") || "") || null
  };
  if (goal) {
    Object.assign(goal, changes, { updatedAt: nowIso() });
    state.ui.modal = null;
    persist();
    render();
    pushToast("目标已更新", null);
  } else {
    const newGoal = makeGoal(changes);
    state.goals.unshift(newGoal);
    state.ui.modal = null;
    persist();
    render();
    pushToast("长期目标已创建", null);
  }
}

function submitSubtaskForm(form) {
  const task = getTask(form.dataset.taskId);
  const title = String(new FormData(form).get("title") || "").trim();
  if (!task || !title) return;
  task.subtasks.push({ id: makeId("step"), title, completed: false, sortRank: task.subtasks.length, createdAt: nowIso() });
  task.updatedAt = nowIso();
  persist();
  render();
}

function submitBatchForm(form) {
  const value = String(new FormData(form).get("value") || "");
  applyBatch(form.dataset.operation, value);
}

function submitGoalAchieveForm(form) {
  const option = String(new FormData(form).get("option") || "detach");
  achieveGoal(state.ui.modal.goalId, option);
}

function submitGoalDeleteForm(form) {
  const option = String(new FormData(form).get("option") || "detach");
  deleteGoal(state.ui.modal.goalId, option);
}

function handleSubmit(event) {
  const form = event.target.closest("form[data-form]");
  if (!form) return;
  event.preventDefault();
  const type = form.dataset.form;
  if (type === "task") submitTaskForm(form);
  if (type === "quick-task") submitTaskForm(form, true);
  if (type === "goal") submitGoalForm(form);
  if (type === "subtask") submitSubtaskForm(form);
  if (type === "batch") submitBatchForm(form);
  if (type === "goal-achieve") submitGoalAchieveForm(form);
  if (type === "goal-delete") submitGoalDeleteForm(form);
}

function handleChange(event) {
  const target = event.target;
  if (target.matches("[data-batch-select]")) {
    toggleSelection(target.dataset.id, target.checked);
    return;
  }
  if (target.matches("[data-setting]")) {
    const key = target.dataset.setting;
    state.settings[key] = target.type === "checkbox" ? target.checked : target.value;
    persist();
    render();
    pushToast("设置已保存", null);
    return;
  }
  if (target.matches("[data-filter-key]")) {
    state.ui.filters[target.dataset.filterKey] = target.value;
    render();
    return;
  }
  if (target.matches("[data-inline-field]")) {
    const task = getTask(target.dataset.id);
    if (!task) return;
    const field = target.dataset.inlineField;
    const value = field === "plannedDate" ? (target.value || null) : field === "goalId" ? (target.value || null) : target.value;
    updateTask(task, { [field]: value });
    pushToast("已保存属性", null);
    return;
  }
  if (target.matches("[data-archive-category]")) {
    state.ui.archiveCategory = target.value;
    render();
    return;
  }
  if (target.matches("[data-action=apply-template]")) {
    const template = state.templates.find((item) => item.id === target.value);
    if (!template) {
      if (state.ui.modal) state.ui.modal.templateId = null;
      return;
    }
    if (state.ui.modal) state.ui.modal.templateId = template.id;
    const form = target.closest("form");
    if (!form) return;
    form.elements.title.value = template.title;
    form.elements.note.value = template.note;
    form.elements.category.value = template.category;
    form.elements.priority.value = template.priority;
    form.elements.tags.value = template.tags.join(", ");
    return;
  }
  if (target.matches("input[type=radio][name=option]")) {
    if (state.ui.modal) state.ui.modal.option = target.value;
  }
}

function handleInput(event) {
  const target = event.target;
  if (target.matches("[data-search-input]")) {
    state.ui.searchQuery = target.value;
    state.ui.focusSearch = true;
    if (state.ui.searchQuery.trim()) state.ui.view = state.ui.view === "search" ? "search" : state.ui.view;
    state.ui.selectedTaskIds = [];
    render();
    return;
  }
  if (target.matches("[data-archive-search]")) {
    state.ui.archiveQuery = target.value;
    state.ui.focusArchiveSearch = true;
    render();
  }
}

function handleClick(event) {
  const target = event.target;
  if (state.ui.contextMenu && !target.closest("[data-context-menu]") && !target.closest("[data-action=open-context]")) {
    state.ui.contextMenu = null;
    render();
  }
  const actionTarget = target.closest("[data-action]");
  if (!actionTarget) return;
  const action = actionTarget.dataset.action;
  if (action === "close-modal") {
    if (!actionTarget.classList.contains("modal-backdrop") || !target.closest(".modal")) {
      state.ui.modal = null;
      render();
    }
    return;
  }
  if (action === "close-drawer") {
    if (!actionTarget.classList.contains("drawer-backdrop") || !target.closest(".drawer")) {
      state.ui.drawerTaskId = null;
      render();
    }
    return;
  }
  if (action === "navigate") {
    navigate(actionTarget.dataset.view);
    return;
  }
  if (action === "toggle-sidebar") {
    state.ui.sidebarOpen = !state.ui.sidebarOpen;
    render();
    return;
  }
  if (action === "open-new-task") {
    openTaskModal(null, { presetDate: actionTarget.dataset.presetDate !== undefined ? actionTarget.dataset.presetDate || null : undefined, goalId: actionTarget.dataset.goalId || null });
    return;
  }
  if (action === "open-quick-add") {
    openTaskModal(null, { quick: true });
    return;
  }
  if (action === "open-new-goal") {
    openGoalModal();
    return;
  }
  if (action === "clear-search") {
    state.ui.searchQuery = "";
    state.ui.focusSearch = false;
    render();
    return;
  }
  if (action === "quick-date") {
    if (state.ui.modal?.type === "task") state.ui.modal.presetDate = actionTarget.dataset.value || null;
    render();
    window.setTimeout(() => document.querySelector(".quick-add-input")?.focus(), 0);
    return;
  }
  if (action === "quick-date-custom") {
    const nextDate = window.prompt("请输入计划日期（YYYY-MM-DD）", state.ui.modal?.presetDate || offsetDate(2));
    if (nextDate && /^\d{4}-\d{2}-\d{2}$/.test(nextDate)) {
      if (state.ui.modal?.type === "task") state.ui.modal.presetDate = nextDate;
      render();
      window.setTimeout(() => document.querySelector(".quick-add-input")?.focus(), 0);
    }
    return;
  }
  if (action === "open-task" || action === "open-task-edit") {
    if (action === "open-task-edit") {
      openTaskModal(actionTarget.dataset.id);
      return;
    }
    openTaskDrawer(actionTarget.dataset.id);
    return;
  }
  if (action === "open-context") {
    const task = getTask(actionTarget.dataset.id);
    if (!task) return;
    const width = 204;
    const height = 370;
    state.ui.contextMenu = { taskId: task.id, x: Math.min(event.clientX, window.innerWidth - width - 10), y: Math.min(event.clientY, window.innerHeight - height - 10) };
    render();
    return;
  }
  if (action === "toggle-task") {
    toggleTask(actionTarget.dataset.id);
    return;
  }
  if (action === "toggle-subtask") {
    const task = getTask(actionTarget.dataset.taskId);
    const step = task?.subtasks.find((item) => item.id === actionTarget.dataset.id);
    if (!task || !step) return;
    step.completed = !step.completed;
    task.updatedAt = nowIso();
    persist();
    render();
    return;
  }
  if (action === "delete-subtask") {
    const task = getTask(actionTarget.dataset.taskId);
    if (!task) return;
    task.subtasks = task.subtasks.filter((item) => item.id !== actionTarget.dataset.id);
    task.updatedAt = nowIso();
    persist();
    render();
    pushToast("子步骤已删除", null);
    return;
  }
  if (action === "delete-task") {
    state.ui.drawerTaskId = null;
    deleteTask(actionTarget.dataset.id);
    return;
  }
  if (action === "save-template") {
    const task = getTask(actionTarget.dataset.id);
    if (task) saveTemplate(task);
    return;
  }
  if (action === "set-priority") {
    const task = getTask(actionTarget.dataset.id);
    if (task) updateTask(task, { priority: actionTarget.dataset.value });
    state.ui.contextMenu = null;
    pushToast("优先级已更新", null);
    return;
  }
  if (action === "set-task-date") {
    const task = getTask(actionTarget.dataset.id);
    if (task) updateTask(task, { plannedDate: actionTarget.dataset.value || null });
    state.ui.contextMenu = null;
    pushToast("计划日期已更新", null);
    return;
  }
  if (action === "open-task-date") {
    openTaskModal(actionTarget.dataset.id);
    return;
  }
  if (action === "toggle-task-goal") {
    const task = getTask(actionTarget.dataset.id);
    if (!task) return;
    if (task.goalId) {
      updateTask(task, { goalId: null });
      state.ui.contextMenu = null;
      pushToast("已解除目标关联", null);
    } else if (state.goals.filter((goal) => goal.status === "active").length === 1) {
      const goal = state.goals.find((item) => item.status === "active");
      updateTask(task, { goalId: goal.id });
      state.ui.contextMenu = null;
      pushToast(`已挂载到「${goal.title}」`, null);
    } else {
      openTaskModal(task.id);
    }
    return;
  }
  if (action === "set-view-mode") {
    state.ui[actionTarget.dataset.modeKey || "allViewMode"] = actionTarget.dataset.viewMode;
    render();
    return;
  }
  if (action === "toggle-filters") {
    state.ui.filterOpen = !state.ui.filterOpen;
    render();
    return;
  }
  if (action === "clear-filter") {
    state.ui.filters[actionTarget.dataset.filterKey] = actionTarget.dataset.filterKey === "status" ? "todo" : "all";
    render();
    return;
  }
  if (action === "reset-filters") {
    state.ui.filters = { category: "all", priority: "all", goal: "all", status: "todo", tag: "all" };
    render();
    return;
  }
  if (action === "toggle-completed") {
    state.ui.completedOpen = !state.ui.completedOpen;
    render();
    return;
  }
  if (action === "focus-overdue") {
    window.scrollTo({ top: 220, behavior: state.settings.reduceMotion ? "auto" : "smooth" });
    return;
  }
  if (action === "open-goal") {
    state.ui.selectedGoalId = actionTarget.dataset.id;
    state.ui.view = "goals";
    state.ui.drawerTaskId = null;
    state.ui.sidebarOpen = false;
    render();
    return;
  }
  if (action === "back-to-goals") {
    state.ui.selectedGoalId = null;
    state.ui.view = "goals";
    render();
    return;
  }
  if (action === "edit-goal") {
    openGoalModal(actionTarget.dataset.id);
    return;
  }
  if (action === "achieve-goal") {
    const goal = getGoal(actionTarget.dataset.id);
    if (!goal) return;
    if (goalStats(goal).remaining) openGoalAchieveModal(goal.id);
    else achieveGoal(goal.id, "detach");
    return;
  }
  if (action === "restore-goal") {
    restoreGoal(actionTarget.dataset.id);
    return;
  }
  if (action === "delete-goal") {
    const goal = getGoal(actionTarget.dataset.id);
    if (!goal) return;
    if (goalStats(goal).remaining) openGoalDeleteModal(goal.id);
    else deleteGoal(goal.id, "detach");
    return;
  }
  if (action === "set-goals-status") {
    state.ui.goalsStatus = actionTarget.dataset.value;
    render();
    return;
  }
  if (action === "set-goals-category") {
    state.ui.goalsCategory = actionTarget.dataset.value;
    render();
    return;
  }
  if (action === "set-archive-tab") {
    state.ui.archiveTab = actionTarget.dataset.value;
    render();
    return;
  }
  if (action === "undo-toast") {
    runUndo(actionTarget.dataset.id);
    return;
  }
  if (action === "clear-selection") {
    state.ui.selectedTaskIds = [];
    render();
    return;
  }
  if (action === "batch-complete") {
    batchComplete();
    return;
  }
  if (action === "batch-delete") {
    batchDelete();
    return;
  }
  if (action === "batch-priority" || action === "batch-category") {
    applyBatch(action === "batch-priority" ? "priority" : "category", actionTarget.dataset.value);
    return;
  }
  if (action === "batch-date" || action === "batch-goal") {
    openBatchModal(action === "batch-date" ? "date" : "goal");
    return;
  }
  if (action === "set-theme") {
    state.settings.theme = actionTarget.dataset.value;
    persist();
    render();
    return;
  }
  if (action === "edit-shortcut") {
    const next = window.prompt("请输入快速添加快捷键", state.settings.shortcut);
    if (next?.trim()) {
      state.settings.shortcut = next.trim();
      persist();
      render();
      pushToast("快捷键偏好已保存", null);
    }
    return;
  }
  if (action === "export-json") {
    exportJson();
    return;
  }
  if (action === "export-csv") {
    exportCsv();
    return;
  }
  if (action === "import-json") {
    document.querySelector("#import-input")?.click();
    return;
  }
  if (action === "backup-now") {
    state.meta.lastBackupDate = dateKey();
    persist();
    pushToast("本地备份快照已生成", null);
    return;
  }
  if (action === "reset-data") {
    if (window.confirm("确定清空当前浏览器中的所有待办、目标和模板吗？此操作不可撤回，建议先导出备份。")) {
      state = createEmptyState();
      state.ui = createUiState();
      persist();
      render();
      pushToast("已清空数据", null, null, "warning");
    }
    return;
  }
  if (action === "load-demo") {
    state = createDemoState();
    state.ui = createUiState();
    persist();
    render();
    pushToast("示例数据已载入", null);
    return;
  }
  if (action === "use-template") {
    openTaskModal(null, { templateId: actionTarget.dataset.id, presetDate: null });
    return;
  }
  if (action === "delete-template") {
    deleteTemplate(actionTarget.dataset.id);
    return;
  }
  if (action === "submit-form") {
    const form = document.querySelector(`form[data-form="${actionTarget.dataset.formTarget}"]`);
    if (form) form.requestSubmit();
  }
}

function handleContextMenu(event) {
  const row = event.target.closest("[data-task-row]");
  if (!row) return;
  event.preventDefault();
  const task = getTask(row.dataset.id);
  if (!task) return;
  const width = 204;
  const height = 370;
  state.ui.contextMenu = { taskId: task.id, x: Math.min(event.clientX, window.innerWidth - width - 10), y: Math.min(event.clientY, window.innerHeight - height - 10) };
  render();
}

function handleDragStart(event) {
  const row = event.target.closest("[data-task-row]");
  if (!row || row.getAttribute("draggable") === "false") return;
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", JSON.stringify({ taskId: row.dataset.id }));
  row.classList.add("dragging");
}

function handleDragEnd(event) {
  const row = event.target.closest("[data-task-row]");
  row?.classList.remove("dragging");
  document.querySelectorAll(".drag-over, .drop-target").forEach((element) => element.classList.remove("drag-over", "drop-target"));
}

function handleDragOver(event) {
  const target = event.target.closest("[data-drop-priority], [data-drop-status], [data-task-row]");
  if (!target) return;
  event.preventDefault();
  if (target.matches("[data-task-row]")) target.classList.add("drop-target");
  else target.classList.add("drag-over");
}

function parseDragId(event) {
  try {
    return JSON.parse(event.dataTransfer.getData("text/plain")).taskId;
  } catch {
    return null;
  }
}

function handleDrop(event) {
  const target = event.target.closest("[data-drop-priority], [data-drop-status], [data-task-row]");
  const taskId = parseDragId(event);
  if (!target || !taskId) return;
  event.preventDefault();
  const task = getTask(taskId);
  if (!task) return;
  if (target.dataset.dropPriority) {
    task.priority = target.dataset.dropPriority === "high" ? "high" : "normal";
    task.sortRank = Date.now();
    task.updatedAt = nowIso();
    persist();
    render();
    pushToast(`已移到${priorityLabel(task.priority)}`, null);
  } else if (target.dataset.dropStatus) {
    if (target.dataset.dropStatus === "completed" && task.status !== "completed") toggleTask(task.id);
    if (target.dataset.dropStatus === "todo" && task.status === "completed") toggleTask(task.id);
  } else if (target.dataset.taskRow && target.dataset.id !== taskId) {
    const destination = getTask(target.dataset.id);
    if (!destination) return;
    task.priority = destination.priority;
    task.sortRank = destination.sortRank - 0.25;
    task.updatedAt = nowIso();
    persist();
    render();
  }
}

function exportJson() {
  const payload = {
    app: "piggyplan",
    version: 1,
    exportedAt: nowIso(),
    data: (() => { const value = clone(state); delete value.ui; return value; })()
  };
  downloadFile(`piggyplan-backup-${dateKey()}.json`, JSON.stringify(payload, null, 2), "application/json");
  pushToast("完整备份已导出", null);
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

function exportCsv() {
  const rows = [["标题", "状态", "分类", "优先级", "计划日期", "实际完成日期", "所属目标", "标签", "备注"]];
  state.tasks.filter((task) => task.status === "completed").forEach((task) => rows.push([
    task.title,
    statusLabel(task.status),
    categoryLabel(task.category),
    priorityLabel(task.priority),
    task.plannedDate ? formatDate(task.plannedDate) : "未安排",
    task.completedAt ? formatDate(dateKey(new Date(task.completedAt))) : "",
    getGoal(task.goalId)?.title || "独立待办",
    task.tags.join("、"),
    task.note
  ]));
  const csv = "\uFEFF" + rows.map((row) => row.map(csvCell).join(",")).join("\r\n");
  downloadFile(`piggyplan-archive-${dateKey()}.csv`, csv, "text/csv;charset=utf-8");
  pushToast("历史 CSV 已导出", null);
}

function downloadFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function importJson(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const payload = JSON.parse(String(reader.result || ""));
      const imported = payload?.data || payload;
      if (!imported || !Array.isArray(imported.tasks) || !Array.isArray(imported.goals)) throw new Error("invalid");
      if (!window.confirm("恢复备份会覆盖当前浏览器中的数据，是否继续？建议先导出当前数据。")) return;
      state = normalizeState(imported);
      state.ui = createUiState();
      persist();
      render();
      pushToast("备份已恢复", null);
    } catch {
      pushToast("备份文件格式不正确，未做任何修改", null, null, "warning");
    }
  };
  reader.readAsText(file);
}

function createUiState() {
  return {
    view: state.settings.startupPage || "today",
    selectedGoalId: null,
    drawerTaskId: null,
    modal: null,
    searchQuery: "",
    filterOpen: false,
    filters: { category: "all", priority: "all", goal: "all", status: "todo", tag: "all" },
    goalsStatus: "active",
    goalsCategory: "all",
    archiveTab: "tasks",
    archiveCategory: "all",
    archiveQuery: "",
    allViewMode: "list",
    goalViewMode: "list",
    completedOpen: false,
    selectedTaskIds: [],
    contextMenu: null,
    sidebarOpen: false,
    mobileMenuOpen: false
  };
}

function handleKeydown(event) {
  const key = event.key.toLowerCase();
  if ((key === "enter" || event.key === " ") && event.target.matches?.('[role="button"][data-action]')) {
    event.target.click();
    event.preventDefault();
    return;
  }
  if (event.key === "Escape") {
    if (state.ui.modal || state.ui.drawerTaskId || state.ui.contextMenu || state.ui.sidebarOpen) {
      state.ui.modal = null;
      state.ui.drawerTaskId = null;
      state.ui.contextMenu = null;
      state.ui.sidebarOpen = false;
      render();
      event.preventDefault();
    }
    return;
  }
  if (event.ctrlKey && event.altKey && key === "t") {
    openTaskModal(null, { quick: true });
    event.preventDefault();
    return;
  }
  if (event.ctrlKey && key === "n") {
    openTaskModal();
    event.preventDefault();
    return;
  }
  if (event.ctrlKey && key === "f") {
    state.ui.focusSearch = true;
    render();
    event.preventDefault();
    return;
  }
  if (event.ctrlKey && event.key === "1") { navigate("today"); event.preventDefault(); return; }
  if (event.ctrlKey && event.key === "2") { navigate("upcoming"); event.preventDefault(); return; }
  if (event.ctrlKey && event.key === "3") { navigate("all"); event.preventDefault(); return; }
  if (state.ui.modal?.quick && event.key === "Enter") {
    document.querySelector('form[data-form="quick-task"]')?.requestSubmit();
    event.preventDefault();
  }
}

function handleFileChange(event) {
  if (event.target.id !== "import-input") return;
  const file = event.target.files?.[0];
  if (file) importJson(file);
  event.target.value = "";
}

document.addEventListener("click", handleClick);
document.addEventListener("change", handleChange);
document.addEventListener("input", handleInput);
document.addEventListener("submit", handleSubmit);
document.addEventListener("contextmenu", handleContextMenu);
document.addEventListener("dragstart", handleDragStart);
document.addEventListener("dragend", handleDragEnd);
document.addEventListener("dragover", handleDragOver);
document.addEventListener("drop", handleDrop);
document.addEventListener("keydown", handleKeydown);
document.addEventListener("change", handleFileChange);

if (typeof navigator !== "undefined" && "serviceWorker" in navigator && typeof location !== "undefined" && location.protocol !== "file:") {
  navigator.serviceWorker.register("./sw.js").catch(() => {
    // Offline caching is an enhancement; the app remains fully usable without it.
  });
}

window.setInterval(() => {
  if (state.ui.lastRenderedDay !== dateKey()) {
    state.ui.lastRenderedDay = dateKey();
    render();
  }
}, 60 * 1000);

render();
