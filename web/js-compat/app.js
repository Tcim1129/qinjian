const state = {
  currentPage: "auth",
  authMode: "login",
  authMethod: "email",
  me: null,
  pairs: [],
  currentPair: null,
  profileFeedback: null,
  productPrefs: {
    aiAssistEnabled: true,
    privacyMode: "cloud",
    preferredEntry: "daily"
  },
  selectedPairType: "couple",
  selectedReportType: "daily",
  selectedMoods: [],
  uploadedImageUrl: null,
  uploadedVoiceUrl: null,
  pendingImageUpload: null,
  pendingVoiceUpload: null,
  clientAIService: null,
  clientAIAvailable: false,
  clientAIFallbackActive: false,
  clientWorkerStatus: "initializing",
  lastClientPrecheck: null,
  lastClientPrecheckGuidance: "",
  localDraftCount: 0,
  localDraftSummary: [],
  checkinMode: "form",
  agentSessionId: null,
  agentMessages: [],
  lastAgentReply: "",
  lastMessageSimulation: null,
  lastNarrativeAlignment: null,
  lastRelationshipTimeline: null,
  pendingTaskFeedback: null,
  todayStatus: null,
  notifications: [],
  homeSnapshot: null,
  reportSnapshot: null,
  timelinePageSnapshot: null,
  privacyStatus: null,
  privacyAuditEntries: [],
  adminPolicies: [],
  isAdmin: false,
  policyWorkbenchError: null,
  phoneCodeCooldown: 0,
  shouldOpenPairOnBootstrap: false,
  timelineFilters: {
    category: "all",
    tone: "all"
  },
  timelineSelectedEventId: null,
  timelineEventDetails: {},
  timelineEventLoadingId: null,
  demoMode: false,
  demoScenario: null,
  contestMode: false,
  contestSnapshot: null
};
const FIRST_LOGIN_PAIR_PROMPT_KEY = "qj_pair_prompt_seen";
const CLIENT_AI_PREFS = Object.freeze({
  aiAssistEnabled: true,
  privacyMode: "cloud",
  preferredEntry: "daily"
});
const PLAN_TYPE_LABELS = {
  low_connection_recovery: "低连接修复",
  conflict_repair_plan: "冲突修复",
  distance_compensation_plan: "异地补偿",
  self_regulation_plan: "自我调节"
};
const POLICY_STATUS_LABELS = {
  active: "生效中",
  inactive: "已停用"
};
const MOOD_TAGS = ["开心", "平静", "感动", "期待", "焦虑", "委屈", "生气", "疲惫"];
const TYPE_LABELS = { couple: "情侣", spouse: "夫妻", bestfriend: "挚友", parent: "育儿夫妻" };
const ATTACHMENT_LABELS = { secure: "安全型", anxious: "焦虑型", avoidant: "回避型", fearful: "恐惧型", unknown: "未分析" };
const ACTIVITY_LABELS = { movie: "一起看电影", meal: "共享一顿饭", chat: "视频深聊", gift: "寄一份礼物", exercise: "同步运动" };
const HEALTH_TEST_QUESTIONS = [
  { q: "你觉得和 TA 的沟通质量如何？", dim: "沟通质量", options: ["非常好", "比较好", "一般", "较差", "很差"] },
  { q: "你是否经常感受到 TA 的支持？", dim: "情感支持", options: ["总是", "经常", "有时", "偶尔", "从不"] },
  { q: "你们之间的信任程度如何？", dim: "信任程度", options: ["完全信任", "比较信任", "一般", "较弱", "很弱"] },
  { q: "你们能否说出自己的真实需求？", dim: "表达能力", options: ["总是可以", "大多可以", "有时可以", "不太可以", "几乎不能"] },
  { q: "冲突过后你们能修复关系吗？", dim: "修复能力", options: ["很快修复", "大多能修复", "有时能", "很难", "几乎不能"] },
  { q: "你是否觉得自己被尊重？", dim: "尊重感", options: ["非常强", "比较强", "一般", "较弱", "很弱"] },
  { q: "你们是否有共同生活目标？", dim: "共同愿景", options: ["非常一致", "比较一致", "一般", "较少一致", "几乎没有"] },
  { q: "这段关系是否给你带来稳定感？", dim: "安全感", options: ["非常强", "比较强", "一般", "较弱", "很弱"] },
  { q: "你们相处时是否能感到轻松？", dim: "幸福感", options: ["总是", "经常", "有时", "偶尔", "从不"] },
  { q: "总体而言，你对这段关系满意吗？", dim: "总体满意", options: ["非常满意", "比较满意", "一般", "不太满意", "很不满意"] }
];
let healthTestState = { current: 0, answers: [] };
const DEMO_QUERY_PARAM = "demo";
function deepClone(value) {
  if (value === null || value === void 0)
    return value;
  return JSON.parse(JSON.stringify(value));
}
function resolveDemoMode() {
  const params = new URLSearchParams(window.location.search);
  return params.get(DEMO_QUERY_PARAM) === "1";
}
function resolveDemoScenario() {
  return deepClone(window.QJ_DEMO_FIXTURE || null);
}
state.demoMode = resolveDemoMode();
state.demoScenario = state.demoMode ? resolveDemoScenario() : null;
state.contestMode = false;
function isDemoMode() {
  return Boolean(state.demoMode && state.demoScenario);
}
function isContestMode() {
  return false;
}
function getDemoFixture(path = "") {
  const source = state.demoScenario || null;
  if (!source || !path)
    return source;
  return path.split(".").reduce((current, key) => current && current[key] !== void 0 ? current[key] : null, source);
}
function updateQueryMode(param, enabled) {
  const params = new URLSearchParams(window.location.search);
  if (enabled) {
    params.set(param, "1");
  } else {
    params.delete(param);
  }
  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash || ""}`;
  window.history.replaceState({}, "", nextUrl);
}
function exitDemoMode() {
  const params = new URLSearchParams(window.location.search);
  params.delete(DEMO_QUERY_PARAM);
  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash || ""}`;
  window.location.href = nextUrl;
}
function enterContestMode() {
}
function exitContestMode() {
}
function toggleContestMode() {
}
const $ = (selector, root = document) => root.querySelector(selector);
const safeSetHtml = (selector, html) => {
  const el = $(selector);
  if (el)
    el.innerHTML = html;
};
const safeSetText = (selector, text) => {
  const el = $(selector);
  if (el)
    el.textContent = text;
};
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
function normalizeProductPrefs(payload = {}) {
  var _a;
  if ((_a = window.QJClientAI) == null ? void 0 : _a.normalizePrefs) {
    return window.QJClientAI.normalizePrefs({
      ai_assist_enabled: payload == null ? void 0 : payload.ai_assist_enabled,
      privacy_mode: payload == null ? void 0 : payload.privacy_mode,
      preferred_entry: payload == null ? void 0 : payload.preferred_entry
    });
  }
  return {
    aiAssistEnabled: (payload == null ? void 0 : payload.ai_assist_enabled) !== false,
    privacyMode: (payload == null ? void 0 : payload.privacy_mode) === "local_first" ? "local_first" : "cloud",
    preferredEntry: ["daily", "emergency", "reflection"].includes(payload == null ? void 0 : payload.preferred_entry) ? payload.preferred_entry : "daily"
  };
}
function currentProductPrefs() {
  var _a, _b, _c;
  return {
    aiAssistEnabled: ((_a = state.productPrefs) == null ? void 0 : _a.aiAssistEnabled) !== false,
    privacyMode: ((_b = state.productPrefs) == null ? void 0 : _b.privacyMode) === "local_first" ? "local_first" : "cloud",
    preferredEntry: ["daily", "emergency", "reflection"].includes((_c = state.productPrefs) == null ? void 0 : _c.preferredEntry) ? state.productPrefs.preferredEntry : "daily"
  };
}
function prefsToApiPayload(prefs = currentProductPrefs()) {
  return {
    ai_assist_enabled: prefs.aiAssistEnabled !== false,
    privacy_mode: prefs.privacyMode === "local_first" ? "local_first" : "cloud",
    preferred_entry: ["daily", "emergency", "reflection"].includes(prefs.preferredEntry) ? prefs.preferredEntry : "daily"
  };
}
function getClientAIService() {
  var _a;
  if (!state.clientAIService && ((_a = window.QJClientAI) == null ? void 0 : _a.createService)) {
    state.clientAIService = window.QJClientAI.createService();
  }
  return state.clientAIService;
}
async function initClientAIServices() {
  const service = getClientAIService();
  if (!service) {
    state.clientAIAvailable = false;
    state.clientWorkerStatus = "unavailable";
    state.clientAIFallbackActive = true;
    return false;
  }
  const ready = await service.init();
  state.clientAIAvailable = Boolean(ready);
  state.clientWorkerStatus = ready ? "ready" : "fallback";
  state.clientAIFallbackActive = !ready;
  state.localDraftCount = await service.countPendingDrafts().catch(() => 0);
  state.localDraftSummary = await service.listDrafts().catch(() => []);
  return ready;
}
function escapeHtml(value) {
  return String(value != null ? value : "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function svgIcon(id, className = "") {
  const extra = className ? ` ${className}` : "";
  return `<svg class="icon${extra}"><use href="#${id}"></use></svg>`;
}
function showToast(message, duration = 2400) {
  const toast = $("#toast");
  if (!toast)
    return;
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("show"), duration);
}
function openModal(html) {
  const overlay = $("#modal-overlay");
  const body = $("#modal-body");
  if (!overlay || !body)
    return;
  body.innerHTML = html;
  overlay.classList.remove("hidden");
}
function closeModal() {
  var _a;
  (_a = $("#modal-overlay")) == null ? void 0 : _a.classList.add("hidden");
}
function hasCurrentPair() {
  return Boolean(state.currentPair && state.currentPair.status === "active");
}
function getPairSnapshot() {
  return hasCurrentPair() ? state.currentPair : null;
}
function ensurePairContext(message = "请先创建或加入关系") {
  if (!api.isLoggedIn()) {
    showToast("请先登录");
    return false;
  }
  if (!hasCurrentPair()) {
    showToast(message);
    return false;
  }
  return true;
}
function ensureLoginContext(message = "请先登录") {
  if (!api.isLoggedIn()) {
    showToast(message);
    return false;
  }
  return true;
}
function getPartnerDisplayName(pair) {
  if (!pair)
    return "关系对象";
  return pair.custom_partner_nickname || pair.partner_nickname || pair.partner_email || pair.partner_phone || "关系对象";
}
function getContextualPlaybookCard() {
  var _a, _b, _c;
  return renderRelationshipPlaybook(
    ((_a = state.homeSnapshot) == null ? void 0 : _a.playbook) || null,
    ((_c = (_b = state.homeSnapshot) == null ? void 0 : _b.tasks) == null ? void 0 : _c.tasks) || []
  );
}
function resolveAssetUrl(path) {
  if (!path)
    return "";
  if (/^https?:\/\//i.test(path))
    return path;
  const origin = window.API_ROOT ? window.API_ROOT.replace(/\/api\/v1$/, "") : window.location.origin;
  return `${origin}${path}`;
}
function setCurrentPair(pairId) {
  const match = state.pairs.find((pair) => pair.id === pairId);
  if (!match)
    return;
  state.currentPair = match;
  localStorage.setItem("qj_current_pair", pairId);
}
function shouldPromptPairSetup() {
  return localStorage.getItem(FIRST_LOGIN_PAIR_PROMPT_KEY) !== "1";
}
function markPairPromptSeen() {
  localStorage.setItem(FIRST_LOGIN_PAIR_PROMPT_KEY, "1");
}
function handleSkipPairSetup() {
  markPairPromptSeen();
  state.shouldOpenPairOnBootstrap = false;
  showToast("已进入单人体验模式，你之后也可以随时去绑定关系");
  showPage("home");
}
function relationStatusLabel(pair) {
  return (pair == null ? void 0 : pair.status) === "active" ? "已配对" : "等待加入";
}
function formatPlanTypeLabel(planType) {
  return PLAN_TYPE_LABELS[planType] || planType || "未分类策略";
}
function formatPolicyStatusLabel(status) {
  return POLICY_STATUS_LABELS[status] || status || "未知状态";
}
function isAdminAccessDenied(error) {
  const message = String((error == null ? void 0 : error.message) || "");
  const normalized = message.toLowerCase();
  return message.includes("管理员") || message.includes("无权") || message.includes("403") || normalized.includes("only admins") || normalized.includes("admin");
}
function summarizePolicyCounts(policies) {
  const source = Array.isArray(policies) ? policies : [];
  return {
    total: source.length,
    active: source.filter((item) => item.status === "active").length,
    inactive: source.filter((item) => item.status !== "active").length
  };
}
function renderPolicyWorkbenchLauncher(policies) {
  const counts = summarizePolicyCounts(policies);
  return `
        <button class="stack-item stack-item--action" type="button" onclick="openPolicyWorkbench()" aria-label="打开策略面板">
            <div>${svgIcon("i-lock")}</div>
            <div class="stack-item__content">
                <strong>策略面板</strong>
                <div class="stack-item__meta">已注册 ${counts.total} 条策略，当前生效 ${counts.active} 条，已停用 ${counts.inactive} 条。</div>
            </div>
            <div class="stack-item__aside"><span class="stack-item__hint">点击管理</span>${svgIcon("i-arrow-right", "icon-sm")}</div>
        </button>`;
}
function renderPolicyWorkbenchErrorNotice(message) {
  if (!message) {
    return "";
  }
  return `
        <div class="stack-item stack-item--static">
            <div>${svgIcon("i-lock")}</div>
            <div class="stack-item__content">
                <strong>策略面板暂不可用</strong>
                <div class="stack-item__meta">${escapeHtml(message)}</div>
            </div>
        </div>`;
}
async function loadAdminPolicies(options = {}) {
  if (isDemoMode()) {
    state.adminPolicies = deepClone(getDemoFixture("adminPolicies") || []);
    state.isAdmin = true;
    state.policyWorkbenchError = null;
    return state.adminPolicies;
  }
  if (!api.isLoggedIn()) {
    state.adminPolicies = [];
    state.isAdmin = false;
    state.policyWorkbenchError = null;
    return [];
  }
  try {
    const policies = await api.getAdminPolicies();
    state.adminPolicies = Array.isArray(policies) ? policies : [];
    state.isAdmin = true;
    state.policyWorkbenchError = null;
    return state.adminPolicies;
  } catch (error) {
    if (isAdminAccessDenied(error)) {
      state.adminPolicies = [];
      state.isAdmin = false;
      state.policyWorkbenchError = null;
      return [];
    }
    state.adminPolicies = [];
    state.isAdmin = false;
    state.policyWorkbenchError = error.message || "策略面板暂不可用";
    if (options.showErrors) {
      showToast(state.policyWorkbenchError);
    }
    throw error;
  }
}
function renderRelationManagementList(pairs, currentPairId) {
  if (!pairs.length) {
    return '<div class="empty-state">你还没有建立任何关系。准备好之后，可以先创建邀请码，或输入对方邀请码加入。</div>';
  }
  return `<div class="stack-list">${pairs.map((pair) => {
    const isCurrent = currentPairId === pair.id;
    const relationLabel = TYPE_LABELS[pair.type] || pair.type;
    const partnerName = pair.status === "active" ? getPartnerDisplayName(pair) : pair.partner_nickname || pair.partner_email || pair.partner_phone || "等待对方加入";
    const actionHint = isCurrent ? "当前关系" : pair.status === "active" ? "进入管理" : "查看邀请";
    return `
            <button class="stack-item stack-item--action" type="button" onclick="openRelationWorkspace('${pair.id}')" aria-label="切换关系 ${escapeHtml(partnerName)}">
                <div>${svgIcon(isCurrent ? "i-heart" : "i-link")}</div>
                <div class="stack-item__content">
                    <strong>${escapeHtml(relationLabel)} · ${escapeHtml(partnerName)}</strong>
                    <div class="stack-item__meta">${relationStatusLabel(pair)} · 创建于 ${escapeHtml(formatDateOnly(pair.created_at))}</div>
            <div class="stack-item__meta">邀请码：${escapeHtml(pair.invite_code || "未生成")} · ${isCurrent ? "当前查看关系" : pair.status === "active" ? "点击切换为当前关系" : "点击查看等待加入状态"}</div>
                    ${pair.custom_partner_nickname ? `<div class="stack-item__meta stack-item__meta--accent">备注名：${escapeHtml(pair.custom_partner_nickname)}</div>` : ""}
                </div>
                <div class="stack-item__aside"><span class="stack-item__hint">${actionHint}</span>${svgIcon("i-arrow-right", "icon-sm")}</div>
            </button>`;
  }).join("")}</div>`;
}
function upsertPair(updatedPair) {
  var _a;
  state.pairs = state.pairs.map((pair) => pair.id === updatedPair.id ? updatedPair : pair);
  if (((_a = state.currentPair) == null ? void 0 : _a.id) === updatedPair.id) {
    state.currentPair = updatedPair;
  }
}
function syncTopbar() {
  const titleMap = {
    auth: "关系支持系统",
    pair: "创建或加入关系",
    "pair-waiting": "等待对方加入",
    home: "关系总览",
    checkin: "每日打卡",
    discover: "功能总览",
    report: "关系简报",
    profile: "账户与设置",
    milestones: "关系里程碑",
    longdistance: "异地关系模式",
    "attachment-test": "依恋分析",
    "health-test": "关系体检",
    community: "社群技巧",
    challenges: "关系挑战",
    courses: "内容展示",
    experts: "咨询服务",
    membership: "会员方案"
  };
  safeSetText("#topbar-title", titleMap[state.currentPage] || "关系支持系统");
}
function syncTabBar() {
  var _a;
  const visible = api.isLoggedIn() || isDemoMode();
  (_a = $("#tab-bar")) == null ? void 0 : _a.classList.toggle("hidden", !visible);
}
function syncTabSelection(pageId) {
  $$(".tab-item").forEach((button) => {
    button.classList.toggle("tab-item--active", button.dataset.page === pageId);
  });
}
function resolveThemeState(pageId) {
  const themeByPage = {
    home: "cover",
    checkin: "journal",
    report: "brief",
    timeline: "proof",
    profile: "archive",
    milestones: "proof"
  };
  return themeByPage[pageId] || "paper";
}
async function showPage(pageId) {
  var _a;
  $$(".page").forEach((page) => page.classList.remove("active"));
  (_a = $(`#page-${pageId}`)) == null ? void 0 : _a.classList.add("active");
  state.currentPage = pageId;
  document.body.dataset.page = pageId;
  document.body.dataset.themeState = resolveThemeState(pageId);
  syncTopbar();
  syncTabSelection(pageId);
  switch (pageId) {
    case "pair":
      renderPairPage();
      break;
    case "pair-waiting":
      renderWaitingPage();
      break;
    case "home":
      await loadHomePage();
      break;
    case "checkin":
      renderCheckinPage();
      await loadCheckinAgentState();
      break;
    case "report":
      await loadReportPage();
      break;
    case "timeline":
      await loadTimelinePage();
      break;
    case "profile":
      await loadProfilePage();
      break;
    case "milestones":
      await loadMilestonesPage();
      break;
    case "longdistance":
      await loadLongDistancePage();
      break;
    case "attachment-test":
      await loadAttachmentPage();
      break;
    case "health-test":
      initHealthTest();
      break;
    case "community":
      await loadCommunityPage();
      break;
    case "challenges":
      await loadChallengesPage();
      break;
    default:
      break;
  }
  syncContestModeUI();
  syncContestPageBanners();
}
async function bootstrapSession() {
  var _a;
  if (isDemoMode()) {
    const demoPairs = deepClone(getDemoFixture("pairs") || []);
    const currentPairId = getDemoFixture("currentPairId");
    api.token = api.token || "demo-mode";
    state.me = deepClone(getDemoFixture("me")) || {
      id: "demo-user",
      nickname: "演示用户",
      email: "demo@qinjian.local"
    };
    state.productPrefs = {
      ...CLIENT_AI_PREFS,
      ...normalizeProductPrefs(state.me)
    };
    state.pairs = demoPairs;
    state.currentPair = demoPairs.find((pair) => pair.id === currentPairId) || demoPairs[0] || null;
    state.notifications = deepClone(getDemoFixture("notifications") || []);
    state.adminPolicies = deepClone(getDemoFixture("adminPolicies") || []);
    state.isAdmin = true;
    state.policyWorkbenchError = null;
    syncNotifications();
    syncTabBar();
    await showPage("home");
    return true;
  }
  if (!api.isLoggedIn()) {
    state.me = null;
    state.pairs = [];
    state.currentPair = null;
    state.productPrefs = { ...CLIENT_AI_PREFS };
    syncTabBar();
    return false;
  }
  try {
    const [me, pairs, summary] = await Promise.all([api.getMe(), api.getMyPairs(), api.getPairSummary().catch(() => null)]);
    state.me = me;
    state.productPrefs = {
      ...CLIENT_AI_PREFS,
      ...normalizeProductPrefs(me)
    };
    state.pairs = pairs;
    const storedPairId = localStorage.getItem("qj_current_pair");
    const activePairs = pairs.filter((pair) => pair.status === "active");
    const pendingPairs = pairs.filter((pair) => pair.status === "pending");
    const activeSummaryPairId = ((_a = summary == null ? void 0 : summary.active_pair) == null ? void 0 : _a.id) || null;
    state.currentPair = activePairs.find((pair) => pair.id === storedPairId) || activePairs.find((pair) => pair.id === activeSummaryPairId) || activePairs[0] || pendingPairs.find((pair) => pair.id === storedPairId) || pendingPairs[0] || null;
    syncTabBar();
    await updateLocalDraftState().catch(() => []);
    syncPendingLocalDrafts({ silent: true }).catch(() => 0);
    if (state.shouldOpenPairOnBootstrap && !activePairs.length && !pendingPairs.length && shouldPromptPairSetup()) {
      state.shouldOpenPairOnBootstrap = false;
      await showPage("pair");
      return true;
    }
    if (activePairs.length > 0) {
      markPairPromptSeen();
      await showPage("home");
      return true;
    }
    if (pendingPairs.length > 0) {
      markPairPromptSeen();
      await showPage("pair-waiting");
      return true;
    }
    await showPage("home");
    return true;
  } catch (error) {
    api.clearToken();
    state.me = null;
    state.pairs = [];
    state.currentPair = null;
    state.productPrefs = { ...CLIENT_AI_PREFS };
    syncTabBar();
    showToast(error.message || "登录状态已失效");
    await showPage("auth");
    return false;
  }
}
function switchAuthMode(mode) {
  state.authMode = mode;
  $("#auth-mode-login").classList.toggle("segmented__item--active", mode === "login");
  $("#auth-mode-register").classList.toggle("segmented__item--active", mode === "register");
  syncAuthForm();
}
function switchAuthMethod(method) {
  state.authMethod = method;
  $("#auth-method-email").classList.toggle("segmented__item--active", method === "email");
  $("#auth-method-phone").classList.toggle("segmented__item--active", method === "phone");
  syncAuthForm();
}
function syncAuthForm() {
  const isEmail = state.authMethod === "email";
  const isRegister = state.authMode === "register";
  $("#auth-nickname-wrap").classList.toggle("hidden", !isEmail || !isRegister);
  $("#auth-email-wrap").classList.toggle("hidden", !isEmail);
  $("#auth-password-wrap").classList.toggle("hidden", !isEmail);
  $("#auth-phone-wrap").classList.toggle("hidden", isEmail);
  $("#auth-phone-code-wrap").classList.toggle("hidden", isEmail);
  $("#auth-phone-note").classList.toggle("hidden", isEmail);
  $("#auth-email").disabled = !isEmail;
  $("#auth-password").disabled = !isEmail;
  $("#auth-phone").disabled = isEmail;
  $("#auth-phone-code").disabled = isEmail;
  $("#auth-nickname").disabled = !isEmail || !isRegister;
  $("#auth-email").required = isEmail;
  $("#auth-password").required = isEmail;
  $("#auth-phone").required = !isEmail;
  $("#auth-phone-code").required = !isEmail;
  $("#auth-nickname").required = isEmail && isRegister;
  $("#auth-submit").textContent = isEmail ? isRegister ? "创建并进入" : "进入系统" : "验证码进入";
}
function validatePhone(phone) {
  return /^1\d{10}$/.test(phone);
}
function updateSendCodeButton() {
  const button = $("#auth-send-code");
  if (!button)
    return;
  if (state.phoneCodeCooldown > 0) {
    button.disabled = true;
    button.textContent = `${state.phoneCodeCooldown}s 后重试`;
    return;
  }
  button.disabled = false;
  button.textContent = "获取验证码";
}
function startPhoneCodeCooldown(seconds = 60) {
  clearInterval(startPhoneCodeCooldown.timer);
  state.phoneCodeCooldown = seconds;
  updateSendCodeButton();
  startPhoneCodeCooldown.timer = window.setInterval(() => {
    state.phoneCodeCooldown = Math.max(0, state.phoneCodeCooldown - 1);
    updateSendCodeButton();
    if (state.phoneCodeCooldown === 0) {
      clearInterval(startPhoneCodeCooldown.timer);
    }
  }, 1e3);
}
async function handleSendPhoneCode() {
  const phone = $("#auth-phone").value.trim();
  if (!validatePhone(phone)) {
    showToast("请输入正确的 11 位手机号");
    return;
  }
  try {
    const payload = await api.sendPhoneCode(phone);
    startPhoneCodeCooldown(60);
    showToast(payload.debug_code ? `验证码已发送：${payload.debug_code}` : "验证码已发送");
  } catch (error) {
    const message = error.message || "发送失败";
    const match = String(message).match(/(\d+)\s*秒/);
    if (match) {
      startPhoneCodeCooldown(Number(match[1]));
    }
    showToast(message);
  }
}
async function handleAuthSubmit(event) {
  event.preventDefault();
  const email = $("#auth-email").value.trim();
  const password = $("#auth-password").value;
  const nickname = $("#auth-nickname").value.trim();
  const phone = $("#auth-phone").value.trim();
  const phoneCode = $("#auth-phone-code").value.trim();
  const submit = $("#auth-submit");
  if (state.authMethod === "phone") {
    if (!validatePhone(phone)) {
      showToast("请输入正确的 11 位手机号");
      return;
    }
    if (!/^\d{6}$/.test(phoneCode)) {
      showToast("请输入 6 位验证码");
      return;
    }
    submit.disabled = true;
    submit.textContent = "登录中...";
    try {
      await api.phoneLogin(phone, phoneCode);
      state.shouldOpenPairOnBootstrap = false;
      showToast("登录成功");
      await bootstrapSession();
    } catch (error) {
      showToast(error.message || "提交失败");
    } finally {
      submit.disabled = false;
      syncAuthForm();
    }
    return;
  }
  if (!email || !password) {
    showToast("请填写邮箱和密码");
    return;
  }
  if (state.authMode === "register" && !nickname) {
    showToast("注册时请填写昵称");
    return;
  }
  if (state.authMode === "register" && password.length < 8) {
    showToast("注册密码至少需要 8 位");
    return;
  }
  submit.disabled = true;
  submit.textContent = state.authMode === "login" ? "登录中..." : "注册中...";
  try {
    if (state.authMode === "login") {
      await api.login(email, password);
      state.shouldOpenPairOnBootstrap = false;
      showToast("登录成功");
    } else {
      await api.register(email, nickname, password);
      state.shouldOpenPairOnBootstrap = true;
      showToast("注册成功");
    }
    await bootstrapSession();
  } catch (error) {
    if (state.authMode === "login" && String(error.message || "").includes("尚未注册")) {
      showToast("这个邮箱还没注册，请先注册新账号");
    } else if (state.authMode === "login" && String(error.message || "").includes("密码错误")) {
      showToast("密码错误，请重新输入");
    } else {
      showToast(error.message || "提交失败");
    }
  } finally {
    submit.disabled = false;
    submit.textContent = state.authMode === "login" ? "进入系统" : "创建并进入";
  }
}
function renderPairPage() {
  var _a;
  const list = $("#pair-existing-list");
  const activePairs = state.pairs.filter((pair) => pair.status === "active");
  const pendingPairs = state.pairs.filter((pair) => pair.status === "pending");
  const allPairs = [...activePairs, ...pendingPairs];
  list.innerHTML = renderRelationManagementList(allPairs, ((_a = state.currentPair) == null ? void 0 : _a.id) || null);
}
async function handleCreatePair() {
  const button = $("#pair-create-btn");
  button.disabled = true;
  button.textContent = "创建中...";
  try {
    const pair = await api.createPair(state.selectedPairType);
    state.pairs = [...state.pairs.filter((item) => item.id !== pair.id), pair];
    state.currentPair = pair;
    showToast("邀请码已生成");
    await showPage("pair-waiting");
  } catch (error) {
    showToast(error.message || "创建失败");
  } finally {
    button.disabled = false;
    button.textContent = "创建邀请码";
  }
}
async function handleJoinPair() {
  const code = $("#pair-join-code").value.trim();
  if (!code) {
    showToast("请输入邀请码");
    return;
  }
  const button = $("#pair-join-btn");
  button.disabled = true;
  button.textContent = "加入中...";
  try {
    await api.joinPair(code);
    showToast("加入成功");
    await bootstrapSession();
  } catch (error) {
    showToast(error.message || "加入失败");
  } finally {
    button.disabled = false;
    button.textContent = "加入关系";
  }
}
function renderWaitingPage() {
  var _a;
  safeSetText("#waiting-invite-code", ((_a = state.currentPair) == null ? void 0 : _a.invite_code) || "------");
}
async function refreshPairStatus() {
  if (!api.isLoggedIn()) {
    renderWaitingPage();
    return;
  }
  await bootstrapSession();
}
function demoMetric(label, value) {
  return `<article class="stat-card"><span>${label}</span><strong>${value}</strong></article>`;
}
function renderNoPairHome() {
  state.homeSnapshot = null;
  safeSetHtml("#home-overview", `
        <p class="eyebrow">准备开始</p>
        <h3>先照顾今天的自己，也可以随时建立关系空间</h3>
        <p>你已经可以先做个人打卡和智能陪伴记录；等建立关系后，再把日报、趋势和双方协作接进来。</p>
        <div class="hero-actions">
          <button class="button button--primary" type="button" onclick="showPage('pair')">现在去绑定关系</button>
          <button class="button button--ghost" type="button" onclick="showPage('discover')">先看功能总览</button>
        </div>
    `);
  safeSetHtml("#home-metrics", [
    demoMetric("连续打卡", "0 天"),
    demoMetric("关系树", "待开启"),
    demoMetric("成长值", "0"),
    demoMetric("当前预警", "未开始")
  ].join(""));
  safeSetHtml("#home-status-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">今日</p><h4>先开始今天的记录</h4></div></div>
        <div class="empty-state">现在就可以先写个人记录，或者直接让系统陪你把今天整理出来。</div>
        <div class="hero-actions">
          <button class="button button--primary" type="button" onclick="openCheckinMode('form')">表单打卡</button>
          <button class="button button--ghost" type="button" onclick="openCheckinMode('voice')">智能陪伴打卡</button>
        </div>`);
  safeSetHtml("#home-report-panel", '<div class="empty-state">建立关系并完成打卡后，这里会出现报告入口和趋势回顾。</div>');
  safeSetHtml("#home-tree-panel", '<div class="empty-state">关系树会在你们开始记录之后自动成长。</div>');
  safeSetHtml("#home-crisis-panel", '<div class="empty-state">关系建立后，这里会根据互动情况提供风险提醒和帮助建议。</div>');
  safeSetHtml("#home-milestones-panel", '<div class="empty-state">关键节点会在建立关系后开始记录。</div>');
  safeSetHtml("#home-tasks-panel", '<div class="empty-state">先创建或加入关系，系统才会生成今日任务。</div>');
  state.notifications = [];
  syncNotifications();
}
async function loadHomePage() {
  var _a;
  const pair = getPairSnapshot();
  const greetingName = ((_a = state.me) == null ? void 0 : _a.nickname) || "你";
  safeSetText("#home-greeting", `${greetingName}，欢迎进入关系总览`);
  renderPairSelect();
  if (!pair) {
    renderNoPairHome();
    return;
  }
  const results = await Promise.allSettled([
    api.getTodayStatus(pair.id),
    api.getCheckinStreak(pair.id),
    api.getTreeStatus(pair.id),
    api.getCrisisStatus(pair.id),
    api.getDailyTasks(pair.id),
    api.getNotifications(),
    api.getMilestones(pair.id)
  ]);
  renderHome({
    pair,
    todayStatus: unwrapResult(results[0], {}),
    streak: unwrapResult(results[1], {}),
    tree: unwrapResult(results[2], {}),
    crisis: unwrapResult(results[3], {}),
    tasks: unwrapResult(results[4], {}),
    notifications: unwrapResult(results[5], []),
    milestones: unwrapResult(results[6], [])
  });
}
function unwrapResult(result, fallback) {
  return result.status === "fulfilled" ? result.value : fallback;
}
function renderPairSelect() {
  var _a;
  const select = $("#home-pair-select");
  if (!select)
    return;
  const source = state.pairs.filter((pair) => pair.status === "active");
  if (!source.length) {
    select.innerHTML = '<option value="">暂无已激活关系</option>';
    select.value = "";
    return;
  }
  select.innerHTML = source.map((pair) => `<option value="${pair.id}">${escapeHtml(TYPE_LABELS[pair.type] || pair.type)} · ${escapeHtml(getPartnerDisplayName(pair))}</option>`).join("");
  select.value = ((_a = getPairSnapshot()) == null ? void 0 : _a.id) || source[0].id;
}
function renderHome(payload) {
  state.homeSnapshot = payload;
  const pairName = getPartnerDisplayName(payload.pair);
  safeSetHtml("#home-overview", `
        <p class="eyebrow">CONNECTED</p>
        <h3>${escapeHtml(TYPE_LABELS[payload.pair.type] || payload.pair.type)} · ${escapeHtml(pairName)}</h3>
        <p>当前展示的是这段关系的核心状态、提醒和下一步动作。</p>
    `);
  safeSetHtml("#home-metrics", [
    demoMetric("连续打卡", `${payload.streak.streak || 0} 天`),
    demoMetric("关系树", `${payload.tree.level_name || "种子"}`),
    demoMetric("成长值", `${payload.tree.growth_points || 0}`),
    demoMetric("当前预警", crisisLabel(payload.crisis.crisis_level || "none"))
  ].join(""));
  safeSetHtml("#home-status-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">今日</p><h4>今日打卡状态</h4></div></div>
    <div class="stack-list">
      <div class="stack-item"><div><strong>我</strong><div class="stack-item__meta">${payload.todayStatus.my_done ? "已完成今日打卡" : "今天还没有提交"}</div></div><span class="pill">${payload.todayStatus.my_done ? "完成" : "待办"}</span></div>
      <div class="stack-item"><div><strong>对方</strong><div class="stack-item__meta">${payload.todayStatus.partner_done ? "对方已经完成" : "对方尚未完成"}</div></div><span class="pill">${payload.todayStatus.partner_done ? "完成" : "等待中"}</span></div>
    </div>
    <div class="hero-actions">
      <button class="button button--primary" type="button" onclick="openCheckinMode('form')">表单打卡</button>
          <button class="button button--secondary" type="button" onclick="openCheckinMode('voice')">智能陪伴打卡</button>
      <button class="button button--ghost" type="button" onclick="showPage('report')">看报告</button>
    </div>`);
  safeSetHtml("#home-report-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">简报</p><h4>报告入口</h4></div></div>
    <div class="empty-state">
      ${payload.todayStatus.both_done ? "双方都已完成打卡，可以生成正式关系报告。" : "双方未全部完成时，网页端优先展示状态与下一步建议。"}
    </div>
    <div class="hero-actions">
      <button class="button button--secondary" type="button" onclick="showPage('report')">进入报告页</button>
    </div>`);
  safeSetHtml("#home-tree-panel", `
    <div class="panel__header"><div><p class="panel__eyebrow">TREE</p><h4>关系树成长</h4></div></div>
    <div class="stack-item"><div>${svgIcon("i-tree")}</div><div><strong>${escapeHtml(payload.tree.level_name || "种子")}</strong><div class="stack-item__meta">当前成长值 ${payload.tree.growth_points || 0}</div></div></div>
    <div class="progress-track"><span class="progress-track__fill" style="width:${payload.tree.progress_percent || 0}%"></span></div>
    <div class="hero-actions">
      <button class="button button--ghost" type="button" ${payload.tree.can_water ? "" : "disabled"} onclick="handleWaterTree()">${payload.tree.can_water ? "浇水 +5" : "今日已浇水"}</button>
    </div>`);
  const crisis = payload.crisis || { crisis_level: "none" };
  const crisisIntervention = crisis.intervention ? `<div class="stack-item__meta">${escapeHtml(crisis.intervention.title || crisis.intervention.description || "")}</div>` : '<div class="stack-item__meta">暂无需要立即介入的强预警。</div>';
  safeSetHtml("#home-crisis-panel", `
    <div class="panel__header"><div><p class="panel__eyebrow">CRISIS</p><h4>危机预警</h4></div></div>
    <div class="stack-item"><div>${svgIcon("i-alert")}</div><div><strong>${crisisLabel(crisis.crisis_level || "none")}</strong>${crisisIntervention}</div></div>
    <div class="hero-actions">
      <button class="button button--ghost" type="button" onclick="openCrisisDetail()">查看详情</button>
    </div>`);
  const milestones = payload.milestones || [];
  safeSetHtml("#home-milestones-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">MILESTONES</p><h4>关键节点</h4></div></div>
        ${milestones.length ? `<div class="stack-list">${milestones.slice(0, 2).map((item) => renderMilestoneItem(item, { compact: true })).join("")}</div>` : '<div class="empty-state">还没有记录关系里程碑。</div>'}
        <div class="hero-actions">
            <button class="button button--ghost" type="button" onclick="showPage('milestones')">进入里程碑页</button>
        </div>`);
  const tasks = payload.tasks.tasks || [];
  const taskAdaptiveHint = renderTaskAdaptiveHint(payload.tasks);
  const playbookCard = renderRelationshipPlaybook(payload.playbook, tasks);
  safeSetHtml("#home-tasks-panel", `
    <div class="panel__header"><div><p class="panel__eyebrow">TASKS</p><h4>今日关系任务</h4></div></div>
    <div class="stack-list">
      ${tasks.length ? tasks.slice(0, 3).map((task) => renderTaskItem(task)).join("") : '<div class="empty-state">今天还没有生成任务。</div>'}
    </div>`);
  state.notifications = Array.isArray(payload.notifications) ? payload.notifications : payload.notifications || [];
  syncNotifications();
}
function renderTaskItem(task) {
  const done = task.status === "completed";
  return `
    <div class="challenge-item">
      <div>${done ? svgIcon("i-check") : svgIcon("i-target")}</div>
      <div>
        <strong>${escapeHtml(task.title)}</strong>
        <div class="stack-item__meta">${escapeHtml(task.description || "")}</div>
      </div>
      ${done ? '<span class="pill">已完成</span>' : `<button class="text-button" type="button" onclick="completeTask('${task.id}')">完成</button>`}
    </div>`;
}
function crisisLabel(level) {
  return { none: "正常", mild: "轻度预警", moderate: "中度预警", severe: "严重预警" }[level] || "正常";
}
function syncNotifications() {
  const button = $("#notification-toggle");
  const count = $("#notification-count");
  const list = $("#notification-drawer-list");
  if (!button || !count || !list)
    return;
  const notifications = state.notifications || [];
  if (!notifications.length) {
    button.classList.add("hidden");
    list.innerHTML = '<div class="empty-state">暂无通知。</div>';
    return;
  }
  button.classList.remove("hidden");
  const unread = notifications.filter((item) => !item.is_read).length;
  count.classList.toggle("hidden", unread === 0);
  count.textContent = unread > 9 ? "9+" : String(unread);
  list.innerHTML = notifications.map((item) => `
    <article class="notification-item">
      <div>${svgIcon("i-bell")}</div>
      <div>
        <strong>${escapeHtml(item.content)}</strong>
        <div class="notification-item__meta">${formatDate(item.created_at)}</div>
      </div>
    </article>`).join("");
}
function formatDate(value) {
  if (!value)
    return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime()))
    return String(value);
  return `${date.getMonth() + 1}-${date.getDate()} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}
function formatDateOnly(value) {
  if (!value)
    return "未设置";
  const date = new Date(value);
  if (Number.isNaN(date.getTime()))
    return String(value);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function maskPhone(phone) {
  if (!phone)
    return "未绑定";
  return String(phone).replace(/^(\d{3})\d+(\d{4})$/, "$1****$2");
}
function getAccountChannels(me) {
  const channels = [];
  if (me.email && !me.email.endsWith("@qinjian.local"))
    channels.push("邮箱账号");
  if (me.phone)
    channels.push("手机号账号");
  if (me.wechat_bound)
    channels.push("微信已绑定");
  return channels.length ? channels.join(" / ") : "基础邮箱账号";
}
function milestoneTypeLabel(type) {
  return {
    anniversary: "纪念日",
    proposal: "重要承诺",
    wedding: "婚礼 / 领证",
    friendship_day: "关系节点",
    custom: "自定义"
  }[type] || "里程碑";
}
function milestoneTimeText(item) {
  if (typeof item.days_until === "number" && item.days_until > 0) {
    return `${item.days_until} 天后到来`;
  }
  if (typeof item.days_until === "number" && item.days_until === 0) {
    return "就是今天";
  }
  if (typeof item.days_since === "number") {
    return item.days_since === 0 ? "今天发生" : `已过去 ${item.days_since} 天`;
  }
  return "时间待确认";
}
function renderMilestoneItem(item, { compact = false } = {}) {
  return `
    <article class="${compact ? "stack-item" : "timeline-card"}">
      <div class="${compact ? "" : "timeline-card__head"}">
        <div>
          <strong>${escapeHtml(item.title || "未命名里程碑")}</strong>
          <div class="stack-item__meta">${escapeHtml(milestoneTypeLabel(item.type))} · ${escapeHtml(formatDateOnly(item.date))}</div>
          <div class="stack-item__meta">${escapeHtml(milestoneTimeText(item))}</div>
        </div>
        <span class="pill">${item.reminder_sent ? "已提醒" : "待提醒"}</span>
      </div>
      ${compact ? "" : `<div class="timeline-card__actions"><button class="button button--ghost" type="button" data-milestone-review="${item.id}">生成成长回顾</button></div>`}
    </article>`;
}
function renderCheckinPage() {
  renderMoods();
  renderOptionGroup("#mood-score-options", [1, 2, 3, 4].map((value) => ({ label: `${value} 分`, value: String(value), name: "mood_score" })));
  renderOptionGroup("#initiative-options", [
    { label: "我更主动", value: "me", name: "interaction_initiative" },
    { label: "对方更主动", value: "partner", name: "interaction_initiative" },
    { label: "差不多", value: "equal", name: "interaction_initiative" }
  ]);
  renderOptionGroup("#deep-conversation-options", [
    { label: "有", value: "true", name: "deep_conversation" },
    { label: "没有", value: "false", name: "deep_conversation" }
  ]);
  renderOptionGroup("#task-completed-options", [
    { label: "完成了", value: "true", name: "task_completed" },
    { label: "还没有", value: "false", name: "task_completed" }
  ]);
  syncCheckinModeUI();
  renderAgentMessages();
  renderCheckinClientAIPanel(state.lastClientPrecheck);
}
function syncCheckinModeUI() {
  const formButton = $("#checkin-mode-form");
  const voiceButton = $("#checkin-mode-voice");
  const form = $("#checkin-form");
  const panel = $("#checkin-agent-panel");
  if (!formButton || !voiceButton || !form || !panel)
    return;
  formButton.classList.toggle("segmented__item--active", state.checkinMode === "form");
  voiceButton.classList.toggle("segmented__item--active", state.checkinMode === "voice");
  form.classList.toggle("hidden", state.checkinMode !== "form");
  panel.classList.toggle("hidden", state.checkinMode !== "voice");
}
function renderAgentMessages() {
  const container = $("#agent-chat-list");
  if (!container)
    return;
  if (!state.agentMessages.length) {
    container.innerHTML = '<div class="empty-state">从一句“今天其实有点累”开始也可以。</div>';
    return;
  }
  container.innerHTML = state.agentMessages.map((item) => `
      <article class="stack-item ${item.role === "user" ? "stack-item--user" : ""}">
        <div>${item.role === "user" ? svgIcon("i-user") : svgIcon("i-heart")}</div>
        <div><strong>${item.role === "user" ? "我" : "亲健 AI"}</strong><div class="stack-item__meta">${escapeHtml(item.content || "")}</div></div>
      </article>`).join("");
}
async function ensureAgentSession() {
  var _a;
  if (state.agentSessionId)
    return state.agentSessionId;
  const session = await api.createAgentSession(((_a = state.currentPair) == null ? void 0 : _a.id) || null);
  state.agentSessionId = session.session_id;
  state.agentMessages = await api.getAgentMessages(state.agentSessionId);
  renderAgentMessages();
  return state.agentSessionId;
}
async function sendAgentChat() {
  if (!ensureLoginContext()) {
    return;
  }
  const input = $("#agent-chat-input");
  const content = input == null ? void 0 : input.value.trim();
  if (!content) {
    showToast("先写一句话");
    return;
  }
  const button = $("#agent-send-btn");
  button.disabled = true;
  button.textContent = "发送中...";
  try {
    await ensureAgentSession();
    state.agentMessages.push({ role: "user", content });
    renderAgentMessages();
    input.value = "";
    const reply = await api.chatWithAgent(state.agentSessionId, content);
    state.agentMessages.push({ role: "assistant", content: reply.reply });
    state.lastAgentReply = reply.reply;
    renderAgentMessages();
    if (reply.action === "checkin_extracted") {
      showToast("系统已帮你整理好今天的打卡");
    }
  } catch (error) {
    showToast(error.message || "发送失败");
  } finally {
    button.disabled = false;
    button.textContent = "发送给系统";
  }
}
function replayAgentReply() {
  if (!state.lastAgentReply) {
    showToast("还没有系统回复");
    return;
  }
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(state.lastAgentReply);
    utterance.lang = "zh-CN";
    window.speechSynthesis.speak(utterance);
    return;
  }
  showToast("当前浏览器不支持朗读");
}
function renderMoods() {
  const container = $("#mood-tags");
  container.innerHTML = MOOD_TAGS.map((mood) => `<button class="tag${state.selectedMoods.includes(mood) ? " is-selected" : ""}" type="button" data-mood="${mood}">${mood}</button>`).join("");
}
function renderOptionGroup(selector, options) {
  const container = $(selector);
  container.innerHTML = options.map((option) => `<button class="select-card" type="button" data-option-name="${option.name}" data-option-value="${option.value}">${option.label}</button>`).join("");
}
function summarizeClientPii(piiSummary = {}) {
  const categories = piiSummary.categories || {};
  return Object.entries(categories).filter(([, count]) => Number(count) > 0).map(([key, count]) => `${key} ${count} 项`);
}
function buildClientGuidance(precheck) {
  if (!precheck) {
    return "输入内容后，系统会先在本地做脱敏、风险预警和意图路由，再决定如何上传。";
  }
  if (precheck.degraded) {
    return "本地预处理暂不可用，系统已切换到云端保护模式。";
  }
  if (precheck.ai_assist_enabled === false) {
    return "你已关闭端侧 AI 辅助，当前仅保留本地脱敏、安全预警和最基本的上传策略判断。";
  }
  if (precheck.risk_level === "high") {
    return "本地预检识别到高风险信号，当前优先保护你，不直接进入普通 AI 建议。";
  }
  if (precheck.upload_policy === "local_only") {
    return "这条记录当前只保存在本地，等你确认后再决定是否同步到云端。";
  }
  if (precheck.upload_policy === "redacted_only") {
    return "内容里有敏感信息，系统会优先上传脱敏摘要而不是原文。";
  }
  if (precheck.intent === "emergency") {
    return "系统判断你更像是在处理当下冲突，建议先用更稳妥的表达方式。";
  }
  if (precheck.intent === "reflection") {
    return "这次输入更像复盘，后面可以结合时间轴和周评估一起看变化。";
  }
  return "本地预检已完成，接下来会交给后端做更完整的深分析。";
}
function renderCheckinClientAIPanel(precheck = state.lastClientPrecheck) {
  var _a, _b, _c, _d;
  const statusChip = $("#checkin-client-ai-status");
  const titleEl = $("#checkin-client-ai-panel h4");
  const summaryEl = $("#checkin-client-ai-summary");
  const metaEl = $("#checkin-client-ai-meta");
  const whyEl = $("#checkin-client-ai-why");
  if (!statusChip || !titleEl || !summaryEl || !metaEl || !whyEl) {
    return;
  }
  const statusText = currentProductPrefs().aiAssistEnabled === false ? "本地守门已开启" : state.clientAIAvailable ? "本地即时判断已就绪" : state.clientAIFallbackActive ? "本地预处理已降级" : "云端保护模式";
  statusChip.textContent = statusText;
  statusChip.className = `status-chip${(precheck == null ? void 0 : precheck.risk_level) === "high" ? " status-chip--danger" : (precheck == null ? void 0 : precheck.risk_level) === "watch" ? " status-chip--warning" : ""}`;
  if (!precheck) {
    titleEl.textContent = currentProductPrefs().aiAssistEnabled === false ? "本地守门已待命" : "本地即时判断已待命";
    summaryEl.textContent = currentProductPrefs().aiAssistEnabled === false ? "你已关闭端侧 AI 辅助，当前仅保留本地脱敏和风险预警。" : state.clientAIFallbackActive ? "本地预处理暂不可用，系统会先走云端保护链路。" : "输入内容后，系统会先在本地判断要不要提醒你、如何保护内容，再决定上传策略。";
    metaEl.innerHTML = [
      `<span class="evidence-pill">隐私模式：${escapeHtml(currentProductPrefs().privacyMode === "local_first" ? "local-first" : "cloud")}</span>`,
      `<span class="evidence-pill">AI 辅助：${currentProductPrefs().aiAssistEnabled ? "开启" : "关闭"}</span>`,
      `<span class="evidence-pill">待同步：${escapeHtml(String(state.localDraftCount || 0))} 条</span>`
    ].join("");
    whyEl.innerHTML = `
            <article class="client-ai-note">
                <p class="client-ai-note__eyebrow">本地即时判断</p>
                <strong>这里会先告诉你现在更像记录、急救还是需要暂停普通建议。</strong>
                <p>它不是代替后端分析，而是在你点击提交前先做一次更近身的守门。</p>
            </article>
            <article class="client-ai-note">
                <p class="client-ai-note__eyebrow">会如何保护你的内容</p>
                <strong>系统会优先决定原文上传、脱敏上传还是只保存在本地。</strong>
                <p>这样你在真正提交前，就知道这条内容会怎样被处理。</p>
            </article>
        `;
    return;
  }
  titleEl.textContent = `本地即时判断：${precheck.intent === "emergency" ? "冲突急救" : precheck.intent === "reflection" ? "复盘路径" : precheck.intent === "crisis" ? "高风险保护" : "日常记录"}`;
  summaryEl.textContent = buildClientGuidance(precheck);
  const pills = [
    `风险：${precheck.risk_level || "none"}`,
    `上传：${precheck.upload_policy || "full"}`,
    `隐私：${precheck.privacy_mode || "cloud"}`,
    `待同步：${String(state.localDraftCount || 0)} 条`
  ];
  const piiItems = summarizeClientPii(precheck.pii_summary || {});
  if (piiItems.length)
    pills.push(`脱敏：${piiItems.join(" / ")}`);
  if (Array.isArray(precheck.client_tags) && precheck.client_tags.length) {
    pills.push(`标签：${precheck.client_tags.slice(0, 2).join(" / ")}`);
  }
  metaEl.innerHTML = pills.map((item) => `<span class="evidence-pill">${escapeHtml(item)}</span>`).join("");
  const whyCards = [];
  if (Array.isArray(precheck.risk_hits) && precheck.risk_hits.length) {
    whyCards.push(`
            <article class="client-ai-note client-ai-note--alert">
                <p class="client-ai-note__eyebrow">为什么这样提醒</p>
                <strong>这次输入里出现了需要先留意的信号。</strong>
                <p>${escapeHtml(precheck.risk_hits.join("、"))}</p>
            </article>
        `);
  }
  if (piiItems.length) {
    whyCards.push(`
            <article class="client-ai-note">
                <p class="client-ai-note__eyebrow">会如何保护你的内容</p>
                <strong>本地已经先识别出敏感信息。</strong>
                <p>${escapeHtml(piiItems.join("、"))}</p>
            </article>
        `);
  }
  if (precheck.upload_policy || precheck.redacted_text) {
    const uploadPreview = precheck.redacted_text && precheck.redacted_text !== ((_a = $("#checkin-content")) == null ? void 0 : _a.value.trim()) ? `上传前会优先使用这段脱敏文本：${escapeHtml(precheck.redacted_text.slice(0, 120))}` : `当前上传策略为 ${escapeHtml(precheck.upload_policy || "full")}。`;
    whyCards.push(`
            <article class="client-ai-note client-ai-note--soft">
                <p class="client-ai-note__eyebrow">上传前会发生什么</p>
                <strong>${precheck.upload_policy === "local_only" ? "这条内容暂时只保存在本地。" : precheck.upload_policy === "redacted_only" ? "系统会优先上传脱敏版本。" : "这条内容可以正常进入云端深分析。"} </strong>
                <p>${uploadPreview}</p>
            </article>
        `);
  }
  if ((_b = precheck.device_meta) == null ? void 0 : _b.image) {
    whyCards.push(`
            <article class="client-ai-note">
                <p class="client-ai-note__eyebrow">图片本地处理</p>
                <strong>图片已先做本地压缩和元信息整理。</strong>
                <p>${escapeHtml(`${precheck.device_meta.image.width || "--"}x${precheck.device_meta.image.height || "--"} · ${Math.round((precheck.device_meta.image.compressed_size || 0) / 1024)} KB`)}</p>
            </article>
        `);
  }
  if ((_c = precheck.device_meta) == null ? void 0 : _c.voice) {
    whyCards.push(`
            <article class="client-ai-note">
                <p class="client-ai-note__eyebrow">语音本地检测</p>
                <strong>录音已先完成时长和静音比例检查。</strong>
                <p>${escapeHtml(`时长 ${precheck.device_meta.voice.duration_seconds || "--"}s · 静音比 ${(_d = precheck.device_meta.voice.silence_ratio) != null ? _d : "--"}`)}</p>
            </article>
        `);
  }
  whyEl.innerHTML = whyCards.length ? whyCards.join("") : '<div class="empty-state">当前没有额外的本地提醒，这条内容会直接进入云端深分析。</div>';
}
function buildAttachmentDeviceMeta() {
  var _a, _b;
  const meta = {};
  if ((_a = state.pendingImageUpload) == null ? void 0 : _a.deviceMeta) {
    meta.image = state.pendingImageUpload.deviceMeta;
  }
  if ((_b = state.pendingVoiceUpload) == null ? void 0 : _b.deviceMeta) {
    meta.voice = state.pendingVoiceUpload.deviceMeta;
  }
  return Object.keys(meta).length ? meta : null;
}
function buildCombinedPrecheck(basePrecheck) {
  var _a, _b, _c, _d;
  if (!basePrecheck) {
    return null;
  }
  const attachmentTags = [
    ...((_b = (_a = state.pendingImageUpload) == null ? void 0 : _a.precheck) == null ? void 0 : _b.client_tags) || [],
    ...((_d = (_c = state.pendingVoiceUpload) == null ? void 0 : _c.precheck) == null ? void 0 : _d.client_tags) || []
  ];
  const deviceMeta = buildAttachmentDeviceMeta();
  const sourceTypes = ["text"];
  if (state.pendingImageUpload)
    sourceTypes.push("image");
  if (state.pendingVoiceUpload)
    sourceTypes.push("voice");
  return {
    ...basePrecheck,
    source_type: sourceTypes.length > 1 ? "mixed" : sourceTypes[0],
    client_tags: Array.from(/* @__PURE__ */ new Set([...basePrecheck.client_tags || [], ...attachmentTags])),
    device_meta: deviceMeta
  };
}
async function updateLocalDraftState() {
  const service = getClientAIService();
  if (!service) {
    state.localDraftCount = 0;
    state.localDraftSummary = [];
    return [];
  }
  const drafts = await service.listDrafts().catch(() => []);
  state.localDraftSummary = drafts;
  state.localDraftCount = drafts.filter((item) => item.status === "pending").length;
  return drafts;
}
function buildClientContextPayload(precheck, uploadPolicy) {
  if (!precheck) {
    return null;
  }
  return {
    source_type: precheck.source_type || "text",
    intent: precheck.intent || "daily",
    risk_level: precheck.risk_level || "none",
    risk_hits: Array.isArray(precheck.risk_hits) ? precheck.risk_hits : [],
    pii_summary: precheck.pii_summary || { total_hits: 0, categories: {} },
    privacy_mode: currentProductPrefs().privacyMode,
    upload_policy: uploadPolicy,
    redacted_text: precheck.redacted_text || null,
    client_tags: Array.isArray(precheck.client_tags) ? precheck.client_tags : [],
    device_meta: precheck.device_meta || null,
    ai_assist_enabled: currentProductPrefs().aiAssistEnabled
  };
}
async function precheckCurrentCheckinContent() {
  var _a, _b;
  const service = getClientAIService();
  const content = ((_a = $("#checkin-content")) == null ? void 0 : _a.value.trim()) || "";
  if (!content) {
    state.lastClientPrecheck = null;
    state.lastClientPrecheckGuidance = "";
    renderCheckinClientAIPanel(null);
    return null;
  }
  const prefs = currentProductPrefs();
  const basePrecheck = service ? await service.precheckText(content, {
    source_type: "text",
    privacy_mode: prefs.privacyMode,
    ai_assist_enabled: prefs.aiAssistEnabled,
    device_meta: buildAttachmentDeviceMeta()
  }) : {
    source_type: "text",
    intent: "daily",
    risk_level: "none",
    risk_hits: [],
    pii_summary: { total_hits: 0, categories: {} },
    privacy_mode: prefs.privacyMode,
    upload_policy: "full",
    redacted_text: content,
    client_tags: ["cloud_fallback"],
    device_meta: buildAttachmentDeviceMeta(),
    ai_assist_enabled: prefs.aiAssistEnabled,
    degraded: true
  };
  const combined = buildCombinedPrecheck(basePrecheck);
  combined.upload_policy = ((_b = window.QJClientAI) == null ? void 0 : _b.determineUploadPolicy) ? window.QJClientAI.determineUploadPolicy(combined, prefs) : "full";
  if (!service) {
    state.clientAIAvailable = false;
    state.clientAIFallbackActive = true;
    state.clientWorkerStatus = "fallback";
  }
  state.lastClientPrecheck = combined;
  state.lastClientPrecheckGuidance = buildClientGuidance(combined);
  renderCheckinClientAIPanel(combined);
  return combined;
}
function scheduleCheckinPrecheck() {
  clearTimeout(scheduleCheckinPrecheck.timer);
  scheduleCheckinPrecheck.timer = setTimeout(() => {
    precheckCurrentCheckinContent().catch(() => {
      state.clientAIFallbackActive = true;
      renderCheckinClientAIPanel(state.lastClientPrecheck);
    });
  }, 220);
}
async function prepareAttachment(type, file) {
  const service = getClientAIService();
  const prefs = currentProductPrefs();
  if (!service) {
    state.clientAIAvailable = false;
    state.clientAIFallbackActive = true;
    state.clientWorkerStatus = "fallback";
    if (type === "image") {
      return {
        file,
        previewUrl: URL.createObjectURL(file),
        deviceMeta: {
          original_type: file.type,
          output_type: file.type,
          original_size: file.size,
          compressed_size: file.size,
          exif_removed: false
        },
        precheck: {
          source_type: "image",
          intent: "daily",
          risk_level: "none",
          risk_hits: [],
          pii_summary: { total_hits: 0, categories: {} },
          privacy_mode: prefs.privacyMode,
          upload_policy: "full",
          redacted_text: null,
          client_tags: ["cloud_fallback"],
          device_meta: {
            original_type: file.type,
            output_type: file.type,
            original_size: file.size,
            compressed_size: file.size,
            exif_removed: false
          },
          ai_assist_enabled: prefs.aiAssistEnabled,
          degraded: true
        }
      };
    }
    return {
      file,
      previewUrl: null,
      deviceMeta: {
        mime_type: file.type,
        size_bytes: file.size,
        duration_seconds: null,
        silence_ratio: null,
        peak_level: null
      },
      precheck: {
        source_type: "voice",
        intent: "daily",
        risk_level: "none",
        risk_hits: [],
        pii_summary: { total_hits: 0, categories: {} },
        privacy_mode: prefs.privacyMode,
        upload_policy: "full",
        redacted_text: null,
        client_tags: ["cloud_fallback"],
        device_meta: {
          mime_type: file.type,
          size_bytes: file.size,
          duration_seconds: null,
          silence_ratio: null,
          peak_level: null
        },
        ai_assist_enabled: prefs.aiAssistEnabled,
        degraded: true
      }
    };
  }
  if (type === "image") {
    const prepared2 = await service.prepareImage(file);
    prepared2.precheck = await service.describeAttachmentMeta("image", prepared2.deviceMeta, {
      privacy_mode: prefs.privacyMode,
      ai_assist_enabled: prefs.aiAssistEnabled
    });
    return prepared2;
  }
  const prepared = await service.inspectVoice(file);
  prepared.precheck = await service.describeAttachmentMeta("voice", prepared.deviceMeta, {
    privacy_mode: prefs.privacyMode,
    ai_assist_enabled: prefs.aiAssistEnabled
  });
  return prepared;
}
async function uploadPreparedAttachment(type, prepared) {
  if (!(prepared == null ? void 0 : prepared.file)) {
    return null;
  }
  const result = await api.uploadFile(type, prepared.file);
  return result.url;
}
async function saveCheckinDraftLocally(basePayload, precheck, uploadPolicy) {
  var _a, _b, _c;
  const service = getClientAIService();
  if (!service) {
    throw new Error("本地保存不可用");
  }
  const draft = await service.saveDraft({
    pairId: ((_a = state.currentPair) == null ? void 0 : _a.id) || null,
    status: uploadPolicy === "local_only" ? "local_only" : "pending",
    createdAt: new Date().toISOString(),
    summary: {
      intent: precheck.intent,
      risk_level: precheck.risk_level,
      guidance: buildClientGuidance(precheck)
    },
    payload: {
      ...basePayload,
      client_context: buildClientContextPayload(precheck, uploadPolicy)
    },
    attachments: {
      imageFile: ((_b = state.pendingImageUpload) == null ? void 0 : _b.file) || null,
      voiceFile: ((_c = state.pendingVoiceUpload) == null ? void 0 : _c.file) || null
    }
  });
  await updateLocalDraftState();
  return draft;
}
async function syncLocalDraftRecord(draft) {
  var _a;
  if (!draft || !api.isLoggedIn()) {
    return false;
  }
  const payload = { ...draft.payload || {} };
  const attachments = draft.attachments || {};
  if (attachments.imageFile) {
    payload.image_url = await uploadPreparedAttachment("image", { file: attachments.imageFile });
  }
  if (attachments.voiceFile) {
    payload.voice_url = await uploadPreparedAttachment("voice", { file: attachments.voiceFile });
  }
  await api.submitCheckin(draft.pairId || null, payload);
  await ((_a = getClientAIService()) == null ? void 0 : _a.deleteDraft(draft.id));
  await updateLocalDraftState();
  return true;
}
async function syncPendingLocalDrafts({ silent = false } = {}) {
  if (!navigator.onLine || !api.isLoggedIn()) {
    return 0;
  }
  const drafts = await updateLocalDraftState();
  const pending = drafts.filter((item) => item.status === "pending");
  let synced = 0;
  for (const draft of pending) {
    try {
      await syncLocalDraftRecord(draft);
      synced += 1;
    } catch (error) {
      if (!silent) {
        showToast(error.message || "本地草稿同步失败");
      }
      break;
    }
  }
  if (!silent && synced > 0) {
    showToast(`已同步 ${synced} 条本地记录`);
  }
  return synced;
}
async function openClientRiskGate(precheck) {
  const resources = await api.getCrisisResources().catch(() => ({ hotlines: [], tips: [] }));
  openModal(`
        <h3>先把你放在更安全的位置</h3>
        <p class="muted-copy">${escapeHtml(buildClientGuidance(precheck))}</p>
        <div class="stack-list">
            ${(precheck.risk_hits || []).map((item) => `<div class="stack-item stack-item--static"><div>${svgIcon("i-alert")}</div><div class="stack-item__content"><strong>命中信号</strong><div class="stack-item__meta">${escapeHtml(item)}</div></div></div>`).join("")}
            ${(resources.hotlines || []).slice(0, 3).map((item) => `<div class="stack-item stack-item--static"><div>${svgIcon("i-phone")}</div><div class="stack-item__content"><strong>${escapeHtml(item.name)}</strong><div class="stack-item__meta">${escapeHtml(item.number)} · ${escapeHtml(item.hours || "")}</div></div></div>`).join("")}
        </div>
        <div class="hero-actions">
            <button class="button button--secondary" type="button" onclick="openCrisisResources()">查看全部资源</button>
            <button class="button button--ghost" type="button" onclick="closeModal()">知道了</button>
        </div>
    `);
}
async function handleCheckinSubmit(event) {
  var _a, _b, _c, _d, _e;
  event.preventDefault();
  if (!ensureLoginContext()) {
    return;
  }
  const content = $("#checkin-content").value.trim();
  if (!content) {
    showToast("请先写下今天的感受");
    return;
  }
  const payload = {
    content,
    mood_tags: state.selectedMoods,
    image_url: null,
    voice_url: null,
    mood_score: parseNullableInt(getSelectedValue("mood_score")),
    interaction_freq: parseNullableInt($("#interaction-frequency").value),
    interaction_initiative: getSelectedValue("interaction_initiative"),
    deep_conversation: parseNullableBool(getSelectedValue("deep_conversation")),
    task_completed: parseNullableBool(getSelectedValue("task_completed"))
  };
  const button = $("#checkin-submit-btn");
  button.disabled = true;
  button.textContent = "提交中...";
  try {
    const precheck = await precheckCurrentCheckinContent();
    const uploadPolicy = (precheck == null ? void 0 : precheck.upload_policy) || "full";
    payload.client_context = buildClientContextPayload(precheck, uploadPolicy);
    if (uploadPolicy !== "full") {
      await saveCheckinDraftLocally(payload, precheck, uploadPolicy);
    }
    if ((precheck == null ? void 0 : precheck.risk_level) === "high") {
      showToast("高风险内容已先保存在本地");
      await openClientRiskGate(precheck);
      resetCheckinForm();
      await showPage("home");
      return;
    }
    if (uploadPolicy === "local_only") {
      showToast("当前记录已保存在本地，稍后可再同步");
      resetCheckinForm();
      await showPage("home");
      return;
    }
    if ((_a = state.pendingImageUpload) == null ? void 0 : _a.file) {
      payload.image_url = await uploadPreparedAttachment("image", state.pendingImageUpload);
    }
    if ((_b = state.pendingVoiceUpload) == null ? void 0 : _b.file) {
      payload.voice_url = await uploadPreparedAttachment("voice", state.pendingVoiceUpload);
    }
    if (uploadPolicy === "redacted_only" && ((_c = payload.client_context) == null ? void 0 : _c.redacted_text)) {
      payload.content = payload.client_context.redacted_text;
    }
    await api.submitCheckin(((_d = state.currentPair) == null ? void 0 : _d.id) || null, payload);
    if (uploadPolicy !== "full") {
      await syncPendingLocalDrafts({ silent: true });
    }
    showToast(((_e = state.currentPair) == null ? void 0 : _e.id) ? "今日打卡已提交" : "个人记录已保存");
    resetCheckinForm();
    await showPage("home");
  } catch (error) {
    showToast(error.message || "提交失败");
  } finally {
    button.disabled = false;
    button.textContent = "提交今日打卡";
  }
}
function getSelectedValue(name) {
  var _a;
  return ((_a = document.querySelector(`[data-selected-name="${name}"]`)) == null ? void 0 : _a.dataset.selectedValue) || null;
}
function parseNullableInt(value) {
  if (value === null || value === void 0 || value === "")
    return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}
function parseNullableBool(value) {
  if (value === null || value === void 0 || value === "")
    return null;
  return value === "true";
}
function resetCheckinForm() {
  const form = $("#checkin-form");
  if (form)
    form.reset();
  state.selectedMoods = [];
  state.uploadedImageUrl = null;
  state.uploadedVoiceUrl = null;
  state.pendingImageUpload = null;
  state.pendingVoiceUpload = null;
  state.lastClientPrecheck = null;
  state.lastClientPrecheckGuidance = "";
  state.agentSessionId = null;
  state.agentMessages = [];
  state.lastAgentReply = "";
  state.lastMessageSimulation = null;
  renderCheckinPage();
  safeSetHtml("#image-upload-preview", "");
  safeSetHtml("#voice-upload-preview", "");
  $$("[data-selected-name]").forEach((item) => {
    delete item.dataset.selectedName;
    delete item.dataset.selectedValue;
    item.classList.remove("select-card--active");
  });
}
async function handleUpload(type, file) {
  var _a;
  if (!ensureLoginContext()) {
    return;
  }
  try {
    if (type === "image") {
      const prepared = await prepareAttachment("image", file);
      state.pendingImageUpload = prepared;
      state.uploadedImageUrl = null;
      $("#image-upload-preview").innerHTML = `<img class="upload-preview__image" src="${prepared.previewUrl}" alt="上传图片预览"><div class="upload-preview__chip">${svgIcon("i-lock")} 已本地压缩与去 EXIF · ${Math.round((prepared.deviceMeta.compressed_size || 0) / 1024)} KB</div>`;
    } else {
      const prepared = await prepareAttachment("voice", file);
      state.pendingVoiceUpload = prepared;
      state.uploadedVoiceUrl = null;
      $("#voice-upload-preview").innerHTML = `<div class="upload-preview__chip">${svgIcon("i-mic")} 已本地读取语音 · ${escapeHtml(`时长 ${prepared.deviceMeta.duration_seconds || "--"}s / 静音比 ${(_a = prepared.deviceMeta.silence_ratio) != null ? _a : "--"}`)}</div>`;
    }
    await precheckCurrentCheckinContent();
    showToast(type === "image" ? "图片已完成本地处理" : "语音元信息已完成本地分析");
  } catch (error) {
    showToast(error.message || "上传失败");
  }
}
async function loadReportPage() {
  if (!hasCurrentPair()) {
    renderReport(null, [], { trend: [] });
    return;
  }
  const pairId = state.currentPair.id;
  const [latest, history, trend] = await Promise.allSettled([
    api.getLatestReport(pairId, state.selectedReportType),
    api.getReportHistory(pairId, state.selectedReportType, 6),
    state.selectedReportType === "daily" ? api.getHealthTrend(pairId, 14) : Promise.resolve({ trend: [] })
  ]);
  renderReport(
    unwrapResult(latest, null),
    unwrapResult(history, []),
    unwrapResult(trend, { trend: [] })
  );
}
async function openCheckinMode(mode = "form") {
  state.checkinMode = mode;
  await showPage("checkin");
}
function renderReport(report, history, trendData) {
  if (report && report.status === "pending") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                当前${formatReportType(state.selectedReportType)}正在后台生成中。页面会在拿到结果后刷新；如果网络波动，也可以稍后再次进入本页查看。
            </div>`);
  } else if (report && report.status === "failed") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                当前${formatReportType(state.selectedReportType)}生成失败，请稍后重试。
            </div>`);
  } else if (!report || report.status !== "completed") {
    safeSetHtml("#report-main", `
      <div class="empty-state">
        当前还没有可展示的${state.selectedReportType === "daily" ? "日报" : state.selectedReportType === "weekly" ? "周报" : "月报"}。完成打卡并触发生成后，这里会显示最新报告。
      </div>`);
  } else {
    const content = report.content || {};
    const score2 = content.health_score || content.overall_health_score || 72;
    const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
    const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);
    safeSetHtml("#report-main", `
      <div class="score-ring" style="--score:${Math.max(1, Math.min(100, score2))}"><span>${score2}</span></div>
      <h4>${state.selectedReportType === "daily" ? "今日关系指数" : state.selectedReportType === "weekly" ? "周关系指数" : "月关系指数"}</h4>
      <p class="muted-copy">${escapeHtml(content.insight || content.encouragement || content.executive_summary || "系统已经生成当前阶段的关系洞察。")}</p>
      ${content.suggestion || content.trend_description ? `<div class="hero-card hero-card--accent"><strong>本阶段建议</strong><p>${escapeHtml(content.suggestion || content.trend_description)}</p></div>` : ""}
            ${renderAttachmentSignals(content)}
      ${renderTrend(trendData)}
      <div class="layout-grid">
        <div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">HIGHLIGHTS</p><h4>积极信号</h4></div></div>${renderBulletList(highlights, "当前没有高亮项")}</div>
        <div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">FOCUS</p><h4>需要关注</h4></div></div>${renderBulletList(concerns, "当前没有额外提醒")}</div>
      </div>`);
  }
  const list = $("#report-history-list");
  if (!list)
    return;
  if (!history.length) {
    list.innerHTML = '<div class="empty-state">当前没有历史报告记录。</div>';
    return;
  }
  list.innerHTML = history.map((item) => `
    <article class="stack-item">
      <div>
        <strong>${formatReportType(state.selectedReportType)} · ${escapeHtml(item.report_date || "未命名")}</strong>
        <div class="stack-item__meta">状态：${escapeHtml(item.status || "completed")}</div>
      </div>
      <span class="pill">已生成</span>
    </article>`).join("");
}
function renderTrend(trendData) {
  const points = (trendData == null ? void 0 : trendData.trend) || [];
  if (points.length < 2)
    return "";
  const width = 280;
  const height = 90;
  const pad = 10;
  const coords = points.map((point, index) => {
    const x = pad + index / (points.length - 1) * (width - pad * 2);
    const y = height - pad - (point.score || 0) / 100 * (height - pad * 2);
    return `${x},${y}`;
  });
  return `
    <div class="panel">
      <div class="panel__header"><div><p class="panel__eyebrow">TREND</p><h4>近阶段变化</h4></div></div>
      <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto">
        <polyline points="${coords.join(" ")}" fill="none" stroke="#d76848" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
      </svg>
    </div>`;
}
function renderBulletList(items, emptyText) {
  if (!items.length) {
    return `<div class="empty-state">${emptyText}</div>`;
  }
  return `<div class="stack-list">${items.map((item) => `<div class="stack-item"><div>${svgIcon("i-check")}</div><div>${escapeHtml(item)}</div></div>`).join("")}</div>`;
}
function renderAttachmentSignals(content) {
  const signals = content == null ? void 0 : content.attachment_signals;
  if (!signals) {
    return "";
  }
  const buildItems = (data) => {
    var _a;
    if (!data) {
      return [];
    }
    const items = [];
    if (data.image) {
      items.push(`图片情绪：${data.image.mood || "unknown"}`);
      items.push(`图片信号：${data.image.social_signal || "无"}`);
      items.push(`图片评分：${(_a = data.image.score) != null ? _a : "--"}`);
    }
    if (data.voice) {
      items.push(`语音语气：${data.voice.tone || "unknown"}`);
      items.push(`背景声音：${data.voice.background_sound || "未知"}`);
      items.push(`关系线索：${data.voice.relationship_signal || "无"}`);
      if (data.voice.transcript) {
        items.push(`语音转写：${data.voice.transcript}`);
      }
    }
    return items;
  };
  const cards = [];
  if (signals.a || signals.b) {
    const aItems = buildItems(signals.a);
    const bItems = buildItems(signals.b);
    if (aItems.length) {
      cards.push(`<div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">ATTACHMENT</p><h4>A 方附件线索</h4></div></div>${renderBulletList(aItems, "当前没有附件分析结果")}</div>`);
    }
    if (bItems.length) {
      cards.push(`<div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">ATTACHMENT</p><h4>B 方附件线索</h4></div></div>${renderBulletList(bItems, "当前没有附件分析结果")}</div>`);
    }
  } else {
    const items = buildItems(signals);
    if (items.length) {
      cards.push(`<div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">ATTACHMENT</p><h4>附件线索</h4></div></div>${renderBulletList(items, "当前没有附件分析结果")}</div>`);
    }
  }
  if (!cards.length) {
    return "";
  }
  return `<div class="layout-grid">${cards.join("")}</div>`;
}
function formatReportType(type) {
  return { daily: "日报", weekly: "周报", monthly: "月报" }[type] || "报告";
}
async function generateReport() {
  if (!ensurePairContext("请先创建或加入关系，再生成报告")) {
    return;
  }
  const button = $("#report-generate-btn");
  button.disabled = true;
  button.textContent = "生成中...";
  const reportType = state.selectedReportType;
  try {
    if (reportType === "daily") {
      await api.generateDailyReport(state.currentPair.id);
    } else if (reportType === "weekly") {
      await api.generateWeeklyReport(state.currentPair.id);
    } else {
      await api.generateMonthlyReport(state.currentPair.id);
    }
    button.textContent = "等待结果...";
    showToast("已触发报告生成，正在等待结果");
    const report = await api.waitForReport(state.currentPair.id, reportType);
    await loadReportPage();
    if ((report == null ? void 0 : report.status) === "completed") {
      showToast(`${formatReportType(reportType)}已生成完成`);
    } else if ((report == null ? void 0 : report.status) === "failed") {
      showToast(`${formatReportType(reportType)}生成失败，请稍后重试`);
    } else {
      showToast(`${formatReportType(reportType)}仍在后台生成，可稍后刷新查看`);
    }
  } catch (error) {
    showToast(error.message || "生成失败");
  } finally {
    button.disabled = false;
    button.textContent = "生成当前简报";
  }
}
async function loadProfilePage() {
  if (!api.isLoggedIn()) {
    safeSetHtml("#profile-summary", `<p class="eyebrow">PROFILE</p><h3>请先登录</h3><p>登录后这里会显示你的账号信息和当前关系状态。</p>`);
    safeSetHtml("#profile-account-panel", '<div class="empty-state">登录后可查看账户资料。</div>');
    safeSetHtml("#profile-pair-panel", '<div class="empty-state">登录后可查看当前关系状态。</div>');
    safeSetHtml("#profile-relations-panel", '<div class="empty-state">登录后可查看全部关系列表和多关系切换入口。</div>');
    safeSetHtml("#profile-privacy-panel", '<div class="empty-state">登录后可查看隐私保护状态、审计时间线和删除请求入口。</div>');
    return;
  }
  const me = state.me || await api.getMe();
  state.me = me;
  state.productPrefs = {
    ...CLIENT_AI_PREFS,
    ...normalizeProductPrefs(me)
  };
  const pair = state.currentPair;
  const allPairs = state.pairs || [];
  const activePairs = allPairs.filter((item) => item.status === "active");
  const pendingPairs = allPairs.filter((item) => item.status === "pending");
  await updateLocalDraftState().catch(() => []);
  const [unbindStatus, privacyStatus, privacyAuditEntries] = await Promise.all([
    pair ? api.getUnbindStatus(pair.id).catch(() => ({ has_request: false })) : Promise.resolve({ has_request: false }),
    api.getPrivacyStatus().catch(() => null),
    api.getMyPrivacyAudit(12).catch(() => [])
  ]);
  state.privacyStatus = privacyStatus;
  state.privacyAuditEntries = Array.isArray(privacyAuditEntries) ? privacyAuditEntries : [];
  await loadAdminPolicies().catch(() => []);
  const adminLauncher = state.isAdmin ? renderPolicyWorkbenchLauncher(state.adminPolicies) : "";
  const adminErrorNotice = renderPolicyWorkbenchErrorNotice(state.policyWorkbenchError);
  safeSetHtml("#profile-summary", `
    <p class="eyebrow">账户</p>
    <h3>${escapeHtml(me.nickname || "用户")}</h3>
        <p>${escapeHtml(isDemoMode() && me.email ? "样例邮箱已隐藏" : me.email || "未填写邮箱")} · ${pair ? "已绑定关系" : "未绑定关系"}</p>
        ${state.profileFeedback ? `<div class="profile-banner"><strong>已同步更新</strong><div>${escapeHtml(state.profileFeedback)}</div></div>` : ""}
        <div class="metric-strip">
            <article class="mini-stat"><span>活跃关系</span><strong>${activePairs.length}</strong></article>
            <article class="mini-stat"><span>待加入关系</span><strong>${pendingPairs.length}</strong></article>
            <article class="mini-stat"><span>当前对象</span><strong>${escapeHtml(pair ? getPartnerDisplayName(pair) : "未设置")}</strong></article>
        </div>`);
  safeSetHtml("#profile-account-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">账户详情</p><h4>账户信息</h4></div></div>
        <p class="panel-inline-hint">点击下面的条目就能直接修改昵称和密码，不再需要额外找设置入口。</p>
        <div class="detail-list">
            <div class="detail-list__item"><span>昵称</span><strong>${escapeHtml(me.nickname || "未设置")}</strong></div>
            <div class="detail-list__item"><span>邮箱</span><strong>${escapeHtml(isDemoMode() && me.email ? "样例邮箱已隐藏" : me.email || "未绑定")}</strong></div>
            <div class="detail-list__item"><span>手机号</span><strong>${escapeHtml(maskPhone(me.phone))}</strong></div>
            <div class="detail-list__item"><span>登录渠道</span><strong>${escapeHtml(getAccountChannels(me))}</strong></div>
            <div class="detail-list__item"><span>账户创建时间</span><strong>${escapeHtml(formatDateOnly(me.created_at))}</strong></div>
            <div class="detail-list__item"><span>账户 ID</span><strong>${escapeHtml(String(me.id).slice(0, 8).toUpperCase())}</strong></div>
        </div>
        <div class="stack-list">
            <button class="stack-item stack-item--action" type="button" onclick="openProfileEditor()" aria-label="修改名称">
                <div>${svgIcon("i-edit")}</div>
                <div class="stack-item__content"><strong>修改名称</strong><div class="stack-item__meta">当前昵称：${escapeHtml(me.nickname || "未设置")}</div></div>
                <div class="stack-item__aside"><span class="stack-item__hint">点击修改</span>${svgIcon("i-arrow-right", "icon-sm")}</div>
            </button>
            <button class="stack-item stack-item--action" type="button" onclick="openPasswordEditor()" aria-label="修改密码">
                <div>${svgIcon("i-lock")}</div>
                <div class="stack-item__content"><strong>修改密码</strong><div class="stack-item__meta">建议定期更新登录密码，保护关系数据和账号安全。</div></div>
                <div class="stack-item__aside"><span class="stack-item__hint">点击修改</span>${svgIcon("i-arrow-right", "icon-sm")}</div>
            </button>
            ${adminLauncher}
            ${adminErrorNotice}
        </div>`);
  safeSetHtml("#profile-pair-panel", pair ? `<div class="panel__header"><div><p class="panel__eyebrow">关系</p><h4>当前关系与切换</h4></div></div>
                 <p class="panel-inline-hint">你可以同时管理多段关系，首页顶部和绑定页都会保留切换入口；这里负责当前关系的详细设置。</p>
              <div class="metric-strip">
                  <article class="mini-stat"><span>关系类型</span><strong>${escapeHtml(TYPE_LABELS[pair.type] || pair.type)}</strong></article>
                  <article class="mini-stat"><span>当前状态</span><strong>${pair.status === "active" ? "已激活" : "等待加入"}</strong></article>
                  <article class="mini-stat"><span>邀请码</span><strong>${escapeHtml(pair.invite_code || "无")}</strong></article>
             </div>
                 <div class="stack-item stack-item--static"><div>${svgIcon("i-link")}</div><div class="stack-item__content"><strong>${escapeHtml(getPartnerDisplayName(pair))}</strong><div class="stack-item__meta">创建于 ${escapeHtml(formatDateOnly(pair.created_at))} · ${pair.status === "active" ? "你们已经在共享关系数据" : "对方加入后会开始共享数据"}</div></div></div>
                 <button class="stack-item stack-item--action" type="button" onclick="openPartnerNicknameEditor()" aria-label="编辑对方备注">
                     <div>${svgIcon("i-edit")}</div>
                     <div class="stack-item__content"><strong>对方备注</strong><div class="stack-item__meta">${escapeHtml(pair.custom_partner_nickname || "尚未设置，当前默认显示系统昵称")}</div></div>
                     <div class="stack-item__aside"><span class="stack-item__hint">点击修改</span>${svgIcon("i-arrow-right", "icon-sm")}</div>
                 </button>
                  <button class="stack-item stack-item--action" type="button" onclick="openUnbindPanel()" aria-label="管理解绑状态">
                      <div>${svgIcon("i-refresh")}</div>
                      <div class="stack-item__content"><strong>解绑状态</strong><div class="stack-item__meta">${unbindStatus.has_request ? unbindStatus.requested_by_me ? `你已发起解绑，剩余 ${unbindStatus.days_remaining} 天。` : "对方已发起解绑，等待你确认。" : "当前没有进行中的解绑申请。"}</div></div>
                      <div class="stack-item__aside"><span class="stack-item__hint">点击处理</span>${svgIcon("i-arrow-right", "icon-sm")}</div>
                  </button>` : '<div class="empty-state">当前没有激活关系。</div>');
  safeSetHtml("#profile-relations-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">关系</p><h4>全部关系</h4></div></div>
        <p class="panel-inline-hint">这里集中展示你账号下的所有关系。点击任意一段关系，就能切换首页、报告、记录和设置的当前关系。</p>
        ${renderRelationManagementList(allPairs, (pair == null ? void 0 : pair.id) || null)}
        <div class="hero-actions">
            <button class="button button--primary" type="button" onclick="showPage('pair')">新增或加入关系</button>
            <button class="button button--ghost" type="button" onclick="showPage('home')">回到当前关系首页</button>
        </div>`);
  safeSetHtml("#profile-privacy-panel", renderPrivacyCenterPanel(privacyStatus, state.privacyAuditEntries));
}
function renderPrivacyProtectionChips(status) {
  if (!status)
    return '<div class="empty-state">隐私状态暂时不可用。</div>';
  const chips = [
    status.sandbox_enabled ? "隐私沙盒已开启" : "隐私沙盒未开启",
    status.log_masking ? "日志脱敏" : "日志明文",
    status.llm_redaction ? "模型输入脱敏" : "模型输入不脱敏",
    status.private_upload_access ? "私有上传访问" : "公开上传兼容",
    status.audit_enabled ? "审计已开启" : "审计未开启"
  ];
  return `
        <div class="evidence-strip">
            ${chips.map((item) => `<span class="evidence-pill">${escapeHtml(item)}</span>`).join("")}
        </div>`;
}
function renderPrivacyAuditTimeline(entries = []) {
  if (!entries.length) {
    return '<div class="empty-state">最近还没有隐私相关活动，等你查看状态、上传文件或提交删除请求后，这里会开始记录。</div>';
  }
  return `
        <div class="stack-list">
            ${entries.map((entry) => `
                <div class="stack-item stack-item--static">
                    <div>${svgIcon("i-lock")}</div>
                    <div class="stack-item__content">
                        <strong>${escapeHtml(entry.event_label || "隐私事件")}</strong>
                        <div class="stack-item__meta">${escapeHtml(entry.summary || "系统记录了一次隐私相关操作。")}</div>
                        <div class="stack-item__meta">${escapeHtml(formatDateOnly(entry.occurred_at))}</div>
                    </div>
                </div>`).join("")}
        </div>`;
}
function renderPrivacyGovernanceLauncher(status, entries = []) {
  const latest = (status == null ? void 0 : status.latest_delete_request) || null;
  const reviewLabel = latest ? latest.status === "manual_review" ? "有人工复核项待处理" : `最新删除状态：${latest.status}` : "最近没有删除请求";
  return `
        <button class="stack-item stack-item--action" type="button" onclick="openPrivacyGovernanceWorkbench()" aria-label="打开隐私治理台">
            <div>${svgIcon("i-lock")}</div>
            <div class="stack-item__content">
                <strong>隐私治理台</strong>
                <div class="stack-item__meta">最近可见 ${entries.length} 条隐私审计，${escapeHtml(reviewLabel)}。</div>
            </div>
            <div class="stack-item__aside"><span class="stack-item__hint">点击管理</span>${svgIcon("i-arrow-right", "icon-sm")}</div>
        </button>`;
}
function renderPrivacyCenterPanel(status, entries = []) {
  var _a, _b, _c;
  const latest = (status == null ? void 0 : status.latest_delete_request) || null;
  const deleteStatus = latest ? `${latest.status}${latest.scheduled_for ? ` · 计划执行：${formatDateOnly(latest.scheduled_for)}` : ""}` : "当前没有进行中的删除请求";
  const deleteAction = (latest == null ? void 0 : latest.can_cancel) ? `<button class="button button--ghost" type="button" onclick="cancelPrivacyDeleteRequestAction()">撤回删除请求</button>` : `<button class="button button--danger" type="button" onclick="submitPrivacyDeleteRequest()">发起删除请求</button>`;
  return `
        <div class="panel__header"><div><p class="panel__eyebrow">PRIVACY CENTER</p><h4>隐私中心与保留治理</h4></div></div>
        <p class="panel-inline-hint">这里展示系统当前启用了哪些保护、审计会保留多久，以及你的删除请求正处在哪一步。</p>
        ${renderPrivacyProtectionChips(status)}
        <div class="detail-list">
            <div class="detail-list__item"><span>审计保留周期</span><strong>${escapeHtml(String((_a = status == null ? void 0 : status.audit_retention_days) != null ? _a : "--"))} 天</strong></div>
            <div class="detail-list__item"><span>上传票据有效期</span><strong>${escapeHtml(String((_b = status == null ? void 0 : status.upload_ticket_ttl_minutes) != null ? _b : "--"))} 分钟</strong></div>
            <div class="detail-list__item"><span>删除宽限期</span><strong>${escapeHtml(String((_c = status == null ? void 0 : status.delete_grace_days) != null ? _c : "--"))} 天</strong></div>
            <div class="detail-list__item"><span>当前删除状态</span><strong>${escapeHtml(deleteStatus)}</strong></div>
            <div class="detail-list__item"><span>端侧引擎</span><strong>${escapeHtml(getClientLayerStatusSummary())}</strong></div>
            <div class="detail-list__item"><span>端侧 AI 辅助</span><strong>${currentProductPrefs().aiAssistEnabled ? "开启" : "关闭"}</strong></div>
            <div class="detail-list__item"><span>隐私模式</span><strong>${escapeHtml(currentProductPrefs().privacyMode === "local_first" ? "local-first" : "cloud")}</strong></div>
            <div class="detail-list__item"><span>默认入口</span><strong>${escapeHtml(currentProductPrefs().preferredEntry)}</strong></div>
            <div class="detail-list__item"><span>本地待同步</span><strong>${escapeHtml(String(state.localDraftCount || 0))} 条</strong></div>
        </div>
        <div class="profile-banner">
            <strong>信任与边界</strong>
            <div>系统会脱敏日志和模型输入，但它仍然不是临床判断，也不能替代人工支持；当关系风险升级时，请把它当成辅助工具，而不是唯一依据。</div>
        </div>
        <div class="hero-actions">
            ${deleteAction}
            <button class="button button--ghost" type="button" onclick="toggleClientAIAssist()">${currentProductPrefs().aiAssistEnabled ? "关闭端侧 AI 辅助" : "开启端侧 AI 辅助"}</button>
            <button class="button button--ghost" type="button" onclick="togglePrivacyMode()">${currentProductPrefs().privacyMode === "local_first" ? "切回云端模式" : "切换 local-first"}</button>
            <button class="button button--ghost" type="button" onclick="cyclePreferredEntry()">切换默认入口</button>
            <button class="button button--secondary" type="button" onclick="syncLocalDraftsFromProfile()">同步本地记录</button>
            ${state.isAdmin ? `<button class="button button--ghost" type="button" onclick="openPrivacyGovernanceWorkbench()">打开隐私治理台</button>` : ""}
        </div>
        <div class="panel__header panel__header--compact"><div><p class="panel__eyebrow">AUDIT</p><h4>最近隐私活动</h4></div></div>
        ${renderPrivacyAuditTimeline(entries)}
        ${state.isAdmin ? renderPrivacyGovernanceLauncher(status, entries) : ""}`;
}
async function submitPrivacyDeleteRequest() {
  if (!api.isLoggedIn())
    return;
  const confirmed = window.confirm("发起删除请求后，系统会进入 7 天宽限期。到期后会删除你的私有数据，并对共享关系数据转入人工复核。确认继续吗？");
  if (!confirmed)
    return;
  try {
    const payload = await api.createPrivacyDeleteRequest();
    state.profileFeedback = `删除请求已创建，当前状态：${payload.status}。`;
    await loadProfilePage();
  } catch (error) {
    state.profileFeedback = error.message || "删除请求创建失败。";
    await loadProfilePage();
  }
}
async function cancelPrivacyDeleteRequestAction() {
  if (!api.isLoggedIn())
    return;
  const confirmed = window.confirm("确认撤回当前删除请求吗？");
  if (!confirmed)
    return;
  try {
    const payload = await api.cancelPrivacyDeleteRequest();
    state.profileFeedback = `删除请求已撤回，当前状态：${payload.status}。`;
    await loadProfilePage();
  } catch (error) {
    state.profileFeedback = error.message || "删除请求撤回失败。";
    await loadProfilePage();
  }
}
async function updateProductPrefs(nextPrefs, successMessage) {
  if (!api.isLoggedIn()) {
    showToast("请先登录");
    return;
  }
  try {
    const me = await api.updateMe(prefsToApiPayload(nextPrefs));
    state.me = me;
    state.productPrefs = {
      ...CLIENT_AI_PREFS,
      ...normalizeProductPrefs(me)
    };
    state.profileFeedback = successMessage;
    showToast(successMessage);
    renderCheckinClientAIPanel(state.lastClientPrecheck);
    await loadProfilePage();
  } catch (error) {
    showToast(error.message || "设置保存失败");
  }
}
async function toggleClientAIAssist() {
  const prefs = currentProductPrefs();
  await updateProductPrefs(
    {
      ...prefs,
      aiAssistEnabled: !prefs.aiAssistEnabled
    },
    !prefs.aiAssistEnabled ? "端侧 AI 辅助已开启" : "端侧 AI 辅助已关闭"
  );
}
async function togglePrivacyMode() {
  const prefs = currentProductPrefs();
  const nextMode = prefs.privacyMode === "local_first" ? "cloud" : "local_first";
  await updateProductPrefs(
    {
      ...prefs,
      privacyMode: nextMode
    },
    nextMode === "local_first" ? "已切换到 local-first 模式" : "已切换到云端模式"
  );
}
async function cyclePreferredEntry() {
  const prefs = currentProductPrefs();
  const options = ["daily", "emergency", "reflection"];
  const currentIndex = options.indexOf(prefs.preferredEntry);
  const nextEntry = options[(currentIndex + 1) % options.length];
  await updateProductPrefs(
    {
      ...prefs,
      preferredEntry: nextEntry
    },
    `默认入口已切换为 ${nextEntry}`
  );
}
async function syncLocalDraftsFromProfile() {
  if (!api.isLoggedIn()) {
    showToast("请先登录");
    return;
  }
  await syncPendingLocalDrafts();
  await loadProfilePage();
}
function buildDemoPrivacyGovernanceData() {
  var _a, _b, _c, _d, _e, _f;
  const latestRequest = ((_a = state.privacyStatus) == null ? void 0 : _a.latest_delete_request) || {
    id: "demo-privacy-delete-request",
    status: "manual_review",
    requested_at: "2026-03-22T09:00:00",
    scheduled_for: "2026-03-29T09:00:00",
    review_note: "演示环境：共享关系数据会进入人工复核。",
    can_cancel: false
  };
  const deleteRequests = [
    {
      ...latestRequest,
      user_id: ((_b = state.me) == null ? void 0 : _b.id) || "demo-user",
      user_email: "demo@sample.invalid",
      user_nickname: ((_c = state.me) == null ? void 0 : _c.nickname) || "演示用户"
    }
  ];
  const audits = Array.isArray(state.privacyAuditEntries) && state.privacyAuditEntries.length ? state.privacyAuditEntries.map((entry) => {
    var _a2, _b2;
    return {
      ...entry,
      user_id: ((_a2 = state.me) == null ? void 0 : _a2.id) || "demo-user",
      pair_id: ((_b2 = state.currentPair) == null ? void 0 : _b2.id) || null,
      source: "privacy"
    };
  }) : [
    {
      event_id: "demo-privacy-audit-1",
      event_type: "privacy.ai.chat.logged",
      event_label: "记录了一次 AI 文本调用",
      summary: "演示环境下，系统只保存脱敏摘要和哈希，不保留原始 prompt。",
      occurred_at: "2026-03-24T09:30:00",
      user_id: ((_d = state.me) == null ? void 0 : _d.id) || "demo-user",
      pair_id: ((_e = state.currentPair) == null ? void 0 : _e.id) || null,
      source: "privacy"
    },
    {
      event_id: "demo-privacy-audit-2",
      event_type: "privacy.retention.purged",
      event_label: "执行了一次隐私保留清扫",
      summary: "上一次 dry run 显示 2 条过期隐私事件、1 个临时转录文件待清理。",
      occurred_at: "2026-03-23T18:00:00",
      user_id: ((_f = state.me) == null ? void 0 : _f.id) || "demo-user",
      pair_id: null,
      source: "admin"
    }
  ];
  return {
    deleteRequests,
    audits,
    sweepSummary: {
      dry_run: true,
      expired_privacy_events: 2,
      stale_temp_files: 1,
      due_requests: deleteRequests.length,
      executed: 0,
      manual_review: deleteRequests.filter((item) => item.status === "manual_review").length
    }
  };
}
function renderAdminPrivacyDeleteRequests(items = []) {
  if (!items.length) {
    return '<div class="empty-state">当前没有待处理的删除请求，用户发起删除或宽限期到期后，这里会出现治理动作。</div>';
  }
  return `
        <div class="privacy-governance__list">
            ${items.map((item) => {
    const canReview = ["pending", "manual_review"].includes(String((item == null ? void 0 : item.status) || ""));
    const reviewNote = (item == null ? void 0 : item.review_note) ? `<div class="privacy-governance-item__note">${escapeHtml(item.review_note)}</div>` : "";
    return `
                    <article class="privacy-governance-item">
                        <div class="privacy-governance-item__header">
                            <div>
                                <p class="panel__eyebrow">DELETE REQUEST</p>
                                <h4>${escapeHtml((item == null ? void 0 : item.user_nickname) || (item == null ? void 0 : item.user_email) || "未知用户")}</h4>
                            </div>
                            <span class="status-chip">${escapeHtml(String((item == null ? void 0 : item.status) || "unknown"))}</span>
                        </div>
                        <div class="detail-list">
                            <div class="detail-list__item"><span>用户邮箱</span><strong>${escapeHtml((item == null ? void 0 : item.user_email) || "未提供")}</strong></div>
                            <div class="detail-list__item"><span>申请时间</span><strong>${escapeHtml(formatDate(item == null ? void 0 : item.requested_at))}</strong></div>
                            <div class="detail-list__item"><span>计划执行</span><strong>${escapeHtml((item == null ? void 0 : item.scheduled_for) ? formatDate(item.scheduled_for) : "待管理员处理")}</strong></div>
                            <div class="detail-list__item"><span>最近处理人</span><strong>${escapeHtml((item == null ? void 0 : item.reviewed_by) || "系统 / 未处理")}</strong></div>
                        </div>
                        ${reviewNote}
                        ${canReview ? `
                            <div class="hero-actions">
                                <button class="button button--primary" type="button" onclick="approvePrivacyDeleteRequest('${escapeHtml(item.id)}')">批准执行</button>
                                <button class="button button--ghost" type="button" onclick="rejectPrivacyDeleteRequest('${escapeHtml(item.id)}')">驳回请求</button>
                            </div>` : ""}
                    </article>`;
  }).join("")}
        </div>`;
}
function renderAdminPrivacyAudits(entries = []) {
  if (!entries.length) {
    return '<div class="empty-state">最近没有新的隐私审计事件。</div>';
  }
  return `
        <div class="stack-list">
            ${entries.map((entry) => `
                <div class="stack-item stack-item--static">
                    <div>${svgIcon("i-lock")}</div>
                    <div class="stack-item__content">
                        <strong>${escapeHtml((entry == null ? void 0 : entry.event_label) || (entry == null ? void 0 : entry.event_type) || "隐私事件")}</strong>
                        <div class="stack-item__meta">${escapeHtml((entry == null ? void 0 : entry.summary) || "系统记录了一次隐私相关动作。")}</div>
                        <div class="stack-item__meta">用户：${escapeHtml((entry == null ? void 0 : entry.user_id) || "系统")} · 来源：${escapeHtml((entry == null ? void 0 : entry.source) || "privacy")} · ${escapeHtml(formatDate(entry == null ? void 0 : entry.occurred_at))}</div>
                    </div>
                </div>`).join("")}
        </div>`;
}
function renderPrivacySweepSummary(summary) {
  var _a, _b, _c, _d, _e;
  if (!summary) {
    return '<div class="empty-state">你可以先跑一次 dry run，确认会清掉多少过期审计和临时转录文件，再决定是否正式执行。</div>';
  }
  return `
        <div class="detail-list">
            <div class="detail-list__item"><span>模式</span><strong>${summary.dry_run ? "Dry Run" : "已执行"}</strong></div>
            <div class="detail-list__item"><span>过期隐私事件</span><strong>${escapeHtml(String((_a = summary.expired_privacy_events) != null ? _a : 0))}</strong></div>
            <div class="detail-list__item"><span>临时转录文件</span><strong>${escapeHtml(String((_b = summary.stale_temp_files) != null ? _b : 0))}</strong></div>
            <div class="detail-list__item"><span>到期删除请求</span><strong>${escapeHtml(String((_c = summary.due_requests) != null ? _c : 0))}</strong></div>
            <div class="detail-list__item"><span>自动执行</span><strong>${escapeHtml(String((_d = summary.executed) != null ? _d : 0))}</strong></div>
            <div class="detail-list__item"><span>转人工复核</span><strong>${escapeHtml(String((_e = summary.manual_review) != null ? _e : 0))}</strong></div>
        </div>`;
}
function renderPrivacyGovernanceWorkbench(data = {}) {
  var _a;
  const deleteRequests = Array.isArray(data.deleteRequests) ? data.deleteRequests : [];
  const audits = Array.isArray(data.audits) ? data.audits : [];
  const status = data.status || state.privacyStatus || null;
  const errorBlock = data.error ? `<div class="profile-banner"><strong>部分数据暂不可用</strong><div>${escapeHtml(data.error)}</div></div>` : "";
  const statusBlock = status ? `<div class="detail-list">
                <div class="detail-list__item"><span>隐私沙盒</span><strong>${status.sandbox_enabled ? "已开启" : "未开启"}</strong></div>
                <div class="detail-list__item"><span>日志脱敏</span><strong>${status.log_masking ? "已开启" : "未开启"}</strong></div>
                <div class="detail-list__item"><span>模型脱敏</span><strong>${status.llm_redaction ? "已开启" : "未开启"}</strong></div>
                <div class="detail-list__item"><span>审计保留</span><strong>${escapeHtml(String((_a = status.audit_retention_days) != null ? _a : "--"))} 天</strong></div>
            </div>` : '<div class="empty-state">当前未拿到最新隐私状态。</div>';
  return `
        <div class="privacy-governance">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">PRIVACY OPS</p>
                    <h3>隐私治理台</h3>
                </div>
            </div>
            <p class="panel-inline-hint">这里集中处理删除请求、查看最近隐私审计，并在正式执行前先跑一遍保留清扫 dry run。</p>
            ${errorBlock}
            ${renderPrivacyProtectionChips(status)}
            <div class="privacy-governance__grid">
                <section class="privacy-governance-card">
                    <div class="panel__header panel__header--compact"><div><p class="panel__eyebrow">STATUS</p><h4>当前保护状态</h4></div></div>
                    ${statusBlock}
                </section>
                <section class="privacy-governance-card">
                    <div class="panel__header panel__header--compact"><div><p class="panel__eyebrow">RETENTION</p><h4>保留清扫</h4></div></div>
                    <p class="panel-inline-hint">先 dry run 再执行，避免直接误删到还需要人工复核的记录。</p>
                    ${renderPrivacySweepSummary(data.sweepSummary)}
                    <div class="hero-actions">
                        <button class="button button--ghost" type="button" onclick="runPrivacyRetentionSweepAction(true)">先跑 Dry Run</button>
                        <button class="button button--danger" type="button" onclick="runPrivacyRetentionSweepAction(false)">正式执行清扫</button>
                    </div>
                </section>
            </div>
            <section class="privacy-governance-card">
                <div class="panel__header panel__header--compact"><div><p class="panel__eyebrow">DELETE REQUESTS</p><h4>删除请求队列</h4></div></div>
                ${renderAdminPrivacyDeleteRequests(deleteRequests)}
            </section>
            <section class="privacy-governance-card">
                <div class="panel__header panel__header--compact"><div><p class="panel__eyebrow">AUDIT</p><h4>最近隐私审计</h4></div></div>
                ${renderAdminPrivacyAudits(audits)}
            </section>
        </div>`;
}
async function openPrivacyGovernanceWorkbench(options = {}) {
  var _a, _b;
  if (isDemoMode()) {
    const demoData = buildDemoPrivacyGovernanceData();
    openModal(renderPrivacyGovernanceWorkbench({
      status: state.privacyStatus,
      deleteRequests: demoData.deleteRequests,
      audits: demoData.audits,
      sweepSummary: options.sweepSummary || demoData.sweepSummary
    }));
    return;
  }
  if (!ensureLoginContext()) {
    return;
  }
  if (!state.isAdmin) {
    try {
      await loadAdminPolicies({ showErrors: false });
    } catch (error) {
    }
  }
  if (!state.isAdmin) {
    showToast("当前账号没有管理员权限");
    return;
  }
  openModal('<h3>隐私治理台</h3><p class="muted-copy">正在加载删除请求与隐私审计...</p>');
  const [requestsResult, auditsResult] = await Promise.allSettled([
    api.getAdminPrivacyDeleteRequests("", 20),
    api.getAdminPrivacyAudits({ limit: 16 })
  ]);
  const errors = [];
  const deleteRequests = requestsResult.status === "fulfilled" ? Array.isArray(requestsResult.value) ? requestsResult.value : [] : (errors.push(((_a = requestsResult.reason) == null ? void 0 : _a.message) || "删除请求读取失败"), []);
  const audits = auditsResult.status === "fulfilled" ? Array.isArray(auditsResult.value) ? auditsResult.value : [] : (errors.push(((_b = auditsResult.reason) == null ? void 0 : _b.message) || "隐私审计读取失败"), []);
  openModal(renderPrivacyGovernanceWorkbench({
    status: state.privacyStatus,
    deleteRequests,
    audits,
    sweepSummary: options.sweepSummary || null,
    error: errors.filter(Boolean).join("；")
  }));
}
async function approvePrivacyDeleteRequest(requestId) {
  const note = window.prompt("可选：填写执行备注", "管理员批准后执行。");
  if (note === null) {
    return;
  }
  try {
    await api.approveAdminPrivacyDeleteRequest(requestId, note);
    showToast("删除请求已批准并执行");
    await loadProfilePage();
    await openPrivacyGovernanceWorkbench();
  } catch (error) {
    showToast(error.message || "批准删除请求失败");
  }
}
async function rejectPrivacyDeleteRequest(requestId) {
  const note = window.prompt("可选：填写驳回备注", "管理员驳回。");
  if (note === null) {
    return;
  }
  try {
    await api.rejectAdminPrivacyDeleteRequest(requestId, note);
    showToast("删除请求已驳回");
    await loadProfilePage();
    await openPrivacyGovernanceWorkbench();
  } catch (error) {
    showToast(error.message || "驳回删除请求失败");
  }
}
async function runPrivacyRetentionSweepAction(dryRun = true) {
  if (!dryRun) {
    const confirmed = window.confirm("正式执行后会清理过期隐私事件和临时转录文件。确认继续吗？");
    if (!confirmed) {
      return;
    }
  }
  try {
    const summary = await api.runAdminPrivacyRetentionSweep(dryRun);
    showToast(dryRun ? "Dry Run 已完成" : "隐私保留清扫已执行");
    await loadProfilePage();
    await openPrivacyGovernanceWorkbench({ sweepSummary: summary });
  } catch (error) {
    showToast(error.message || "执行隐私清扫失败");
  }
}
async function openUnbindPanel() {
  if (!ensurePairContext("请先选择一段关系，再处理解绑")) {
    return;
  }
  try {
    const status = await api.getUnbindStatus(state.currentPair.id);
    const html = status.has_request ? `<h3>解绑状态</h3><p>${status.requested_by_me ? `你已发起解绑，剩余 ${status.days_remaining} 天。` : "对方已经发起解绑，你可以确认解除。"}</p>
         <div class="hero-actions">
           ${status.requested_by_me && status.days_remaining > 0 ? `<button class="button button--ghost" type="button" onclick="cancelUnbind()">撤回</button>` : ""}
           <button class="button button--danger" type="button" onclick="confirmUnbind()">确认解绑</button>
         </div>` : `<h3>发起解绑</h3><p>解绑后将无法继续共享打卡和报告。</p><div class="hero-actions"><button class="button button--danger" type="button" onclick="requestUnbind()">发起解绑</button></div>`;
    openModal(html);
  } catch (error) {
    showToast(error.message || "读取解绑状态失败");
  }
}
function openPartnerNicknameEditor() {
  if (!ensurePairContext("请先选择一段关系，再修改备注")) {
    return;
  }
  const pair = state.currentPair;
  if (!pair) {
    showToast("当前没有可编辑的关系");
    return;
  }
  openModal(`
      <h3>编辑对方备注</h3>
      <p class="muted-copy">备注名会优先显示在首页、配对列表和个人中心，方便你在多段关系之间切换。</p>
      <label class="field">
        <span>备注名</span>
        <input id="partner-nickname-input" class="input" type="text" maxlength="24" placeholder="例如：宝宝 / 搭子 / 育儿搭档" value="${escapeHtml(pair.custom_partner_nickname || "")}">
      </label>
      <div class="hero-actions">
        <button class="button button--ghost" type="button" onclick="closeModal()">取消</button>
        <button class="button button--primary" type="button" onclick="savePartnerNickname()">保存备注</button>
      </div>
    `);
}
async function loadCheckinAgentState() {
  if (!api.isLoggedIn() || state.checkinMode !== "voice") {
    return;
  }
  try {
    await ensureAgentSession();
  } catch (error) {
    showToast(error.message || "无法初始化智能陪伴");
  }
}
function openProfileEditor() {
  if (!api.isLoggedIn() || !state.me) {
    showToast("请先登录");
    return;
  }
  openModal(`
      <h3>修改名称</h3>
      <p class="muted-copy">更新后，网页端、小程序和 app 会统一使用这个昵称。</p>
      <label class="field">
        <span>昵称</span>
        <input id="profile-nickname-input" class="input" type="text" maxlength="20" placeholder="输入新的昵称" value="${escapeHtml(state.me.nickname || "")}">
      </label>
      <div class="hero-actions">
        <button class="button button--ghost" type="button" onclick="closeModal()">取消</button>
        <button class="button button--primary" type="button" onclick="saveProfileChanges()">保存</button>
      </div>
    `);
}
function openPasswordEditor() {
  if (!api.isLoggedIn()) {
    showToast("请先登录");
    return;
  }
  openModal(`
      <h3>修改密码</h3>
      <p class="muted-copy">密码不会显示在界面中，修改后新的密码立即生效。</p>
      <label class="field">
        <span>当前密码</span>
        <input id="current-password-input" class="input" type="password" placeholder="请输入当前密码">
      </label>
      <label class="field">
        <span>新密码</span>
        <input id="next-password-input" class="input" type="password" minlength="8" placeholder="至少 8 位">
      </label>
      <div class="hero-actions">
        <button class="button button--ghost" type="button" onclick="closeModal()">取消</button>
        <button class="button button--primary" type="button" onclick="savePasswordChanges()">保存</button>
      </div>
    `);
}
async function saveProfileChanges() {
  var _a;
  const nickname = ((_a = $("#profile-nickname-input")) == null ? void 0 : _a.value.trim()) || "";
  if (!nickname) {
    showToast("昵称不能为空");
    return;
  }
  try {
    const me = await api.updateMe({ nickname });
    state.me = me;
    state.profileFeedback = `昵称已更新为“${nickname}”，三端会使用同一份账户名称。`;
    closeModal();
    showToast("名称已更新");
    await loadProfilePage();
    if (state.currentPage === "home") {
      await loadHomePage();
    }
  } catch (error) {
    showToast(error.message || "保存失败");
  }
}
async function savePasswordChanges() {
  var _a, _b;
  const currentPassword = ((_a = $("#current-password-input")) == null ? void 0 : _a.value) || "";
  const nextPassword = ((_b = $("#next-password-input")) == null ? void 0 : _b.value) || "";
  if (!currentPassword || !nextPassword) {
    showToast("请填写完整密码信息");
    return;
  }
  try {
    await api.changePassword(currentPassword, nextPassword);
    state.profileFeedback = "登录密码已更新，请使用新密码继续登录。";
    closeModal();
    showToast("密码已更新");
    await loadProfilePage();
  } catch (error) {
    showToast(error.message || "修改失败");
  }
}
async function savePartnerNickname() {
  if (!ensurePairContext("请先选择一段关系，再修改备注")) {
    return;
  }
  const input = $("#partner-nickname-input");
  const customNickname = (input == null ? void 0 : input.value.trim()) || "";
  try {
    const updatedPair = await api.updatePartnerNickname(state.currentPair.id, customNickname);
    upsertPair(updatedPair);
    state.profileFeedback = customNickname ? `“${customNickname}” 已同步到首页、当前关系列表和个人中心。` : "备注名已清空，页面已恢复显示默认对象名称。";
    closeModal();
    showToast(customNickname ? "备注已更新" : "备注已清空");
    if (state.currentPage === "profile") {
      await loadProfilePage();
    }
    if (state.currentPage === "home") {
      renderPairSelect();
      await loadHomePage();
    } else {
      renderPairPage();
    }
  } catch (error) {
    showToast(error.message || "保存失败");
  }
}
async function requestUnbind() {
  try {
    await api.requestUnbind(state.currentPair.id);
    closeModal();
    showToast("解绑请求已发起");
  } catch (error) {
    showToast(error.message || "操作失败");
  }
}
async function confirmUnbind() {
  try {
    await api.confirmUnbind(state.currentPair.id);
    closeModal();
    showToast("配对已解除");
    await bootstrapSession();
  } catch (error) {
    showToast(error.message || "操作失败");
  }
}
async function cancelUnbind() {
  try {
    await api.cancelUnbind(state.currentPair.id);
    closeModal();
    showToast("解绑请求已撤回");
  } catch (error) {
    showToast(error.message || "操作失败");
  }
}
function renderPolicyWorkbench(policies, errorMessage = "") {
  const source = Array.isArray(policies) ? policies : [];
  const counts = summarizePolicyCounts(source);
  const listHtml = source.length ? source.map((policy, index) => renderPolicyWorkbenchItem(policy, index, source.length)).join("") : '<div class="empty-state">还没有可管理的策略版本，先新增一条，或者确认策略库迁移已完成。</div>';
  return `
        <div class="policy-workbench">
            <div class="panel__header"><div><p class="panel__eyebrow">策略面板</p><h3>策略设置</h3></div></div>
            <p class="muted-copy">这里管理真正进入系统的干预策略版本。只有处于“生效中”的策略会参与后续选策和排期。</p>
            ${errorMessage ? `<div class="profile-banner"><strong>发布台提示</strong><div>${escapeHtml(errorMessage)}</div></div>` : ""}
            <div class="metric-strip">
                <article class="mini-stat"><span>策略总数</span><strong>${counts.total}</strong></article>
                <article class="mini-stat"><span>生效中</span><strong>${counts.active}</strong></article>
                <article class="mini-stat"><span>已停用</span><strong>${counts.inactive}</strong></article>
            </div>
            <div class="profile-banner">
                <strong>发布与回滚说明</strong>
                <div>每次创建、编辑、启停、排序和回滚都会被记成审计事件。回滚不会抹掉历史，而是追加一条新的“恢复到某版本”记录。</div>
            </div>
            <div class="hero-actions">
                <button class="button button--primary" type="button" onclick="openPolicyEditor()">新增策略</button>
                <button class="button button--ghost" type="button" onclick="refreshPolicyWorkbench()">刷新列表</button>
            </div>
            <div class="policy-workbench__list">${listHtml}</div>
        </div>`;
}
function renderPolicyWorkbenchItem(policy, index, total) {
  const chips = [
    policy.branch_label ? `<span class="pill">${escapeHtml(policy.branch_label)}</span>` : "",
    policy.intensity_label ? `<span class="pill">${escapeHtml(policy.intensity_label)}</span>` : "",
    policy.copy_mode_label ? `<span class="pill">${escapeHtml(policy.copy_mode_label)}</span>` : "",
    policy.version ? `<span class="pill">${escapeHtml(policy.version)}</span>` : "",
    `<span class="pill">${escapeHtml(policy.policy_id)}</span>`
  ].filter(Boolean).join("");
  const statusClass = policy.status === "active" ? "status-chip status-chip--success" : "status-chip";
  const toggleLabel = policy.status === "active" ? "停用" : "启用";
  const toggleVariant = policy.status === "active" ? "button--danger" : "button--secondary";
  const disableUp = index === 0 ? "disabled" : "";
  const disableDown = index === total - 1 ? "disabled" : "";
  const updatedAt = policy.updated_at ? formatDate(policy.updated_at) : "刚创建";
  return `
        <article class="policy-workbench-item">
            <div class="policy-workbench-item__header">
                <div>
                    <p class="panel__eyebrow">${escapeHtml(formatPlanTypeLabel(policy.plan_type))}</p>
                    <h4>${escapeHtml(policy.title || policy.policy_id)}</h4>
                    <div class="policy-workbench-item__meta">策略 ID：${escapeHtml(policy.policy_id)} · 最近更新：${escapeHtml(updatedAt)}</div>
                </div>
                <div class="policy-workbench-item__status">
                    <span class="${statusClass}">${escapeHtml(formatPolicyStatusLabel(policy.status))}</span>
                </div>
            </div>
            <p class="muted-copy">${escapeHtml(policy.summary || "暂无摘要")}</p>
            <div class="policy-workbench__chips">${chips}</div>
            <div class="detail-list">
                <div class="detail-list__item"><span>适用时机</span><strong>${escapeHtml(policy.when_to_use || "未填写")}</strong></div>
                <div class="detail-list__item"><span>成功信号</span><strong>${escapeHtml(policy.success_marker || "未填写")}</strong></div>
                <div class="detail-list__item"><span>护栏规则</span><strong>${escapeHtml(policy.guardrail || "未填写")}</strong></div>
                <div class="detail-list__item"><span>来源</span><strong>${escapeHtml(policy.source || "unknown")}</strong></div>
            </div>
            <div class="hero-actions">
                <button class="button button--ghost" type="button" onclick='openPolicyEditor(${JSON.stringify(policy.policy_id)})'>编辑</button>
                <button class="button button--ghost" type="button" onclick='openPolicyAudit(${JSON.stringify(policy.policy_id)})'>审计</button>
                <button class="button ${toggleVariant}" type="button" onclick='togglePolicyWorkbenchItem(${JSON.stringify(policy.policy_id)}, ${JSON.stringify(policy.status === "active" ? "inactive" : "active")})'>${toggleLabel}</button>
                <button class="button button--ghost" type="button" onclick='movePolicyWorkbenchItem(${JSON.stringify(policy.policy_id)}, -1)' ${disableUp}>上移</button>
                <button class="button button--ghost" type="button" onclick='movePolicyWorkbenchItem(${JSON.stringify(policy.policy_id)}, 1)' ${disableDown}>下移</button>
            </div>
        </article>`;
}
function summarizePolicyAuditValue(value) {
  if (value === null || value === void 0 || value === "") {
    return "空";
  }
  if (Array.isArray(value)) {
    const preview = value.map((item) => summarizePolicyAuditValue(item)).join("、");
    return preview.length > 88 ? `${preview.slice(0, 88)}…` : preview;
  }
  if (typeof value === "object") {
    const preview = JSON.stringify(value);
    return preview.length > 88 ? `${preview.slice(0, 88)}…` : preview;
  }
  return String(value);
}
function renderPolicyAuditChange(change) {
  return `
        <div class="policy-history-item__change">
            <span>${escapeHtml((change == null ? void 0 : change.label) || (change == null ? void 0 : change.field) || "字段")}</span>
            <strong>${escapeHtml(summarizePolicyAuditValue(change == null ? void 0 : change.before_value))} → ${escapeHtml(summarizePolicyAuditValue(change == null ? void 0 : change.after_value))}</strong>
        </div>`;
}
function renderPolicyAuditEntry(policyId, entry) {
  var _a;
  const actorLabel = ((_a = entry == null ? void 0 : entry.actor) == null ? void 0 : _a.email) || "管理员";
  const changedFields = Array.isArray(entry == null ? void 0 : entry.changed_fields) ? entry.changed_fields : [];
  const changeHtml = changedFields.length ? changedFields.map((change) => renderPolicyAuditChange(change)).join("") : '<p class="muted-copy">这次操作主要用于留痕，没有捕获到需要展示的字段变化。</p>';
  const noteHtml = (entry == null ? void 0 : entry.note) ? `<div class="policy-history-item__note">备注：${escapeHtml(entry.note)}</div>` : "";
  const restoreButton = (entry == null ? void 0 : entry.can_restore) ? `<button class="button button--secondary" type="button" onclick='rollbackPolicyWorkbenchItem(${JSON.stringify(policyId)}, ${JSON.stringify(entry.event_id)})'>回滚到此版本</button>` : "";
  return `
        <article class="policy-history-item">
            <div class="policy-history-item__header">
                <div>
                    <p class="panel__eyebrow">${escapeHtml((entry == null ? void 0 : entry.event_type) || "admin.policy")}</p>
                    <h4>${escapeHtml((entry == null ? void 0 : entry.event_label) || "策略事件")}</h4>
                </div>
                <span class="status-chip">${escapeHtml(formatDate(entry == null ? void 0 : entry.occurred_at))}</span>
            </div>
                <p class="muted-copy">${escapeHtml((entry == null ? void 0 : entry.summary) || "系统记录了一次策略面板操作。")}</p>
            <div class="policy-history-item__meta">操作者：${escapeHtml(actorLabel)}</div>
            <div class="policy-history-item__changes">${changeHtml}</div>
            ${noteHtml}
            <div class="hero-actions">
                ${restoreButton}
            </div>
        </article>`;
}
function renderPolicyAuditPanel(policy, entries, errorMessage = "") {
  const latestEntry = Array.isArray(entries) && entries.length ? entries[0] : null;
  const listHtml = Array.isArray(entries) && entries.length ? entries.map((entry) => renderPolicyAuditEntry(policy.policy_id, entry)).join("") : '<div class="empty-state">这条策略还没有管理员审计记录。创建、编辑、启停、排序后，这里会自动沉淀时间顺序的发布历史。</div>';
  return `
        <div class="policy-history">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">POLICY AUDIT</p>
                    <h3>${escapeHtml(policy.title || policy.policy_id)}</h3>
                </div>
            </div>
            <p class="muted-copy">这里记录的是管理员对这条策略做过的所有发布动作。你可以回看为什么改、何时改，也可以把系统恢复到某一个已验证过的版本。</p>
            ${errorMessage ? `<div class="profile-banner"><strong>审计加载提示</strong><div>${escapeHtml(errorMessage)}</div></div>` : ""}
            <div class="metric-strip">
                <article class="mini-stat"><span>当前状态</span><strong>${escapeHtml(formatPolicyStatusLabel(policy.status))}</strong></article>
                <article class="mini-stat"><span>审计条目</span><strong>${Array.isArray(entries) ? entries.length : 0}</strong></article>
                <article class="mini-stat"><span>最近动作</span><strong>${escapeHtml((latestEntry == null ? void 0 : latestEntry.event_label) || "暂无")}</strong></article>
            </div>
            <div class="hero-actions">
                <button class="button button--ghost" type="button" onclick="openPolicyWorkbench()">返回列表</button>
                <button class="button button--ghost" type="button" onclick='openPolicyEditor(${JSON.stringify(policy.policy_id)})'>编辑当前版本</button>
                <button class="button button--ghost" type="button" onclick='openPolicyAudit(${JSON.stringify(policy.policy_id)})'>刷新审计</button>
            </div>
            <div class="profile-banner">
                <strong>回滚规则</strong>
                <div>回滚会恢复这条策略当时的完整快照，并额外生成一条新的回滚事件，所以发布历史始终可追踪，不会被覆盖。</div>
            </div>
            <div class="policy-history__list">${listHtml}</div>
        </div>`;
}
function renderPolicyEditor(policy = null) {
  const isEditing = Boolean(policy);
  const metadataValue = (policy == null ? void 0 : policy.metadata_json) ? JSON.stringify(policy.metadata_json, null, 2) : "";
  return `
        <div class="policy-editor">
            <div class="panel__header"><div><p class="panel__eyebrow">POLICY EDITOR</p><h3>${isEditing ? "编辑策略" : "新增策略"}</h3></div></div>
            <p class="muted-copy">策略一旦生效，就会进入选策、排期和剧本链路。建议把标题、适用时机和护栏都写清楚。</p>
            <input id="policy-editor-existing-id" type="hidden" value="${escapeHtml((policy == null ? void 0 : policy.policy_id) || "")}">
            <label class="field">
                <span>策略 ID</span>
                <input id="policy-editor-policy-id" class="input" type="text" maxlength="80" placeholder="例如：lcr-steady-clear-v2" value="${escapeHtml((policy == null ? void 0 : policy.policy_id) || "")}" ${isEditing ? "readonly" : ""}>
            </label>
            <label class="field">
                <span>方案类型</span>
                <input id="policy-editor-plan-type" class="input" type="text" maxlength="50" placeholder="例如：low_connection_recovery" value="${escapeHtml((policy == null ? void 0 : policy.plan_type) || "")}">
            </label>
            <label class="field">
                <span>策略名称</span>
                <input id="policy-editor-title" class="input" type="text" maxlength="120" placeholder="例如：稳定重连版" value="${escapeHtml((policy == null ? void 0 : policy.title) || "")}">
            </label>
            <label class="field">
                <span>策略摘要</span>
                <textarea id="policy-editor-summary" class="input input--textarea" placeholder="这一版策略解决什么问题、适合什么状态">${escapeHtml((policy == null ? void 0 : policy.summary) || "")}</textarea>
            </label>
            <div class="policy-editor__grid">
                <label class="field">
                    <span>分支编码</span>
                    <input id="policy-editor-branch" class="input" type="text" maxlength="30" placeholder="steady" value="${escapeHtml((policy == null ? void 0 : policy.branch) || "")}">
                </label>
                <label class="field">
                    <span>分支标签</span>
                    <input id="policy-editor-branch-label" class="input" type="text" maxlength="50" placeholder="稳步推进" value="${escapeHtml((policy == null ? void 0 : policy.branch_label) || "")}">
                </label>
                <label class="field">
                    <span>强度编码</span>
                    <input id="policy-editor-intensity" class="input" type="text" maxlength="20" placeholder="steady" value="${escapeHtml((policy == null ? void 0 : policy.intensity) || "")}">
                </label>
                <label class="field">
                    <span>强度标签</span>
                    <input id="policy-editor-intensity-label" class="input" type="text" maxlength="50" placeholder="稳定版" value="${escapeHtml((policy == null ? void 0 : policy.intensity_label) || "")}">
                </label>
                <label class="field">
                    <span>文案风格编码</span>
                    <input id="policy-editor-copy-mode" class="input" type="text" maxlength="20" placeholder="clear / gentle / example" value="${escapeHtml((policy == null ? void 0 : policy.copy_mode) || "")}">
                </label>
                <label class="field">
                    <span>文案风格标签</span>
                    <input id="policy-editor-copy-mode-label" class="input" type="text" maxlength="50" placeholder="更具体 / 更温和" value="${escapeHtml((policy == null ? void 0 : policy.copy_mode_label) || "")}">
                </label>
                <label class="field">
                    <span>版本号</span>
                    <input id="policy-editor-version" class="input" type="text" maxlength="20" placeholder="v1" value="${escapeHtml((policy == null ? void 0 : policy.version) || "v1")}">
                </label>
                <label class="field">
                    <span>状态</span>
                    <select id="policy-editor-status" class="input">
                        <option value="active" ${(policy == null ? void 0 : policy.status) !== "inactive" ? "selected" : ""}>生效中</option>
                        <option value="inactive" ${(policy == null ? void 0 : policy.status) === "inactive" ? "selected" : ""}>已停用</option>
                    </select>
                </label>
            </div>
            <label class="field">
                <span>适用时机</span>
                <textarea id="policy-editor-when-to-use" class="input" placeholder="在什么风险、动量和互动状态下启用">${escapeHtml((policy == null ? void 0 : policy.when_to_use) || "")}</textarea>
            </label>
            <label class="field">
                <span>成功信号</span>
                <textarea id="policy-editor-success-marker" class="input" placeholder="怎么判断这版策略开始起效">${escapeHtml((policy == null ? void 0 : policy.success_marker) || "")}</textarea>
            </label>
            <label class="field">
                <span>护栏规则</span>
                <textarea id="policy-editor-guardrail" class="input" placeholder="什么情况下不要继续推高策略强度">${escapeHtml((policy == null ? void 0 : policy.guardrail) || "")}</textarea>
            </label>
            <label class="field">
                <span>附加元数据（可选 JSON）</span>
                <textarea id="policy-editor-metadata" class="input input--textarea" placeholder='例如：{"coach_note":"..." }'>${escapeHtml(metadataValue)}</textarea>
            </label>
            <div class="hero-actions">
                <button class="button button--ghost" type="button" onclick="openPolicyWorkbench()">返回列表</button>
                <button class="button button--primary" type="button" onclick="savePolicyWorkbenchItem()">${isEditing ? "保存修改" : "创建策略"}</button>
            </div>
        </div>`;
}
async function openPolicyWorkbench() {
  if (!ensureLoginContext()) {
    return;
  }
  openModal('<h3>策略面板</h3><p class="muted-copy">正在加载策略列表...</p>');
  try {
    await loadAdminPolicies({ showErrors: true });
    if (!state.isAdmin) {
      closeModal();
      showToast("当前账号没有管理员权限");
      return;
    }
    openModal(renderPolicyWorkbench(state.adminPolicies));
  } catch (error) {
    openModal(renderPolicyWorkbench([], error.message || "策略面板暂不可用"));
  }
}
async function refreshPolicyWorkbench() {
  await openPolicyWorkbench();
}
async function openPolicyAudit(policyId) {
  if (!state.isAdmin) {
    showToast("当前账号没有管理员权限");
    return;
  }
  openModal('<h3>策略审计</h3><p class="muted-copy">正在加载这条策略的审计历史...</p>');
  try {
    if (!Array.isArray(state.adminPolicies) || !state.adminPolicies.length) {
      await loadAdminPolicies({ showErrors: true });
    }
    const policy = state.adminPolicies.find((item) => item.policy_id === policyId);
    if (!policy) {
      throw new Error("未找到对应策略，请先刷新列表。");
    }
    const auditEntries = await api.getAdminPolicyAudit(policyId, 20);
    openModal(renderPolicyAuditPanel(policy, auditEntries));
  } catch (error) {
    const policy = state.adminPolicies.find((item) => item.policy_id === policyId) || {
      policy_id: policyId,
      title: policyId,
      status: "inactive"
    };
    openModal(renderPolicyAuditPanel(policy, [], error.message || "策略审计暂时不可用"));
  }
}
function openPolicyEditor(policyId = "") {
  if (!state.isAdmin) {
    showToast("当前账号没有管理员权限");
    return;
  }
  const policy = policyId ? state.adminPolicies.find((item) => item.policy_id === policyId) || null : null;
  openModal(renderPolicyEditor(policy));
}
function readPolicyEditorPayload() {
  var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k, _l, _m, _n, _o, _p;
  const metadataRaw = ((_a = $("#policy-editor-metadata")) == null ? void 0 : _a.value.trim()) || "";
  let metadata = null;
  if (metadataRaw) {
    try {
      metadata = JSON.parse(metadataRaw);
    } catch (error) {
      throw new Error("附加元数据需要是合法的 JSON 对象");
    }
    if (!metadata || Array.isArray(metadata) || typeof metadata !== "object") {
      throw new Error("附加元数据需要是合法的 JSON 对象");
    }
  }
  return {
    policy_id: ((_b = $("#policy-editor-policy-id")) == null ? void 0 : _b.value.trim()) || "",
    plan_type: ((_c = $("#policy-editor-plan-type")) == null ? void 0 : _c.value.trim()) || "",
    title: ((_d = $("#policy-editor-title")) == null ? void 0 : _d.value.trim()) || "",
    summary: ((_e = $("#policy-editor-summary")) == null ? void 0 : _e.value.trim()) || "",
    branch: ((_f = $("#policy-editor-branch")) == null ? void 0 : _f.value.trim()) || "",
    branch_label: ((_g = $("#policy-editor-branch-label")) == null ? void 0 : _g.value.trim()) || "",
    intensity: ((_h = $("#policy-editor-intensity")) == null ? void 0 : _h.value.trim()) || "",
    intensity_label: ((_i = $("#policy-editor-intensity-label")) == null ? void 0 : _i.value.trim()) || "",
    copy_mode: ((_j = $("#policy-editor-copy-mode")) == null ? void 0 : _j.value.trim()) || null,
    copy_mode_label: ((_k = $("#policy-editor-copy-mode-label")) == null ? void 0 : _k.value.trim()) || null,
    when_to_use: ((_l = $("#policy-editor-when-to-use")) == null ? void 0 : _l.value.trim()) || "",
    success_marker: ((_m = $("#policy-editor-success-marker")) == null ? void 0 : _m.value.trim()) || "",
    guardrail: ((_n = $("#policy-editor-guardrail")) == null ? void 0 : _n.value.trim()) || "",
    version: ((_o = $("#policy-editor-version")) == null ? void 0 : _o.value.trim()) || "v1",
    status: ((_p = $("#policy-editor-status")) == null ? void 0 : _p.value) || "active",
    metadata_json: metadata
  };
}
async function savePolicyWorkbenchItem() {
  var _a;
  try {
    const existingPolicyId = ((_a = $("#policy-editor-existing-id")) == null ? void 0 : _a.value.trim()) || "";
    const payload = readPolicyEditorPayload();
    if (!payload.policy_id || !payload.plan_type || !payload.title) {
      showToast("请至少填写策略 ID、方案类型和策略名称");
      return;
    }
    if (existingPolicyId) {
      const updatePayload = { ...payload };
      delete updatePayload.policy_id;
      await api.updateAdminPolicy(existingPolicyId, updatePayload);
      showToast("策略已更新");
    } else {
      await api.createAdminPolicy(payload);
      showToast("策略已创建");
    }
    await loadAdminPolicies({ showErrors: true });
    if (state.currentPage === "profile") {
      await loadProfilePage();
    }
    openModal(renderPolicyWorkbench(state.adminPolicies));
  } catch (error) {
    showToast(error.message || "保存策略失败");
  }
}
async function togglePolicyWorkbenchItem(policyId, nextStatus) {
  try {
    await api.toggleAdminPolicy(policyId, nextStatus);
    await loadAdminPolicies({ showErrors: true });
    if (state.currentPage === "profile") {
      await loadProfilePage();
    }
    openModal(renderPolicyWorkbench(state.adminPolicies));
    showToast(nextStatus === "active" ? "策略已启用" : "策略已停用");
  } catch (error) {
    showToast(error.message || "切换策略状态失败");
  }
}
async function movePolicyWorkbenchItem(policyId, direction) {
  const current = Array.isArray(state.adminPolicies) ? [...state.adminPolicies] : [];
  const index = current.findIndex((item) => item.policy_id === policyId);
  const nextIndex = index + Number(direction || 0);
  if (index < 0 || nextIndex < 0 || nextIndex >= current.length) {
    return;
  }
  const [moved] = current.splice(index, 1);
  current.splice(nextIndex, 0, moved);
  try {
    const reordered = await api.reorderAdminPolicies(current.map((item) => item.policy_id));
    state.adminPolicies = Array.isArray(reordered) ? reordered : current;
    if (state.currentPage === "profile") {
      await loadProfilePage();
    }
    openModal(renderPolicyWorkbench(state.adminPolicies));
    showToast("策略顺序已更新");
  } catch (error) {
    showToast(error.message || "更新策略顺序失败");
  }
}
async function rollbackPolicyWorkbenchItem(policyId, targetEventId) {
  const confirmed = window.confirm("确认把这条策略回滚到选中的历史版本吗？系统会额外记录一条新的回滚事件。");
  if (!confirmed) {
    return;
  }
  try {
    await api.rollbackAdminPolicy(policyId, targetEventId);
    await loadAdminPolicies({ showErrors: true });
    if (state.currentPage === "profile") {
      await loadProfilePage();
    }
    await openPolicyAudit(policyId);
    showToast("策略已回滚到所选版本");
  } catch (error) {
    showToast(error.message || "回滚策略失败");
  }
}
async function loadMilestonesPage() {
  if (!hasCurrentPair()) {
    renderMilestones([]);
    return;
  }
  try {
    const milestones = await api.getMilestones(state.currentPair.id);
    renderMilestones(milestones);
  } catch (error) {
    $("#milestone-summary").innerHTML = `
        <p class="eyebrow">LIVE DATA</p>
        <h3>里程碑暂时不可用</h3>
        <p>${escapeHtml(error.message || "读取失败，请稍后重试。")}</p>`;
    $("#milestone-list").innerHTML = '<div class="timeline-empty">当前无法读取里程碑，请稍后刷新。</div>';
  }
}
function renderMilestones(milestones) {
  const list = Array.isArray(milestones) ? milestones : [];
  const upcoming = list.filter((item) => typeof item.days_until === "number" && item.days_until >= 0);
  const past = list.filter((item) => typeof item.days_since === "number" && item.days_since > 0);
  const nextMilestone = upcoming[0] || list[0] || null;
  $("#milestone-summary").innerHTML = `
    <p class="eyebrow">关系时间线</p>
    <h3>${nextMilestone ? escapeHtml(nextMilestone.title) : "还没有记录关键节点"}</h3>
    <p>${nextMilestone ? `${escapeHtml(milestoneTypeLabel(nextMilestone.type))} · ${escapeHtml(milestoneTimeText(nextMilestone))}` : "从纪念日、重要承诺或育儿关键事件开始，让系统记住你们的重要时刻。"}</p>
    <div class="metric-strip">
      <article class="mini-stat"><span>总节点数</span><strong>${list.length}</strong></article>
      <article class="mini-stat"><span>待到来</span><strong>${upcoming.length}</strong></article>
      <article class="mini-stat"><span>已纪念</span><strong>${past.length}</strong></article>
    </div>`;
  $("#milestone-list").innerHTML = list.length ? list.map((item) => renderMilestoneItem(item)).join("") : '<div class="timeline-empty">还没有里程碑，先补一个对你们最重要的时间点。</div>';
}
async function handleMilestoneSubmit(event) {
  event.preventDefault();
  if (!ensurePairContext("请先创建或加入关系，再保存里程碑")) {
    return;
  }
  const type = $("#milestone-type-input").value;
  const title = $("#milestone-title-input").value.trim();
  const milestoneDate = $("#milestone-date-input").value;
  if (!title || !milestoneDate) {
    showToast("请填写标题和日期");
    return;
  }
  const button = $("#milestone-submit-btn");
  button.disabled = true;
  button.textContent = "保存中...";
  try {
    await api.createMilestone(state.currentPair.id, type, title, milestoneDate);
    $("#milestone-form").reset();
    showToast("里程碑已保存");
    await Promise.all([loadMilestonesPage(), loadHomePage()]);
  } catch (error) {
    showToast(error.message || "保存失败");
  } finally {
    button.disabled = false;
    button.textContent = "保存里程碑";
  }
}
async function openMilestoneReview(milestoneId) {
  var _a;
  if (!ensurePairContext("请先选择一段关系，再生成成长回顾")) {
    return;
  }
  openModal('<h3>生成中</h3><p class="muted-copy">正在汇总历史报告并生成这个节点的成长回顾，请稍候。</p>');
  try {
    const payload = await api.generateMilestoneReview(milestoneId);
    const review = payload.review || {};
    openModal(`
        <h3>关系成长回顾</h3>
        <p class="muted-copy">${escapeHtml(review.growth_story || review.summary || review.executive_summary || "系统已生成该里程碑对应的关系回顾。")}</p>
        ${((_a = review.highlights) == null ? void 0 : _a.length) ? `<div class="stack-list">${review.highlights.map((item) => `<div class="stack-item"><div>${svgIcon("i-check")}</div><div>${escapeHtml(item)}</div></div>`).join("")}</div>` : ""}
        ${review.blessing ? `<div class="hero-card hero-card--accent"><strong>祝福语</strong><p>${escapeHtml(review.blessing)}</p></div>` : ""}
        ${(review.suggestions || review.action_plan || []).length ? `<div class="hero-card hero-card--accent"><strong>下一步建议</strong><p>${escapeHtml((review.suggestions || review.action_plan).join("；"))}</p></div>` : ""}
        <div class="hero-actions"><button class="button button--ghost" type="button" onclick="closeModal()">关闭</button></div>`);
  } catch (error) {
    openModal(`
        <h3>生成失败</h3>
        <p class="muted-copy">${escapeHtml(error.message || "暂时无法生成回顾，请稍后重试。")}</p>
        <div class="hero-actions"><button class="button button--ghost" type="button" onclick="closeModal()">关闭</button></div>`);
  }
}
async function loadLongDistancePage() {
  if (!hasCurrentPair()) {
    renderLongDistance({ activities: [] });
    return;
  }
  const [health, activities] = await Promise.allSettled([
    api.getLongDistanceHealth(state.currentPair.id),
    api.getLongDistanceActivities(state.currentPair.id)
  ]);
  renderLongDistance({
    ...unwrapResult(health, {}),
    activities: unwrapResult(activities, [])
  });
}
function renderLongDistance(data) {
  var _a, _b, _c, _d;
  $("#longdistance-health").innerHTML = `
    <p class="eyebrow">LONG DISTANCE</p>
    <h3>异地关系健康指数 ${(_a = data.health_index) != null ? _a : "--"}</h3>
    <p>沟通及时性 ${(_b = data.communication_timeliness) != null ? _b : "--"} · 表达频率 ${(_c = data.expression_frequency) != null ? _c : "--"} · 深聊率 ${(_d = data.deep_conversation_rate) != null ? _d : "--"}</p>`;
  const list = $("#longdistance-activities");
  const activities = data.activities || [];
  if (!activities.length) {
    list.innerHTML = '<div class="empty-state">还没有创建异地互动活动。</div>';
    return;
  }
  list.innerHTML = activities.map((item) => `
    <article class="stack-item">
      <div>${svgIcon(item.status === "completed" ? "i-check" : "i-spark")}</div>
      <div>
        <strong>${escapeHtml(item.title || ACTIVITY_LABELS[item.type] || "活动")}</strong>
        <div class="stack-item__meta">${item.status === "completed" ? "已完成" : "待完成"} · ${formatDate(item.created_at)}</div>
      </div>
      ${item.status === "completed" ? "" : `<button class="text-button" type="button" onclick="completeLongDistanceActivity('${item.id}')">完成</button>`}
    </article>`).join("");
}
async function createLongDistanceActivity(type) {
  if (!ensurePairContext("请先创建或加入关系，再创建异地活动")) {
    return;
  }
  try {
    await api.createLongDistanceActivity(state.currentPair.id, type, ACTIVITY_LABELS[type]);
    showToast("活动已创建");
    await loadLongDistancePage();
  } catch (error) {
    showToast(error.message || "创建失败");
  }
}
async function completeLongDistanceActivity(activityId) {
  try {
    await api.completeLongDistanceActivity(activityId);
    showToast("活动已标记完成");
    await loadLongDistancePage();
  } catch (error) {
    showToast(error.message || "操作失败");
  }
}
async function loadAttachmentPage() {
  if (!hasCurrentPair()) {
    renderAttachment({ attachment_a: { type: "unknown", label: "未分析" }, attachment_b: { type: "unknown", label: "未分析" }, analyzed_at: null });
    return;
  }
  try {
    const data = await api.getAttachmentAnalysis(state.currentPair.id);
    renderAttachment(data);
  } catch (error) {
    renderAttachment({ attachment_a: { type: "unknown", label: "未分析" }, attachment_b: { type: "unknown", label: "未分析" }, analyzed_at: null });
  }
}
function renderAttachment(data) {
  $("#attachment-summary").innerHTML = `
    <p class="eyebrow">PAIR DATA</p>
    <h3>依恋风格不是标签，而是理解互动方式的入口</h3>
    <p>${data.analyzed_at ? `上次分析时间：${escapeHtml(data.analyzed_at)}` : "当前还没有完成真实分析，可以直接点击按钮触发。"}</p>`;
  $("#attachment-result").innerHTML = [
    renderAttachmentCard("A 方", data.attachment_a),
    renderAttachmentCard("B 方", data.attachment_b)
  ].join("");
}
function renderAttachmentCard(title, entry = {}) {
  const label = entry.label || ATTACHMENT_LABELS[entry.type] || "未分析";
  return `
    <article class="compare-card">
      <h5>${title}</h5>
      <div class="pill">${escapeHtml(label)}</div>
      <p class="muted-copy">${attachmentDescription(entry.type)}</p>
    </article>`;
}
function attachmentDescription(type) {
  return {
    secure: "倾向稳定回应和明确表达，是关系中的安全锚点。",
    anxious: "更需要确定性和及时反馈，容易放大回应延迟。",
    avoidant: "更重视独立空间，面对压力时可能选择后撤。",
    fearful: "既渴望亲近也担心受伤，需要更细腻的安全感建设。"
  }[type] || "当前还没有足够数据形成稳定画像。";
}
async function runAttachmentAnalysis() {
  if (!ensurePairContext("请先创建或加入关系，再开始依恋分析")) {
    return;
  }
  const button = $("#attachment-run-btn");
  button.disabled = true;
  button.textContent = "分析中...";
  try {
    await api.triggerAttachmentAnalysis(state.currentPair.id);
    showToast("依恋分析已触发");
    await loadAttachmentPage();
  } catch (error) {
    showToast(error.message || "分析失败");
  } finally {
    button.disabled = false;
    button.textContent = "开始分析";
  }
}
function initHealthTest() {
  healthTestState = { current: 0, answers: [] };
  $("#ht-result").classList.add("hidden");
  $("#ht-question-area").classList.remove("hidden");
  renderHealthQuestion();
}
function renderHealthQuestion() {
  const item = HEALTH_TEST_QUESTIONS[healthTestState.current];
  $("#ht-question-num").textContent = `问题 ${healthTestState.current + 1}/${HEALTH_TEST_QUESTIONS.length}`;
  $("#ht-progress-text").textContent = `${healthTestState.current}/${HEALTH_TEST_QUESTIONS.length}`;
  $("#ht-progress-bar").style.width = `${healthTestState.current / HEALTH_TEST_QUESTIONS.length * 100}%`;
  $("#ht-question-text").textContent = item.q;
  $("#ht-options").innerHTML = item.options.map((option, index) => `<button type="button" onclick="answerHealthQuestion(${index})">${escapeHtml(option)}</button>`).join("");
}
function answerHealthQuestion(optionIndex) {
  const item = HEALTH_TEST_QUESTIONS[healthTestState.current];
  const scores = [100, 75, 50, 25, 0];
  healthTestState.answers.push({ dim: item.dim, score: scores[optionIndex] });
  healthTestState.current += 1;
  if (healthTestState.current >= HEALTH_TEST_QUESTIONS.length) {
    showHealthTestResult();
    return;
  }
  renderHealthQuestion();
}
function showHealthTestResult() {
  $("#ht-question-area").classList.add("hidden");
  $("#ht-result").classList.remove("hidden");
  $("#ht-progress-bar").style.width = "100%";
  $("#ht-progress-text").textContent = `${HEALTH_TEST_QUESTIONS.length}/${HEALTH_TEST_QUESTIONS.length}`;
  const total = Math.round(healthTestState.answers.reduce((sum, item) => sum + item.score, 0) / healthTestState.answers.length);
  $("#ht-gauge").style.setProperty("--score", total);
  $("#ht-score").textContent = total;
  const level = total >= 80 ? ["关系非常健康", "你们已经具备很好的互动基础，重点是保持稳定节奏。"] : total >= 60 ? ["关系总体不错", "主要提升空间在表达细节和修复速度。"] : total >= 40 ? ["关系需要关注", "建议你们把“说清楚需求”和“及时回应”作为短期目标。"] : ["关系需要干预", "当前已经出现较多低分维度，建议尽快建立支持性对话机制。"];
  $("#ht-level").textContent = level[0];
  $("#ht-desc").textContent = level[1];
  $("#ht-dimensions").innerHTML = healthTestState.answers.map((entry) => `
    <article class="stack-item">
      <div>${svgIcon("i-chart")}</div>
      <div>
        <strong>${escapeHtml(entry.dim)}</strong>
        <div class="stack-item__meta">评分 ${entry.score}</div>
      </div>
    </article>`).join("");
  const weakPoints = healthTestState.answers.filter((entry) => entry.score < 50);
  $("#ht-suggestion-list").innerHTML = weakPoints.length ? weakPoints.map((entry) => `<div class="stack-item"><div>${svgIcon("i-spark")}</div><div><strong>${escapeHtml(entry.dim)}</strong><div class="stack-item__meta">建议围绕这个维度安排一次具体对话和一个行动。</div></div></div>`).join("") : '<div class="empty-state">当前各维度没有明显短板，可以继续保持记录与复盘。</div>';
}
function resetHealthTest() {
  initHealthTest();
}
async function loadCommunityPage() {
  if (!hasCurrentPair()) {
    renderCommunity([], []);
    return;
  }
  const [tips, notifications] = await Promise.allSettled([
    api.getCommunityTips(state.currentPair.type),
    api.getNotifications()
  ]);
  renderCommunity(unwrapResult(tips, []), unwrapResult(notifications, []));
}
function renderCommunity(tipsPayload, notificationsPayload) {
  var _a, _b;
  const tips = tipsPayload.tips || tipsPayload || [];
  const notifications = Array.isArray(notificationsPayload) ? notificationsPayload : notificationsPayload || [];
  $("#community-highlight").innerHTML = `
    <p class="eyebrow">COMMUNITY</p>
    <h3>${escapeHtml(((_a = tips[0]) == null ? void 0 : _a.title) || "社群技巧")}</h3>
    <p>${escapeHtml(((_b = tips[0]) == null ? void 0 : _b.content) || "这里会显示关系经营建议与运营型内容。")}</p>`;
  $("#community-tips-list").innerHTML = tips.length ? tips.map((tip) => `<article class="stack-item"><div>${svgIcon("i-star")}</div><div><strong>${escapeHtml(tip.title || "建议")}</strong><div class="stack-item__meta">${escapeHtml(tip.content || "")}</div></div></article>`).join("") : '<div class="empty-state">暂无技巧内容。</div>';
  $("#community-notification-list").innerHTML = notifications.length ? notifications.map((item) => `<article class="stack-item"><div>${svgIcon("i-bell")}</div><div><strong>${escapeHtml(item.content)}</strong><div class="stack-item__meta">${formatDate(item.created_at)}</div></div></article>`).join("") : '<div class="empty-state">暂无通知内容。</div>';
}
async function generateCommunityTip() {
  if (!ensurePairContext("请先创建或加入关系，再生成新的建议")) {
    return;
  }
  try {
    await api.generateTip(state.currentPair.type);
    showToast("已生成一条新建议");
    await loadCommunityPage();
  } catch (error) {
    showToast(error.message || "生成失败");
  }
}
async function loadChallengesPage() {
  if (!hasCurrentPair()) {
    renderChallenges({}, {});
    return;
  }
  const [tasks, streak] = await Promise.allSettled([
    api.getDailyTasks(state.currentPair.id),
    api.getCheckinStreak(state.currentPair.id)
  ]);
  renderChallenges(unwrapResult(tasks, {}), unwrapResult(streak, {}));
}
function renderChallenges(tasksPayload, streakPayload) {
  const tasks = tasksPayload.tasks || [];
  const completed = tasks.filter((item) => item.status === "completed").length;
  const percent = tasks.length ? Math.round(completed / tasks.length * 100) : 0;
  const strategy = tasksPayload.adaptive_strategy || {};
  const strategyNote = strategy.reason ? `<p class="panel-note">${escapeHtml(strategy.reason)}</p>` : "";
  const selectionNote = taskPolicySelectionReason(strategy) ? `<p class="panel-note task-strategy__note">${escapeHtml(taskPolicySelectionReason(strategy))}</p>` : "";
  const copyModeNote = taskCopyModeReason(strategy) ? `<p class="panel-note task-strategy__note">${escapeHtml(taskCopyModeReason(strategy))}</p>` : "";
  const categoryCopyNote = taskCategoryCopySummary(strategy) ? `<p class="panel-note task-strategy__note">${escapeHtml(taskCategoryCopySummary(strategy))}</p>` : "";
  $("#challenge-overview").innerHTML = `
    <p class="eyebrow">TASKS</p>
    <h3>今日完成率 ${percent}%</h3>
    <p>连续打卡 ${streakPayload.streak || 0} 天 · 今日已完成 ${completed}/${tasks.length} 项任务。</p>
    ${strategyNote}
    ${selectionNote}
    ${copyModeNote}
    ${categoryCopyNote}
    <div class="progress-track"><span class="progress-track__fill" style="width:${percent}%"></span></div>`;
  $("#challenge-task-list").innerHTML = tasks.length ? tasks.map((task) => renderTaskItem(task)).join("") : '<div class="empty-state">当前还没有挑战任务。</div>';
}
async function completeTask(taskId) {
  var _a, _b, _c;
  if (!ensurePairContext("请先创建或加入关系，再更新任务状态")) {
    return;
  }
  try {
    const payload = await api.completeTask(taskId);
    const shouldPromptFeedback = !String(taskId).startsWith("demo-") && ((_a = payload == null ? void 0 : payload.task) == null ? void 0 : _a.status) === "completed" && ((_b = payload == null ? void 0 : payload.task) == null ? void 0 : _b.needs_feedback) !== false;
    showToast("任务已完成");
    if (state.currentPage === "home") {
      await loadHomePage();
    } else if (state.currentPage === "report") {
      await loadReportPage();
    } else {
      await loadChallengesPage();
    }
    if (shouldPromptFeedback) {
      openTaskFeedback(taskId, ((_c = payload == null ? void 0 : payload.task) == null ? void 0 : _c.title) || "");
    }
  } catch (error) {
    showToast(error.message || "操作失败");
  }
}
async function handleWaterTree() {
  if (!ensurePairContext("请先创建或加入关系，再浇灌关系树")) {
    return;
  }
  try {
    await api.waterTree(state.currentPair.id);
    showToast("关系树已浇水");
    await loadHomePage();
  } catch (error) {
    showToast(error.message || "操作失败");
  }
}
async function openCrisisDetail() {
  var _a, _b;
  const current = ((_a = state.homeSnapshot) == null ? void 0 : _a.crisis) || { crisis_level: "none" };
  const intervention = current.intervention || {};
  openModal('<h3>加载中</h3><p class="muted-copy">正在整理当前阶段的支持建议和修复步骤，请稍候。</p>');
  const protocol = ((_b = state.currentPair) == null ? void 0 : _b.id) ? await api.getRepairProtocol(state.currentPair.id).catch(() => null) : null;
  openModal(`
    <h3>${crisisLabel(current.crisis_level || "none")}</h3>
    <p>${escapeHtml(intervention.title || intervention.description || "当前没有额外说明。")}</p>
    ${(intervention.action_items || []).length ? `<div class="stack-list">${intervention.action_items.map((item) => `<div class="stack-item"><div>${svgIcon("i-check")}</div><div>${escapeHtml(item)}</div></div>`).join("")}</div>` : ""}
    ${renderRepairProtocol(protocol)}
    <div class="hero-actions">
      <button class="button button--secondary" type="button" onclick="openCrisisResources()">查看专业资源</button>
      <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
    </div>`);
}
async function openCrisisResources() {
  const resources = await api.getCrisisResources().catch(() => ({ hotlines: [], tips: [] }));
  openModal(`
    <h3>专业帮助资源</h3>
    <div class="stack-list">
      ${(resources.hotlines || []).map((item) => `<div class="stack-item"><div>${svgIcon("i-phone")}</div><div><strong>${escapeHtml(item.name)}</strong><div class="stack-item__meta">${escapeHtml(item.number)} · ${escapeHtml(item.hours || "")}</div></div></div>`).join("")}
      ${(resources.tips || []).map((item) => `<div class="stack-item"><div>${svgIcon("i-spark")}</div><div>${escapeHtml(item)}</div></div>`).join("")}
    </div>
    <div class="hero-actions"><button class="button button--ghost" type="button" onclick="closeModal()">关闭</button></div>`);
}
function handleSwitchPair(pairId) {
  setCurrentPair(pairId);
  bootstrapSession();
}
function openRelationWorkspace(pairId) {
  const pair = state.pairs.find((item) => item.id === pairId);
  if (!pair) {
    showToast("没有找到这段关系");
    return;
  }
  setCurrentPair(pairId);
  showToast(pair.status === "active" ? "已切换当前关系" : "已打开等待加入状态");
  showPage(pair.status === "active" ? "home" : "pair-waiting");
}
function handleLogout() {
  if (isDemoMode()) {
    exitDemoMode();
    return;
  }
  api.clearToken();
  localStorage.removeItem("qj_current_pair");
  state.me = null;
  state.pairs = [];
  state.currentPair = null;
  state.profileFeedback = null;
  state.productPrefs = { ...CLIENT_AI_PREFS };
  updateLocalDraftState().catch(() => []);
  renderCheckinClientAIPanel(null);
  syncTabBar();
  showToast("已退出登录");
  showPage("auth");
}
function bindOptionEvents() {
  document.addEventListener("click", (event) => {
    const moodButton = event.target.closest("[data-mood]");
    if (moodButton) {
      const mood = moodButton.dataset.mood;
      if (state.selectedMoods.includes(mood)) {
        state.selectedMoods = state.selectedMoods.filter((item) => item !== mood);
      } else {
        state.selectedMoods.push(mood);
      }
      renderMoods();
      return;
    }
    const optionButton = event.target.closest("[data-option-name]");
    if (optionButton) {
      const { optionName, optionValue } = optionButton.dataset;
      $$(`[data-option-name="${optionName}"]`).forEach((button) => {
        button.classList.remove("select-card--active");
        delete button.dataset.selectedName;
        delete button.dataset.selectedValue;
      });
      optionButton.classList.add("select-card--active");
      optionButton.dataset.selectedName = optionName;
      optionButton.dataset.selectedValue = optionValue;
      return;
    }
    const pairTypeButton = event.target.closest("[data-pair-type]");
    if (pairTypeButton) {
      state.selectedPairType = pairTypeButton.dataset.pairType;
      $$("[data-pair-type]").forEach((button) => button.classList.remove("select-card--active"));
      pairTypeButton.classList.add("select-card--active");
      return;
    }
    const reportButton = event.target.closest("[data-report-type]");
    if (reportButton) {
      state.selectedReportType = reportButton.dataset.reportType;
      $$("[data-report-type]").forEach((button) => button.classList.remove("segmented__item--active"));
      reportButton.classList.add("segmented__item--active");
      loadReportPage();
      return;
    }
    const jumpButton = event.target.closest("[data-jump-page]");
    if (jumpButton) {
      showPage(jumpButton.dataset.jumpPage);
      return;
    }
    const reviewButton = event.target.closest("[data-milestone-review]");
    if (reviewButton) {
      openMilestoneReview(reviewButton.dataset.milestoneReview);
      return;
    }
    const activityButton = event.target.closest("[data-ld-type]");
    if (activityButton) {
      createLongDistanceActivity(activityButton.dataset.ldType);
      return;
    }
  });
}
function bindStaticEvents() {
  var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r, _s, _t, _u, _v, _w, _x, _y, _z, _A, _B, _C, _D, _E, _F, _G, _H;
  (_a = $("#auth-mode-login")) == null ? void 0 : _a.addEventListener("click", () => switchAuthMode("login"));
  (_b = $("#auth-mode-register")) == null ? void 0 : _b.addEventListener("click", () => switchAuthMode("register"));
  (_c = $("#auth-method-email")) == null ? void 0 : _c.addEventListener("click", () => switchAuthMethod("email"));
  (_d = $("#auth-method-phone")) == null ? void 0 : _d.addEventListener("click", () => switchAuthMethod("phone"));
  (_e = $("#auth-send-code")) == null ? void 0 : _e.addEventListener("click", handleSendPhoneCode);
  (_f = $("#auth-form")) == null ? void 0 : _f.addEventListener("submit", handleAuthSubmit);
  (_g = $("#pair-create-btn")) == null ? void 0 : _g.addEventListener("click", handleCreatePair);
  (_h = $("#pair-join-btn")) == null ? void 0 : _h.addEventListener("click", handleJoinPair);
  (_i = $("#waiting-copy-btn")) == null ? void 0 : _i.addEventListener("click", async () => {
    var _a2;
    const code = (_a2 = $("#waiting-invite-code")) == null ? void 0 : _a2.textContent;
    try {
      if (code) {
        await navigator.clipboard.writeText(code);
        showToast("邀请码已复制");
      }
    } catch (error) {
      showToast("复制失败，请手动复制");
    }
  });
  (_j = $("#waiting-refresh-btn")) == null ? void 0 : _j.addEventListener("click", refreshPairStatus);
  (_k = $("#pair-skip-btn")) == null ? void 0 : _k.addEventListener("click", handleSkipPairSetup);
  (_l = $("#home-pair-select")) == null ? void 0 : _l.addEventListener("change", (event) => {
    setCurrentPair(event.target.value);
    loadHomePage();
  });
  (_m = $("#checkin-form")) == null ? void 0 : _m.addEventListener("submit", handleCheckinSubmit);
  (_n = $("#image-upload-trigger")) == null ? void 0 : _n.addEventListener("click", () => {
    var _a2;
    return (_a2 = $("#image-upload-input")) == null ? void 0 : _a2.click();
  });
  (_o = $("#voice-upload-trigger")) == null ? void 0 : _o.addEventListener("click", () => {
    var _a2;
    return (_a2 = $("#voice-upload-input")) == null ? void 0 : _a2.click();
  });
  (_p = $("#checkin-mode-form")) == null ? void 0 : _p.addEventListener("click", () => {
    state.checkinMode = "form";
    syncCheckinModeUI();
  });
  (_q = $("#checkin-mode-voice")) == null ? void 0 : _q.addEventListener("click", async () => {
    state.checkinMode = "voice";
    syncCheckinModeUI();
    if (api.isLoggedIn()) {
      await ensureAgentSession().catch(() => null);
    }
  });
  (_r = $("#checkin-content")) == null ? void 0 : _r.addEventListener("input", scheduleCheckinPrecheck);
  (_s = $("#agent-send-btn")) == null ? void 0 : _s.addEventListener("click", sendAgentChat);
  (_t = $("#agent-replay-btn")) == null ? void 0 : _t.addEventListener("click", replayAgentReply);
  (_u = $("#image-upload-input")) == null ? void 0 : _u.addEventListener("change", (event) => {
    var _a2;
    const file = (_a2 = event.target.files) == null ? void 0 : _a2[0];
    if (file)
      handleUpload("image", file);
  });
  (_v = $("#voice-upload-input")) == null ? void 0 : _v.addEventListener("change", (event) => {
    var _a2;
    const file = (_a2 = event.target.files) == null ? void 0 : _a2[0];
    if (file)
      handleUpload("voice", file);
  });
  (_w = $("#report-generate-btn")) == null ? void 0 : _w.addEventListener("click", generateReport);
  (_x = $("#timeline-refresh-btn")) == null ? void 0 : _x.addEventListener("click", loadTimelinePage);
  (_y = $("#logout-btn")) == null ? void 0 : _y.addEventListener("click", handleLogout);
  (_z = $("#milestone-form")) == null ? void 0 : _z.addEventListener("submit", handleMilestoneSubmit);
  (_A = $("#attachment-run-btn")) == null ? void 0 : _A.addEventListener("click", runAttachmentAnalysis);
  (_B = $("#community-refresh-btn")) == null ? void 0 : _B.addEventListener("click", loadCommunityPage);
  (_C = $("#community-generate-btn")) == null ? void 0 : _C.addEventListener("click", generateCommunityTip);
  (_D = $("#notification-toggle")) == null ? void 0 : _D.addEventListener("click", () => {
    var _a2;
    return (_a2 = $("#notification-drawer")) == null ? void 0 : _a2.classList.toggle("hidden");
  });
  (_E = $("#notification-read-all")) == null ? void 0 : _E.addEventListener("click", async () => {
    if (!api.isLoggedIn()) {
      showToast("请先登录");
      return;
    }
    await api.markNotificationsRead();
    showToast("通知已全部标记为已读");
    await loadHomePage();
  });
  (_F = $("#modal-overlay")) == null ? void 0 : _F.addEventListener("click", (event) => {
    if (event.target.id === "modal-overlay")
      closeModal();
  });
  (_G = $("#modal-close")) == null ? void 0 : _G.addEventListener("click", closeModal);
  (_H = $("#longdistance-refresh")) == null ? void 0 : _H.addEventListener("click", loadLongDistancePage);
  window.addEventListener("online", () => {
    syncPendingLocalDrafts({ silent: true }).catch(() => 0);
  });
  $$(".tab-item").forEach((button) => {
    button.addEventListener("click", () => showPage(button.dataset.page));
  });
}
function exposeGlobals() {
  window.showPage = showPage;
  window.closeModal = closeModal;
  window.initHealthTest = initHealthTest;
  window.answerHealthQuestion = answerHealthQuestion;
  window.resetHealthTest = resetHealthTest;
  window.completeTask = completeTask;
  window.handleSwitchPair = handleSwitchPair;
  window.openRelationWorkspace = openRelationWorkspace;
  window.handleWaterTree = handleWaterTree;
  window.openCrisisDetail = openCrisisDetail;
  window.openCrisisResources = openCrisisResources;
  window.requestUnbind = requestUnbind;
  window.confirmUnbind = confirmUnbind;
  window.cancelUnbind = cancelUnbind;
  window.openMilestoneReview = openMilestoneReview;
  window.completeLongDistanceActivity = completeLongDistanceActivity;
  window.openProfileEditor = openProfileEditor;
  window.openPasswordEditor = openPasswordEditor;
  window.openMessageSimulator = openMessageSimulator;
  window.openNarrativeAlignment = openNarrativeAlignment;
  window.openRelationshipTimeline = openRelationshipTimeline;
  window.runMessageSimulation = runMessageSimulation;
  window.useSimulationRewrite = useSimulationRewrite;
  window.copySimulationRewrite = copySimulationRewrite;
  window.copyNarrativeOpening = copyNarrativeOpening;
  window.openTaskFeedback = openTaskFeedback;
  window.submitTaskFeedback = submitTaskFeedback;
  window.openCheckinMode = openCheckinMode;
  window.saveProfileChanges = saveProfileChanges;
  window.savePasswordChanges = savePasswordChanges;
  window.submitPrivacyDeleteRequest = submitPrivacyDeleteRequest;
  window.cancelPrivacyDeleteRequestAction = cancelPrivacyDeleteRequestAction;
  window.toggleClientAIAssist = toggleClientAIAssist;
  window.togglePrivacyMode = togglePrivacyMode;
  window.cyclePreferredEntry = cyclePreferredEntry;
  window.syncLocalDraftsFromProfile = syncLocalDraftsFromProfile;
  window.openPrivacyGovernanceWorkbench = openPrivacyGovernanceWorkbench;
  window.approvePrivacyDeleteRequest = approvePrivacyDeleteRequest;
  window.rejectPrivacyDeleteRequest = rejectPrivacyDeleteRequest;
  window.runPrivacyRetentionSweepAction = runPrivacyRetentionSweepAction;
  window.openPolicyWorkbench = openPolicyWorkbench;
  window.refreshPolicyWorkbench = refreshPolicyWorkbench;
  window.openPolicyEditor = openPolicyEditor;
  window.savePolicyWorkbenchItem = savePolicyWorkbenchItem;
  window.togglePolicyWorkbenchItem = togglePolicyWorkbenchItem;
  window.movePolicyWorkbenchItem = movePolicyWorkbenchItem;
}
function syncTopbar() {
  const titleMap = {
    auth: "关系支持系统",
    contest: "比赛展示驾驶舱",
    pair: "建立一段关系",
    "pair-waiting": "等待对方加入",
    home: "关系总览",
    checkin: "留下今天的关系记录",
    discover: "功能总览",
    report: "关系简报",
    profile: "我的关系空间",
    milestones: "关系时间线",
    longdistance: "异地关系模式",
    "attachment-test": "依恋分析",
    "health-test": "关系体检",
    community: "社群技巧",
    challenges: "今日挑战",
    courses: "成长内容",
    experts: "专业支持",
    membership: "会员方案"
  };
  const subtitleMap = {
    auth: "从今天开始，慢慢把关系养好。",
    contest: "把评委最该看到的主链路固定下来，同时保留完整产品能力。",
    pair: "先把彼此放进同一个空间，再开始共同记录。",
    "pair-waiting": "邀请码已经准备好，差最后一步。",
    home: "先看输入状态、当前路径和下一步动作。",
    checkin: "表单和智能陪伴，都服务于更真实的一句心里话。",
    discover: "先看主链路，再进入简报、时间轴回看和干预动作。",
    report: "把复杂情绪和互动模式，翻译成一份好读的简报。",
    profile: "把账户、关系和边界感，收进一个安静空间。",
    milestones: "重要时刻不只是纪念，也能成为成长线索。",
    longdistance: "异地不是缺席，而是需要更精心的同步。",
    "attachment-test": "看见互动背后的依恋模式，才知道怎么靠近。",
    "health-test": "先知道关系在哪里，再知道下一步去哪。",
    community: "把有用的方法，做成能马上实践的小动作。",
    challenges: "任务不该像 KPI，而该像今天的一次小靠近。",
    courses: "内容不只增长知识，也该提升相处质量。",
    experts: "当关系需要更稳的支持时，这里接住你。",
    membership: "把高频陪伴、报告和服务，放进长期关系系统。"
  };
  const captionMap = {
    auth: "亲健",
    contest: "校赛模式",
    pair: "关系设置",
    "pair-waiting": "邀请",
    home: "首页",
    checkin: "记录",
    discover: "总览",
    report: "简报",
    profile: "我的",
    milestones: "里程碑",
    longdistance: "异地关系",
    "attachment-test": "依恋",
    "health-test": "体检",
    community: "社区",
    challenges: "挑战",
    courses: "课程",
    experts: "咨询",
    membership: "会员"
  };
  safeSetText("#topbar-title", titleMap[state.currentPage] || "关系支持系统");
  safeSetText("#topbar-subtitle", subtitleMap[state.currentPage] || "把复杂关系，做成更轻一点、更近一点的日常。");
  safeSetText("#topbar-caption", captionMap[state.currentPage] || "亲健");
  syncContestModeUI();
  const ritualButton = document.querySelector('.pill-button[data-jump-page="checkin"]');
  if (ritualButton) {
    const hiddenPages = /* @__PURE__ */ new Set(["auth", "pair", "pair-waiting", "contest"]);
    ritualButton.classList.toggle("hidden", hiddenPages.has(state.currentPage));
    ritualButton.textContent = state.currentPage === "checkin" ? "回到首页" : "今日记录";
    ritualButton.dataset.jumpPage = state.currentPage === "checkin" ? "home" : "checkin";
  }
}
function demoMetric(label, value, note = "") {
  return `
    <article class="stat-card">
      <span>${label}</span>
      <strong>${value}</strong>
      ${note ? `<p>${note}</p>` : ""}
    </article>`;
}
function renderPairSelect() {
  var _a;
  const select = $("#home-pair-select");
  if (!select)
    return;
  const source = state.pairs.filter((pair) => pair.status === "active");
  select.disabled = !source.length;
  if (!source.length) {
    select.innerHTML = '<option value="">单人模式中</option>';
    select.value = "";
    return;
  }
  select.innerHTML = source.map((pair) => `
        <option value="${pair.id}">
            ${escapeHtml(TYPE_LABELS[pair.type] || pair.type)} · ${escapeHtml(getPartnerDisplayName(pair))}
        </option>`).join("");
  select.value = ((_a = getPairSnapshot()) == null ? void 0 : _a.id) || source[0].id;
}
function renderClientLayerSummaryCard({ solo = false } = {}) {
  const prefs = currentProductPrefs();
  const precheck = state.lastClientPrecheck;
  const statusLabel = prefs.aiAssistEnabled ? state.clientAIAvailable ? "本地即时判断已开启" : state.clientAIFallbackActive ? "本地层暂时降级" : "等待本地层启动" : "端侧 AI 辅助已关闭";
  const summaryText = precheck ? buildClientGuidance(precheck) : prefs.aiAssistEnabled ? "输入内容后，浏览器会先在本地做脱敏、风险预警和意图路由，再把需要的部分交给云端深分析。" : "当前只保留本地脱敏和安全预警，复杂理解与建议生成仍由云端负责。";
  const pills = [
    `隐私模式：${prefs.privacyMode === "local_first" ? "local-first" : "cloud"}`,
    `默认入口：${prefs.preferredEntry}`,
    `本地待同步：${state.localDraftCount || 0} 条`
  ];
  if ((precheck == null ? void 0 : precheck.risk_level) && precheck.risk_level !== "none") {
    pills.push(`风险：${precheck.risk_level}`);
  }
  if (precheck == null ? void 0 : precheck.upload_policy) {
    pills.push(`上传：${precheck.upload_policy}`);
  }
  if (Array.isArray(precheck == null ? void 0 : precheck.client_tags) && precheck.client_tags.length) {
    pills.push(`标签：${precheck.client_tags.slice(0, 2).join(" / ")}`);
  }
  return `
        <div class="hero-card hero-card--accent">
            <strong>${escapeHtml(solo ? "这台设备会先替你做一层本地判断" : "本地即时判断与云端深分析会分层协作")}</strong>
            <p>${escapeHtml(summaryText)}</p>
            <div class="evidence-strip">
                <span class="evidence-pill">${escapeHtml(statusLabel)}</span>
                ${pills.map((item) => `<span class="evidence-pill">${escapeHtml(item)}</span>`).join("")}
            </div>
        </div>
    `;
}
function getHomeFocusConfig(payload) {
  const today = payload.todayStatus || {};
  const hasReport = Boolean(today.has_report || today.has_solo_report);
  if (!today.my_done) {
    return {
      title: "输入层还没建立，系统暂时不会贸然判断",
      description: "先完成今天的记录，画像、简报、预演和修复建议才会建立在真实依据上。",
      primaryLabel: "开始今日记录",
      primaryAction: "openCheckinMode('form')",
      secondaryLabel: "补充语音输入",
      secondaryAction: "openCheckinMode('voice')"
    };
  }
  if (!today.partner_done) {
    return {
      title: "单侧输入已到位，等待双侧对齐",
      description: "你的记录已经进入系统，等对方补齐后，今天的关系判断会更完整、更稳。",
      primaryLabel: "继续补充记录",
      primaryAction: "openCheckinMode('voice')",
      secondaryLabel: "看看简报入口",
      secondaryAction: "showPage('report')"
    };
  }
  if (!hasReport) {
    return {
      title: "双侧输入已齐，可以生成今天的关系简报",
      description: "现在最有价值的动作不是继续堆输入，而是把今天的互动读成一张可行动的总览。",
      primaryLabel: "进入关系简报",
      primaryAction: "showPage('report')",
      secondaryLabel: "补充一句原始记录",
      secondaryAction: "openCheckinMode('form')"
    };
  }
  return {
    title: "今日关系总览已更新",
    description: "当前状态、风险提醒和下一步动作都已经整理好，可以直接进入完整主流程。",
    primaryLabel: "查看最新简报",
    primaryAction: "showPage('report')",
    secondaryLabel: "进入时间轴",
    secondaryAction: "showPage('timeline')"
  };
}
function getClientLayerStatusSummary() {
  if (currentProductPrefs().aiAssistEnabled === false) {
    return "仅保留本地脱敏与风险预警";
  }
  if (state.clientAIAvailable) {
    return "本地预检已就绪";
  }
  if (state.clientAIFallbackActive) {
    return "已切换到云端保护兜底";
  }
  return "本地预检初始化中";
}
function renderClientLayerSummaryCard({ solo = false } = {}) {
  const precheck = state.lastClientPrecheck;
  const prefs = currentProductPrefs();
  const pills = [
    `端侧状态：${getClientLayerStatusSummary()}`,
    `隐私模式：${prefs.privacyMode === "local_first" ? "local-first" : "cloud"}`,
    `默认入口：${prefs.preferredEntry}`,
    `待同步：${String(state.localDraftCount || 0)} 条`
  ];
  if (precheck == null ? void 0 : precheck.upload_policy) {
    pills.push(`上传策略：${precheck.upload_policy}`);
  }
  if (Array.isArray(precheck == null ? void 0 : precheck.client_tags) && precheck.client_tags.length) {
    pills.push(`本地标签：${precheck.client_tags.slice(0, 2).join(" / ")}`);
  }
  const summary = precheck ? buildClientGuidance(precheck) : solo ? "你开始输入后，系统会先在本地做脱敏、风险预警和上传策略判断，再决定是否送入云端深分析。" : "每次输入都会先经过端侧预检，再进入服务端深分析和时间轴写回。";
  return `
        <div class="hero-card hero-card--accent">
            <strong>本地即时判断</strong>
            <p>${escapeHtml(summary)}</p>
            <div class="evidence-strip">
                ${pills.map((item) => `<span class="evidence-pill">${escapeHtml(item)}</span>`).join("")}
            </div>
            ${Array.isArray(precheck == null ? void 0 : precheck.risk_hits) && precheck.risk_hits.length ? `<p class="panel-note">最近一次本地命中：${escapeHtml(precheck.risk_hits.join("、"))}</p>` : ""}
        </div>
    `;
}
function renderNoPairHome() {
  state.homeSnapshot = null;
  safeSetHtml("#home-overview", `
        <div class="home-hero">
          <div class="home-hero__copy">
            <p class="eyebrow">单人模式</p>
            <h3>先照顾今天的自己，也是在照顾关系的未来</h3>
            <p>没绑定关系也没关系。你可以先写个人记录、用智能陪伴整理情绪，等准备好了再把对方邀请进来。</p>
          </div>
          <div class="home-hero__badge">
            <span>当前模式</span>
            <strong>单人体验</strong>
          </div>
        </div>
        <div class="context-pills">
          <span class="context-chip">支持个人打卡</span>
          <span class="context-chip">支持智能陪伴记录</span>
          <span class="context-chip">支持个人简报</span>
        </div>
        <div class="hero-actions">
          <button class="button button--primary" type="button" onclick="showPage('pair')">现在去绑定关系</button>
          <button class="button button--ghost" type="button" onclick="openCheckinMode('voice')">先从智能陪伴开始</button>
        </div>
    `);
  safeSetHtml("#home-metrics", [
    demoMetric("今日模式", "单人记录", "先为自己留下今天，也能慢慢形成稳定节奏。"),
    demoMetric("智能陪伴", "已开启", "像聊天那样完成打卡，而不是面对冷冰冰表单。"),
    demoMetric("个人简报", "可生成", "即使还没绑定，也能形成一份属于你的日记型简报。"),
    demoMetric("下一步", "邀请对方", "准备好了再把这段关系变成共同空间。")
  ].join(""));
  safeSetHtml("#home-status-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">今日</p><h4>今天先照顾你自己</h4></div></div>
        <div class="pulse-grid">
          <article class="pulse-tile"><span>情绪</span><strong>还未记录</strong><p>先写下一句真实感受。</p></article>
          <article class="pulse-tile"><span>互动</span><strong>自由模式</strong><p>没有关系绑定，也能开始积累自己的节奏。</p></article>
        </div>
        <div class="hero-actions">
          <button class="button button--primary" type="button" onclick="openCheckinMode('form')">写一条今日记录</button>
          <button class="button button--secondary" type="button" onclick="openCheckinMode('voice')">让系统陪你聊</button>
        </div>
    `);
  safeSetHtml("#home-report-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">简报</p><h4>个人简报也值得被认真对待</h4></div></div>
        <p class="panel-note">当你完成今天的个人记录后，这里会变成一张更柔和、更像日记的情绪简报入口。</p>
        <div class="hero-actions">
          <button class="button button--ghost" type="button" onclick="showPage('report')">去看个人简报页</button>
        </div>
    `);
  safeSetHtml("#home-tree-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">TREE</p><h4>关系树会在绑定后开始生长</h4></div></div>
        <p class="panel-note">现在先把记录习惯养起来，等彼此进入同一个空间，成长值和里程碑会自然接上。</p>
    `);
  safeSetHtml("#home-crisis-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">支持</p><h4>这里不会拿风险词吓你</h4></div></div>
        <p class="panel-note">真正需要帮助时，系统会给出更温和的提醒与可执行的下一步，而不是制造焦虑。</p>
    `);
  safeSetHtml("#home-milestones-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">时间线</p><h4>重要时刻以后都能被记住</h4></div></div>
        <p class="panel-note">纪念日、重要承诺、第一次和解，这些都值得成为关系时间线的一部分。</p>
    `);
  safeSetHtml("#home-tasks-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">RITUALS</p><h4>双人任务会在绑定后出现</h4></div></div>
        <p class="panel-note">现在先把今天的心情留住，等关系建立后，系统会开始生成更贴合你们的日常小动作。</p>
    `);
  state.notifications = [];
  syncNotifications();
}
async function loadHomePage() {
  var _a, _b;
  const pair = getPairSnapshot();
  const greetingName = ((_a = state.me) == null ? void 0 : _a.nickname) || "你";
  safeSetText("#home-greeting", `${greetingName}，欢迎进入关系总览`);
  renderPairSelect();
  if (!pair) {
    renderNoPairHome();
    return;
  }
  const results = await Promise.allSettled([
    api.getTodayStatus(pair.id),
    api.getCheckinStreak(pair.id),
    api.getTreeStatus(pair.id),
    api.getCrisisStatus(pair.id),
    api.getDailyTasks(pair.id),
    api.getRelationshipPlaybook(pair.id),
    api.getNotifications(),
    api.getMilestones(pair.id),
    api.getLatestReport(pair.id, "daily")
  ]);
  const homePayload = {
    pair,
    todayStatus: unwrapResult(results[0], {}),
    streak: unwrapResult(results[1], {}),
    tree: unwrapResult(results[2], {}),
    crisis: unwrapResult(results[3], {}),
    tasks: unwrapResult(results[4], {}),
    playbook: unwrapResult(results[5], null),
    notifications: unwrapResult(results[6], []),
    milestones: unwrapResult(results[7], []),
    latestReport: unwrapResult(results[8], null)
  };
  renderHome(homePayload);
  if (homePayload.playbook && $("#home-tasks-panel")) {
    safeSetHtml(
      "#home-tasks-panel",
      `${$("#home-tasks-panel").innerHTML}${renderRelationshipPlaybook(
        homePayload.playbook,
        ((_b = homePayload.tasks) == null ? void 0 : _b.tasks) || []
      )}`
    );
  }
}
function renderHome(payload) {
  var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r, _s, _t;
  state.homeSnapshot = payload;
  const pairName = getPartnerDisplayName(payload.pair);
  const focus = getHomeFocusConfig(payload);
  const playbook = payload.playbook || null;
  const crisis = payload.crisis || { crisis_level: "none" };
  const milestones = Array.isArray(payload.milestones) ? payload.milestones : [];
  const nextMilestone = milestones[0] || null;
  const latestContent = ((_a = payload.latestReport) == null ? void 0 : _a.content) || {};
  const latestScore = latestContent.health_score || latestContent.overall_health_score || null;
  const latestInsight = latestContent.insight || latestContent.encouragement || latestContent.executive_summary || "";
  const focusText = latestContent.suggestion || (playbook == null ? void 0 : playbook.branch_reason) || focus.description;
  const myCheckin = ((_b = payload.todayStatus) == null ? void 0 : _b.my_checkin) || {};
  const moodText = myCheckin.mood_score ? `${myCheckin.mood_score}/4` : "未记录";
  const interactionText = myCheckin.interaction_freq || myCheckin.interaction_freq === 0 ? `${myCheckin.interaction_freq} 次` : "未记录";
  const deepTalkText = myCheckin.deep_conversation === true ? "有" : myCheckin.deep_conversation === false ? "没有" : "未记录";
  const myStatusText = ((_c = payload.todayStatus) == null ? void 0 : _c.my_done) ? "你已完成今日记录" : "今天还没开始";
  const partnerStatusText = ((_d = payload.todayStatus) == null ? void 0 : _d.partner_done) ? "对方也已完成" : "还在等待对方";
  const reportStatusText = ((_e = payload.todayStatus) == null ? void 0 : _e.has_report) ? "今日简报已可读" : ((_f = payload.todayStatus) == null ? void 0 : _f.both_done) ? "已满足生成简报条件" : "先完成今天的记录";
  const branchLabel = (playbook == null ? void 0 : playbook.active_branch_label) || "待识别";
  const cycleText = (playbook == null ? void 0 : playbook.current_day) && (playbook == null ? void 0 : playbook.total_days) ? `第 ${playbook.current_day}/${playbook.total_days} 天` : "待启动";
  const cycleProgress = (playbook == null ? void 0 : playbook.current_day) && (playbook == null ? void 0 : playbook.total_days) ? Math.min(100, Math.max(0, Math.round(playbook.current_day / playbook.total_days * 100))) : 0;
  const cycleNote = ((_g = playbook == null ? void 0 : playbook.today_card) == null ? void 0 : _g.title) || (nextMilestone == null ? void 0 : nextMilestone.title) || "继续积累记录后，系统会给出更稳定的当前周期。";
  const stageText = ((_h = payload.todayStatus) == null ? void 0 : _h.has_report) ? "简报已就绪" : ((_i = payload.todayStatus) == null ? void 0 : _i.both_done) ? "等待生成简报" : ((_j = payload.todayStatus) == null ? void 0 : _j.my_done) ? "等待双侧对齐" : "待开始";
  const boundaryNote = ((_k = payload.latestReport) == null ? void 0 : _k.limitation_note) || latestContent.professional_note || "系统提供的是关系支持建议，不替代专业判断或安全评估。";
  const handoffNote = ((_l = payload.latestReport) == null ? void 0 : _l.safety_handoff) || "";
  safeSetHtml("#home-overview", `
        <div class="home-hero">
          <div class="home-hero__copy">
            <p class="eyebrow">关系总览</p>
            <h3>${focus.title}</h3>
            <p>${focus.description}</p>
          </div>
          <div class="home-hero__badge">
            <span>当前关系</span>
            <strong>${escapeHtml(`${TYPE_LABELS[payload.pair.type] || payload.pair.type} · ${pairName}`)}</strong>
          </div>
        </div>
        <div class="context-pills">
          <span class="context-chip">${myStatusText}</span>
          <span class="context-chip">${partnerStatusText}</span>
          <span class="context-chip">${reportStatusText}</span>
          <span class="context-chip">当前路径：${escapeHtml(branchLabel)}</span>
        </div>
        <div class="hero-actions">
          <button class="button button--primary" type="button" onclick="${focus.primaryAction}">${focus.primaryLabel}</button>
          <button class="button button--ghost" type="button" onclick="${focus.secondaryAction}">${focus.secondaryLabel}</button>
        </div>
    `);
  safeSetHtml("#home-metrics", [
    demoMetric("连续记录", `${payload.streak.streak || 0} 天`, "稳定输入会让后续判断更可靠。"),
    demoMetric("当前路径", branchLabel, (playbook == null ? void 0 : playbook.branch_reason) || (playbook == null ? void 0 : playbook.summary) || "路径会随事件流和反馈持续更新。"),
    demoMetric("风险区间", crisisLabel(crisis.crisis_level || "none"), crisis.crisis_level === "none" ? "当前没有明显升级信号。" : "建议结合支持建议和修复协议一起看。"),
    demoMetric("当前周期", cycleText, cycleNote)
  ].join(""));
  safeSetHtml("#home-status-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">输入概况</p><h4>今天的输入状态</h4></div></div>
        <div class="pulse-grid">
          <article class="pulse-tile"><span>我的记录</span><strong>${((_m = payload.todayStatus) == null ? void 0 : _m.my_done) ? "已完成" : "待补充"}</strong><p>${moodText === "未记录" ? "先写下最真实的一句。" : `心情 ${moodText}`}</p></article>
          <article class="pulse-tile"><span>对方记录</span><strong>${((_n = payload.todayStatus) == null ? void 0 : _n.partner_done) ? "已完成" : "等待同步"}</strong><p>${partnerStatusText}</p></article>
          <article class="pulse-tile"><span>互动频率</span><strong>${interactionText}</strong><p>频率只是表象，更重要的是节奏和反馈。</p></article>
          <article class="pulse-tile"><span>当前阶段</span><strong>${stageText}</strong><p>${((_o = payload.todayStatus) == null ? void 0 : _o.has_report) ? "可以进入关系简报继续演示。" : "先补齐输入，再让系统判断。"}</p></article>
        </div>
        <div class="journal-quote">
          ${myCheckin.content ? `原始记录片段：${escapeHtml(myCheckin.content)}` : "原始记录片段还没出现。哪怕先写一句，也会让后面的简报更接近真实场景。"}
        </div>
        <div class="hero-actions">
          <button class="button button--primary" type="button" onclick="openCheckinMode('form')">填写表单记录</button>
          <button class="button button--secondary" type="button" onclick="openCheckinMode('voice')">补充语音输入</button>
        </div>
        ${renderClientLayerSummaryCard()}
    `);
  safeSetHtml("#home-report-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">最新简报</p><h4>关系简报与下一步动作</h4></div></div>
        ${latestInsight ? `
            <div class="report-preview">
              <div class="report-preview__score">${latestScore != null ? latestScore : "--"}</div>
              <div>
                <strong>${((_p = payload.todayStatus) == null ? void 0 : _p.has_report) ? "今日关系简报已更新" : "最近一次关系简报"}</strong>
                <p>${escapeHtml(latestInsight)}</p>
              </div>
            </div>
        ` : `<p class="panel-note">${((_q = payload.todayStatus) == null ? void 0 : _q.both_done) ? "双方记录已齐，现在最值得做的是生成今天的关系简报。" : "简报不该先于记录出现，所以这里会等你们先把今天说清楚。"}</p>`}
        <div class="hero-card hero-card--accent">
          <strong>当前最值得执行的一步</strong>
          <p>${escapeHtml(focusText || "先用聊天前预演看一眼这句话会被怎样接住，再决定要不要直接发出去。")}</p>
        </div>
        <div class="hero-actions">
          <button class="button button--ghost" type="button" onclick="showPage('report')">${((_r = payload.todayStatus) == null ? void 0 : _r.has_report) ? "阅读完整简报" : "进入简报页"}</button>
          <button class="button button--secondary" type="button" onclick="openMessageSimulator()">聊天前预演</button>
        </div>
    `);
  safeSetHtml("#home-tree-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">当前路径</p><h4>当前策略</h4></div></div>
        <div class="report-preview">
          <div class="report-preview__score report-preview__score--soft">${escapeHtml(cycleText)}</div>
          <div>
            <strong>${escapeHtml(branchLabel)}</strong>
            <p>${escapeHtml((playbook == null ? void 0 : playbook.branch_reason) || (playbook == null ? void 0 : playbook.summary) || "系统会根据事件流、反馈和风险信号持续调整当前路径。")}</p>
          </div>
        </div>
        <div class="progress-track"><span class="progress-track__fill" style="width:${cycleProgress}%"></span></div>
        <div class="hero-actions">
          <button class="button button--ghost" type="button" onclick="showPage('timeline')">进入时间轴</button>
        </div>
    `);
  safeSetHtml("#home-crisis-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">SAFETY BOUNDARY</p><h4>${escapeHtml(crisisLabel(crisis.crisis_level || "none"))}</h4></div></div>
        <p class="panel-note">${escapeHtml(((_s = crisis.intervention) == null ? void 0 : _s.description) || ((_t = crisis.intervention) == null ? void 0 : _t.title) || (crisis.crisis_level === "none" ? "今天没有明显升级信号，继续保持稳定记录就好。" : "系统已经捕捉到一些需要留意的互动变化。"))}</p>
        <div class="hero-card hero-card--accent">
          <strong>系统边界</strong>
          <p>${escapeHtml(boundaryNote)}</p>
          ${handoffNote ? `<p>${escapeHtml(handoffNote)}</p>` : ""}
        </div>
        <div class="hero-actions">
          <button class="button button--ghost" type="button" onclick="openCrisisDetail()">查看支持建议</button>
        </div>
    `);
  safeSetHtml("#home-milestones-panel", `
        <div class="panel panel--tint narrative-lab-card">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">DUAL VIEW</p>
                    <h4>双方叙事对齐</h4>
                </div>
                <button class="button button--secondary" type="button" onclick="openNarrativeAlignment()">看共同版本</button>
            </div>
            <p class="panel-note">${escapeHtml(latestContent.suggestion || "先把双方版本对齐，再讨论谁该怎么做，通常会比直接争论更有效。")}</p>
            ${latestInsight ? `<div class="hero-card hero-card--accent"><strong>这份简报最值得先对齐的一点</strong><p>${escapeHtml(latestInsight)}</p></div>` : ""}
            ${nextMilestone ? `
              <div class="stack-list">
                ${renderMilestoneItem(nextMilestone, { compact: true })}
              </div>
            ` : '<p class="panel-note">纪念日、重要承诺、第一次和解，都会让这段关系更有被珍惜的感觉。</p>'}
            <div class="hero-actions">
              <button class="button button--ghost" type="button" onclick="showPage('milestones')">进入关系时间线</button>
            </div>
        </div>
    `);
  const tasks = payload.tasks.tasks || [];
  const taskAdaptiveHint = renderTaskAdaptiveHint(payload.tasks);
  safeSetHtml("#home-tasks-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">RITUALS</p><h4>今天更适合做什么</h4></div></div>
        <p class="panel-note">${escapeHtml(payload.tasks.combination_insight || "系统会根据你们的关系节奏，慢慢给出更贴合的互动建议。")}</p>
        ${taskAdaptiveHint}
        <div class="stack-list">
          ${tasks.length ? tasks.slice(0, 3).map((task) => renderTaskItem(task)).join("") : '<div class="empty-state">今天还没有生成任务，先去完成记录吧。</div>'}
        </div>
    `);
  state.notifications = Array.isArray(payload.notifications) ? payload.notifications : payload.notifications || [];
  syncNotifications();
}
function renderContestMetric(label, value, note = "") {
  return `
        <article class="contest-metric">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(value || "待确认")}</strong>
            <p>${escapeHtml(note || "等待更多线索")}</p>
        </article>
    `;
}
function renderContestCard(step) {
  return `
        <article class="panel contest-stage-card contest-stage-card--${escapeHtml(step.tone || "neutral")}">
            <div class="contest-stage-card__top">
                <div>
                    <p class="panel__eyebrow">${escapeHtml(step.eyebrow || "主链路")}</p>
                    <h4>${escapeHtml(step.title || "未命名步骤")}</h4>
                </div>
                <span class="pill">${escapeHtml(step.step || "--")}</span>
            </div>
            <p class="contest-stage-card__status">${escapeHtml(step.status || "观察中")}</p>
            <p class="panel-note">${escapeHtml(step.summary || "继续推进这一段演示链路。")}</p>
            ${step.meta ? `<div class="stack-item__meta">${escapeHtml(step.meta)}</div>` : ""}
            <div class="hero-actions">
                <button class="button button--primary" type="button" onclick="${step.primaryAction}">${escapeHtml(step.primaryLabel || "进入")}</button>
                ${step.secondaryAction ? `<button class="button button--ghost" type="button" onclick="${step.secondaryAction}">${escapeHtml(step.secondaryLabel || "查看")}</button>` : ""}
            </div>
        </article>
    `;
}
function renderContestProofCard(item) {
  return `
        <article class="panel contest-proof-card">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">${escapeHtml(item.eyebrow || "说明")}</p>
                    <h4>${escapeHtml(item.title || "作品亮点")}</h4>
                </div>
            </div>
            <p class="panel-note">${escapeHtml(item.body || "")}</p>
            ${item.meta ? `<div class="stack-item__meta">${escapeHtml(item.meta)}</div>` : ""}
        </article>
    `;
}
function renderContestBanner(config = {}) {
  return `
        <section class="panel panel--tint contest-inline-banner">
            <div class="contest-inline-banner__copy">
                <div>
                    <p class="panel__eyebrow">${escapeHtml(config.eyebrow || "比赛模式")}</p>
                    <h4>${escapeHtml(config.title || "返回比赛主线")}</h4>
                </div>
                <p>${escapeHtml(config.body || "回到比赛驾驶舱继续按照固定主链路演示。")}</p>
            </div>
            <div class="hero-actions">
                <button class="button button--secondary" type="button" onclick="showPage('contest')">${escapeHtml(config.primaryLabel || "返回比赛主线")}</button>
                ${config.secondaryAction ? `<button class="button button--ghost" type="button" onclick="${config.secondaryAction}">${escapeHtml(config.secondaryLabel || "继续")}</button>` : ""}
            </div>
        </section>
    `;
}
function renderContestModalReturn(nextAction = "", nextLabel = "") {
  return "";
}
function syncContestPageBanners() {
  document.body.dataset.contestMode = "false";
}
function syncContestModeUI() {
  document.body.dataset.contestMode = "false";
}
function buildContestJourneySteps(snapshot = {}) {
  var _a, _b, _c, _d, _e;
  const todayStatus = snapshot.todayStatus || {};
  const latestReport = snapshot.latestReport || null;
  const reportContent = (latestReport == null ? void 0 : latestReport.content) || {};
  const playbook = snapshot.playbook || null;
  const safetyStatus = snapshot.safetyStatus || null;
  const timeline = snapshot.timeline || { events: [] };
  const assessmentTrend = snapshot.assessmentTrend || null;
  const latestScore = reportContent.health_score || reportContent.overall_health_score || ((_a = snapshot.scorecard) == null ? void 0 : _a.health_now) || "--";
  const riskText = crisisLabel((safetyStatus == null ? void 0 : safetyStatus.risk_level) || ((_b = snapshot.crisis) == null ? void 0 : _b.crisis_level) || (playbook == null ? void 0 : playbook.risk_level) || "none");
  const timelineEvents = Array.isArray(timeline.events) ? timeline.events : [];
  const trendSummary = (assessmentTrend == null ? void 0 : assessmentTrend.change_summary) || "用时间轴和正式评估说明系统如何持续跟踪这段关系。";
  const narrativePreview = isDemoMode() ? getDemoFixture("narrativeAlignment.shared_story") || "" : reportContent.insight || reportContent.suggestion || "";
  const repairPreview = isDemoMode() ? getDemoFixture("repairProtocol.summary") || "" : (safetyStatus == null ? void 0 : safetyStatus.recommended_action) || (playbook == null ? void 0 : playbook.branch_reason) || "";
  return [
    {
      step: "01",
      eyebrow: "输入",
      title: "今日记录",
      status: todayStatus.my_done ? "已完成输入" : "待填写输入",
      summary: ((_c = todayStatus.my_checkin) == null ? void 0 : _c.content) || "先留下一句真实记录，让后面的判断和修复不再悬空。",
      meta: todayStatus.my_done ? "这一步负责给简报、预演和时间轴提供真实起点。" : "比赛演示建议先从一次准备好的记录开始。",
      tone: todayStatus.my_done ? "progress" : "neutral",
      primaryAction: "showPage('checkin')",
      primaryLabel: "进入记录页",
      secondaryAction: "showPage('contest')",
      secondaryLabel: "回到驾驶舱"
    },
    {
      step: "02",
      eyebrow: "判断",
      title: "当前判断",
      status: (latestReport == null ? void 0 : latestReport.status) === "completed" ? `已生成简报 · ${latestScore}` : "等待生成简报",
      summary: reportContent.insight || reportContent.executive_summary || "把当前阶段、风险和下一步动作读成一张真正可行动的总览。",
      meta: `当前风险 ${riskText}，这是答辩里最适合先讲清楚的一页。`,
      tone: (latestReport == null ? void 0 : latestReport.status) === "completed" ? "insight" : "neutral",
      primaryAction: "showPage('report')",
      primaryLabel: "打开简报",
      secondaryAction: "openMessageSimulator()",
      secondaryLabel: "继续消息预演"
    },
    {
      step: "03",
      eyebrow: "行动",
      title: "消息预演",
      status: "开口前预演",
      summary: isDemoMode() ? getDemoFixture("messageSimulation.risk_reason") || "先看这句话会不会被对方接成压力。" : reportContent.suggestion || "先让评委看到系统如何把建议落到下一句话。",
      meta: "这一页最容易让评委感知“系统在事前降低冲突风险”。",
      tone: "support",
      primaryAction: "openMessageSimulator()",
      primaryLabel: "打开预演",
      secondaryAction: "openNarrativeAlignment()",
      secondaryLabel: "继续双视角对齐"
    },
    {
      step: "04",
      eyebrow: "对齐",
      title: "双视角叙事对齐",
      status: "把错位翻译成共同版本",
      summary: narrativePreview || "对齐双方版本，避免在“谁更委屈”上继续打转。",
      meta: "这一页适合讲“AI补位而不是替代”，它帮助双方更容易进入现实沟通。",
      tone: "insight",
      primaryAction: "openNarrativeAlignment()",
      primaryLabel: "打开对齐结果",
      secondaryAction: "openCrisisDetail()",
      secondaryLabel: "继续修复协议"
    },
    {
      step: "05",
      eyebrow: "修复",
      title: "修复协议",
      status: riskText,
      summary: repairPreview || "系统会根据当前风险和路径，给出结构化的修复步骤。",
      meta: ((_d = playbook == null ? void 0 : playbook.today_card) == null ? void 0 : _d.action) || "这里要让评委看到“从判断走向行动”的连续干预。",
      tone: "warning",
      primaryAction: "openCrisisDetail()",
      primaryLabel: "查看修复协议",
      secondaryAction: "showPage('timeline')",
      secondaryLabel: "最后看证据复盘"
    },
    {
      step: "06",
      eyebrow: "证据",
      title: "证据复盘",
      status: `${timeline.event_count || timelineEvents.length || 0} 个节点`,
      summary: ((_e = timelineEvents[0]) == null ? void 0 : _e.summary) || trendSummary,
      meta: "这一页负责证明系统不是一次性生成，而是有事件流、趋势和可追踪证据。",
      tone: "movement",
      primaryAction: "showPage('timeline')",
      primaryLabel: "打开时间轴",
      secondaryAction: "showPage('contest')",
      secondaryLabel: "回到驾驶舱"
    }
  ];
}
function renderContestPage(snapshot = {}) {
  var _a, _b, _c, _d;
  state.contestSnapshot = snapshot;
  const pair = snapshot.pair || state.currentPair || null;
  const todayStatus = snapshot.todayStatus || {};
  const latestReport = snapshot.latestReport || null;
  const playbook = snapshot.playbook || null;
  const safetyStatus = snapshot.safetyStatus || null;
  const assessmentTrend = snapshot.assessmentTrend || null;
  const scorecard = snapshot.scorecard || null;
  const timeline = snapshot.timeline || { event_count: 0, latest_event_at: null, events: [], highlights: [] };
  const partnerName = pair ? getPartnerDisplayName(pair) : "当前关系";
  const reportContent = (latestReport == null ? void 0 : latestReport.content) || {};
  const latestInsight = reportContent.insight || reportContent.executive_summary || reportContent.suggestion || "先看清当前阶段，再决定怎么推进这段关系。";
  const nextAction = ((_a = playbook == null ? void 0 : playbook.today_card) == null ? void 0 : _a.action) || (safetyStatus == null ? void 0 : safetyStatus.recommended_action) || reportContent.suggestion || "先做一个低刺激修复动作，再决定是否继续深入。";
  const riskText = crisisLabel((safetyStatus == null ? void 0 : safetyStatus.risk_level) || (playbook == null ? void 0 : playbook.risk_level) || ((_b = snapshot.crisis) == null ? void 0 : _b.crisis_level) || "none");
  const latestScore = reportContent.health_score || reportContent.overall_health_score || (scorecard == null ? void 0 : scorecard.health_now) || "--";
  const steps = buildContestJourneySteps(snapshot);
  const proofCards = [
    {
      eyebrow: "系统定位",
      title: "完整软件系统，不是聊天拼盘",
      body: "前端、后端、数据层、关系画像、时间轴和修复协议都在同一套系统里协同工作，比赛模式只是把最强主链路提到最前面。",
      meta: pair ? `当前样例关系：${partnerName}` : "比赛模式保留全部功能，只改变展示顺序。"
    },
    {
      eyebrow: "设计原则",
      title: "AI 补位，而不是替代现实关系",
      body: "参考文献综述里的共识，这套系统强调人机协同、现实沟通补位、依赖边界和可解释提醒，而不是把 AI 包装成关系替身。",
      meta: (safetyStatus == null ? void 0 : safetyStatus.limitation_note) || "所有建议都带边界说明，必要时转向现实支持。"
    },
    {
      eyebrow: "长期追踪",
      title: "从一次判断延伸到持续复盘",
      body: "文献建议重视长期轨迹、异质性和伦理嵌入。我们用时间轴、正式周评估和路径迁移，让系统不只会生成一句话。",
      meta: (assessmentTrend == null ? void 0 : assessmentTrend.change_summary) || `${timeline.event_count || 0} 个事件节点已进入可回看证据链。`
    }
  ];
  safeSetHtml("#contest-overview", `
        <div class="contest-hero">
            <div class="contest-hero__copy">
                <p class="eyebrow">答辩入口</p>
                <h3>亲健：完整关系支持系统的比赛展示模式</h3>
                <p>这不是临时拼页面，而是把原有完整系统压缩成评委最容易理解的一条主链路：记录 -> 判断 -> 预演 -> 对齐 -> 修复 -> 证据复盘。</p>
                <div class="context-pills">
                    <span class="context-chip">${escapeHtml(pair ? `${TYPE_LABELS[pair.type] || pair.type} · ${partnerName}` : "等待选择关系")}</span>
                    <span class="context-chip">当前风险：${escapeHtml(riskText)}</span>
                    <span class="context-chip">当前简报：${escapeHtml(String(latestScore))}</span>
                    <span class="context-chip">${(playbook == null ? void 0 : playbook.active_branch_label) ? `当前路径：${escapeHtml(playbook.active_branch_label)}` : "当前路径待识别"}</span>
                </div>
            </div>
            <div class="contest-hero__aside">
                <div class="hero-card hero-card--accent">
                    <strong>评委先看什么</strong>
                    <p>${escapeHtml(latestInsight)}</p>
                </div>
                <div class="hero-card">
                    <strong>下一步就讲什么</strong>
                    <p>${escapeHtml(nextAction)}</p>
                </div>
                <div class="hero-actions">
                    <button class="button button--primary" type="button" onclick="showPage('checkin')">开始答辩链路</button>
                    <button class="button button--ghost" type="button" onclick="showPage('home')">查看完整首页</button>
                </div>
            </div>
        </div>
    `);
  safeSetHtml("#contest-stage-nav", [
    renderContestMetric("当前阶段", (playbook == null ? void 0 : playbook.active_branch_label) || "待识别", (playbook == null ? void 0 : playbook.branch_reason) || "系统会根据最近事件和反馈更新当前路径。"),
    renderContestMetric("今日动作", ((_c = playbook == null ? void 0 : playbook.today_card) == null ? void 0 : _c.title) || "先完成记录", ((_d = playbook == null ? void 0 : playbook.today_card) == null ? void 0 : _d.action) || nextAction),
    renderContestMetric("证据节点", `${timeline.event_count || 0} 个`, timeline.latest_event_at ? `最近更新 ${formatDate(timeline.latest_event_at)}` : "等待更多事件写回"),
    renderContestMetric("正式周评估", (assessmentTrend == null ? void 0 : assessmentTrend.latest_score) ? `${assessmentTrend.latest_score} 分` : "待补充", (assessmentTrend == null ? void 0 : assessmentTrend.change_summary) || "趋势会在正式评估后更清楚")
  ].join(""));
  safeSetHtml("#contest-journey-grid", steps.map((step) => renderContestCard(step)).join(""));
  safeSetHtml("#contest-proof-grid", proofCards.map((item) => renderContestProofCard(item)).join(""));
}
async function loadContestPage() {
  if (!api.isLoggedIn() && !isDemoMode()) {
    safeSetHtml("#contest-overview", `
            <div class="empty-state">请先登录或进入样例模式，再开启比赛展示模式。</div>
        `);
    safeSetHtml("#contest-stage-nav", "");
    safeSetHtml("#contest-journey-grid", "");
    safeSetHtml("#contest-proof-grid", "");
    return;
  }
  if (isDemoMode()) {
    renderContestPage({
      pair: deepClone((getDemoFixture("pairs") || [])[0] || null),
      todayStatus: deepClone(getDemoFixture("todayStatus") || {}),
      latestReport: deepClone(getDemoFixture("latestReport") || null),
      playbook: deepClone(getDemoFixture("playbook") || null),
      safetyStatus: deepClone(getDemoFixture("safetyStatus") || null),
      timeline: deepClone(getDemoFixture("timeline") || null),
      assessmentTrend: deepClone(getDemoFixture("assessmentTrend") || null),
      scorecard: deepClone(getDemoFixture("scorecard") || null),
      crisis: deepClone(getDemoFixture("crisis") || null)
    });
    return;
  }
  const pair = getPairSnapshot();
  if (!pair) {
    safeSetHtml("#contest-overview", `
            <div class="hero-card hero-card--summary">
                <strong>比赛模式已经开启</strong>
                <p>当前账号还没有激活中的关系样例。你可以先进入完整功能创建关系，或直接查看完整产品结构。</p>
                <div class="hero-actions">
                    <button class="button button--primary" type="button" onclick="showPage('pair')">先去建立关系</button>
                    <button class="button button--ghost" type="button" onclick="showPage('home')">查看完整首页</button>
                </div>
            </div>
        `);
    safeSetHtml("#contest-stage-nav", "");
    safeSetHtml("#contest-journey-grid", "");
    safeSetHtml("#contest-proof-grid", "");
    return;
  }
  safeSetHtml("#contest-overview", '<div class="empty-state">正在整理比赛主链路、当前判断和证据摘要，请稍候。</div>');
  safeSetHtml("#contest-stage-nav", "");
  safeSetHtml("#contest-journey-grid", "");
  safeSetHtml("#contest-proof-grid", "");
  const [todayResult, reportResult, playbookResult, safetyResult, timelineResult, assessmentResult, scorecardResult, crisisResult] = await Promise.allSettled([
    api.getTodayStatus(pair.id),
    api.getLatestReport(pair.id, "daily"),
    api.getRelationshipPlaybook(pair.id),
    api.getSafetyStatus(pair.id),
    api.getRelationshipTimeline(pair.id, 12),
    api.getWeeklyAssessmentTrend(pair.id),
    api.getInterventionScorecard(pair.id),
    api.getCrisisStatus(pair.id)
  ]);
  renderContestPage({
    pair,
    todayStatus: unwrapResult(todayResult, {}),
    latestReport: unwrapResult(reportResult, null),
    playbook: unwrapResult(playbookResult, null),
    safetyStatus: unwrapResult(safetyResult, null),
    timeline: unwrapResult(timelineResult, { event_count: 0, latest_event_at: null, events: [], highlights: [] }),
    assessmentTrend: unwrapResult(assessmentResult, null),
    scorecard: unwrapResult(scorecardResult, null),
    crisis: unwrapResult(crisisResult, null)
  });
}
function renderTaskItem(task) {
  const done = task.status === "completed";
  const feedback = task.feedback || null;
  const copyModeText = task.copy_mode ? task.copy_mode_source === "category" ? `${taskCategoryLabel(task.category)}任务已调成${taskCopyModeLabel(task.copy_mode)}表达` : `任务说明已调成${taskCopyModeLabel(task.copy_mode)}表达` : "";
  const feedbackText = (feedback == null ? void 0 : feedback.usefulness_score) ? `已反馈 · ${taskFeedbackLabel(feedback.usefulness_score)}` : "已完成";
  return `
    <div class="challenge-item challenge-item--task">
      <div>${done ? svgIcon("i-check") : svgIcon("i-spark")}</div>
      <div class="stack-item__content">
        <strong>${escapeHtml(task.title)}</strong>
        <div class="stack-item__meta">${escapeHtml(task.description || "")}</div>
        ${copyModeText ? `<div class="stack-item__meta task-copy-mode">${escapeHtml(copyModeText)}</div>` : ""}
        ${(feedback == null ? void 0 : feedback.note) ? `<div class="stack-item__meta stack-item__meta--accent">${escapeHtml(feedback.note)}</div>` : ""}
      </div>
      ${done ? task.needs_feedback ? `<button class="text-button" type="button" onclick="openTaskFeedback('${task.id}', ${JSON.stringify(task.title || "")})">补反馈</button>` : `<span class="pill">${escapeHtml(feedbackText)}</span>` : `<button class="text-button" type="button" onclick="completeTask('${task.id}')">去完成</button>`}
    </div>`;
}
function crisisLabel(level) {
  return {
    none: "平稳进行中",
    mild: "有一点需要留意",
    moderate: "建议认真介入",
    severe: "需要立刻支持"
  }[level] || "平稳进行中";
}
function syncReportTypeAvailability(isSolo) {
  $$("[data-report-type]").forEach((button) => {
    const blocked = isSolo && button.dataset.reportType !== "daily";
    button.disabled = blocked;
    button.classList.toggle("segmented__item--disabled", blocked);
    button.classList.toggle("segmented__item--active", button.dataset.reportType === state.selectedReportType);
  });
}
async function loadReportPage() {
  var _a;
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const isSolo = !pairId;
  if (isSolo && state.selectedReportType !== "daily") {
    state.selectedReportType = "daily";
  }
  syncReportTypeAvailability(isSolo);
  safeSetText("#report-generate-btn", isSolo ? "生成个人简报" : "生成当前简报");
  const reportType = isSolo ? "daily" : state.selectedReportType;
  const [latest, history, trend] = await Promise.allSettled([
    api.getLatestReport(pairId, reportType),
    api.getReportHistory(pairId, reportType, 6),
    api.getHealthTrend(pairId, 14)
  ]);
  renderReport(
    unwrapResult(latest, null),
    unwrapResult(history, []),
    unwrapResult(trend, { trend: [] }),
    { solo: isSolo, reportType }
  );
}
function buildReportCockpitModules(options = {}, isSolo = false) {
  const scorecard = options.planScorecard || {};
  const evaluation = options.planEvaluation || {};
  const experiment = options.planExperiment || {};
  const registry = options.planPolicyRegistry || {};
  const schedule = options.planPolicySchedule || {};
  const currentPolicy = registry.current_policy || experiment.current_policy || null;
  const recommendedPolicy = registry.recommended_policy || null;
  const currentStage = schedule.current_stage || null;
  return [
    {
      eyebrow: isSolo ? "个人闭环" : "系统脉冲",
      title: isSolo ? "调节动量" : "关系动量",
      value: planMomentumLabel(scorecard.momentum),
      note: scorecard.primary_goal || (scorecard.risk_now ? `当前风险：${crisisLabel(scorecard.risk_now)}` : "系统还在观察这一轮最真实的变化。"),
      tone: "brief-cockpit-card--accent"
    },
    {
      eyebrow: "依据",
      title: "这轮判定",
      value: evaluation.verdict_label || "等待证据",
      note: evaluation.summary || [evaluation.confidence_label, evaluation.data_quality_label].filter(Boolean).join(" · ") || "证据正在累积，先不要急着下结论。",
      tone: ""
    },
    {
      eyebrow: "策略",
      title: "当前策略",
      value: (currentPolicy == null ? void 0 : currentPolicy.title) || "待确定版本",
      note: recommendedPolicy ? `建议下一版：${recommendedPolicy.title || recommendedPolicy.policy_id || "更稳的策略版本"}` : [currentPolicy == null ? void 0 : currentPolicy.branch_label, currentPolicy == null ? void 0 : currentPolicy.intensity_label, currentPolicy == null ? void 0 : currentPolicy.copy_mode_label].filter(Boolean).join(" · ") || "系统会根据更多反馈确定更合适的策略。",
      tone: ""
    },
    {
      eyebrow: "排期",
      title: "排期阶段",
      value: (currentStage == null ? void 0 : currentStage.title) || schedule.schedule_label || "观察中",
      note: (currentStage == null ? void 0 : currentStage.checkpoint_date) ? `检查点：${formatDateOnly(currentStage.checkpoint_date)}` : schedule.selection_reason || "先把这一轮证据收集完整，再决定是否推进。",
      tone: ""
    }
  ];
}
function renderReportCockpit(report, options = {}) {
  const isSolo = Boolean(options.solo);
  const reportType = options.reportType || state.selectedReportType;
  const reportLabel = formatReportType(reportType, { solo: isSolo });
  const content = (report == null ? void 0 : report.content) || {};
  const score2 = Math.max(1, Math.min(100, content.health_score || content.overall_health_score || 72));
  const primaryInsight = content.insight || content.self_insight || content.executive_summary || "系统已经整理好这一阶段最值得先读的一句判断。";
  const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || "";
  const encouragement = content.encouragement || content.relationship_note || "";
  const focusText = suggestion || "先把最真实的感受说清楚，再决定要不要继续推进。";
  const modules = buildReportCockpitModules(options, isSolo);
  const actionButtons = isSolo ? `
            <button class="button button--secondary" type="button" onclick="showPage('checkin')">回到今日记录</button>
            <button class="button button--ghost" type="button" onclick="openMethodologyExplainer()">判断说明</button>
        ` : `
            <button class="button button--secondary" type="button" onclick="openMessageSimulator()">聊天前预演</button>
            <button class="button button--ghost" type="button" onclick="openNarrativeAlignment()">双视角对齐</button>
            <button class="button button--ghost" type="button" onclick="openMethodologyExplainer()">判断说明</button>
        `;
  return `
        <section class="brief-cockpit" style="--score:${score2}">
            <div class="brief-cockpit__hero">
                <div class="brief-cockpit__score-panel">
                    <div class="brief-cockpit__score-ring">
                        <strong>${score2}</strong>
                        <span>${escapeHtml(reportLabel)}</span>
                    </div>
                    <p>${escapeHtml(formatDateOnly((report == null ? void 0 : report.report_date) || new Date().toISOString()))}</p>
                </div>
                <div class="brief-cockpit__copy">
    <p class="eyebrow">${isSolo ? "个人总览" : "关系总览"}</p>
                    <h4>${escapeHtml(reportLabel)}</h4>
                    <p class="brief-cockpit__lede">${escapeHtml(primaryInsight)}</p>
                    <div class="brief-cockpit__story">
                        <article class="brief-cockpit__story-card">
                            <span>当前读法</span>
                            <strong>${escapeHtml(focusText)}</strong>
                        </article>
                        <article class="brief-cockpit__story-card">
                            <span>${encouragement ? "给此刻的一句提醒" : "系统姿态"}</span>
                            <strong>${escapeHtml(encouragement || "它不是在给结论，而是在帮你把复杂关系拆成可行动的下一步。")}</strong>
                        </article>
                    </div>
                </div>
                <div class="brief-cockpit__actions">
                    ${actionButtons}
                </div>
            </div>
            <div class="brief-cockpit__grid">
                ${modules.map((item) => `
                    <article class="brief-cockpit-card ${item.tone || ""}">
                        <p class="panel__eyebrow">${escapeHtml(item.eyebrow || "MODULE")}</p>
                        <span>${escapeHtml(item.title || "模块")}</span>
                        <strong>${escapeHtml(item.value || "观察中")}</strong>
                        <p>${escapeHtml(item.note || "等待更多数据")}</p>
                    </article>
                `).join("")}
            </div>
        </section>
    `;
}
function renderReport(report, history, trendData, options = {}) {
  var _a, _b;
  const isSolo = Boolean(options.solo);
  const reportType = options.reportType || state.selectedReportType;
  const reportLabel = formatReportType(reportType, { solo: isSolo });
  const scorecardPanel = renderInterventionScorecard(options.planScorecard, { solo: isSolo });
  const evaluationPanel = renderInterventionEvaluation(options.planEvaluation, { solo: isSolo });
  const experimentPanel = renderInterventionExperiment(options.planExperiment, { solo: isSolo });
  const policyRegistryPanel = renderPolicyRegistry(options.planPolicyRegistry, { solo: isSolo });
  const policySchedulePanel = renderPolicySchedule(options.planPolicySchedule, { solo: isSolo });
  const narrativePromo = renderNarrativeAlignmentPromo(
    isSolo,
    "系统会把双方最近同一阶段的记录整理成共同版本和错位点，适合在真正开口前先对齐一下理解。"
  );
  const simulatorPromo = renderMessageSimulatorPromo(
    isSolo,
    ((_a = report == null ? void 0 : report.content) == null ? void 0 : _a.suggestion) || ((_b = report == null ? void 0 : report.content) == null ? void 0 : _b.trend_description) || ""
  );
  if (report && report.status === "pending") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                ${reportLabel} 正在后台生成。稍等片刻再回来，它会比即时结果更像一份真正可读的简报。
            </div>
            ${scorecardPanel}
            ${narrativePromo}
            ${simulatorPromo}`);
  } else if (report && report.status === "failed") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                ${reportLabel} 生成失败了。别担心，重新触发一次通常就能恢复。
            </div>
            ${scorecardPanel}
            ${narrativePromo}
            ${simulatorPromo}`);
  } else if (!report || report.status !== "completed") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                这里还没有可展示的${reportLabel}。先完成今天的记录，再回来读一份更像“关系编辑稿”的简报。
            </div>
            ${scorecardPanel}
            ${narrativePromo}
            ${simulatorPromo}`);
  } else {
    const content = report.content || {};
    const primaryInsight = content.insight || content.self_insight || content.executive_summary || "系统已经整理好这一阶段的关系洞察。";
    const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || "";
    const encouragement = content.encouragement || content.relationship_note || "";
    const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
    const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);
    const focusText = suggestion || (concerns[0] || "继续把真实感受说清楚，比急着解决更重要。");
    safeSetHtml("#report-main", `
            <section class="report-hero">
                <div class="report-hero__score">
                    <span>${Math.max(1, Math.min(100, score))}</span>
                    <small>/100</small>
                </div>
                <div class="report-hero__copy">
    <p class="eyebrow">${isSolo ? "个人简报" : "关系简报"}</p>
                    <h4>${reportLabel}</h4>
                    <p>${escapeHtml(primaryInsight)}</p>
                </div>
            </section>
            <div class="report-summary-grid">
                <article class="insight-card">
                    <span>一句结论</span>
                    <strong>${escapeHtml(primaryInsight)}</strong>
                </article>
                <article class="insight-card">
                    <span>下一步动作</span>
                    <strong>${escapeHtml(focusText)}</strong>
                </article>
                <article class="insight-card">
                    <span>报告日期</span>
                    <strong>${escapeHtml(report.report_date || formatDateOnly(new Date().toISOString()))}</strong>
                </article>
            </div>
        ${suggestion ? `<div class="panel panel--tint"><div class="panel__header"><div><p class="panel__eyebrow">下一步</p><h4>这一阶段最值得做的动作</h4></div></div><p class="panel-note">${escapeHtml(suggestion)}</p></div>` : ""}
            ${renderAttachmentSignals(content)}
            ${renderTrend(trendData, { solo: isSolo })}
                <article class="insight-card">
                    <span>涓昏鏈夌敤搴?/span>
                    <strong>${escapeHtml(usefulnessAvg)}</strong>
                </article>
                <article class="insight-card">
                    <span>鎵ц鎽╂摝</span>
                    <strong>${escapeHtml(frictionAvg)}</strong>
                </article>
            </div>
            <p class="panel-note intervention-scorecard__feedback-note">${escapeHtml(feedbackNote)}</p>
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">BRIGHT SIDE</p><h4>积极信号</h4></div></div>
                    ${renderBulletList(highlights, "目前还没有明显高亮项，继续记录会让这部分更清晰。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">FOCUS</p><h4>需要关注</h4></div></div>
                    ${renderBulletList(concerns, "目前没有额外提醒，继续保持稳定节奏就好。")}
                </div>
            </div>
            ${encouragement ? `<div class="editorial-quote"><p>${escapeHtml(encouragement)}</p></div>` : ""}
            ${scorecardPanel}
            ${narrativePromo}
            ${simulatorPromo}
        `);
  }
  const list = $("#report-history-list");
  if (!list)
    return;
  if (!history.length) {
    list.innerHTML = '<div class="empty-state">现在还没有历史简报记录。</div>';
    return;
  }
  list.innerHTML = history.map((item) => `
        <article class="stack-item history-card">
            <div class="stack-item__content">
                <strong>${formatReportType(item.type || reportType, { solo: isSolo })}</strong>
                <div class="stack-item__meta">${escapeHtml(item.report_date || "未命名日期")} · ${escapeHtml(item.status || "completed")}</div>
            </div>
            <span class="pill">可回看</span>
        </article>
    `).join("");
}
function renderReport(report, history, trendData, options = {}) {
  var _a, _b;
  const isSolo = Boolean(options.solo);
  const reportType = options.reportType || state.selectedReportType;
  const reportLabel = formatReportType(reportType, { solo: isSolo });
  const scorecardPanel = renderInterventionScorecard(options.planScorecard, { solo: isSolo });
  const evaluationPanel = renderInterventionEvaluation(options.planEvaluation, { solo: isSolo });
  const experimentPanel = renderInterventionExperiment(options.planExperiment, { solo: isSolo });
  const policyRegistryPanel = renderPolicyRegistry(options.planPolicyRegistry, { solo: isSolo });
  const policySchedulePanel = renderPolicySchedule(options.planPolicySchedule, { solo: isSolo });
  const narrativePromo = renderNarrativeAlignmentPromo(
    isSolo,
    "系统会把双方最近同一阶段的记录整理成共同版本和错位点，适合在真正开口前先对齐一下理解。"
  );
  const simulatorPromo = renderMessageSimulatorPromo(
    isSolo,
    ((_a = report == null ? void 0 : report.content) == null ? void 0 : _a.suggestion) || ((_b = report == null ? void 0 : report.content) == null ? void 0 : _b.trend_description) || ""
  );
  if (report && report.status === "pending") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                ${reportLabel} 正在后台生成。稍等片刻再回来，它会比即时结果更像一份真正可读的简报。
            </div>
            ${scorecardPanel}
            ${evaluationPanel}
            ${experimentPanel}
            ${policyRegistryPanel}
            ${policySchedulePanel}
            ${narrativePromo}
            ${simulatorPromo}`);
  } else if (report && report.status === "failed") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                ${reportLabel} 生成失败了。别担心，重新触发一次通常就能恢复。
            </div>
            ${scorecardPanel}
            ${evaluationPanel}
            ${experimentPanel}
            ${policyRegistryPanel}
            ${policySchedulePanel}
            ${narrativePromo}
            ${simulatorPromo}`);
  } else if (!report || report.status !== "completed") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                这里还没有可展示的 ${reportLabel}。先完成今天的记录，再回来读一份更像“关系编辑稿”的简报。
            </div>
            ${scorecardPanel}
            ${evaluationPanel}
            ${experimentPanel}
            ${policyRegistryPanel}
            ${policySchedulePanel}
            ${narrativePromo}
            ${simulatorPromo}`);
  } else {
    const content = report.content || {};
    const score2 = content.health_score || content.overall_health_score || 72;
    const primaryInsight = content.insight || content.self_insight || content.executive_summary || "系统已经整理好这一阶段的关系洞察。";
    const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || "";
    const encouragement = content.encouragement || content.relationship_note || "";
    const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
    const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);
    const focusText = suggestion || (concerns[0] || "继续把真实感受说清楚，比急着解决更重要。");
    safeSetHtml("#report-main", `
            ${renderReportCockpit(report, options)}
            <div class="report-summary-grid">
                <article class="insight-card">
                    <span>一句结论</span>
                    <strong>${escapeHtml(primaryInsight)}</strong>
                </article>
                <article class="insight-card">
                    <span>下一步动作</span>
                    <strong>${escapeHtml(focusText)}</strong>
                </article>
                <article class="insight-card">
                    <span>报告日期</span>
                    <strong>${escapeHtml(report.report_date || formatDateOnly(new Date().toISOString()))}</strong>
                </article>
            </div>
        ${suggestion ? `<div class="panel panel--tint"><div class="panel__header"><div><p class="panel__eyebrow">下一步</p><h4>这一阶段最值得做的动作</h4></div></div><p class="panel-note">${escapeHtml(suggestion)}</p></div>` : ""}
            ${renderAttachmentSignals(content)}
            ${renderTrend(trendData, { solo: isSolo })}
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">BRIGHT SIDE</p><h4>积极信号</h4></div></div>
                    ${renderBulletList(highlights, "目前还没有明显高亮项，继续记录会让这部分更清晰。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">FOCUS</p><h4>需要留意</h4></div></div>
                    ${renderBulletList(concerns, "目前没有额外提醒，继续保持稳定节奏就好。")}
                </div>
            </div>
            ${encouragement ? `<div class="editorial-quote"><p>${escapeHtml(encouragement)}</p></div>` : ""}
            ${scorecardPanel}
            ${evaluationPanel}
            ${experimentPanel}
            ${policyRegistryPanel}
            ${policySchedulePanel}
            ${narrativePromo}
            ${simulatorPromo}
        `);
  }
  const list = $("#report-history-list");
  if (!list)
    return;
  if (!history.length) {
    list.innerHTML = '<div class="empty-state">现在还没有历史简报记录。</div>';
    return;
  }
  list.innerHTML = history.map((item) => `
        <article class="stack-item history-card">
            <div class="stack-item__content">
                <strong>${formatReportType(item.type || reportType, { solo: isSolo })}</strong>
                <div class="stack-item__meta">${escapeHtml(item.report_date || "未命名日期")} 路 ${escapeHtml(item.status || "completed")}</div>
            </div>
            <span class="pill">可回看</span>
        </article>
    `).join("");
}
function renderTrend(trendData, options = {}) {
  const isSolo = Boolean(options.solo);
  const points = (trendData == null ? void 0 : trendData.trend) || [];
  if (points.length < 2)
    return "";
  const width = 320;
  const height = 108;
  const pad = 12;
  const coords = points.map((point, index) => {
    const x = pad + index / Math.max(points.length - 1, 1) * (width - pad * 2);
    const y = height - pad - (point.score || 0) / 100 * (height - pad * 2);
    return { x, y, score: point.score || 0, date: point.date };
  });
  const polyline = coords.map((point) => `${point.x},${point.y}`).join(" ");
  const directionLabel = {
    improving: "正在慢慢变好",
    stable: "整体比较平稳",
    declining: "需要更多照顾",
    insufficient_data: "还在形成趋势"
  }[trendData == null ? void 0 : trendData.direction] || "趋势仍在形成";
  return `
    <div class="panel panel--trend">
      <div class="panel__header">
        <div>
    <p class="panel__eyebrow">${isSolo ? "情绪趋势" : "关系趋势"}</p>
          <h4>近阶段走势</h4>
        </div>
        <span class="pill">${directionLabel}</span>
      </div>
      <svg viewBox="0 0 ${width} ${height}" class="trend-chart" aria-hidden="true">
        <defs>
          <linearGradient id="trend-line" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#d68463"></stop>
            <stop offset="100%" stop-color="#5b7a6c"></stop>
          </linearGradient>
        </defs>
        <polyline points="${polyline}" fill="none" stroke="url(#trend-line)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline>
        ${coords.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="4.5" fill="#fff7f2" stroke="#d68463" stroke-width="2"></circle>`).join("")}
      </svg>
    </div>`;
}
function formatReportType(type, options = {}) {
  const solo = Boolean(options.solo);
  if (solo && type === "daily")
    return "个人简报";
  return { daily: "日报", weekly: "周报", monthly: "月报", solo: "个人简报" }[type] || "简报";
}
function messageRiskLabel(level) {
  return {
    low: "低误读风险",
    medium: "中等风险",
    high: "高升级风险"
  }[level] || "仍需斟酌";
}
function alignmentScoreLabel(score2) {
  if (score2 >= 78)
    return "叙事较对齐";
  if (score2 >= 58)
    return "存在偏差";
  return "明显错位";
}
function planMomentumLabel(momentum) {
  return {
    early: "刚开始",
    improving: "正在起效",
    mixed: "部分起效",
    stalled: "需要调参"
  }[momentum] || "继续观察";
}
function taskIntensityLabel(intensity) {
  return {
    light: "减压版任务",
    steady: "稳定版任务",
    stretch: "进阶版任务"
  }[intensity] || "今日任务";
}
function taskFeedbackLabel(score2) {
  const value = Number(score2 || 0);
  if (value >= 5)
    return "很有用";
  if (value >= 4)
    return "挺有用";
  if (value >= 3)
    return "一般";
  if (value >= 2)
    return "偏弱";
  return "待反馈";
}
function taskFrictionLabel(score2) {
  const value = Number(score2 || 0);
  if (value <= 1.5)
    return "很轻松";
  if (value <= 2.5)
    return "比较轻松";
  if (value <= 3.5)
    return "还可以";
  if (value <= 4.5)
    return "有点难";
  return "很费劲";
}
function taskCopyModeLabel(mode) {
  return {
    clear: "更具体",
    gentle: "更温和",
    compact: "更简短",
    example: "带示例"
  }[mode] || "";
}
function taskCategoryLabel(category) {
  return {
    communication: "沟通类",
    repair: "修复类",
    activity: "陪伴类",
    reflection: "调节类",
    connection: "连接类"
  }[category] || "当前这类";
}
function taskCopyModeReason(strategy = {}) {
  const count = Number(strategy.copy_feedback_count || 0);
  const suffix = count ? `（基于最近 ${count} 次反馈）` : "";
  return {
    clear: `系统发现你更吃“具体一点、一步一步”的任务写法${suffix}。`,
    gentle: `系统发现你更适合低压力、允许缓冲的任务语气${suffix}。`,
    compact: `系统发现你更适合更短、更直接的任务表述${suffix}。`,
    example: `系统发现你更适合带一句参考开场的任务提示${suffix}。`
  }[strategy.copy_mode] || "";
}
function taskPolicySelectionReason(strategy = {}) {
  const selection = strategy.policy_selection || {};
  if (!selection.reason)
    return "";
  if (selection.auto_applied) {
    return `${selection.label || "自动选策"}：${selection.reason}`;
  }
  return `${selection.label || "继续观察"}：${selection.reason}`;
}
function taskPolicyScheduleReason(strategy = {}) {
  const schedule = strategy.policy_schedule || {};
  if (!schedule.summary)
    return "";
  return `${schedule.schedule_label || "策略排期"}：${schedule.summary}`;
}
function taskCategoryCopySummary(strategy = {}) {
  const preferences = Object.entries(strategy.category_preferences || {}).filter(([, value]) => value == null ? void 0 : value.copy_mode);
  if (!preferences.length)
    return "";
  return preferences.slice(0, 2).map(([category, value]) => `${taskCategoryLabel(category)}任务更适合${taskCopyModeLabel(value.copy_mode)}表达`).join("；");
}
function renderTaskAdaptiveHint(tasksPayload = {}) {
  var _a;
  const strategy = tasksPayload.adaptive_strategy;
  if (!strategy)
    return "";
  const scorecard = tasksPayload.plan_scorecard || {};
  const selection = strategy.policy_selection || {};
  const copyModeNote = taskCopyModeReason(strategy);
  const selectionNote = taskPolicySelectionReason(strategy);
  const scheduleNote = taskPolicyScheduleReason(strategy);
  const categoryCopyNote = taskCategoryCopySummary(strategy);
  return `
        <div class="task-strategy">
            <div class="task-strategy__meta">
                <span class="pill">${escapeHtml(taskIntensityLabel(strategy.intensity))}</span>
                ${strategy.momentum && strategy.momentum !== "none" ? `<span class="pill">${escapeHtml(planMomentumLabel(strategy.momentum))}</span>` : ""}
                ${scorecard.plan_type ? `<span class="pill">${escapeHtml(scorecard.plan_type)}</span>` : ""}
                ${strategy.copy_mode ? `<span class="pill">${escapeHtml(taskCopyModeLabel(strategy.copy_mode))}</span>` : ""}
                ${selection.label ? `<span class="pill">${escapeHtml(selection.label)}</span>` : ""}
                ${((_a = strategy.policy_schedule) == null ? void 0 : _a.schedule_label) ? `<span class="pill">${escapeHtml(strategy.policy_schedule.schedule_label)}</span>` : ""}
            </div>
            ${strategy.reason ? `<p class="panel-note">${escapeHtml(strategy.reason)}</p>` : ""}
            ${selectionNote ? `<p class="panel-note task-strategy__note">${escapeHtml(selectionNote)}</p>` : ""}
            ${scheduleNote ? `<p class="panel-note task-strategy__note">${escapeHtml(scheduleNote)}</p>` : ""}
            ${copyModeNote ? `<p class="panel-note task-strategy__note">${escapeHtml(copyModeNote)}</p>` : ""}
            ${categoryCopyNote ? `<p class="panel-note task-strategy__note">${escapeHtml(categoryCopyNote)}</p>` : ""}
        </div>
    `;
}
function renderRelationshipPlaybook(playbook, tasks = []) {
  var _a, _b, _c, _d, _e;
  if (!playbook)
    return "";
  const currentDay = Number(playbook.current_day || 1);
  const totalDays = Number(playbook.total_days || 7);
  const latestTransition = playbook.latest_transition || null;
  const previewDays = (playbook.days || []).slice(
    Math.max(currentDay - 1, 0),
    Math.min(currentDay + 2, (playbook.days || []).length)
  );
  const linkedTasks = Array.isArray(tasks) ? tasks.slice(0, 2).map((task) => `<div class="stack-item"><div>${svgIcon("i-check")}</div><div>${escapeHtml(task.title)}</div></div>`).join("") : "";
  const runtimeNote = latestTransition ? `
        <div class="playbook-runtime ${latestTransition.is_new ? "playbook-runtime--fresh" : ""}">
            <strong>${latestTransition.is_new ? "本次已自动切分支" : "最近一次剧本迁移"}</strong>
            <p>${escapeHtml(latestTransition.trigger_summary || "剧本正在按当前节奏推进。")}</p>
            <div class="stack-item__meta">
                ${latestTransition.created_at ? `${escapeHtml(formatDate(latestTransition.created_at))} · ` : ""}
                ${escapeHtml(latestTransition.to_branch_label || playbook.active_branch_label || "推进中")}
            </div>
        </div>
    ` : "";
  return `
        <section class="panel panel--tint playbook-card">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">7天计划</p>
                    <h4>${escapeHtml(playbook.title || "本周关系剧本")}</h4>
                </div>
                <div class="playbook-card__header-actions">
                    <span class="pill">${escapeHtml(playbook.active_branch_label || playbook.active_branch || "进行中")}</span>
                    <button class="text-button" type="button" onclick="openMethodologyExplainer()">判断说明</button>
                </div>
            </div>
            <p class="panel-note">${escapeHtml(playbook.summary || "")}</p>
            <div class="task-strategy__meta">
                <span class="pill">第 ${escapeHtml(currentDay)}/${escapeHtml(totalDays)} 天</span>
                ${playbook.momentum ? `<span class="pill">${escapeHtml(planMomentumLabel(playbook.momentum))}</span>` : ""}
                ${((_a = playbook.focus_tags) == null ? void 0 : _a.length) ? `<span class="pill">${escapeHtml(playbook.focus_tags[0])}</span>` : ""}
                ${playbook.transition_count ? `<span class="pill">已迁移 ${escapeHtml(playbook.transition_count)} 次</span>` : ""}
            </div>
            <div class="hero-card hero-card--accent playbook-card__today">
                <strong>${escapeHtml(((_b = playbook.today_card) == null ? void 0 : _b.title) || "今天这一格")}</strong>
                <p>${escapeHtml(((_c = playbook.today_card) == null ? void 0 : _c.action) || playbook.branch_reason || "")}</p>
                ${playbook.branch_reason ? `<div class="stack-item__meta">${escapeHtml(playbook.branch_reason)}</div>` : ""}
                ${((_d = playbook.today_card) == null ? void 0 : _d.success_signal) ? `<div class="stack-item__meta">成功信号：${escapeHtml(playbook.today_card.success_signal)}</div>` : ""}
                ${((_e = playbook.today_card) == null ? void 0 : _e.checkin_prompt) ? `<div class="stack-item__meta">今晚复盘：${escapeHtml(playbook.today_card.checkin_prompt)}</div>` : ""}
                ${linkedTasks ? `<div class="stack-list playbook-card__tasks">${linkedTasks}</div>` : ""}
            </div>
            ${runtimeNote}
            ${renderTheoryBasis(playbook.theory_basis || [], {
    title: "这套剧本背后的理论依据",
    note: playbook.clinical_disclaimer || ""
  })}
            ${previewDays.length ? `
                <div class="playbook-card__days">
                    ${previewDays.map((day) => `
                        <article class="playbook-day playbook-day--${escapeHtml(day.status || "upcoming")}">
                            <div>
                                <strong>${escapeHtml(day.label || `第 ${day.day_index || 1} 天`)}</strong>
                                <p>${escapeHtml(day.title || "")}</p>
                            </div>
                            <span class="pill">${escapeHtml(day.branch_mode_label || playbook.active_branch_label || "推进中")}</span>
                        </article>
                    `).join("")}
                </div>
            ` : ""}
        </section>
    `;
}
function theoryEvidenceLabel(card) {
  if (!card)
    return "依据";
  return card.evidence_label || card.evidence_level || "依据";
}
function theoryEvidenceTone(card) {
  const level = String((card == null ? void 0 : card.evidence_level) || "").toLowerCase();
  if (level === "moderate")
    return "theory-card__badge--moderate";
  if (level === "practice")
    return "theory-card__badge--practice";
  if (level === "emerging")
    return "theory-card__badge--emerging";
  return "";
}
function renderTheoryBasis(cards = [], options = {}) {
  const theoryCards = Array.isArray(cards) ? cards : [];
  const title = options.title || "理论依据";
  const note = options.note || "";
  if (!theoryCards.length && !note)
    return "";
  return `
        <section class="theory-basis">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">METHOD</p>
                    <h4>${escapeHtml(title)}</h4>
                </div>
            </div>
            ${theoryCards.length ? `
                <div class="theory-basis__grid">
                    ${theoryCards.map((card) => `
                        <article class="theory-card">
                            <div class="theory-card__top">
                                <strong>${escapeHtml(card.name || "方法依据")}</strong>
                                <span class="pill ${theoryEvidenceTone(card)}">${escapeHtml(theoryEvidenceLabel(card))}</span>
                            </div>
                            <p>${escapeHtml(card.summary || "")}</p>
                            ${card.how_it_is_used ? `<div class="stack-item__meta">系统怎么用：${escapeHtml(card.how_it_is_used)}</div>` : ""}
                            ${card.boundary ? `<div class="stack-item__meta">边界：${escapeHtml(card.boundary)}</div>` : ""}
                        </article>
                    `).join("")}
                </div>
            ` : ""}
            ${note ? `<p class="theory-basis__note">${escapeHtml(note)}</p>` : ""}
        </section>
    `;
}
function renderMethodologyExplainer(payload) {
  if (!payload) {
    return '<div class="empty-state">暂时还没有可展示的判断说明。</div>';
  }
  return `
        <section class="methodology-sheet">
            <div class="simulation-result__top">
                <span class="pill">${escapeHtml(payload.system_name || "关系行为干预系统")}</span>
                <span class="pill">${escapeHtml(payload.model_family || "规则引擎")}</span>
            </div>
            <div class="simulation-result__grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">MEASURE</p><h4>系统测什么</h4></div></div>
                    ${renderBulletList(payload.measurement_model || [], "当前会先看打卡、任务和风险变化。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">DECIDE</p><h4>系统怎么决策</h4></div></div>
                    ${renderBulletList(payload.decision_model || [], "当前采用规则引擎和反馈闭环。")}
                </div>
            </div>
            <div class="simulation-result__grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">MODULES</p><h4>当前启用模块</h4></div></div>
                    ${renderBulletList(payload.active_modules || [], "当前启用模块会随着关系状态扩展。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">FOCUS</p><h4>当前重点</h4></div></div>
                    ${renderBulletList(payload.current_focus || [], "系统会先抓住当前这轮最重要的 2-3 个动作方向。")}
                </div>
            </div>
            ${renderTheoryBasis(payload.theory_basis || [], {
    title: "理论依据与证据边界",
    note: payload.disclaimer || ""
  })}
            <div class="hero-actions">
                <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
            </div>
        </section>
    `;
}
async function openMethodologyExplainer() {
  var _a;
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  openModal(`
        <h3>判断说明</h3>
        <div class="empty-state">正在整理这套系统的理论依据、证据边界和当前决策逻辑，请稍候。</div>
    `);
  try {
    const payload = await api.getMethodology(pairId);
    openModal(`
            <h3>判断说明</h3>
            <p class="muted-copy">这套系统目前不是临床诊断模型，而是“关系心理学启发 + 行为科学执行 + 反馈闭环”的工程化干预系统。</p>
            ${renderMethodologyExplainer(payload)}
        `);
  } catch (error) {
    openModal(`
            <h3>判断说明</h3>
            <div class="empty-state">${escapeHtml(error.message || "暂时无法加载判断说明。")}</div>
            <div class="hero-actions">
                <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
            </div>
        `);
  }
}
function openTaskFeedback(taskId, taskTitle = "") {
  state.pendingTaskFeedback = { taskId, taskTitle };
  const playbookCard = getContextualPlaybookCard();
  openModal(`
        <h3>这一步有没有用？</h3>
        <p class="muted-copy">你的反馈会直接影响下一轮任务强度和建议方式。只需要十几秒，系统就会更像真的在学习你们。</p>
        ${taskTitle ? `<div class="hero-card hero-card--accent"><strong>刚完成的任务</strong><p>${escapeHtml(taskTitle)}</p></div>` : ""}
        <label class="field">
            <span>这一步对关系有没有帮助</span>
            <select id="task-feedback-usefulness" class="input">
                <option value="5">很有用</option>
                <option value="4">比较有用</option>
                <option value="3" selected>一般</option>
                <option value="2">不太有用</option>
                <option value="1">几乎没用</option>
            </select>
        </label>
        <label class="field">
            <span>做起来费劲吗</span>
            <select id="task-feedback-friction" class="input">
                <option value="1">很轻松</option>
                <option value="2">比较轻松</option>
                <option value="3" selected>还行</option>
                <option value="4">有点难</option>
                <option value="5">很费劲</option>
            </select>
        </label>
        <label class="field">
            <span>补充一句也可以不写</span>
            <textarea id="task-feedback-note" class="input input--textarea feedback-textarea" placeholder="例如：这一步不难，但如果再具体一点会更容易做。"></textarea>
        </label>
        <div class="hero-actions">
            <button class="button button--primary" type="button" onclick="submitTaskFeedback()">提交反馈</button>
            <button class="button button--ghost" type="button" onclick="closeModal()">稍后再说</button>
        </div>
        ${playbookCard}
    `);
}
async function submitTaskFeedback() {
  var _a, _b, _c;
  const pending = state.pendingTaskFeedback;
  if (!(pending == null ? void 0 : pending.taskId)) {
    showToast("没有待反馈的任务");
    return;
  }
  const usefulness = Number(((_a = $("#task-feedback-usefulness")) == null ? void 0 : _a.value) || 3);
  const friction = Number(((_b = $("#task-feedback-friction")) == null ? void 0 : _b.value) || 3);
  const note = (((_c = $("#task-feedback-note")) == null ? void 0 : _c.value) || "").trim();
  try {
    await api.submitTaskFeedback(pending.taskId, {
      usefulness_score: usefulness,
      friction_score: friction,
      note: note || null
    });
    state.pendingTaskFeedback = null;
    closeModal();
    showToast("反馈已记录，系统会据此调整下一轮任务");
    if (state.currentPage === "home") {
      await loadHomePage();
    } else if (state.currentPage === "challenges") {
      await loadChallengesPage();
    } else if (state.currentPage === "report") {
      await loadReportPage();
    }
  } catch (error) {
    showToast(error.message || "反馈提交失败");
  }
}
function renderInterventionScorecard(scorecard, options = {}) {
  if (!scorecard)
    return "";
  const isSolo = Boolean(options.solo);
  const completionRate = Math.round(Number(scorecard.completion_rate || 0) * 100);
  const healthDelta = typeof scorecard.health_delta === "number" ? `${scorecard.health_delta > 0 ? "+" : ""}${scorecard.health_delta.toFixed(1)}` : "暂无";
  const riskBefore = crisisLabel(scorecard.risk_before || "none");
  const riskNow = crisisLabel(scorecard.risk_now || "none");
  const feedbackCount = Number(scorecard.feedback_count || 0);
  const usefulnessAvg2 = typeof scorecard.usefulness_avg === "number" ? `${scorecard.usefulness_avg.toFixed(1)}/5` : "等待收集";
  const frictionAvg2 = typeof scorecard.friction_avg === "number" ? `${scorecard.friction_avg.toFixed(1)}/5` : "等待收集";
  const feedbackNote2 = feedbackCount ? `最近已收集 ${feedbackCount} 条主观反馈，有用度 ${taskFeedbackLabel(scorecard.usefulness_avg)}，执行摩擦 ${taskFrictionLabel(scorecard.friction_avg)}。` : "系统还在等待“这一步有没有用”的反馈，收集几次后就会继续调整任务强度。";
  return `
        <section class="panel intervention-scorecard">
            <div class="panel__header">
                <div>
            <p class="panel__eyebrow">效果闭环</p>
                    <h4>${isSolo ? "自我调节效果" : "干预效果闭环"}</h4>
                </div>
                <span class="pill">${escapeHtml(planMomentumLabel(scorecard.momentum))}</span>
            </div>
            ${scorecard.primary_goal ? `<p class="panel-note">${escapeHtml(scorecard.primary_goal)}</p>` : ""}
            <div class="report-summary-grid intervention-scorecard__metrics">
                <article class="insight-card">
                    <span>动作完成率</span>
                    <strong>${escapeHtml(completionRate)}%</strong>
                </article>
                <article class="insight-card">
                    <span>健康分变化</span>
                    <strong>${escapeHtml(healthDelta)}</strong>
                </article>
                <article class="insight-card">
                    <span>风险变化</span>
                    <strong>${escapeHtml(`${riskBefore} -> ${riskNow}`)}</strong>
                </article>
            </div>
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">有效点</p><h4>已经起效的地方</h4></div></div>
                    ${renderBulletList(scorecard.wins || [], "计划还在起步阶段，先观察哪些动作最容易坚持。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">继续关注</p><h4>还要继续盯的点</h4></div></div>
                    ${renderBulletList(scorecard.watchouts || [], "当前没有额外预警，继续看这一周是否能稳定维持。")}
                </div>
            </div>
            <div class="panel panel--tint">
                    <div class="panel__header"><div><p class="panel__eyebrow">下一轮</p><h4>下一轮最值得做的动作</h4></div></div>
                ${renderBulletList(scorecard.next_actions || [], "先保留一个最有效的小动作继续做下去。")}
            </div>
        </section>
    `;
}
function evaluationVerdictLabel(verdict) {
  return {
    positive_signal: "正向信号",
    mixed_signal: "混合信号",
    negative_signal: "负向信号",
    insufficient_data: "证据不足"
  }[verdict] || "评估中";
}
function evaluationVerdictTone(verdict) {
  return {
    positive_signal: "evaluation-chip--positive",
    mixed_signal: "evaluation-chip--mixed",
    negative_signal: "evaluation-chip--negative",
    insufficient_data: "evaluation-chip--insufficient"
  }[verdict] || "";
}
function evaluationMetricTone(status) {
  return {
    improved: "evaluation-chip--positive",
    slight_improved: "evaluation-chip--positive",
    strong: "evaluation-chip--positive",
    good: "evaluation-chip--positive",
    stable: "evaluation-chip--mixed",
    fair: "evaluation-chip--mixed",
    mixed: "evaluation-chip--mixed",
    building: "evaluation-chip--mixed",
    enough: "evaluation-chip--positive",
    adaptive: "evaluation-chip--mixed",
    worse: "evaluation-chip--negative",
    weak: "evaluation-chip--negative",
    poor: "evaluation-chip--negative",
    turbulent: "evaluation-chip--negative",
    short: "evaluation-chip--insufficient",
    thin: "evaluation-chip--insufficient",
    partial: "evaluation-chip--mixed",
    unknown: "evaluation-chip--insufficient"
  }[status] || "";
}
function renderEvaluationMetrics(metrics = []) {
  const items = Array.isArray(metrics) ? metrics : [];
  if (!items.length) {
    return '<div class="empty-state">当前还没有足够的数据来展示评估指标。</div>';
  }
  return `
        <div class="evaluation-grid">
            ${items.map((metric) => `
                <article class="evaluation-metric">
                    <div class="evaluation-metric__top">
                        <span>${escapeHtml(metric.label || "指标")}</span>
                        <span class="pill ${evaluationMetricTone(metric.status)}">${escapeHtml(metric.current || metric.delta || metric.status || "观察中")}</span>
                    </div>
                    <strong>${escapeHtml(metric.summary || "")}</strong>
                    ${metric.baseline || metric.current || metric.delta ? `
                        <div class="stack-item__meta">
                            ${metric.baseline ? `基线 ${escapeHtml(metric.baseline)}` : ""}
                            ${metric.current ? `${metric.baseline ? " · " : ""}当前 ${escapeHtml(metric.current)}` : ""}
                            ${metric.delta ? `${metric.baseline || metric.current ? " · " : ""}变化 ${escapeHtml(metric.delta)}` : ""}
                        </div>
                    ` : ""}
                    ${metric.note ? `<div class="stack-item__meta">${escapeHtml(metric.note)}</div>` : ""}
                </article>
            `).join("")}
        </div>
    `;
}
function renderInterventionEvaluation(evaluation, options = {}) {
  if (!evaluation)
    return "";
  const isSolo = Boolean(options.solo);
  return `
        <section class="panel intervention-evaluation">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">单案例测量</p>
                    <h4>${isSolo ? "这轮自我调节评估" : "这轮干预是否在起效"}</h4>
                </div>
                <div class="playbook-card__header-actions">
                    <span class="pill ${evaluationVerdictTone(evaluation.verdict)}">${escapeHtml(evaluation.verdict_label || evaluationVerdictLabel(evaluation.verdict))}</span>
                    <button class="text-button" type="button" onclick="openMethodologyExplainer()">判断说明</button>
                </div>
            </div>
            <p class="panel-note">${escapeHtml(evaluation.summary || "")}</p>
            <div class="task-strategy__meta">
                <span class="pill">${escapeHtml(evaluation.evaluation_label || "单案例连续评估")}</span>
                <span class="pill">${escapeHtml(evaluation.confidence_label || "低置信")}</span>
                <span class="pill">${escapeHtml(evaluation.data_quality_label || "低数据完备度")}</span>
            </div>
            ${renderEvaluationMetrics(evaluation.primary_metrics || [])}
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">PROCESS</p><h4>过程指标</h4></div></div>
                    ${renderEvaluationMetrics(evaluation.process_metrics || [])}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">DECISION</p><h4>下一步建议</h4></div></div>
                    <div class="hero-card hero-card--accent">
                        <strong>${escapeHtml(evaluation.recommendation_label || "继续观察")}</strong>
                        <p>${escapeHtml(evaluation.recommendation_reason || "")}</p>
                    </div>
                    ${renderBulletList(evaluation.next_measurements || [], "继续保持记录和反馈就好。")}
                </div>
            </div>
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">GAPS</p><h4>当前证据还缺什么</h4></div></div>
                    ${renderBulletList(evaluation.data_gaps || [], "当前数据已经够看这一轮的大致走向。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">NOTE</p><h4>评估说明</h4></div></div>
                    <p class="panel-note">${escapeHtml(evaluation.scientific_note || "")}</p>
                    <p class="panel-note">${escapeHtml(evaluation.clinical_disclaimer || "")}</p>
                </div>
            </div>
        </section>
    `;
}
function experimentComparisonTone(status) {
  return {
    better_than_baseline: "evaluation-chip--positive",
    worse_than_baseline: "evaluation-chip--negative",
    similar_to_baseline: "evaluation-chip--mixed",
    first_observation: "evaluation-chip--insufficient"
  }[status] || "";
}
function renderExperimentObservations(points = []) {
  const items = Array.isArray(points) ? points : [];
  if (!items.length) {
    return '<div class="empty-state">当前还没有足够的策略观测记录。</div>';
  }
  return `
        <div class="experiment-observations">
            ${items.slice(0, 5).map((point) => {
    var _a;
    return `
                <article class="experiment-observation ${point.is_current ? "experiment-observation--current" : ""}">
                    <div class="evaluation-metric__top">
                        <span>${escapeHtml(point.observed_on || "本次")}</span>
                        <span class="pill ${evaluationVerdictTone(point.verdict)}">${escapeHtml(point.verdict_label || evaluationVerdictLabel(point.verdict))}</span>
                    </div>
                    <strong>${escapeHtml(((_a = point.policy) == null ? void 0 : _a.label) || "当前策略")}</strong>
                    <p>${escapeHtml(point.summary || "")}</p>
                    <div class="stack-item__meta">
                        ${typeof point.completion_rate === "number" ? `完成 ${(point.completion_rate * 100).toFixed(0)}%` : "完成率待观察"}
                        ${point.usefulness_avg ? ` · 有用度 ${escapeHtml(point.usefulness_avg.toFixed(1))}/5` : ""}
                        ${point.friction_avg ? ` · 摩擦 ${escapeHtml(point.friction_avg.toFixed(1))}/5` : ""}
                    </div>
                </article>
            `;
  }).join("")}
        </div>
    `;
}
function renderExperimentVariants(variants = []) {
  const items = Array.isArray(variants) ? variants : [];
  if (!items.length) {
    return '<div class="empty-state">当前还没有足够的策略变体可比较。</div>';
  }
  return `
        <div class="experiment-variants">
            ${items.slice(0, 4).map((variant) => `
                <article class="experiment-variant ${variant.is_current ? "experiment-variant--current" : ""}">
                    <div class="experiment-variant__top">
                        <strong>${escapeHtml(variant.label || "策略变体")}</strong>
                        <span class="pill ${evaluationVerdictTone(variant.latest_verdict)}">${escapeHtml(variant.latest_verdict_label || "观察中")}</span>
                    </div>
                    <p>${escapeHtml(variant.summary || "")}</p>
                    <div class="stack-item__meta">
                        ${escapeHtml(String(variant.observation_count || 0))} 次观测
                        ${typeof variant.avg_completion_rate === "number" ? ` · 完成 ${(variant.avg_completion_rate * 100).toFixed(0)}%` : ""}
                        ${typeof variant.avg_usefulness === "number" ? ` · 有用度 ${variant.avg_usefulness.toFixed(1)}/5` : ""}
                        ${typeof variant.avg_friction === "number" ? ` · 摩擦 ${variant.avg_friction.toFixed(1)}/5` : ""}
                    </div>
                </article>
            `).join("")}
        </div>
    `;
}
function renderInterventionExperiment(experiment, options = {}) {
  if (!experiment)
    return "";
  const isSolo = Boolean(options.solo);
  const policy = experiment.current_policy || {};
  return `
        <section class="panel intervention-experiment">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">EXPERIMENT LEDGER</p>
                    <h4>${isSolo ? "这轮自我调节实验账本" : "这轮策略实验账本"}</h4>
                </div>
                <span class="pill ${experimentComparisonTone(experiment.comparison_status)}">${escapeHtml(experiment.comparison_label || "继续观察")}</span>
            </div>
            <p class="panel-note">${escapeHtml(experiment.hypothesis || "")}</p>
            <div class="task-strategy__meta">
                <span class="pill">${escapeHtml(experiment.experiment_label || "单案例策略实验账本")}</span>
                <span class="pill">${escapeHtml(policy.label || "当前策略")}</span>
                ${policy.copy_mode_label ? `<span class="pill">${escapeHtml(policy.copy_mode_label)}</span>` : ""}
            </div>
            <div class="hero-card hero-card--accent">
                <strong>${escapeHtml(experiment.comparison_label || "继续观察")}</strong>
                <p>${escapeHtml(experiment.comparison_summary || "")}</p>
            </div>
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">当前策略</p><h4>当前在试什么</h4></div></div>
                    <div class="experiment-policy-card">
                        <strong>${escapeHtml(policy.label || "当前策略")}</strong>
                        <p>${escapeHtml(experiment.recommendation_reason || experiment.next_question || "")}</p>
                        <div class="task-strategy__meta">
                            <span class="pill">${escapeHtml(policy.branch_label || "当前路径")}</span>
                            <span class="pill">${escapeHtml(policy.intensity_label || "当前强度")}</span>
                            ${policy.copy_mode_label ? `<span class="pill">${escapeHtml(policy.copy_mode_label)}</span>` : ""}
                        </div>
                    </div>
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">下个问题</p><h4>下一步最该验证什么</h4></div></div>
                    <div class="hero-card hero-card--summary">
                        <strong>${escapeHtml(experiment.recommendation_label || "继续观察")}</strong>
                        <p>${escapeHtml(experiment.next_question || "")}</p>
                    </div>
                    <p class="panel-note">${escapeHtml(experiment.scientific_note || "")}</p>
                </div>
            </div>
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">依据</p><h4>最近证据点</h4></div></div>
                    ${renderExperimentObservations(experiment.evidence_points || [])}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">版本</p><h4>试过的策略版本</h4></div></div>
                    ${renderExperimentVariants(experiment.strategy_variants || [])}
                </div>
            </div>
            <p class="panel-note">${escapeHtml(experiment.clinical_disclaimer || "")}</p>
        </section>
    `;
}
function renderRegisteredPolicyCard(policy, options = {}) {
  if (!policy)
    return "";
  const title = options.title || policy.title || "策略版本";
  const stateBadges = [
    policy.is_current ? '<span class="pill">当前版本</span>' : "",
    policy.is_recommended ? '<span class="pill">推荐切换</span>' : "",
    policy.latest_verdict_label ? `<span class="pill ${evaluationVerdictTone(policy.latest_verdict)}">${escapeHtml(policy.latest_verdict_label)}</span>` : ""
  ].filter(Boolean).join("");
  const metaBadges = [
    policy.branch_label ? `<span class="pill">${escapeHtml(policy.branch_label)}</span>` : "",
    policy.intensity_label ? `<span class="pill">${escapeHtml(policy.intensity_label)}</span>` : "",
    policy.copy_mode_label ? `<span class="pill">${escapeHtml(policy.copy_mode_label)}</span>` : "",
    policy.version ? `<span class="pill">${escapeHtml(policy.version)}</span>` : ""
  ].filter(Boolean).join("");
  const observationText = Number(policy.observation_count || 0) > 0 ? `${escapeHtml(String(policy.observation_count || 0))} 次观察` : "还在等待更多观察";
  const completionText = typeof policy.avg_completion_rate === "number" ? `完成 ${(policy.avg_completion_rate * 100).toFixed(0)}%` : "完成率待观察";
  const usefulnessText = typeof policy.avg_usefulness === "number" ? `有用度 ${policy.avg_usefulness.toFixed(1)}/5` : "有用度待观察";
  const frictionText = typeof policy.avg_friction === "number" ? `摩擦 ${policy.avg_friction.toFixed(1)}/5` : "摩擦待观察";
  return `
        <article class="policy-card ${policy.is_current ? "policy-card--current" : ""} ${policy.is_recommended ? "policy-card--recommended" : ""}">
            <div class="policy-card__top">
                <strong>${escapeHtml(title)}</strong>
                <div class="task-strategy__meta">${stateBadges}</div>
            </div>
            <p>${escapeHtml(policy.summary || "")}</p>
            <div class="task-strategy__meta">${metaBadges}</div>
            <div class="policy-card__metrics">
                <span>${observationText}</span>
                <span>${completionText}</span>
                <span>${usefulnessText}</span>
                <span>${frictionText}</span>
            </div>
            ${policy.summary_note ? `<p class="panel-note">${escapeHtml(policy.summary_note)}</p>` : ""}
            ${policy.selection_reason ? `<p class="panel-note">${escapeHtml(policy.selection_reason)}</p>` : ""}
            <div class="policy-card__footer">
                <div>
                    <span>适用时机</span>
                    <strong>${escapeHtml(policy.when_to_use || "")}</strong>
                </div>
                <div>
                    <span>起效标记</span>
                    <strong>${escapeHtml(policy.success_marker || "")}</strong>
                </div>
                <div>
                    <span>护栏</span>
                    <strong>${escapeHtml(policy.guardrail || "")}</strong>
                </div>
            </div>
        </article>
    `;
}
function renderPolicyRegistry(registry, options = {}) {
  var _a;
  if (!registry)
    return "";
  const isSolo = Boolean(options.solo);
  const policies = Array.isArray(registry.policies) ? registry.policies : [];
  const compactPolicies = policies.filter((policy) => !policy.is_current && !policy.is_recommended).slice(0, 4);
  return `
            <section class="panel policy-registry">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">策略库</p>
                    <h4>${isSolo ? "自我调节策略注册表" : "干预策略注册表"}</h4>
                </div>
                ${registry.selection_label ? `<span class="pill">${escapeHtml(registry.selection_label)}</span>` : ""}
            </div>
            <p class="panel-note">${escapeHtml(registry.selection_reason || registry.scientific_note || "")}</p>
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">CURRENT</p><h4>系统当前在执行哪一版</h4></div></div>
                    ${renderRegisteredPolicyCard(registry.current_policy, { title: ((_a = registry.current_policy) == null ? void 0 : _a.title) || "当前版本" })}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">RECOMMENDED</p><h4>下一版最值得尝试什么</h4></div></div>
                    ${registry.recommended_policy ? renderRegisteredPolicyCard(registry.recommended_policy, { title: registry.recommended_policy.title || "推荐版本" }) : '<div class="empty-state">当前还没有更强的替代版本，系统会先继续观察这版策略是否稳定起效。</div>'}
                </div>
            </div>
            <div class="panel panel--tint">
                <div class="panel__header"><div><p class="panel__eyebrow">CATALOG</p><h4>已注册的候选版本</h4></div></div>
                ${compactPolicies.length ? `
                    <div class="policy-registry__grid">
                        ${compactPolicies.map((policy) => renderRegisteredPolicyCard(policy, { title: policy.title || "候选版本" })).join("")}
                    </div>
                ` : '<div class="empty-state">当前计划类型还没有更多候选版本，后续会随着实验账本继续扩展。</div>'}
            </div>
            <p class="panel-note">${escapeHtml(registry.scientific_note || "")}</p>
            <p class="panel-note">${escapeHtml(registry.clinical_disclaimer || "")}</p>
        </section>
    `;
}
function renderPolicyScheduleMetrics(metrics = []) {
  const items = Array.isArray(metrics) ? metrics : [];
  if (!items.length) {
    return '<div class="empty-state">当前还没有足够的数据来生成排期观测点。</div>';
  }
  return `
        <div class="policy-schedule__metrics">
            ${items.map((metric) => `
                <article class="policy-schedule-metric">
                    <strong>${escapeHtml(metric.label || "观测点")}</strong>
                    <div class="stack-item__meta">${escapeHtml(metric.current || "待观察")} -> ${escapeHtml(metric.target || "待达成")}</div>
                    ${metric.why ? `<p>${escapeHtml(metric.why)}</p>` : ""}
                </article>
            `).join("")}
        </div>
    `;
}
function renderPolicyScheduleStage(stage, title) {
  if (!stage) {
    return '<div class="empty-state">当前没有这一阶段的排期安排。</div>';
  }
  return `
        <article class="schedule-stage">
            <div class="schedule-stage__top">
                <strong>${escapeHtml(title || stage.title || "阶段")}</strong>
                <span class="pill">${escapeHtml(stage.phase_label || stage.phase || "阶段")}</span>
            </div>
            <p>${escapeHtml(stage.summary || "")}</p>
            <div class="task-strategy__meta">
                ${stage.branch_label ? `<span class="pill">${escapeHtml(stage.branch_label)}</span>` : ""}
                ${stage.intensity_label ? `<span class="pill">${escapeHtml(stage.intensity_label)}</span>` : ""}
                ${stage.copy_mode_label ? `<span class="pill">${escapeHtml(stage.copy_mode_label)}</span>` : ""}
            </div>
            <div class="schedule-stage__stats">
                <span>周期 ${escapeHtml(String(stage.days_total || 0))} 天</span>
                <span>已跑 ${escapeHtml(String(stage.days_observed || 0))} 天</span>
                <span>剩余 ${escapeHtml(String(stage.days_remaining || 0))} 天</span>
                <span>检查点 ${escapeHtml(stage.checkpoint_date || "待定")}</span>
            </div>
        </article>
    `;
}
function renderPolicySchedule(schedule, options = {}) {
  var _a, _b;
  if (!schedule)
    return "";
  const isSolo = Boolean(options.solo);
  return `
            <section class="panel policy-schedule">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">策略排期</p>
                    <h4>${isSolo ? "自我调节策略排期器" : "干预策略排期器"}</h4>
                </div>
                <span class="pill">${escapeHtml(schedule.schedule_label || "继续观察")}</span>
            </div>
            <p class="panel-note">${escapeHtml(schedule.scientific_note || "")}</p>
            <div class="layout-grid report-grid">
                <div class="panel">
                <div class="panel__header"><div><p class="panel__eyebrow">当前周期</p><h4>这轮现在怎么跑</h4></div></div>
                    ${renderPolicyScheduleStage(schedule.current_stage, ((_a = schedule.current_policy) == null ? void 0 : _a.title) || "当前版本")}
                </div>
                <div class="panel">
                <div class="panel__header"><div><p class="panel__eyebrow">下一周期</p><h4>下一轮最该怎么接</h4></div></div>
                    ${renderPolicyScheduleStage(schedule.next_stage, ((_b = schedule.recommended_policy) == null ? void 0 : _b.title) || "下一版本")}
                </div>
            </div>
            <div class="layout-grid report-grid">
                <div class="panel">
                <div class="panel__header"><div><p class="panel__eyebrow">观测指标</p><h4>这一轮重点看什么</h4></div></div>
                    ${renderPolicyScheduleMetrics(schedule.measurement_plan || [])}
                </div>
                <div class="panel">
                <div class="panel__header"><div><p class="panel__eyebrow">护栏规则</p><h4>什么时候推进、保持或回退</h4></div></div>
                    <div class="schedule-guardrails">
                        <div>
                            <strong>推进条件</strong>
                            ${renderBulletList(schedule.advance_when || [], "先把当前周期跑完再判断是否推进。")}
                        </div>
                        <div>
                            <strong>保持条件</strong>
                            ${renderBulletList(schedule.hold_when || [], "当前先继续保持这版策略。")}
                        </div>
                        <div>
                            <strong>回退条件</strong>
                            ${renderBulletList(schedule.backoff_when || [], "一旦风险明显上升，就优先回退。")}
                        </div>
                    </div>
                </div>
            </div>
            ${schedule.fallback_stage ? `
                <div class="panel panel--tint">
                    <div class="panel__header"><div><p class="panel__eyebrow">FALLBACK</p><h4>如果这版卡住，先退到哪一版</h4></div></div>
                    ${renderPolicyScheduleStage(schedule.fallback_stage, schedule.fallback_stage.title || "回退版本")}
                </div>
            ` : ""}
            <p class="panel-note">${escapeHtml(schedule.clinical_disclaimer || "")}</p>
        </section>
    `;
}
function renderPolicyAuditSignals(signals = []) {
  const items = Array.isArray(signals) ? signals : [];
  if (!items.length) {
    return '<div class="empty-state">系统暂时还没有积累出足够的决策信号。</div>';
  }
  return `
        <div class="policy-audit__signals">
            ${items.map((signal) => `
                <article class="policy-audit__signal">
                    <span>${escapeHtml(signal.label || "信号")}</span>
                    <strong>${escapeHtml(signal.value || "等待中")}</strong>
                </article>
            `).join("")}
        </div>
    `;
}
function renderPolicyAuditTrail(items = []) {
  const trails = Array.isArray(items) ? items : [];
  if (!trails.length) {
    return '<div class="empty-state">目前还没有记录到策略决策轨迹。</div>';
  }
  return `
        <div class="policy-audit__trail">
            ${trails.map((item) => `
                <article class="policy-audit__trail-item">
                    <div class="policy-audit__trail-top">
                        <strong>${escapeHtml(item.selection_label || item.schedule_label || "决策")}</strong>
                        <span>${escapeHtml(formatDate(item.occurred_at))}</span>
                    </div>
                    <p>${escapeHtml(item.summary || "系统记录到一个决策节点。")}</p>
                    <div class="task-strategy__meta">
                        ${item.selected_policy_label ? `<span class="pill">${escapeHtml(item.selected_policy_label)}</span>` : ""}
                        ${item.schedule_label ? `<span class="pill">${escapeHtml(item.schedule_label)}</span>` : ""}
                        ${item.auto_applied ? '<span class="pill">自动执行</span>' : '<span class="pill">已记录</span>'}
                    </div>
                </article>
            `).join("")}
        </div>
    `;
}
function renderPolicyAuditEvents(events = []) {
  const items = Array.isArray(events) ? events : [];
  if (!items.length) {
    return '<div class="empty-state">随着证据继续积累，支撑事件会显示在这里。</div>';
  }
  return `
        <div class="policy-audit__events">
            ${items.map((event) => `
                <article class="policy-audit__event">
                    <div class="policy-audit__event-top">
                        <span class="pill">${escapeHtml(event.category_label || "事件")}</span>
                        <span>${escapeHtml(formatDate(event.occurred_at))}</span>
                    </div>
                    <strong>${escapeHtml(event.label || "证据事件")}</strong>
                    <p>${escapeHtml(event.summary || "系统记录到一条相关的支撑信号。")}</p>
                </article>
            `).join("")}
        </div>
    `;
}
function renderPolicyDecisionAudit(audit, options = {}) {
  if (!audit)
    return "";
  const isSolo = Boolean(options.solo);
  const currentPolicy = audit.current_policy || {};
  const recommendedPolicy = audit.recommended_policy || null;
  const latestDecision = Array.isArray(audit.decision_history) ? audit.decision_history[0] : null;
  const pills = [
    audit.selection_label,
    audit.schedule_label,
    audit.active_branch_label,
    audit.next_checkpoint ? `检查点 ${audit.next_checkpoint}` : ""
  ].filter(Boolean);
  return `
        <section class="panel policy-audit">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">策略审计</p>
                    <h4>${isSolo ? "系统为什么继续保持这条自我调节路径" : "系统为什么选择这条关系策略"}</h4>
                </div>
                ${audit.evidence_observation_count ? `<span class="pill">${escapeHtml(String(audit.evidence_observation_count))} 条观察</span>` : ""}
            </div>
            <p class="panel-note">${escapeHtml(audit.selection_reason || audit.schedule_summary || "这里会说明策略选择、排期变化和证据之间是怎样连起来的。")}</p>
            <div class="policy-audit__hero">
                <div>
                    <span>当前策略</span>
                    <strong>${escapeHtml(currentPolicy.title || currentPolicy.policy_id || "当前策略")}</strong>
                </div>
                <div>
                    <span>建议下一步</span>
                    <strong>${escapeHtml((recommendedPolicy == null ? void 0 : recommendedPolicy.title) || "继续观察当前策略")}</strong>
                </div>
                <div class="task-strategy__meta">
                    ${pills.map((item) => `<span class="pill">${escapeHtml(item)}</span>`).join("")}
                </div>
            </div>
            ${renderPolicyAuditSignals(audit.signals || [])}
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">轨迹</p><h4>最近的策略检查点</h4></div></div>
                    ${renderPolicyAuditTrail(audit.decision_history || [])}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">支撑信号</p><h4>支撑这次选择的事件</h4></div></div>
                    ${renderPolicyAuditEvents(audit.supporting_events || [])}
                </div>
            </div>
            ${latestDecision ? `<div class="panel panel--tint"><div class="panel__header"><div><p class="panel__eyebrow">最新记录</p><h4>最近一次审计记录</h4></div></div><p class="panel-note">${escapeHtml(latestDecision.summary || "")}</p></div>` : ""}
            <p class="panel-note">${escapeHtml(audit.scientific_note || "")}</p>
            <p class="panel-note">${escapeHtml(audit.clinical_disclaimer || "")}</p>
        </section>
    `;
}
function renderPolicyAuditPeek(audit) {
  var _a;
  if (!audit)
    return "";
  const latestDecision = Array.isArray(audit.decision_history) ? audit.decision_history[0] : null;
  return `
        <article class="timeline-note-card timeline-note-card--soft">
            <p class="panel__eyebrow">策略审计</p>
            <h4>${escapeHtml(((_a = audit.current_policy) == null ? void 0 : _a.title) || "当前策略")}</h4>
            <p>${escapeHtml(audit.selection_reason || audit.schedule_summary || "系统还在为下一次策略检查点继续收集证据。")}</p>
            <div class="task-strategy__meta">
                ${audit.selection_label ? `<span class="pill">${escapeHtml(audit.selection_label)}</span>` : ""}
                ${audit.schedule_label ? `<span class="pill">${escapeHtml(audit.schedule_label)}</span>` : ""}
                ${audit.next_checkpoint ? `<span class="pill">${escapeHtml(String(audit.next_checkpoint))}</span>` : ""}
            </div>
            ${latestDecision ? `<p class="panel-note">${escapeHtml(latestDecision.summary || "")}</p>` : ""}
        </article>
    `;
}
function renderInterventionScorecard(scorecard, options = {}) {
  if (!scorecard)
    return "";
  const isSolo = Boolean(options.solo);
  const completionRate = Math.round(Number(scorecard.completion_rate || 0) * 100);
  const healthDelta = typeof scorecard.health_delta === "number" ? `${scorecard.health_delta > 0 ? "+" : ""}${scorecard.health_delta.toFixed(1)}` : "暂无";
  const riskBefore = crisisLabel(scorecard.risk_before || "none");
  const riskNow = crisisLabel(scorecard.risk_now || "none");
  const feedbackCount = Number(scorecard.feedback_count || 0);
  const usefulnessAvg2 = typeof scorecard.usefulness_avg === "number" ? `${scorecard.usefulness_avg.toFixed(1)}/5` : "待收集";
  const frictionAvg2 = typeof scorecard.friction_avg === "number" ? `${scorecard.friction_avg.toFixed(1)}/5` : "待收集";
  const feedbackNote2 = feedbackCount ? `最近已收集 ${feedbackCount} 条主观反馈，有用度 ${taskFeedbackLabel(scorecard.usefulness_avg)}，执行摩擦 ${taskFrictionLabel(scorecard.friction_avg)}。` : "系统还在等待“这步到底有没有用”的反馈，收集几次后就会更会调整任务强度。";
  return `
        <section class="panel intervention-scorecard">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">效果闭环</p>
                    <h4>${isSolo ? "自我调节效果" : "干预效果闭环"}</h4>
                </div>
                <span class="pill">${escapeHtml(planMomentumLabel(scorecard.momentum))}</span>
            </div>
            ${scorecard.primary_goal ? `<p class="panel-note">${escapeHtml(scorecard.primary_goal)}</p>` : ""}
            <div class="report-summary-grid intervention-scorecard__metrics">
                <article class="insight-card">
                    <span>动作完成率</span>
                    <strong>${escapeHtml(completionRate)}%</strong>
                </article>
                <article class="insight-card">
                    <span>健康分变化</span>
                    <strong>${escapeHtml(healthDelta)}</strong>
                </article>
                <article class="insight-card">
                    <span>风险变化</span>
                    <strong>${escapeHtml(`${riskBefore} -> ${riskNow}`)}</strong>
                </article>
                <article class="insight-card">
                    <span>主观有用度</span>
                    <strong>${escapeHtml(usefulnessAvg2)}</strong>
                </article>
                <article class="insight-card">
                    <span>执行摩擦</span>
                    <strong>${escapeHtml(frictionAvg2)}</strong>
                </article>
            </div>
            <p class="panel-note intervention-scorecard__feedback-note">${escapeHtml(feedbackNote2)}</p>
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">有效点</p><h4>已经起效的地方</h4></div></div>
                    ${renderBulletList(scorecard.wins || [], "计划还在起步阶段，先观察哪些动作最容易坚持。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">继续关注</p><h4>还要继续盯的点</h4></div></div>
                    ${renderBulletList(scorecard.watchouts || [], "当前没有额外预警，继续看这一周是否能稳定维持。")}
                </div>
            </div>
            <div class="panel panel--tint">
                <div class="panel__header"><div><p class="panel__eyebrow">下一轮</p><h4>下一轮最值得做的动作</h4></div></div>
                ${renderBulletList(scorecard.next_actions || [], "先保留一个最有效的小动作继续做下去。")}
            </div>
        </section>
    `;
}
function renderNarrativeAlignmentPromo(isSolo, hintText = "") {
  if (isSolo)
    return "";
  return `
        <div class="panel narrative-lab-card">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">DUAL VIEW</p>
                    <h4>双方叙事对齐</h4>
                </div>
                <button class="button button--secondary" type="button" onclick="openNarrativeAlignment()">看共同版本</button>
            </div>
            <p class="panel-note">${escapeHtml(hintText || "把双方最近同一天的记录整理成“共同版本、错位点和更好开场白”，让系统不只停在总结，而是帮助双方对齐。")}</p>
        </div>
    `;
}
function renderMessageSimulatorPromo(isSolo, hintText = "") {
  if (isSolo)
    return "";
  return `
        <div class="panel panel--tint message-lab-card">
            <div class="panel__header">
                <div>
                    <p class="panel__eyebrow">MESSAGE LAB</p>
                    <h4>聊天前预演</h4>
                </div>
                <button class="button button--secondary" type="button" onclick="openMessageSimulator()">试一句准备发的话</button>
            </div>
            <p class="panel-note">${escapeHtml(hintText || "在发出去之前，先看一眼这句话更可能被怎样理解，再决定要不要直接按发送。")}</p>
        </div>
    `;
}
function renderNarrativeAlignmentResult(payload) {
  if (!payload)
    return "";
  const alignmentScore = Number(payload.alignment_score || 0);
  return `
        <section class="narrative-alignment">
            <div class="narrative-alignment__top">
                <span class="pill narrative-alignment__score">${escapeHtml(alignmentScoreLabel(alignmentScore))}</span>
                <span class="pill">对齐度 ${escapeHtml(alignmentScore)}</span>
                ${payload.current_risk_level ? `<span class="pill">${escapeHtml(crisisLabel(payload.current_risk_level))}</span>` : ""}
                ${payload.active_plan_type ? `<span class="pill">${escapeHtml(payload.active_plan_type)}</span>` : ""}
            </div>
            <section class="hero-card hero-card--accent">
                <strong>共同版本</strong>
                <p>${escapeHtml(payload.shared_story || "系统已经整理出这一天双方共同在经历的版本。")}</p>
            </section>
            <div class="simulation-result__grid">
                <article class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">VIEW A</p><h4>${escapeHtml(payload.user_a_label || "A方")}</h4></div></div>
                    <p class="panel-note">${escapeHtml(payload.view_a_summary || "A方视角暂未识别。")}</p>
                </article>
                <article class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">VIEW B</p><h4>${escapeHtml(payload.user_b_label || "B方")}</h4></div></div>
                    <p class="panel-note">${escapeHtml(payload.view_b_summary || "B方视角暂未识别。")}</p>
                </article>
            </div>
            <section class="hero-card">
                <strong>最容易错位的地方</strong>
                <p>${escapeHtml(payload.misread_risk || "当前最容易错位的点暂未识别。")}</p>
            </section>
            <div class="simulation-result__grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">GAPS</p><h4>分歧点</h4></div></div>
                    ${renderBulletList(payload.divergence_points || [], "双方这次的差别更多来自表达方式，而不是立场本身。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">BRIDGE</p><h4>桥接动作</h4></div></div>
                    ${renderBulletList(payload.bridge_actions || [], "先确认版本，再谈下一步动作。")}
                </div>
            </div>
            ${payload.suggested_opening ? `<div class="hero-card narrative-alignment__opening"><strong>更容易开启对齐的第一句</strong><p>${escapeHtml(payload.suggested_opening)}</p></div>` : ""}
            ${payload.coach_note ? `<div class="editorial-quote"><p>${escapeHtml(payload.coach_note)}</p></div>` : ""}
            <div class="hero-actions">
                <button class="button button--secondary" type="button" onclick="copyNarrativeOpening()">复制开场白</button>
                <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
            </div>
        </section>
    `;
}
function safetyRiskLabel(level) {
  return {
    none: "稳定",
    low: "低风险",
    mild: "轻度波动",
    moderate: "需要谨慎",
    high: "高风险",
    severe: "请升级支持"
  }[level] || "持续观察";
}
function renderSafetyStatusPanel(status, options = {}) {
  if (!status) {
    return "";
  }
  const compactClass = options.compact ? " safety-panel--compact" : "";
  const evidence = Array.isArray(status.evidence_summary) ? status.evidence_summary : [];
  const dataNotes = options.dataNotes || [
    state.currentPair ? "最近打卡、报告、危机与任务反馈" : "最近个人记录、报告与干预反馈",
    "当前剧本分支、策略排期与风险信号",
    "事件流中的近 7-30 天关系趋势"
  ];
  return `
        <section class="safety-panel${compactClass}">
            <div class="safety-panel__head">
                <div>
    <p class="panel__eyebrow">${escapeHtml(options.eyebrow || "信任与边界")}</p>
                    <h4>${escapeHtml(options.title || "信任与边界")}</h4>
                </div>
                <div class="safety-panel__chips">
                    <span class="pill pill--accent">${escapeHtml(safetyRiskLabel(status.risk_level))}</span>
                    ${status.handoff_recommendation ? '<span class="pill">建议升级支持</span>' : '<span class="pill">系统辅助判断</span>'}
                </div>
            </div>
            ${status.why_now ? `<p class="safety-panel__summary">${escapeHtml(status.why_now)}</p>` : ""}
            ${evidence.length ? `<div class="safety-panel__evidence">${evidence.map((item) => `<span class="safety-panel__evidence-chip">${escapeHtml(item)}</span>`).join("")}</div>` : ""}
            <div class="safety-panel__body">
                <article>
                    <strong>系统用了哪些数据</strong>
                    <ul>${dataNotes.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
                </article>
                <article>
                    <strong>这次判断依据</strong>
                    <p>${escapeHtml(status.recommended_action || "系统会结合当前风险、最近事件和正在执行的计划，给出当前最稳妥的下一步。")}</p>
                </article>
            </div>
            ${status.limitation_note ? `<p class="safety-panel__note">${escapeHtml(status.limitation_note)}</p>` : ""}
            ${status.handoff_recommendation ? `<p class="safety-panel__note safety-panel__note--handoff">${escapeHtml(status.handoff_recommendation)}</p>` : ""}
        </section>
    `;
}
function renderAssessmentTrendCard(trend, options = {}) {
  if (!trend) {
    return "";
  }
  const latestScore = Number(trend.latest_score || 0);
  const points = Array.isArray(trend.trend_points) ? trend.trend_points.slice(0, 4) : [];
  const dimensions = Array.isArray(trend.dimension_scores) ? trend.dimension_scores.slice(0, 5) : [];
  return `
        <section class="assessment-panel">
            <div class="assessment-panel__head">
                <div>
    <p class="panel__eyebrow">${escapeHtml(options.eyebrow || "阶段评估")}</p>
                    <h4>${escapeHtml(options.title || "近 4 次关系体检趋势")}</h4>
                </div>
                <div class="assessment-panel__score">
                    <span>最新总分</span>
                    <strong>${escapeHtml(String(latestScore || "--"))}</strong>
                </div>
            </div>
            ${trend.change_summary ? `<p class="assessment-panel__summary">${escapeHtml(trend.change_summary)}</p>` : ""}
            ${points.length ? `<div class="assessment-panel__points">
                ${points.map((point) => {
    var _a, _b;
    return `
                    <article class="assessment-panel__point">
                        <span>${escapeHtml(point.submitted_at ? formatDateOnly(point.submitted_at) : point.recorded_at ? formatDateOnly(point.recorded_at) : "本周")}</span>
                        <strong>${escapeHtml(String((_b = (_a = point.total_score) != null ? _a : point.score) != null ? _b : "--"))}</strong>
                        <p>${escapeHtml(point.change_summary || point.summary || "已记录本周体检。")}</p>
                    </article>
                `;
  }).join("")}
            </div>` : ""}
            ${dimensions.length ? `<div class="assessment-panel__dimensions">
                ${dimensions.map((item) => {
    var _a;
    return `
                    <div class="assessment-panel__dimension">
                        <span>${escapeHtml(item.label || item.dimension || "维度")}</span>
                        <strong>${escapeHtml(String((_a = item.score) != null ? _a : "--"))}</strong>
                    </div>
                `;
  }).join("")}
            </div>` : ""}
        </section>
    `;
}
function renderMessageSimulationResult(payload) {
  if (!payload)
    return "";
  return `
        <div class="simulation-result">
            <div class="simulation-result__top">
                <span class="pill simulation-risk simulation-risk--${escapeHtml(payload.risk_level || "medium")}">${escapeHtml(messageRiskLabel(payload.risk_level))}</span>
                ${payload.suggested_tone ? `<span class="pill">${escapeHtml(payload.suggested_tone)}</span>` : ""}
                ${payload.conversation_goal ? `<span class="pill">${escapeHtml(payload.conversation_goal)}</span>` : ""}
            </div>
            <div class="simulation-result__grid">
                <article class="hero-card">
                    <strong>对方第一感受</strong>
                    <p>${escapeHtml(payload.partner_view || "系统暂时无法判断。")}</p>
                </article>
                <article class="hero-card">
                    <strong>大概率走向</strong>
                    <p>${escapeHtml(payload.likely_impact || "系统暂时无法判断。")}</p>
                </article>
            </div>
            <div class="hero-card hero-card--accent">
                <strong>为什么有这个风险</strong>
                <p>${escapeHtml(payload.risk_reason || "它可能在情绪上先被接成压力，而不是需求。")}</p>
            </div>
            <div class="hero-card simulation-rewrite">
                <strong>更稳妥的表达版本</strong>
                <p>${escapeHtml(payload.safer_rewrite || payload.draft || "")}</p>
            </div>
            <div class="simulation-result__grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">DO</p><h4>建议这样做</h4></div></div>
                    ${renderBulletList(payload.do_list || [], "先说感受，再说具体需求。")}
                </div>
                <div class="panel">
        <div class="panel__header"><div><p class="panel__eyebrow">避免</p><h4>尽量避免</h4></div></div>
                    ${renderBulletList(payload.avoid_list || [], "避免绝对化和翻旧账。")}
                </div>
            </div>
            <div class="hero-actions">
                <button class="button button--secondary" type="button" onclick="useSimulationRewrite()">把改写放回输入框</button>
                <button class="button button--ghost" type="button" onclick="copySimulationRewrite()">复制改写版本</button>
            </div>
        </div>
    `;
}
function renderRelationshipTimelineRibbon(timeline, options = {}) {
  const isSolo = Boolean(options.solo);
  const events = Array.isArray(timeline == null ? void 0 : timeline.events) ? timeline.events.slice(0, 3) : [];
  const latestEventAt = (timeline == null ? void 0 : timeline.latest_event_at) ? formatDate(timeline.latest_event_at) : "刚刚";
  const headline = isSolo ? "把记录、反馈、策略和状态切换读成一条连续的个人节律。" : "把打卡、风险、任务、剧本迁移串成一条真正可回放的关系时间轴。";
  if (!events.length) {
    return `
            <section class="timeline-ribbon timeline-ribbon--empty">
                <div class="timeline-ribbon__top">
                    <div>
                        <p class="panel__eyebrow">${isSolo ? "个人时间线" : "关系时间线"}</p>
                        <h4>关系时间轴回放</h4>
                    </div>
                    <button class="button button--ghost" type="button" onclick="showPage('timeline')">打开时间轴</button>
                </div>
                <p class="timeline-ribbon__headline">${headline}</p>
                <div class="empty-state">时间轴会在更多记录、任务和策略更新后变得更完整。</div>
            </section>
        `;
  }
  return `
        <section class="timeline-ribbon">
            <div class="timeline-ribbon__top">
                <div>
                    <p class="panel__eyebrow">${isSolo ? "个人时间线" : "关系时间线"}</p>
                    <h4>关系时间轴回放</h4>
                </div>
                <div class="timeline-ribbon__stats">
                    <span class="pill">${escapeHtml(String((timeline == null ? void 0 : timeline.event_count) || events.length))} 个节点</span>
                    <span class="timeline-ribbon__stamp">最近更新 ${escapeHtml(latestEventAt)}</span>
                </div>
            </div>
            <p class="timeline-ribbon__headline">${headline}</p>
            <div class="timeline-ribbon__list">
                ${events.map((item) => `
                    <article class="timeline-ribbon__event timeline-ribbon__event--${escapeHtml(item.tone || "neutral")}">
                        <div class="timeline-ribbon__event-meta">
                            <span>${escapeHtml(item.category_label || "节点")}</span>
                            <span>${escapeHtml(formatDate(item.occurred_at))}</span>
                        </div>
                        <strong>${escapeHtml(item.label || item.summary || "最近有新的变化")}</strong>
                        <p>${escapeHtml(item.summary || "系统记录了一次新的状态变化。")}</p>
                    </article>
                `).join("")}
            </div>
            <div class="timeline-ribbon__actions">
                <button class="button button--secondary" type="button" onclick="showPage('timeline')">进入时间轴</button>
            </div>
        </section>
    `;
}
function renderRelationshipTimelinePanel(payload, options = {}) {
  const isSolo = Boolean(options.solo);
  const events = Array.isArray(payload == null ? void 0 : payload.events) ? payload.events : [];
  const highlights = Array.isArray(payload == null ? void 0 : payload.highlights) ? payload.highlights : [];
  const title = isSolo ? "个人时间轴回放" : "关系时间轴回放";
  const description = isSolo ? "这里会把你最近的记录、生成、反馈和策略切换放到同一条时间线上。" : "这里会把你们最近的记录、风险、任务、剧本迁移和关键洞察串成一条完整叙事。";
  return `
        <section class="relationship-timeline">
            <div class="relationship-timeline__hero">
                <div>
                    <p class="panel__eyebrow">${isSolo ? "个人时间线" : "关系时间线"}</p>
                    <h3>${title}</h3>
                    <p class="muted-copy">${description}</p>
                </div>
                <div class="relationship-timeline__hero-stats">
                    <div class="relationship-timeline__hero-card">
                        <span>已回放节点</span>
                        <strong>${escapeHtml(String((payload == null ? void 0 : payload.event_count) || events.length))}</strong>
                    </div>
                    <div class="relationship-timeline__hero-card">
                        <span>最近一次更新</span>
                        <strong>${escapeHtml((payload == null ? void 0 : payload.latest_event_at) ? formatDate(payload.latest_event_at) : "刚刚")}</strong>
                    </div>
                </div>
            </div>
            ${highlights.length ? `
                <div class="relationship-timeline__highlights">
                    ${highlights.map((item) => `<span class="relationship-timeline__highlight">${escapeHtml(item)}</span>`).join("")}
                </div>
            ` : ""}
            <div class="relationship-timeline__list">
                ${events.length ? events.map((item) => `
                    <article class="relationship-timeline__item relationship-timeline__item--${escapeHtml(item.tone || "neutral")}">
                        <div class="relationship-timeline__rail">
                            <span class="relationship-timeline__dot"></span>
                        </div>
                        <div class="relationship-timeline__content">
                            <div class="relationship-timeline__meta">
                                <span class="pill">${escapeHtml(item.category_label || "节点")}</span>
                                <span>${escapeHtml(item.tone_label || "持续记录")}</span>
                                <span>${escapeHtml(formatDate(item.occurred_at))}</span>
                            </div>
                            <h4>${escapeHtml(item.label || item.summary || "最近有新的变化")}</h4>
                            <p>${escapeHtml(item.summary || "系统记录了一次新的状态变化。")}</p>
                            ${item.detail ? `<p class="relationship-timeline__detail">${escapeHtml(item.detail)}</p>` : ""}
                            ${(item.tags || []).length ? `
                                <div class="relationship-timeline__tags">
                                    ${(item.tags || []).map((tag) => `<span class="relationship-timeline__tag">${escapeHtml(tag)}</span>`).join("")}
                                </div>
                            ` : ""}
                        </div>
                    </article>
                `).join("") : '<div class="empty-state">还没有足够的时间轴节点，先继续写下今天的记录。</div>'}
            </div>
            <div class="hero-actions">
                ${isSolo ? `<button class="button button--secondary" type="button" onclick="showPage('checkin'); closeModal();">去写今天记录</button>` : '<button class="button button--secondary" type="button" onclick="openMessageSimulator()">聊天前预演</button>'}
                <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
            </div>
        </section>
    `;
}
function renderReportCockpit(report, options = {}) {
  const isSolo = Boolean(options.solo);
  const reportType = options.reportType || state.selectedReportType;
  const reportLabel = formatReportType(reportType, { solo: isSolo });
  const content = (report == null ? void 0 : report.content) || {};
  const score2 = Math.max(1, Math.min(100, content.health_score || content.overall_health_score || 72));
  const primaryInsight = content.insight || content.self_insight || content.executive_summary || "系统已经整理好这段时间最值得先读的一句判断。";
  const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || "";
  const encouragement = content.encouragement || content.relationship_note || "";
  const focusText = suggestion || "先把最真实的感受说清楚，再决定要不要继续推进。";
  const modules = buildReportCockpitModules(options, isSolo);
  const actionButtons = isSolo ? `
            <button class="button button--secondary" type="button" onclick="showPage('checkin')">回到今日记录</button>
            <button class="button button--ghost" type="button" onclick="showPage('timeline')">时间轴</button>
            <button class="button button--ghost" type="button" onclick="openMethodologyExplainer()">判断说明</button>
        ` : `
            <button class="button button--secondary" type="button" onclick="openMessageSimulator()">聊天前预演</button>
            <button class="button button--ghost" type="button" onclick="showPage('timeline')">时间轴</button>
            <button class="button button--ghost" type="button" onclick="openNarrativeAlignment()">双视角对齐</button>
            <button class="button button--ghost" type="button" onclick="openMethodologyExplainer()">判断说明</button>
        `;
  return `
        <section class="brief-cockpit" style="--score:${score2}">
            <div class="brief-cockpit__hero">
                <div class="brief-cockpit__score-panel">
                    <div class="brief-cockpit__score-ring">
                        <strong>${score2}</strong>
                        <span>${escapeHtml(reportLabel)}</span>
                    </div>
                    <p>${escapeHtml(formatDateOnly((report == null ? void 0 : report.report_date) || new Date().toISOString()))}</p>
                </div>
                <div class="brief-cockpit__copy">
            <p class="eyebrow">${isSolo ? "个人简报" : "关系简报"}</p>
                    <h4>${escapeHtml(reportLabel)}</h4>
                    <p class="brief-cockpit__lede">${escapeHtml(primaryInsight)}</p>
                    <div class="brief-cockpit__story">
                        <article class="brief-cockpit__story-card">
                            <span>当前读法</span>
                            <strong>${escapeHtml(focusText)}</strong>
                        </article>
                        <article class="brief-cockpit__story-card">
                            <span>${encouragement ? "给此刻的一句提醒" : "系统姿态"}</span>
                            <strong>${escapeHtml(encouragement || "它不是在给结论，而是在帮你把复杂关系拆成可行动的下一步。")}</strong>
                        </article>
                    </div>
                </div>
                <div class="brief-cockpit__actions">
                    ${actionButtons}
                </div>
            </div>
            <div class="brief-cockpit__grid">
                ${modules.map((item) => `
                    <article class="brief-cockpit-card ${item.tone || ""}">
                        <p class="panel__eyebrow">${escapeHtml(item.eyebrow || "MODULE")}</p>
                        <span>${escapeHtml(item.title || "模块")}</span>
                        <strong>${escapeHtml(item.value || "观察中")}</strong>
                        <p>${escapeHtml(item.note || "等待更多数据")}</p>
                    </article>
                `).join("")}
            </div>
        </section>
    `;
}
function renderReport(report, history, trendData, options = {}) {
  var _a, _b;
  const isSolo = Boolean(options.solo);
  const reportType = options.reportType || state.selectedReportType;
  const reportLabel = formatReportType(reportType, { solo: isSolo });
  const scorecardPanel = renderInterventionScorecard(options.planScorecard, { solo: isSolo });
  const evaluationPanel = renderInterventionEvaluation(options.planEvaluation, { solo: isSolo });
  const experimentPanel = renderInterventionExperiment(options.planExperiment, { solo: isSolo });
  const policyRegistryPanel = renderPolicyRegistry(options.planPolicyRegistry, { solo: isSolo });
  const policySchedulePanel = renderPolicySchedule(options.planPolicySchedule, { solo: isSolo });
  const policyAuditPanel = renderPolicyDecisionAudit(options.planPolicyAudit, { solo: isSolo });
  const timelineRibbon = renderRelationshipTimelineRibbon(options.timeline, { solo: isSolo });
  const narrativePromo = renderNarrativeAlignmentPromo(
    isSolo,
    "系统会把双方最近同一阶段的记录整理成共同版本和错位点，适合在真正开口前先对齐一下理解。"
  );
  const simulatorPromo = renderMessageSimulatorPromo(
    isSolo,
    ((_a = report == null ? void 0 : report.content) == null ? void 0 : _a.suggestion) || ((_b = report == null ? void 0 : report.content) == null ? void 0 : _b.trend_description) || ""
  );
  if (report && report.status === "pending") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                ${reportLabel} 正在后台生成。稍等片刻再回来，它会比即时结果更像一份真正可读的简报。
            </div>
            ${timelineRibbon}
            ${scorecardPanel}
            ${evaluationPanel}
            ${experimentPanel}
            ${policyRegistryPanel}
            ${policySchedulePanel}
            ${policyAuditPanel}
            ${narrativePromo}
            ${simulatorPromo}`);
  } else if (report && report.status === "failed") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                ${reportLabel} 生成失败了。别担心，重新触发一次通常就能恢复。
            </div>
            ${timelineRibbon}
            ${scorecardPanel}
            ${evaluationPanel}
            ${experimentPanel}
            ${policyRegistryPanel}
            ${policySchedulePanel}
            ${policyAuditPanel}
            ${narrativePromo}
            ${simulatorPromo}`);
  } else if (!report || report.status !== "completed") {
    safeSetHtml("#report-main", `
            <div class="empty-state">
                这里还没有可展示的 ${reportLabel}。先完成今天的记录，再回来读一份更像“关系编辑稿”的简报。
            </div>
            ${timelineRibbon}
            ${scorecardPanel}
            ${evaluationPanel}
            ${experimentPanel}
            ${policyRegistryPanel}
            ${policySchedulePanel}
            ${policyAuditPanel}
            ${narrativePromo}
            ${simulatorPromo}`);
  } else {
    const content = report.content || {};
    const primaryInsight = content.insight || content.self_insight || content.executive_summary || "系统已经整理好这一阶段的关系洞察。";
    const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || "";
    const encouragement = content.encouragement || content.relationship_note || "";
    const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
    const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);
    const focusText = suggestion || (concerns[0] || "继续把真实感受说清楚，比急着解决更重要。");
    safeSetHtml("#report-main", `
            ${renderReportCockpit(report, options)}
            ${timelineRibbon}
            <div class="report-summary-grid">
                <article class="insight-card">
                    <span>一句结论</span>
                    <strong>${escapeHtml(primaryInsight)}</strong>
                </article>
                <article class="insight-card">
                    <span>下一步动作</span>
                    <strong>${escapeHtml(focusText)}</strong>
                </article>
                <article class="insight-card">
                    <span>报告日期</span>
                    <strong>${escapeHtml(report.report_date || formatDateOnly(new Date().toISOString()))}</strong>
                </article>
            </div>
        ${suggestion ? `<div class="panel panel--tint"><div class="panel__header"><div><p class="panel__eyebrow">下一步</p><h4>这一阶段最值得做的动作</h4></div></div><p class="panel-note">${escapeHtml(suggestion)}</p></div>` : ""}
            ${renderAttachmentSignals(content)}
            ${renderTrend(trendData, { solo: isSolo })}
            <div class="layout-grid report-grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">BRIGHT SIDE</p><h4>积极信号</h4></div></div>
                    ${renderBulletList(highlights, "目前还没有明显高亮项，继续记录会让这部分更清晰。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">FOCUS</p><h4>需要留意</h4></div></div>
                    ${renderBulletList(concerns, "目前没有额外提醒，继续保持稳定节奏就好。")}
                </div>
            </div>
            ${encouragement ? `<div class="editorial-quote"><p>${escapeHtml(encouragement)}</p></div>` : ""}
            ${scorecardPanel}
            ${evaluationPanel}
            ${experimentPanel}
            ${policyRegistryPanel}
            ${policySchedulePanel}
            ${policyAuditPanel}
            ${narrativePromo}
            ${simulatorPromo}
        `);
  }
  const list = $("#report-history-list");
  if (!list)
    return;
  if (!history.length) {
    list.innerHTML = '<div class="empty-state">现在还没有历史简报记录。</div>';
    return;
  }
  list.innerHTML = history.map((item) => `
        <article class="stack-item history-card">
            <div class="stack-item__content">
                <strong>${formatReportType(item.type || reportType, { solo: isSolo })}</strong>
                <div class="stack-item__meta">${escapeHtml(item.report_date || "未命名日期")} · ${escapeHtml(item.status === "completed" ? "已完成" : item.status || "已完成")}</div>
            </div>
            <span class="pill">可回看</span>
        </article>
    `).join("");
}
function getTimelineFilterSets(events = []) {
  const categories = [{ value: "all", label: "全部类别" }];
  const tones = [{ value: "all", label: "全部语气" }];
  const categoryMap = /* @__PURE__ */ new Map();
  const toneMap = /* @__PURE__ */ new Map();
  events.forEach((event) => {
    if ((event == null ? void 0 : event.category) && !categoryMap.has(event.category)) {
      categoryMap.set(event.category, event.category_label || event.category);
    }
    if ((event == null ? void 0 : event.tone) && !toneMap.has(event.tone)) {
      toneMap.set(event.tone, event.tone_label || event.tone);
    }
  });
  categoryMap.forEach((label, value) => categories.push({ value, label }));
  toneMap.forEach((label, value) => tones.push({ value, label }));
  return { categories, tones };
}
function getFilteredTimelineEvents(events = []) {
  return events.filter((event) => {
    if (state.timelineFilters.category !== "all" && event.category !== state.timelineFilters.category) {
      return false;
    }
    if (state.timelineFilters.tone !== "all" && event.tone !== state.timelineFilters.tone) {
      return false;
    }
    return true;
  });
}
function groupTimelineEventsByDate(events = []) {
  const groups = [];
  const bucket = /* @__PURE__ */ new Map();
  events.forEach((event) => {
    const key = formatDateOnly(event.occurred_at);
    if (!bucket.has(key)) {
      bucket.set(key, []);
      groups.push({ date: key, events: bucket.get(key) });
    }
    bucket.get(key).push(event);
  });
  return groups;
}
function timelinePayloadEntries(payload = {}) {
  const labelMap = {
    mode: "记录模式",
    mood_score: "情绪分",
    interaction_freq: "互动频率",
    deep_conversation: "深聊",
    task_completed: "任务完成",
    report_type: "报告类型",
    health_score: "健康分",
    level: "风险等级",
    previous_level: "上一等级",
    reason: "原因",
    task_count: "任务数",
    intensity: "任务强度",
    momentum: "当前动量",
    category: "任务类别",
    title: "标题",
    usefulness_score: "有用度",
    friction_score: "摩擦感",
    plan_type: "计划类型",
    transition_type: "迁移类型",
    trigger_type: "触发类型",
    to_branch: "目标分支",
    to_day: "推进到",
    risk_level: "预演风险",
    alignment_score: "对齐分",
    verdict: "评估结论",
    recommendation_label: "系统建议"
  };
  return Object.entries(payload).filter(([, value]) => value !== null && value !== void 0 && value !== "").filter(([, value]) => !Array.isArray(value) && typeof value !== "object").slice(0, 8).map(([key, value]) => ({
    key,
    label: labelMap[key] || key.replace(/_/g, " "),
    value: String(value)
  }));
}
function timelineEvidenceReason(event, snapshot = {}) {
  var _a, _b;
  const scorecard = snapshot.scorecard || {};
  const playbook = snapshot.playbook || {};
  const schedule = snapshot.schedule || {};
  const payload = (event == null ? void 0 : event.payload) || {};
  switch (event == null ? void 0 : event.category) {
    case "risk":
      return payload.reason || playbook.branch_reason || "风险类节点会直接影响系统后续是继续推进、减压还是进入修复分支。";
    case "action":
      return schedule.selection_reason || ((_a = scorecard.next_actions) == null ? void 0 : _a[0]) || "行动类节点会回流到效果闭环，影响下一轮任务强度和表达方式。";
    case "playbook":
      return playbook.branch_reason || "剧本迁移说明系统已经基于最近的证据调整了这段关系的推进路径。";
    case "strategy":
      return ((_b = schedule.current_stage) == null ? void 0 : _b.summary) || "策略类节点会影响系统如何安排观察期、检查点和下一轮切换。";
    case "coach":
    case "alignment":
      return "这类节点代表系统已经开始直接参与“事前理解”和“沟通准备”。";
    default:
      return scorecard.primary_goal || "这个节点会被沉淀进时间轴，和其它事件一起决定系统的后续判断。";
  }
}
function renderTimelineEvidenceDrawer(event, snapshot = {}) {
  var _a, _b;
  if (!event) {
    return `
            <article class="timeline-evidence timeline-evidence--empty">
                <p class="panel__eyebrow">证据抽屉</p>
                <h4>点开左侧任一节点</h4>
                <p>这里会解释这个节点为什么出现、它和当前剧本/策略有什么关系，以及系统接下来会参考什么。</p>
            </article>
        `;
  }
  const entries = timelinePayloadEntries(event.payload || {});
  const reportContent = ((_a = snapshot.latestReport) == null ? void 0 : _a.content) || {};
  const playbook = snapshot.playbook || {};
  const scorecard = snapshot.scorecard || {};
  const schedule = snapshot.schedule || {};
  const nextHint = schedule.selection_reason || ((_b = scorecard.next_actions) == null ? void 0 : _b[0]) || reportContent.suggestion || playbook.branch_reason || "继续积累更多真实记录，让系统更稳地判断下一步。";
  return `
        <article class="timeline-evidence timeline-evidence--${escapeHtml(event.tone || "neutral")}">
            <div class="timeline-evidence__top">
                <div>
                    <p class="panel__eyebrow">证据抽屉</p>
                    <h4>${escapeHtml(event.label || "选中节点")}</h4>
                </div>
                <span class="pill">${escapeHtml(event.category_label || "节点")}</span>
            </div>
            <p class="timeline-evidence__summary">${escapeHtml(event.summary || "系统记录了一次变化。")}</p>
            ${event.detail ? `<p class="timeline-evidence__detail">${escapeHtml(event.detail)}</p>` : ""}
            <div class="timeline-evidence__meta">
                <span>${escapeHtml(formatDate(event.occurred_at))}</span>
                <span>${escapeHtml(event.tone_label || "持续记录")}</span>
                ${event.entity_type ? `<span>${escapeHtml(event.entity_type)}</span>` : ""}
            </div>
            ${entries.length ? `
                <div class="timeline-evidence__grid">
                    ${entries.map((item) => `
                        <article class="timeline-evidence__cell">
                            <span>${escapeHtml(item.label)}</span>
                            <strong>${escapeHtml(item.value)}</strong>
                        </article>
                    `).join("")}
                </div>
            ` : ""}
            <div class="timeline-evidence__note">
                <span>系统为什么记住它</span>
                <p>${escapeHtml(timelineEvidenceReason(event, snapshot))}</p>
            </div>
            <div class="timeline-evidence__note timeline-evidence__note--soft">
                <span>它会影响什么</span>
                <p>${escapeHtml(nextHint)}</p>
            </div>
            ${(event.tags || []).length ? `<div class="relationship-timeline__tags">${(event.tags || []).map((tag) => `<span class="relationship-timeline__tag">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
        </article>
    `;
}
function renderTimelineBranchOverlay(snapshot = {}) {
  var _a, _b;
  const playbook = snapshot.playbook || null;
  const scorecard = snapshot.scorecard || null;
  const schedule = snapshot.schedule || null;
  const policyAudit = snapshot.policyAudit || null;
  const latestReport = snapshot.latestReport || null;
  const latestTransition = (playbook == null ? void 0 : playbook.latest_transition) || null;
  const currentStage = (schedule == null ? void 0 : schedule.current_stage) || null;
  const focusText = (playbook == null ? void 0 : playbook.branch_reason) || (currentStage == null ? void 0 : currentStage.summary) || (scorecard == null ? void 0 : scorecard.primary_goal) || "系统还在根据最近的记录和反馈观察这条关系接下来更适合怎么推进。";
  const reportContent = (latestReport == null ? void 0 : latestReport.content) || {};
  const latestInsight = reportContent.insight || reportContent.executive_summary || reportContent.self_insight || reportContent.trend_description || "";
  return `
        <div class="timeline-branch-panel">
            <article class="timeline-branch-panel__hero">
                <p class="panel__eyebrow">分支视图</p>
                <h4>${escapeHtml((playbook == null ? void 0 : playbook.active_branch_label) || (currentStage == null ? void 0 : currentStage.phase_label) || "观察中")}</h4>
                <p>${escapeHtml(focusText)}</p>
                <div class="timeline-branch-panel__meta">
                    ${(playbook == null ? void 0 : playbook.current_day) ? `<span class="pill">第 ${escapeHtml(playbook.current_day)}/${escapeHtml(playbook.total_days || 7)} 天</span>` : ""}
                    ${(playbook == null ? void 0 : playbook.transition_count) ? `<span class="pill">已迁移 ${escapeHtml(playbook.transition_count)} 次</span>` : ""}
                    ${(currentStage == null ? void 0 : currentStage.checkpoint_date) ? `<span class="pill">检查点 ${escapeHtml(formatDateOnly(currentStage.checkpoint_date))}</span>` : ""}
                    ${(scorecard == null ? void 0 : scorecard.momentum) ? `<span class="pill">${escapeHtml(planMomentumLabel(scorecard.momentum))}</span>` : ""}
                </div>
                <div class="timeline-branch-panel__actions">
                    ${snapshot.isSolo ? '<button class="button button--ghost" type="button" onclick="openMethodologyExplainer()">判断说明</button>' : '<button class="button button--secondary" type="button" onclick="openMessageSimulator()">聊天前预演</button><button class="button button--ghost" type="button" onclick="openNarrativeAlignment()">双视角对齐</button>'}
                </div>
            </article>
            <article class="timeline-note-card">
                <p class="panel__eyebrow">最近切换</p>
                <h4>${escapeHtml((latestTransition == null ? void 0 : latestTransition.label) || (latestTransition == null ? void 0 : latestTransition.to_branch_label) || "最近一次分支变化")}</h4>
                <p>${escapeHtml((latestTransition == null ? void 0 : latestTransition.trigger_summary) || latestInsight || "最近没有明显分支切换，系统仍在按当前节奏推进。")}</p>
                <div class="stack-item__meta">${escapeHtml((latestTransition == null ? void 0 : latestTransition.created_at) ? formatDate(latestTransition.created_at) : "持续观察中")}</div>
            </article>
            <article class="timeline-note-card timeline-note-card--soft">
                <p class="panel__eyebrow">当前策略</p>
                <h4>${escapeHtml(((_a = schedule == null ? void 0 : schedule.current_policy) == null ? void 0 : _a.title) || "当前策略")}</h4>
                <p>${escapeHtml((schedule == null ? void 0 : schedule.selection_reason) || ((_b = scorecard == null ? void 0 : scorecard.next_actions) == null ? void 0 : _b[0]) || "系统会根据时间轴里持续出现的信号微调策略。")}</p>
            </article>
        </div>
    `;
}
function renderTimelineWorkspace(snapshot = {}) {
  var _a, _b;
  const timeline = snapshot.timeline || {};
  const events = Array.isArray(timeline.events) ? timeline.events : [];
  const filters = getTimelineFilterSets(events);
  if (!filters.categories.some((item) => item.value === state.timelineFilters.category)) {
    state.timelineFilters.category = "all";
  }
  if (!filters.tones.some((item) => item.value === state.timelineFilters.tone)) {
    state.timelineFilters.tone = "all";
  }
  const filteredEvents = getFilteredTimelineEvents(events);
  if (!filteredEvents.some((item) => String(item.id) === String(state.timelineSelectedEventId))) {
    state.timelineSelectedEventId = ((_a = filteredEvents[0]) == null ? void 0 : _a.id) || null;
  }
  const selectedEvent = filteredEvents.find((item) => String(item.id) === String(state.timelineSelectedEventId)) || null;
  const groups = groupTimelineEventsByDate(filteredEvents);
  const latestEventAt = timeline.latest_event_at ? formatDate(timeline.latest_event_at) : "刚刚";
  const playbook = snapshot.playbook || null;
  const scorecard = snapshot.scorecard || null;
  const reportContent = ((_b = snapshot.latestReport) == null ? void 0 : _b.content) || {};
  const intro = reportContent.insight || reportContent.executive_summary || (scorecard == null ? void 0 : scorecard.primary_goal) || "把这段关系最近发生的重要变化按顺序铺开，才能看清系统为什么做出这些判断。";
  return `
        <section class="timeline-stage">
            <div class="timeline-stage__hero">
                <div class="timeline-stage__headline">
            <p class="eyebrow">${snapshot.isSolo ? "个人时间线" : "关系时间线"}</p>
                    <h4>从记录到分支切换的完整轨道</h4>
                    <p>${escapeHtml(intro)}</p>
                </div>
                <div class="timeline-stage__stats">
                    <article class="timeline-stage__stat">
                        <span>时间轴节点</span>
                        <strong>${escapeHtml(String(filteredEvents.length))}</strong>
                        <p>当前筛选结果 / 总计 ${escapeHtml(String(events.length))}</p>
                    </article>
                    <article class="timeline-stage__stat">
                        <span>当前路径</span>
                        <strong>${escapeHtml((playbook == null ? void 0 : playbook.active_branch_label) || "观察中")}</strong>
                        <p>${escapeHtml((playbook == null ? void 0 : playbook.branch_reason) || "系统正在根据最近的事件调整节奏。")}</p>
                    </article>
                    <article class="timeline-stage__stat">
                        <span>当前动量</span>
                        <strong>${escapeHtml((scorecard == null ? void 0 : scorecard.momentum) ? planMomentumLabel(scorecard.momentum) : "持续观察")}</strong>
                        <p>${escapeHtml((scorecard == null ? void 0 : scorecard.risk_now) ? `风险 ${crisisLabel(scorecard.risk_now)}` : "最近更新 " + latestEventAt)}</p>
                    </article>
                </div>
            </div>
            <div class="timeline-stage__controls">
                <label class="field timeline-stage__filter">
                    <span>筛选类别</span>
                    <select id="timeline-filter-category" class="input">
                        ${filters.categories.map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === state.timelineFilters.category ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}
                    </select>
                </label>
                <label class="field timeline-stage__filter">
                    <span>筛选语气</span>
                    <select id="timeline-filter-tone" class="input">
                        ${filters.tones.map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === state.timelineFilters.tone ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}
                    </select>
                </label>
                <div class="timeline-stage__filter-summary">
                    <span class="pill">最近更新 ${escapeHtml(latestEventAt)}</span>
                    <button id="timeline-clear-filters" class="button button--ghost" type="button">清空筛选</button>
                </div>
            </div>
            <div class="timeline-stage__grid">
                <div class="timeline-stage__stream">
                    ${groups.length ? groups.map((group) => `
                        <section class="timeline-stage__day">
                            <div class="timeline-stage__day-label">
                                <span>${escapeHtml(group.date)}</span>
                            </div>
                            <div class="relationship-timeline__list">
                                ${group.events.map((item) => `
                                    <button class="relationship-timeline__item relationship-timeline__item--${escapeHtml(item.tone || "neutral")} ${String(item.id) === String(state.timelineSelectedEventId) ? "relationship-timeline__item--selected" : ""}" type="button" data-timeline-event-id="${escapeHtml(String(item.id))}">
                                        <div class="relationship-timeline__rail">
                                            <span class="relationship-timeline__dot"></span>
                                        </div>
                                        <div class="relationship-timeline__content">
                                            <div class="relationship-timeline__meta">
                                                <span class="pill">${escapeHtml(item.category_label || "节点")}</span>
                                                <span>${escapeHtml(item.tone_label || "持续记录")}</span>
                                                <span>${escapeHtml(formatDate(item.occurred_at))}</span>
                                            </div>
                                            <h4>${escapeHtml(item.label || item.summary || "最近有新的变化")}</h4>
                                            <p>${escapeHtml(item.summary || "系统记录了一次新的状态变化。")}</p>
                                            ${item.detail ? `<p class="relationship-timeline__detail">${escapeHtml(item.detail)}</p>` : ""}
                                            ${(item.tags || []).length ? `<div class="relationship-timeline__tags">${(item.tags || []).map((tag) => `<span class="relationship-timeline__tag">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
                                        </div>
                                    </button>
                                `).join("")}
                            </div>
                        </section>
                    `).join("") : '<div class="empty-state">当前筛选条件下还没有事件，换个筛选器试试。</div>'}
                </div>
                <aside class="timeline-stage__aside">
                    ${renderTimelineBranchOverlay(snapshot)}
                    ${renderTimelineEvidenceDrawer(selectedEvent, snapshot)}
                </aside>
            </div>
        </section>
    `;
}
function bindTimelinePageControls() {
  var _a, _b, _c;
  (_a = $("#timeline-filter-category")) == null ? void 0 : _a.addEventListener("change", (event) => {
    state.timelineFilters.category = event.target.value;
    rerenderTimelinePage();
  });
  (_b = $("#timeline-filter-tone")) == null ? void 0 : _b.addEventListener("change", (event) => {
    state.timelineFilters.tone = event.target.value;
    rerenderTimelinePage();
  });
  (_c = $("#timeline-clear-filters")) == null ? void 0 : _c.addEventListener("click", () => {
    state.timelineFilters = { category: "all", tone: "all" };
    rerenderTimelinePage();
  });
  $$("[data-timeline-event-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.timelineSelectedEventId = button.dataset.timelineEventId;
      rerenderTimelinePage();
    });
  });
}
function rerenderTimelinePage() {
  const shell = $("#timeline-main");
  if (!shell)
    return;
  shell.innerHTML = renderTimelineWorkspace(state.timelinePageSnapshot || {});
  bindTimelinePageControls();
}
async function loadTimelinePage() {
  var _a, _b, _c, _d;
  if (!api.isLoggedIn()) {
    safeSetHtml("#timeline-main", '<div class="empty-state">请先登录后再查看关系时间轴。</div>');
    return;
  }
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const isSolo = !pairId;
  const reportType = isSolo ? "daily" : state.selectedReportType;
  safeSetHtml("#timeline-main", `
        <section class="timeline-stage timeline-stage--loading">
            <div class="empty-state">正在整理最近这段时间的事件轨道、分支迁移和策略线索，请稍候。</div>
        </section>
    `);
  const [timelineResult, playbookResult, scorecardResult, scheduleResult, policyAuditResult, reportResult] = await Promise.allSettled([
    api.getRelationshipTimeline(pairId, 36),
    api.getRelationshipPlaybook(pairId),
    api.getInterventionScorecard(pairId),
    api.getPolicySchedule(pairId),
    api.getPolicyDecisionAudit(pairId),
    api.getLatestReport(pairId, reportType)
  ]);
  state.timelinePageSnapshot = {
    isSolo,
    timeline: unwrapResult(timelineResult, { event_count: 0, latest_event_at: null, events: [], highlights: [] }),
    playbook: unwrapResult(playbookResult, null),
    scorecard: unwrapResult(scorecardResult, null),
    schedule: unwrapResult(scheduleResult, null),
    policyAudit: unwrapResult(policyAuditResult, null),
    latestReport: unwrapResult(reportResult, null)
  };
  state.timelineSelectedEventId = ((_d = (_c = (_b = state.timelinePageSnapshot.timeline) == null ? void 0 : _b.events) == null ? void 0 : _c[0]) == null ? void 0 : _d.id) || null;
  rerenderTimelinePage();
}
async function openRelationshipTimeline() {
  var _a, _b, _c;
  const isSolo = Boolean(((_a = state.reportSnapshot) == null ? void 0 : _a.isSolo) || !state.currentPair);
  if (isSolo) {
    if (!ensureLoginContext("请先登录")) {
      return;
    }
  } else if (!ensurePairContext("请先进入一段已激活的关系")) {
    return;
  }
  openModal(`
        <h3>${isSolo ? "个人时间轴回放" : "关系时间轴回放"}</h3>
        <p class="muted-copy">正在把最近的记录、风险、任务和策略变化串成一条完整叙事，请稍候。</p>
        <div class="empty-state">正在加载时间轴...</div>
    `);
  try {
    const cached = ((_b = state.reportSnapshot) == null ? void 0 : _b.timeline) || state.lastRelationshipTimeline;
    const payload = cached || await api.getRelationshipTimeline(((_c = state.currentPair) == null ? void 0 : _c.id) || null, 28);
    state.lastRelationshipTimeline = payload;
    if (state.reportSnapshot) {
      state.reportSnapshot.timeline = payload;
    }
    openModal(`
            <h3>${isSolo ? "个人时间轴回放" : "关系时间轴回放"}</h3>
            ${renderRelationshipTimelinePanel(payload, { solo: isSolo })}
        `);
  } catch (error) {
    openModal(`
            <h3>${isSolo ? "个人时间轴回放" : "关系时间轴回放"}</h3>
            <div class="empty-state">${escapeHtml(error.message || "暂时无法读取时间轴，请稍后重试。")}</div>
            <div class="hero-actions">
                <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
            </div>
        `);
  }
}
async function openNarrativeAlignment() {
  var _a, _b;
  if (!ensurePairContext("请先进入一段已激活的关系")) {
    return;
  }
  state.lastNarrativeAlignment = null;
  const partnerName = getPartnerDisplayName(state.currentPair);
  const reportContent = ((_b = (_a = state.reportSnapshot) == null ? void 0 : _a.latestReport) == null ? void 0 : _b.content) || {};
  const alignmentHint = reportContent.suggestion || reportContent.trend_description || reportContent.professional_note || "";
  openModal(`
        <h3>双方叙事对齐</h3>
        <p class="muted-copy">正在整理你和 ${escapeHtml(partnerName)} 最近同一阶段的记录，看看双方其实在经历什么、哪里最容易错位、以及更适合怎样开口。</p>
        ${alignmentHint ? `<div class="hero-card hero-card--accent"><strong>结合当前简报最该先对齐的一点</strong><p>${escapeHtml(alignmentHint)}</p></div>` : ""}
        <div class="empty-state">正在生成双视角对齐结果，请稍候。</div>
    `);
  try {
    const payload = await api.getLatestNarrativeAlignment(state.currentPair.id);
    state.lastNarrativeAlignment = payload;
    openModal(`
            <h3>双方叙事对齐</h3>
            <p class="muted-copy">${escapeHtml(payload.checkin_date || "")} 的双方记录已经整理成一份可直接拿来沟通的共同版本。</p>
            ${renderNarrativeAlignmentResult(payload)}
        `);
  } catch (error) {
    openModal(`
            <h3>双方叙事对齐</h3>
            <div class="empty-state">${escapeHtml(error.message || "暂时无法生成双视角对齐，请稍后重试。")}</div>
            <div class="hero-actions">
                <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
            </div>
        `);
  }
}
function openMessageSimulator() {
  var _a, _b;
  if (!ensurePairContext("请先进入一段已激活的关系")) {
    return;
  }
  state.lastMessageSimulation = null;
  const partnerName = getPartnerDisplayName(state.currentPair);
  const reportContent = ((_b = (_a = state.reportSnapshot) == null ? void 0 : _a.latestReport) == null ? void 0 : _b.content) || {};
  const hint = reportContent.suggestion || reportContent.trend_description || reportContent.professional_note || "";
  const playbookCard = getContextualPlaybookCard();
  openModal(`
        <h3>聊天前预演</h3>
        <p class="muted-copy">在发给 ${escapeHtml(partnerName)} 之前，先看看这句话更可能被怎样接住。它不会替你说话，但能帮你把误读和升级风险降下来。</p>
        ${hint ? `<div class="hero-card hero-card--accent"><strong>结合当前简报的提醒</strong><p>${escapeHtml(hint)}</p></div>` : ""}
        <label class="field">
            <span>准备发送的话</span>
            <textarea id="message-simulator-input" class="input input--textarea simulation-textarea" placeholder="例如：你今天怎么又这么晚才回我，我真的很烦。"></textarea>
        </label>
        <div class="hero-actions">
            <button id="message-simulator-run" class="button button--primary" type="button" onclick="runMessageSimulation()">开始预演</button>
            <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
        </div>
        ${renderContestModalReturn("openNarrativeAlignment()", "下一步看双视角对齐")}
        <div id="message-simulator-result" class="simulation-result-wrap">
            <div class="empty-state">输入一句你准备发的话，系统会结合最近的关系状态给出一版更稳的表达建议。</div>
        </div>
        ${playbookCard}
    `);
}
async function runMessageSimulation() {
  if (!ensurePairContext("请先进入一段已激活的关系")) {
    return;
  }
  const input = $("#message-simulator-input");
  const draft = input == null ? void 0 : input.value.trim();
  if (!draft) {
    showToast("先输入一句准备发的话");
    return;
  }
  const button = $("#message-simulator-run");
  if (button) {
    button.disabled = true;
    button.textContent = "预演中...";
  }
  safeSetHtml("#message-simulator-result", '<div class="empty-state">正在结合你们最近的关系状态做预演，请稍候。</div>');
  try {
    const payload = await api.simulateRelationshipMessage(state.currentPair.id, draft);
    state.lastMessageSimulation = payload;
    safeSetHtml("#message-simulator-result", renderMessageSimulationResult(payload));
  } catch (error) {
    safeSetHtml("#message-simulator-result", `<div class="empty-state">${escapeHtml(error.message || "预演失败，请稍后重试。")}</div>`);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "开始预演";
    }
  }
}
function useSimulationRewrite() {
  var _a;
  const rewrite = (_a = state.lastMessageSimulation) == null ? void 0 : _a.safer_rewrite;
  const input = $("#message-simulator-input");
  if (!rewrite || !input) {
    showToast("还没有可用的改写版本");
    return;
  }
  input.value = rewrite;
  showToast("已把更稳妥的版本放回输入框");
}
async function copySimulationRewrite() {
  var _a;
  const rewrite = (_a = state.lastMessageSimulation) == null ? void 0 : _a.safer_rewrite;
  if (!rewrite) {
    showToast("还没有可复制的改写版本");
    return;
  }
  try {
    await navigator.clipboard.writeText(rewrite);
    showToast("改写版本已复制");
  } catch (error) {
    showToast("复制失败，请手动选择文本");
  }
}
async function copyNarrativeOpening() {
  var _a;
  const opening = (_a = state.lastNarrativeAlignment) == null ? void 0 : _a.suggested_opening;
  if (!opening) {
    showToast("还没有可复制的开场白");
    return;
  }
  try {
    await navigator.clipboard.writeText(opening);
    showToast("已复制更适合开口的版本");
  } catch (error) {
    showToast("复制失败，请手动选择文本");
  }
}
function renderRepairProtocol(protocol) {
  if (!protocol) {
    return '<div class="empty-state">当前还没有可展示的修复协议。</div>';
  }
  const focusTags = Array.isArray(protocol.focus_tags) ? protocol.focus_tags : [];
  return `
        <section class="repair-protocol">
            <div class="repair-protocol__top">
                <div>
                    <p class="panel__eyebrow">REPAIR PROTOCOL</p>
                    <h4>${escapeHtml(protocol.title || "修复协议")}</h4>
                </div>
                <span class="pill">${escapeHtml(crisisLabel(protocol.level || "none"))}</span>
            </div>
            <p class="panel-note">${escapeHtml(protocol.summary || "系统已经为当前阶段生成一组修复步骤。")}</p>
            <div class="repair-protocol__meta">
                ${protocol.timing_hint ? `<span class="pill">${escapeHtml(protocol.timing_hint)}</span>` : ""}
                ${protocol.active_plan_type ? `<span class="pill">${escapeHtml(protocol.active_plan_type)}</span>` : ""}
                ${focusTags.map((tag) => `<span class="pill">${escapeHtml(tag)}</span>`).join("")}
            </div>
            <div class="stack-list">
                ${(protocol.steps || []).map((step) => `
                    <article class="stack-item stack-item--static">
                        <div class="protocol-step__index">${step.sequence}</div>
                        <div class="stack-item__content">
                            <strong>${escapeHtml(step.title)}</strong>
                            <div class="stack-item__meta">${escapeHtml(step.action || "")}</div>
                            ${step.why ? `<div class="stack-item__meta">为什么：${escapeHtml(step.why)}</div>` : ""}
                            ${step.duration_hint ? `<div class="stack-item__meta">建议时长：${escapeHtml(step.duration_hint)}</div>` : ""}
                        </div>
                    </article>
                `).join("")}
            </div>
            <div class="repair-protocol__grid">
                <div class="panel">
        <div class="panel__header"><div><p class="panel__eyebrow">避免</p><h4>这时候别做</h4></div></div>
                    ${renderBulletList(protocol.do_not || [], "先避免让局面继续升级。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">SUCCESS</p><h4>算是往前走的信号</h4></div></div>
                    <p class="panel-note">${escapeHtml(protocol.success_signal || "只要双方停止升级，就已经是第一步进展。")}</p>
                </div>
            </div>
            ${protocol.escalation_rule ? `<div class="hero-card hero-card--accent"><strong>什么时候升级求助</strong><p>${escapeHtml(protocol.escalation_rule)}</p></div>` : ""}
            ${renderTheoryBasis(protocol.theory_basis || [], {
    title: "这份修复协议的理论依据",
    note: protocol.clinical_disclaimer || ""
  })}
        </section>
    `;
}
async function generateReport() {
  var _a;
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const isSolo = !pairId;
  const reportType = isSolo ? "daily" : state.selectedReportType;
  if (isSolo && reportType !== "daily") {
    showToast("单人模式目前只支持个人简报");
    return;
  }
  const button = $("#report-generate-btn");
  if (button) {
    button.disabled = true;
    button.textContent = "生成中...";
  }
  try {
    if (reportType === "daily") {
      await api.generateDailyReport(pairId);
    } else if (reportType === "weekly") {
      await api.generateWeeklyReport(pairId);
    } else {
      await api.generateMonthlyReport(pairId);
    }
    if (button)
      button.textContent = "等待结果...";
    showToast(`已开始生成${formatReportType(reportType, { solo: isSolo })}`);
    const report = await api.waitForReport(pairId, reportType);
    await loadReportPage();
    if ((report == null ? void 0 : report.status) === "completed") {
      showToast(`${formatReportType(reportType, { solo: isSolo })}已生成完成`);
    } else if ((report == null ? void 0 : report.status) === "failed") {
      showToast(`${formatReportType(reportType, { solo: isSolo })}生成失败，请稍后重试`);
    } else {
      showToast(`${formatReportType(reportType, { solo: isSolo })}仍在后台生成，可稍后刷新查看`);
    }
  } catch (error) {
    showToast(error.message || "生成失败");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = isSolo ? "生成个人简报" : "生成当前简报";
    }
  }
}
function getSoloReportButtonState(todayStatus = {}, latestReport = null) {
  if (!(todayStatus == null ? void 0 : todayStatus.my_done)) {
    return { label: "先完成今日记录", disabled: false, tone: "idle" };
  }
  if ((latestReport == null ? void 0 : latestReport.status) === "pending") {
    return { label: "个人简报生成中...", disabled: true, tone: "pending" };
  }
  if ((todayStatus == null ? void 0 : todayStatus.has_report) && (latestReport == null ? void 0 : latestReport.status) === "completed") {
    return { label: "今日简报已就绪", disabled: true, tone: "ready" };
  }
  return { label: "生成个人简报", disabled: false, tone: "action" };
}
function renderNoPairHome(payload = {}) {
  var _a;
  const todayStatus = payload.todayStatus || {};
  const myCheckin = todayStatus.my_checkin || {};
  const latestReport = payload.latestReport || null;
  const latestContent = (latestReport == null ? void 0 : latestReport.content) || {};
  const streakDays = ((_a = payload.streak) == null ? void 0 : _a.streak) || 0;
  const reportState = getSoloReportButtonState(todayStatus, latestReport);
  const hasCheckin = Boolean(todayStatus == null ? void 0 : todayStatus.my_done);
  const hasReadyReport = reportState.tone === "ready";
  const latestInsight = latestContent.insight || latestContent.self_insight || latestContent.encouragement || "";
  const latestSuggestion = latestContent.suggestion || latestContent.self_care_tip || "";
  const latestScore = latestContent.health_score || null;
  const moodText = myCheckin.mood_score ? `${myCheckin.mood_score}/4` : hasCheckin ? "已记录" : "还未记录";
  const interactionText = myCheckin.interaction_freq || myCheckin.interaction_freq === 0 ? `${myCheckin.interaction_freq} 次` : "自由模式";
  const deepTalkText = myCheckin.deep_conversation === true ? "有" : myCheckin.deep_conversation === false ? "没有" : "未记录";
  const heroTitle = hasReadyReport ? "你已经把今天照顾成一份可以回看的简报" : hasCheckin ? "今天已经被认真记住了" : "先照顾今天的自己，也是在照顾关系的未来";
  const heroDescription = hasReadyReport ? "个人记录、系统整理和下一步建议都已经准备好。现在的体验更像一本温柔的关系日记，而不是冷冰冰的数据页。" : hasCheckin ? "你已经完成了今天的个人记录。关系的改变，往往从先把自己的真实感受说清楚开始。" : "没绑定关系也没关系。你可以先写个人记录、用智能陪伴整理情绪，等准备好了再把对方邀请进来。";
  const primaryAction = hasCheckin ? "showPage('report')" : "openCheckinMode('form')";
  const primaryLabel = hasCheckin ? "去看个人简报" : "写一条今日记录";
  const secondaryAction = hasReadyReport ? "showPage('pair')" : "openCheckinMode('voice')";
  const secondaryLabel = hasReadyReport ? "现在去绑定关系" : "让系统陪你聊";
  const reportPanelContent = hasReadyReport ? `
            <div class="report-preview">
              <div class="report-preview__score">${latestScore != null ? latestScore : "--"}</div>
              <div>
                <strong>今天的个人简报已经准备好了</strong>
                <p>${escapeHtml(latestInsight || "你今天留下的内容，已经被整理成一份更像日记的简报。")}</p>
              </div>
            </div>
            ${latestSuggestion ? `<p class="panel-note">${escapeHtml(latestSuggestion)}</p>` : ""}
        ` : reportState.tone === "pending" ? `<p class="panel-note">个人简报正在生成中。稍等一会儿回来，它会比“即时结果”更像一份真正可读的情绪编辑稿。</p>` : hasCheckin ? `<p class="panel-note">今天的记录已经保存。如果你还没看到简报，大概率只是系统还在整理，很快就会出现在这里。</p>` : `<p class="panel-note">当你完成今天的个人记录后，这里会变成一张更柔和、更像日记的情绪简报入口。</p>`;
  state.homeSnapshot = {
    solo: true,
    todayStatus,
    streak: payload.streak || {},
    latestReport,
    notifications: Array.isArray(payload.notifications) ? payload.notifications : []
  };
  safeSetHtml("#home-overview", `
        <div class="home-hero">
          <div class="home-hero__copy">
            <p class="eyebrow">单人模式</p>
            <h3>${heroTitle}</h3>
            <p>${heroDescription}</p>
          </div>
          <div class="home-hero__badge">
            <span>当前模式</span>
            <strong>单人体验</strong>
          </div>
        </div>
        <div class="context-pills">
          <span class="context-chip">${hasCheckin ? "今日记录已完成" : "今天还没开始"}</span>
          <span class="context-chip">${hasReadyReport ? "个人简报已就绪" : reportState.tone === "pending" ? "个人简报生成中" : "随时开始单人体验"}</span>
          <span class="context-chip">${streakDays ? `${streakDays} 天连续记录` : "先养成一点自己的节奏"}</span>
        </div>
        <div class="hero-actions">
          <button class="button button--primary" type="button" onclick="${primaryAction}">${primaryLabel}</button>
          <button class="button button--ghost" type="button" onclick="${secondaryAction}">${secondaryLabel}</button>
        </div>
    `);
  safeSetHtml("#home-metrics", [
    demoMetric("连续节奏", `${streakDays} 天`, streakDays ? "关系和情绪都更喜欢被连续地照顾。" : "从今天开始，也已经算一种节奏。"),
    demoMetric("今日状态", hasCheckin ? "已记录" : "待开始", hasCheckin ? "你已经替今天留下一点痕迹。" : "先把一句真实的话留在今天。"),
    demoMetric("个人简报", hasReadyReport ? "已生成" : reportState.tone === "pending" ? "生成中" : "未生成", hasReadyReport ? "它已经准备好被阅读。" : "简报会在记录之后自然出现。"),
    demoMetric("下一步", hasReadyReport ? "邀请对方" : hasCheckin ? "等待简报" : "开始记录", hasReadyReport ? "准备好了再把这段关系变成共同空间。" : "今天先照顾好自己。")
  ].join(""));
  safeSetHtml("#home-status-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">今日</p><h4>${hasCheckin ? "今天已经被你记住了" : "今天先照顾你自己"}</h4></div></div>
        <div class="pulse-grid">
          <article class="pulse-tile"><span>情绪</span><strong>${moodText}</strong><p>先看见自己，再决定怎么靠近别人。</p></article>
          <article class="pulse-tile"><span>互动</span><strong>${interactionText}</strong><p>没绑定关系，也能先记录自己的节奏。</p></article>
          <article class="pulse-tile"><span>深聊</span><strong>${deepTalkText}</strong><p>一句说清楚的话，常常比很多句表面交流更重要。</p></article>
          <article class="pulse-tile"><span>当前阶段</span><strong>${hasReadyReport ? "可读简报" : hasCheckin ? "等待整理" : "待开始"}</strong><p>${hasReadyReport ? "今天的状态已经被整理成简报。" : hasCheckin ? "系统正在把今天的内容变成一份更好读的回顾。" : "先写下一句真实感受。"}</p></article>
        </div>
        <div class="journal-quote">
          ${myCheckin.content ? escapeHtml(myCheckin.content) : "今天的记录还没落下。哪怕先写一句，也会让后面的简报更接近你自己。"}
        </div>
        <div class="hero-actions">
          <button class="button button--primary" type="button" onclick="${primaryAction}">${primaryLabel}</button>
          <button class="button button--secondary" type="button" onclick="openCheckinMode('voice')">让系统继续陪你聊</button>
        </div>
        ${renderClientLayerSummaryCard({ solo: true })}
    `);
  safeSetHtml("#home-report-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">简报</p><h4>${hasReadyReport ? "你的个人简报已经就绪" : "个人简报也值得被认真对待"}</h4></div></div>
        ${reportPanelContent}
        <div class="hero-actions">
          <button class="button button--ghost" type="button" onclick="${hasCheckin ? "showPage('report')" : "openCheckinMode('form')"}">${hasCheckin ? "进入个人简报页" : "先去完成记录"}</button>
        </div>
    `);
  safeSetHtml("#home-tree-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">TREE</p><h4>关系树会在绑定后开始生长</h4></div></div>
        <p class="panel-note">现在先把记录习惯养起来，等彼此进入同一个空间，成长值和里程碑会自然接上。</p>
    `);
  safeSetHtml("#home-crisis-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">支持</p><h4>这里不会拿风险词吓你</h4></div></div>
        <p class="panel-note">真正需要帮助时，系统会给出更温和的提醒与可执行的下一步，而不是制造焦虑。</p>
    `);
  safeSetHtml("#home-milestones-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">TIMELINE</p><h4>重要时刻以后都能被记住</h4></div></div>
        <p class="panel-note">纪念日、重要承诺、第一次和解，这些都值得成为关系时间线的一部分。</p>
    `);
  safeSetHtml("#home-tasks-panel", `
        <div class="panel__header"><div><p class="panel__eyebrow">RITUALS</p><h4>双人任务会在绑定后出现</h4></div></div>
        <p class="panel-note">现在先把今天的心情留住，等关系建立后，系统会开始生成更贴合你们的日常小动作。</p>
    `);
  state.notifications = Array.isArray(payload.notifications) ? payload.notifications : [];
  syncNotifications();
}
async function loadHomePage() {
  var _a;
  const pair = getPairSnapshot();
  const greetingName = ((_a = state.me) == null ? void 0 : _a.nickname) || "你";
  safeSetText("#home-greeting", `${greetingName}，欢迎进入关系总览`);
  renderPairSelect();
  if (isDemoMode()) {
    const demoPair = pair || deepClone((getDemoFixture("pairs") || [])[0] || null);
    if (!demoPair) {
      renderNoPairHome({
        todayStatus: deepClone(getDemoFixture("todayStatus") || {}),
        streak: deepClone(getDemoFixture("streak") || {}),
        latestReport: deepClone(getDemoFixture("latestReport") || null),
        notifications: deepClone(getDemoFixture("notifications") || [])
      });
      return;
    }
    renderHome({
      pair: demoPair,
      todayStatus: deepClone(getDemoFixture("todayStatus") || {}),
      streak: deepClone(getDemoFixture("streak") || {}),
      tree: deepClone(getDemoFixture("tree") || {}),
      crisis: deepClone(getDemoFixture("crisis") || {}),
      tasks: deepClone(getDemoFixture("tasks") || {}),
      playbook: deepClone(getDemoFixture("playbook") || null),
      notifications: deepClone(getDemoFixture("notifications") || []),
      milestones: deepClone(getDemoFixture("milestones") || []),
      timeline: deepClone(getDemoFixture("timeline") || { events: [], highlights: [] }),
      latestReport: deepClone(getDemoFixture("latestReport") || null)
    });
    return;
  }
  if (!pair) {
    const results2 = await Promise.allSettled([
      api.getTodayStatus(null),
      api.getCheckinStreak(null),
      api.getLatestReport(null, "daily"),
      api.getNotifications()
    ]);
    renderNoPairHome({
      todayStatus: unwrapResult(results2[0], {}),
      streak: unwrapResult(results2[1], {}),
      latestReport: unwrapResult(results2[2], null),
      notifications: unwrapResult(results2[3], [])
    });
    return;
  }
  const results = await Promise.allSettled([
    api.getTodayStatus(pair.id),
    api.getCheckinStreak(pair.id),
    api.getTreeStatus(pair.id),
    api.getCrisisStatus(pair.id),
    api.getDailyTasks(pair.id),
    api.getRelationshipPlaybook(pair.id),
    api.getNotifications(),
    api.getMilestones(pair.id),
    api.getLatestReport(pair.id, "daily"),
    api.getRelationshipTimeline(pair.id, 8)
  ]);
  const tasksResult = results[4];
  if (tasksResult.status === "rejected") {
    console.warn("Daily tasks request failed:", tasksResult.reason);
  }
  renderHome({
    pair,
    todayStatus: unwrapResult(results[0], {}),
    streak: unwrapResult(results[1], {}),
    tree: unwrapResult(results[2], {}),
    crisis: unwrapResult(results[3], {}),
    tasks: unwrapResult(results[4], {}),
    playbook: unwrapResult(results[5], null),
    notifications: unwrapResult(results[6], []),
    milestones: unwrapResult(results[7], []),
    latestReport: unwrapResult(results[8], null),
    timeline: unwrapResult(results[9], { event_count: 0, latest_event_at: null, events: [], highlights: [] })
  });
}
async function loadReportPage() {
  var _a;
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const isSolo = !pairId;
  if (isSolo && state.selectedReportType !== "daily") {
    state.selectedReportType = "daily";
  }
  syncReportTypeAvailability(isSolo);
  const reportType = isSolo ? "daily" : state.selectedReportType;
  const [latest, history, trend, today, scorecard, evaluation, experiment, policyRegistry, policySchedule, policyAudit, timeline] = await Promise.allSettled([
    api.getLatestReport(pairId, reportType),
    api.getReportHistory(pairId, reportType, 6),
    api.getHealthTrend(pairId, 14),
    api.getTodayStatus(pairId),
    api.getInterventionScorecard(pairId),
    api.getInterventionEvaluation(pairId),
    api.getInterventionExperiment(pairId),
    api.getPolicyRegistry(pairId),
    api.getPolicySchedule(pairId),
    api.getPolicyDecisionAudit(pairId),
    api.getRelationshipTimeline(pairId, 24)
  ]);
  const latestReport = unwrapResult(latest, null);
  const todayStatus = unwrapResult(today, {});
  const planScorecard = unwrapResult(scorecard, null);
  const planEvaluation = unwrapResult(evaluation, null);
  const planExperiment = unwrapResult(experiment, null);
  const planPolicyRegistry = unwrapResult(policyRegistry, null);
  const planPolicySchedule = unwrapResult(policySchedule, null);
  const planPolicyAudit = unwrapResult(policyAudit, null);
  const timelinePayload = unwrapResult(timeline, null);
  const button = $("#report-generate-btn");
  const soloButton = getSoloReportButtonState(todayStatus, latestReport);
  state.reportSnapshot = {
    isSolo,
    reportType,
    latestReport,
    todayStatus,
    planScorecard,
    planEvaluation,
    planExperiment,
    planPolicyRegistry,
    planPolicySchedule,
    planPolicyAudit,
    timeline: timelinePayload
  };
  state.lastRelationshipTimeline = timelinePayload || state.lastRelationshipTimeline;
  if (button) {
    button.textContent = isSolo ? soloButton.label : "生成当前简报";
    button.disabled = isSolo ? soloButton.disabled : false;
  }
  renderReport(
    latestReport,
    unwrapResult(history, []),
    unwrapResult(trend, { trend: [] }),
    {
      solo: isSolo,
      reportType,
      planScorecard,
      planEvaluation,
      planExperiment,
      planPolicyRegistry,
      planPolicySchedule,
      planPolicyAudit,
      timeline: timelinePayload
    }
  );
}
async function generateReport() {
  var _a, _b, _c, _d, _e, _f, _g;
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const isSolo = !pairId;
  const reportType = isSolo ? "daily" : state.selectedReportType;
  const snapshot = state.reportSnapshot || {};
  if (isSolo && reportType !== "daily") {
    showToast("单人模式目前只支持个人简报");
    return;
  }
  if (isSolo && !((_b = snapshot.todayStatus) == null ? void 0 : _b.my_done)) {
    showToast("先完成今日记录，再回来读个人简报");
    await showPage("checkin");
    return;
  }
  if (isSolo && ((_c = snapshot.latestReport) == null ? void 0 : _c.status) === "pending") {
    showToast("个人简报正在生成中，稍等一下就好");
    return;
  }
  if (isSolo && ((_d = snapshot.todayStatus) == null ? void 0 : _d.has_report) && ((_e = snapshot.latestReport) == null ? void 0 : _e.status) === "completed") {
    showToast("今天的个人简报已经准备好了");
    return;
  }
  const button = $("#report-generate-btn");
  if (button) {
    button.disabled = true;
    button.textContent = "生成中...";
  }
  try {
    if (reportType === "daily") {
      await api.generateDailyReport(pairId);
    } else if (reportType === "weekly") {
      await api.generateWeeklyReport(pairId);
    } else {
      await api.generateMonthlyReport(pairId);
    }
    if (button)
      button.textContent = "等待结果...";
    showToast(`已开始生成${formatReportType(reportType, { solo: isSolo })}`);
    const report = await api.waitForReport(pairId, reportType);
    await loadReportPage();
    if ((report == null ? void 0 : report.status) === "completed") {
      showToast(`${formatReportType(reportType, { solo: isSolo })}已生成完成`);
    } else if ((report == null ? void 0 : report.status) === "failed") {
      showToast(`${formatReportType(reportType, { solo: isSolo })}生成失败，请稍后重试`);
    } else {
      showToast(`${formatReportType(reportType, { solo: isSolo })}仍在后台生成，可稍后刷新查看`);
    }
  } catch (error) {
    showToast(error.message || "生成失败");
  } finally {
    if (button) {
      if (isSolo) {
        const soloButton = getSoloReportButtonState(
          ((_f = state.reportSnapshot) == null ? void 0 : _f.todayStatus) || snapshot.todayStatus || {},
          ((_g = state.reportSnapshot) == null ? void 0 : _g.latestReport) || snapshot.latestReport || null
        );
        button.disabled = soloButton.disabled;
        button.textContent = soloButton.label;
      } else {
        button.disabled = false;
        button.textContent = "生成当前简报";
      }
    }
  }
}
async function loadReportPage() {
  var _a;
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const isSolo = !pairId;
  if (isSolo && state.selectedReportType !== "daily") {
    state.selectedReportType = "daily";
  }
  syncReportTypeAvailability(isSolo);
  if (isDemoMode()) {
    renderReport(
      deepClone(getDemoFixture("latestReport") || null),
      deepClone(getDemoFixture("reportHistory") || []),
      deepClone(getDemoFixture("healthTrend") || { trend: [] }),
      {
        solo: false,
        reportType: "daily",
        planScorecard: deepClone(getDemoFixture("scorecard") || null),
        planEvaluation: null,
        planExperiment: null,
        planPolicyRegistry: null,
        planPolicySchedule: deepClone(getDemoFixture("policySchedule") || null),
        planPolicyAudit: deepClone(getDemoFixture("policyAudit") || null),
        timeline: deepClone(getDemoFixture("timeline") || null)
      }
    );
    return;
  }
  const reportType = isSolo ? "daily" : state.selectedReportType;
  const [latest, history, trend, today, scorecard, evaluation, experiment, policyRegistry, policySchedule, policyAudit, timeline] = await Promise.allSettled([
    api.getLatestReport(pairId, reportType),
    api.getReportHistory(pairId, reportType, 6),
    api.getHealthTrend(pairId, 14),
    api.getTodayStatus(pairId),
    api.getInterventionScorecard(pairId),
    api.getInterventionEvaluation(pairId),
    api.getInterventionExperiment(pairId),
    api.getPolicyRegistry(pairId),
    api.getPolicySchedule(pairId),
    api.getPolicyDecisionAudit(pairId),
    api.getRelationshipTimeline(pairId, 24)
  ]);
  const latestReport = unwrapResult(latest, null);
  const todayStatus = unwrapResult(today, {});
  const planScorecard = unwrapResult(scorecard, null);
  const planEvaluation = unwrapResult(evaluation, null);
  const planExperiment = unwrapResult(experiment, null);
  const planPolicyRegistry = unwrapResult(policyRegistry, null);
  const planPolicySchedule = unwrapResult(policySchedule, null);
  const planPolicyAudit = unwrapResult(policyAudit, null);
  const timelinePayload = unwrapResult(timeline, null);
  const button = $("#report-generate-btn");
  const soloButton = getSoloReportButtonState(todayStatus, latestReport);
  state.reportSnapshot = {
    isSolo,
    reportType,
    latestReport,
    todayStatus,
    planScorecard,
    planEvaluation,
    planExperiment,
    planPolicyRegistry,
    planPolicySchedule,
    planPolicyAudit,
    timeline: timelinePayload
  };
  state.lastRelationshipTimeline = timelinePayload || state.lastRelationshipTimeline;
  if (button) {
    button.textContent = isSolo ? soloButton.label : "生成当前简报";
    button.disabled = isSolo ? soloButton.disabled : false;
  }
  renderReport(
    latestReport,
    unwrapResult(history, []),
    unwrapResult(trend, { trend: [] }),
    {
      solo: isSolo,
      reportType,
      planScorecard,
      planEvaluation,
      planExperiment,
      planPolicyRegistry,
      planPolicySchedule,
      planPolicyAudit,
      timeline: timelinePayload
    }
  );
}
function renderTimelineEvidenceDrawer(event, snapshot = {}) {
  var _a, _b, _c;
  if (!event) {
    return `
            <article class="timeline-evidence timeline-evidence--empty">
                <p class="panel__eyebrow">证据抽屉</p>
                <h4>先在左侧选择一个节点</h4>
                <p>这里会说明这个节点为什么存在、它连接了哪些证据，以及它会怎样影响当前策略。</p>
            </article>
        `;
  }
  const eventId = String(event.id || "");
  const detailState = eventId ? state.timelineEventDetails[eventId] : null;
  const detail = detailState && !detailState.error ? detailState : null;
  const loadError = (detailState == null ? void 0 : detailState.error) || "";
  const loading = Boolean(eventId && state.timelineEventLoadingId === eventId);
  const eventView = (detail == null ? void 0 : detail.event) || event;
  const entries = ((_a = detail == null ? void 0 : detail.metrics) == null ? void 0 : _a.length) ? detail.metrics : timelinePayloadEntries(eventView.payload || {});
  const evidenceCards = Array.isArray(detail == null ? void 0 : detail.evidence_cards) ? detail.evidence_cards : [];
  const impactModules = Array.isArray(detail == null ? void 0 : detail.impact_modules) ? detail.impact_modules : [];
  const currentContext = (detail == null ? void 0 : detail.current_context) || null;
  const reportContent = ((_b = snapshot.latestReport) == null ? void 0 : _b.content) || {};
  const playbook = snapshot.playbook || {};
  const scorecard = snapshot.scorecard || {};
  const schedule = snapshot.schedule || {};
  const nextHint = (detail == null ? void 0 : detail.recommended_next_action) || (currentContext == null ? void 0 : currentContext.recommended_next_action) || schedule.selection_reason || ((_c = scorecard.next_actions) == null ? void 0 : _c[0]) || reportContent.suggestion || playbook.branch_reason || "继续补充更具体的信号，系统才能对下一步做出更稳的判断。";
  const summaryText = (detail == null ? void 0 : detail.event_summary) || eventView.summary || "系统在这里记录到一次有意义的状态变化。";
  const contextEntries = [
    { label: "当前计划", value: (currentContext == null ? void 0 : currentContext.active_plan_type) || null },
    { label: "当前路径", value: (currentContext == null ? void 0 : currentContext.active_branch_label) || null },
    { label: "当前节奏", value: (currentContext == null ? void 0 : currentContext.momentum) ? planMomentumLabel(currentContext.momentum) : null },
    { label: "当前风险", value: (currentContext == null ? void 0 : currentContext.risk_level) ? crisisLabel(currentContext.risk_level) : null }
  ].filter((item) => item.value);
  const latestInsight = (currentContext == null ? void 0 : currentContext.latest_report_insight) || reportContent.insight || reportContent.executive_summary || "";
  const detailCards = evidenceCards.length ? `
            <div class="timeline-evidence__cards">
                ${evidenceCards.map((card) => `
                    <article class="timeline-evidence__card timeline-evidence__card--${escapeHtml(card.tone || "neutral")}">
                        <span>${escapeHtml(card.title)}</span>
                        <p>${escapeHtml(card.body)}</p>
                    </article>
                `).join("")}
            </div>
        ` : "";
  const impactPanel = impactModules.length ? `
            <div class="timeline-evidence__note timeline-evidence__note--soft">
                <span>影响到的模块</span>
                <div class="relationship-timeline__tags">
                    ${impactModules.map((item) => `<span class="relationship-timeline__tag">${escapeHtml(item)}</span>`).join("")}
                </div>
            </div>
        ` : "";
  const contextPanel = currentContext && (contextEntries.length || latestInsight || nextHint) ? `
            <article class="timeline-evidence__context">
                <div class="timeline-evidence__context-top">
                    <span>当前状态背景</span>
                    ${currentContext.active_branch_label ? `<strong>${escapeHtml(currentContext.active_branch_label)}</strong>` : ""}
                </div>
                ${contextEntries.length ? `
                    <div class="timeline-evidence__grid timeline-evidence__grid--tight">
                        ${contextEntries.map((item) => `
                            <article class="timeline-evidence__cell">
                                <span>${escapeHtml(item.label)}</span>
                                <strong>${escapeHtml(item.value)}</strong>
                            </article>
                        `).join("")}
                    </div>
                ` : ""}
                ${latestInsight ? `
                    <div class="timeline-evidence__note timeline-evidence__note--soft">
                        <span>最新简报判断</span>
                        <p>${escapeHtml(latestInsight)}</p>
                    </div>
                ` : ""}
                <div class="timeline-evidence__note">
                    <span>这会带来什么变化</span>
                    <p>${escapeHtml(nextHint)}</p>
                </div>
            </article>
        ` : `
            <div class="timeline-evidence__note timeline-evidence__note--soft">
                <span>这会带来什么变化</span>
                <p>${escapeHtml(nextHint)}</p>
            </div>
        `;
  const loadingPanel = loading && !detail && !loadError ? `
            <div class="timeline-evidence__loading">
                <span class="pill">正在加载</span>
                <p>系统正在读取这个节点关联的指标、证据卡片和当前背景信息。</p>
            </div>
        ` : "";
  const errorPanel = loadError ? `
            <div class="timeline-evidence__note timeline-evidence__note--warning">
                <span>详情加载说明</span>
                <p>${escapeHtml(loadError)}</p>
            </div>
        ` : "";
  return `
        <article class="timeline-evidence timeline-evidence--${escapeHtml(eventView.tone || "neutral")} ${loading && !detail ? "timeline-evidence--loading" : ""}">
            <div class="timeline-evidence__top">
                <div>
                    <p class="panel__eyebrow">证据抽屉</p>
                    <h4>${escapeHtml(eventView.label || "当前节点")}</h4>
                </div>
                <span class="pill">${escapeHtml(eventView.category_label || "节点")}</span>
            </div>
            <p class="timeline-evidence__summary">${escapeHtml(summaryText)}</p>
            ${eventView.detail ? `<p class="timeline-evidence__detail">${escapeHtml(eventView.detail)}</p>` : ""}
            <div class="timeline-evidence__meta">
                <span>${escapeHtml(formatDate(eventView.occurred_at))}</span>
                <span>${escapeHtml(eventView.tone_label || "已记录信号")}</span>
                ${eventView.entity_type ? `<span>${escapeHtml(eventView.entity_type)}</span>` : ""}
            </div>
            ${loadingPanel}
            ${errorPanel}
            ${entries.length ? `
                <div class="timeline-evidence__grid">
                    ${entries.map((item) => `
                        <article class="timeline-evidence__cell">
                            <span>${escapeHtml(item.label)}</span>
                            <strong>${escapeHtml(item.value)}</strong>
                        </article>
                    `).join("")}
                </div>
            ` : ""}
            ${detailCards}
            ${impactPanel}
            <div class="timeline-evidence__note">
                <span>Why the system kept it</span>
                <p>${escapeHtml(timelineEvidenceReason(eventView, snapshot))}</p>
            </div>
            ${contextPanel}
            ${(eventView.tags || []).length ? `<div class="relationship-timeline__tags">${(eventView.tags || []).map((tag) => `<span class="relationship-timeline__tag">${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
        </article>
    `;
}
function bindTimelinePageControls() {
  var _a, _b, _c;
  (_a = $("#timeline-filter-category")) == null ? void 0 : _a.addEventListener("change", (event) => {
    state.timelineFilters.category = event.target.value;
    rerenderTimelinePage();
  });
  (_b = $("#timeline-filter-tone")) == null ? void 0 : _b.addEventListener("change", (event) => {
    state.timelineFilters.tone = event.target.value;
    rerenderTimelinePage();
  });
  (_c = $("#timeline-clear-filters")) == null ? void 0 : _c.addEventListener("click", () => {
    state.timelineFilters = { category: "all", tone: "all" };
    rerenderTimelinePage();
  });
  $$("[data-timeline-event-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.timelineSelectedEventId = button.dataset.timelineEventId;
      rerenderTimelinePage();
      void ensureTimelineEventDetail(button.dataset.timelineEventId);
    });
  });
}
async function ensureTimelineEventDetail(eventId) {
  const key = String(eventId || "").trim();
  if (!key || !api.isLoggedIn()) {
    return null;
  }
  if (state.timelineEventDetails[key] || state.timelineEventLoadingId === key) {
    return state.timelineEventDetails[key] || null;
  }
  state.timelineEventLoadingId = key;
  rerenderTimelinePage();
  try {
    const payload = await api.getRelationshipTimelineEventDetail(key);
    state.timelineEventDetails = {
      ...state.timelineEventDetails,
      [key]: payload
    };
    return payload;
  } catch (error) {
    state.timelineEventDetails = {
      ...state.timelineEventDetails,
      [key]: {
        error: error.message || "当前暂时无法加载这个节点的详细证据。"
      }
    };
    return null;
  } finally {
    if (state.timelineEventLoadingId === key) {
      state.timelineEventLoadingId = null;
    }
    rerenderTimelinePage();
  }
}
function rerenderTimelinePage() {
  const shell = $("#timeline-main");
  if (!shell)
    return;
  shell.innerHTML = renderTimelineWorkspace(state.timelinePageSnapshot || {});
  bindTimelinePageControls();
  if (state.timelineSelectedEventId) {
    void ensureTimelineEventDetail(state.timelineSelectedEventId);
  }
}
async function loadTimelinePage() {
  var _a, _b, _c, _d, _e, _f, _g;
  if (!api.isLoggedIn()) {
    safeSetHtml("#timeline-main", '<div class="empty-state">请先登录后再查看关系时间轴。</div>');
    return;
  }
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const isSolo = !pairId;
  const reportType = isSolo ? "daily" : state.selectedReportType;
  safeSetHtml("#timeline-main", `
        <section class="timeline-stage timeline-stage--loading">
            <div class="empty-state">正在整理最新事件流、分支切换和策略信号，请稍候。</div>
        </section>
    `);
  if (isDemoMode()) {
    state.timelinePageSnapshot = {
      isSolo: false,
      timeline: deepClone(getDemoFixture("timeline") || { event_count: 0, latest_event_at: null, events: [], highlights: [] }),
      playbook: deepClone(getDemoFixture("playbook") || null),
      scorecard: deepClone(getDemoFixture("scorecard") || null),
      schedule: deepClone(getDemoFixture("policySchedule") || null),
      policyAudit: deepClone(getDemoFixture("policyAudit") || null),
      latestReport: deepClone(getDemoFixture("latestReport") || null)
    };
    state.timelineSelectedEventId = ((_d = (_c = (_b = state.timelinePageSnapshot.timeline) == null ? void 0 : _b.events) == null ? void 0 : _c[0]) == null ? void 0 : _d.id) || null;
    state.timelineEventDetails = deepClone(getDemoFixture("timelineEventDetails") || {});
    state.timelineEventLoadingId = null;
    rerenderTimelinePage();
    return;
  }
  const [timelineResult, playbookResult, scorecardResult, scheduleResult, policyAuditResult, reportResult] = await Promise.allSettled([
    api.getRelationshipTimeline(pairId, 36),
    api.getRelationshipPlaybook(pairId),
    api.getInterventionScorecard(pairId),
    api.getPolicySchedule(pairId),
    api.getPolicyDecisionAudit(pairId),
    api.getLatestReport(pairId, reportType)
  ]);
  state.timelinePageSnapshot = {
    isSolo,
    timeline: unwrapResult(timelineResult, { event_count: 0, latest_event_at: null, events: [], highlights: [] }),
    playbook: unwrapResult(playbookResult, null),
    scorecard: unwrapResult(scorecardResult, null),
    schedule: unwrapResult(scheduleResult, null),
    policyAudit: unwrapResult(policyAuditResult, null),
    latestReport: unwrapResult(reportResult, null)
  };
  state.timelineSelectedEventId = ((_g = (_f = (_e = state.timelinePageSnapshot.timeline) == null ? void 0 : _e.events) == null ? void 0 : _f[0]) == null ? void 0 : _g.id) || null;
  state.timelineEventDetails = {};
  state.timelineEventLoadingId = null;
  rerenderTimelinePage();
}
function renderTimelineBranchOverlay(snapshot = {}) {
  var _a, _b;
  const playbook = snapshot.playbook || null;
  const scorecard = snapshot.scorecard || null;
  const schedule = snapshot.schedule || null;
  const policyAudit = snapshot.policyAudit || null;
  const latestReport = snapshot.latestReport || null;
  const latestTransition = (playbook == null ? void 0 : playbook.latest_transition) || null;
  const currentStage = (schedule == null ? void 0 : schedule.current_stage) || null;
  const focusText = (playbook == null ? void 0 : playbook.branch_reason) || (currentStage == null ? void 0 : currentStage.summary) || (scorecard == null ? void 0 : scorecard.primary_goal) || "系统仍在结合最近事件和反馈，判断更稳妥的下一条分支。";
  const reportContent = (latestReport == null ? void 0 : latestReport.content) || {};
  const latestInsight = reportContent.insight || reportContent.executive_summary || reportContent.self_insight || reportContent.trend_description || "";
  return `
        <div class="timeline-branch-panel">
            <article class="timeline-branch-panel__hero">
                <p class="panel__eyebrow">分支视图</p>
                <h4>${escapeHtml((playbook == null ? void 0 : playbook.active_branch_label) || (currentStage == null ? void 0 : currentStage.phase_label) || "观察中")}</h4>
                <p>${escapeHtml(focusText)}</p>
                <div class="timeline-branch-panel__meta">
                    ${(playbook == null ? void 0 : playbook.current_day) ? `<span class="pill">第 ${escapeHtml(playbook.current_day)}/${escapeHtml(playbook.total_days || 7)} 天</span>` : ""}
                    ${(playbook == null ? void 0 : playbook.transition_count) ? `<span class="pill">${escapeHtml(String(playbook.transition_count))} 次切换</span>` : ""}
                    ${(currentStage == null ? void 0 : currentStage.checkpoint_date) ? `<span class="pill">检查点 ${escapeHtml(formatDateOnly(currentStage.checkpoint_date))}</span>` : ""}
                    ${(scorecard == null ? void 0 : scorecard.momentum) ? `<span class="pill">${escapeHtml(planMomentumLabel(scorecard.momentum))}</span>` : ""}
                </div>
                <div class="timeline-branch-panel__actions">
                    ${snapshot.isSolo ? '<button class="button button--ghost" type="button" onclick="openMethodologyExplainer()">方法说明</button>' : '<button class="button button--secondary" type="button" onclick="openMessageSimulator()">聊天前预演</button><button class="button button--ghost" type="button" onclick="openNarrativeAlignment()">双视角对齐</button>'}
                </div>
            </article>
            <article class="timeline-note-card">
                <p class="panel__eyebrow">最近切换</p>
                <h4>${escapeHtml((latestTransition == null ? void 0 : latestTransition.label) || (latestTransition == null ? void 0 : latestTransition.to_branch_label) || "近期没有新的分支切换")}</h4>
                <p>${escapeHtml((latestTransition == null ? void 0 : latestTransition.trigger_summary) || latestInsight || "最近还没有记录到新的分支切换，因此系统仍沿着当前路径继续观察。")}</p>
                <div class="stack-item__meta">${escapeHtml((latestTransition == null ? void 0 : latestTransition.created_at) ? formatDate(latestTransition.created_at) : "持续观察中")}</div>
            </article>
            <article class="timeline-note-card timeline-note-card--soft">
                <p class="panel__eyebrow">当前策略</p>
                <h4>${escapeHtml(((_a = schedule == null ? void 0 : schedule.current_policy) == null ? void 0 : _a.title) || "当前策略")}</h4>
                <p>${escapeHtml((policyAudit == null ? void 0 : policyAudit.selection_reason) || (currentStage == null ? void 0 : currentStage.summary) || ((_b = scorecard == null ? void 0 : scorecard.next_actions) == null ? void 0 : _b[0]) || "系统会继续根据事件流和反馈回路微调当前策略。")}</p>
            </article>
            ${renderPolicyAuditPeek(policyAudit)}
        </div>
    `;
}
function syncTopbar() {
  const titleMap = {
    auth: "关系支持系统",
    pair: "建立一段关系",
    "pair-waiting": "等待对方加入",
    home: "关系总览",
    checkin: "留下今天的关系记录",
    discover: "功能总览",
    report: "关系简报",
    timeline: "关系时间轴",
    profile: "我的关系空间",
    milestones: "关系时间线",
    longdistance: "异地关系模式",
    "attachment-test": "依恋分析",
    "health-test": "关系体检",
    community: "社群技巧",
    challenges: "今日挑战",
    courses: "成长内容",
    experts: "专业支持",
    membership: "会员方案"
  };
  const subtitleMap = {
    auth: "从今天开始，慢慢把关系养好。",
    pair: "先把彼此放进同一个空间，再开始共同记录。",
    "pair-waiting": "邀请码已经准备好，差最后一步。",
    home: "先看输入状态、当前路径和下一步动作。",
    checkin: "表单和智能陪伴，都服务于更真实的一句心里话。",
    discover: "先看系统主链，再进入简报、证据回放和干预动作。",
    report: "把复杂情绪和互动模式，翻译成一份好读的简报。",
    timeline: "把最近这段关系如何一步步走到现在，铺成一张可回放、可筛选的事件轨道。",
    profile: "把账户、关系和边界感，收进一个安静空间。",
    milestones: "重要时刻不只是一条纪念，也能成为成长线索。",
    longdistance: "异地不是缺席，而是需要更精心的同步。",
    "attachment-test": "看见互动背后的依恋模式，才知道怎么靠近。",
    "health-test": "先知道关系在哪里，再知道下一步去哪里。",
    community: "把有用的方法，做成能马上实践的小动作。",
    challenges: "任务不该像 KPI，而该像今天的一次小靠近。",
    courses: "内容不只增长知识，也该提升相处质量。",
    experts: "当关系需要更稳的支持时，这里接住你。",
    membership: "把高频陪伴、报告和服务，放进长期关系系统。"
  };
  const captionMap = {
    auth: "亲健",
    pair: "关系设置",
    "pair-waiting": "邀请",
    home: "首页",
    checkin: "记录",
    discover: "总览",
    report: "简报",
    timeline: "时间轴",
    profile: "我的",
    milestones: "里程碑",
    longdistance: "异地关系",
    "attachment-test": "依恋",
    "health-test": "体检",
    community: "社区",
    challenges: "挑战",
    courses: "课程",
    experts: "咨询",
    membership: "会员"
  };
  safeSetText("#topbar-title", titleMap[state.currentPage] || "关系支持系统");
  safeSetText("#topbar-subtitle", subtitleMap[state.currentPage] || "把复杂关系，做成更轻一点、更近一点的日常。");
  safeSetText("#topbar-caption", captionMap[state.currentPage] || "亲健");
  const ritualButton = document.querySelector('.pill-button[data-jump-page="checkin"]');
  if (ritualButton) {
    const hiddenPages = /* @__PURE__ */ new Set(["auth", "pair", "pair-waiting"]);
    ritualButton.classList.toggle("hidden", hiddenPages.has(state.currentPage));
  }
}
function renderMessageSimulationResult(payload) {
  if (!payload)
    return "";
  return `
        <div class="simulation-result">
            <div class="simulation-result__top">
                <span class="pill simulation-risk simulation-risk--${escapeHtml(payload.risk_level || "medium")}">${escapeHtml(messageRiskLabel(payload.risk_level))}</span>
                ${payload.suggested_tone ? `<span class="pill">${escapeHtml(payload.suggested_tone)}</span>` : ""}
                ${payload.conversation_goal ? `<span class="pill">${escapeHtml(payload.conversation_goal)}</span>` : ""}
            </div>
            <div class="simulation-result__grid">
                <article class="hero-card">
                    <strong>对方第一感受</strong>
                    <p>${escapeHtml(payload.partner_view || "系统暂时无法判断。")}</p>
                </article>
                <article class="hero-card">
                    <strong>大概率走向</strong>
                    <p>${escapeHtml(payload.likely_impact || "系统暂时无法判断。")}</p>
                </article>
            </div>
            <div class="hero-card hero-card--accent">
                <strong>为什么会有这个风险</strong>
                <p>${escapeHtml(payload.risk_reason || "系统认为这句话更容易先被接成压力，而不是需求。")}</p>
            </div>
            <div class="hero-card simulation-rewrite">
                <strong>更稳妥的表达版本</strong>
                <p>${escapeHtml(payload.safer_rewrite || payload.draft || "")}</p>
            </div>
            <div class="simulation-result__grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">DO</p><h4>建议这样做</h4></div></div>
                    ${renderBulletList(payload.do_list || [], "先说感受，再说具体需求。")}
                </div>
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">AVOID</p><h4>尽量避免</h4></div></div>
                    ${renderBulletList(payload.avoid_list || [], "避免绝对化和翻旧账。")}
                </div>
            </div>
            ${(payload.evidence_summary || []).length || payload.limitation_note || payload.safety_handoff ? renderSafetyStatusPanel({
    risk_level: payload.risk_level || "low",
    why_now: payload.risk_reason || payload.likely_impact || "",
    evidence_summary: payload.evidence_summary || [],
    limitation_note: payload.limitation_note || "",
    recommended_action: payload.partner_view || payload.safer_rewrite || "",
    handoff_recommendation: payload.safety_handoff || ""
  }, {
    compact: true,
    title: payload.safety_handoff ? "这次更该先看边界" : "这次建议背后的依据"
  }) : ""}
            <div class="hero-actions">
                <button class="button button--secondary" type="button" onclick="useSimulationRewrite()">把改写放回输入框</button>
                <button class="button button--ghost" type="button" onclick="copySimulationRewrite()">复制改写版本</button>
            </div>
            ${renderContestModalReturn("openNarrativeAlignment()", "继续双视角对齐")}
        </div>
    `;
}
async function runMessageSimulation() {
  if (!ensurePairContext("请先进入一段已激活的关系")) {
    return;
  }
  const input = $("#message-simulator-input");
  const draft = input == null ? void 0 : input.value.trim();
  if (!draft) {
    showToast("先输入一句准备发的话");
    return;
  }
  const button = $("#message-simulator-run");
  if (button) {
    button.disabled = true;
    button.textContent = "预演中...";
  }
  safeSetHtml("#message-simulator-result", '<div class="empty-state">正在结合最近的关系状态做预演，请稍候。</div>');
  try {
    const payload = isDemoMode() ? {
      ...deepClone(getDemoFixture("messageSimulation") || {}),
      draft
    } : await api.simulateRelationshipMessage(state.currentPair.id, draft);
    state.lastMessageSimulation = payload;
    safeSetHtml("#message-simulator-result", renderMessageSimulationResult(payload));
  } catch (error) {
    safeSetHtml("#message-simulator-result", `<div class="empty-state">${escapeHtml(error.message || "预演失败，请稍后重试。")}</div>`);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "开始预演";
    }
  }
}
async function openNarrativeAlignment() {
  if (!ensurePairContext("请先进入一段已激活的关系")) {
    return;
  }
  state.lastNarrativeAlignment = null;
  const partnerName = getPartnerDisplayName(state.currentPair);
  openModal(`
        <h3>双方叙事对齐</h3>
        <p class="muted-copy">正在整理你和 ${escapeHtml(partnerName)} 最近同一阶段的记录，看看双方其实在经历什么、哪里最容易错位，以及更适合怎么开口。</p>
        <div class="empty-state">正在生成双视角对齐结果，请稍候。</div>
    `);
  try {
    const payload = isDemoMode() ? deepClone(getDemoFixture("narrativeAlignment") || {}) : await api.getLatestNarrativeAlignment(state.currentPair.id);
    state.lastNarrativeAlignment = payload;
    openModal(`
            <h3>双方叙事对齐</h3>
            <p class="muted-copy">${escapeHtml(payload.checkin_date || "")} 的双方记录已经整理成一份可直接拿来沟通的共同版本。</p>
            ${renderNarrativeAlignmentResult(payload)}
            ${renderContestModalReturn("openCrisisDetail()", "继续修复协议")}
        `);
  } catch (error) {
    openModal(`
            <h3>双方叙事对齐</h3>
            <div class="empty-state">${escapeHtml(error.message || "暂时无法生成双视角对齐，请稍后重试。")}</div>
            <div class="hero-actions">
                <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
            </div>
            ${renderContestModalReturn()}
        `);
  }
}
function renderRepairProtocol(protocol) {
  var _a;
  if (!protocol) {
    return '<div class="empty-state">当前还没有可展示的修复协议。</div>';
  }
  const focusTags = Array.isArray(protocol.focus_tags) ? protocol.focus_tags : [];
  return `
        <section class="repair-protocol">
            <div class="repair-protocol__top">
                <div>
                    <p class="panel__eyebrow">REPAIR PROTOCOL</p>
                    <h4>${escapeHtml(protocol.title || "修复协议")}</h4>
                </div>
                <span class="pill">${escapeHtml(crisisLabel(protocol.level || "none"))}</span>
            </div>
            <p class="panel-note">${escapeHtml(protocol.summary || "系统已经为当前阶段生成了一组修复步骤。")}</p>
            <div class="repair-protocol__meta">
                ${protocol.timing_hint ? `<span class="pill">${escapeHtml(protocol.timing_hint)}</span>` : ""}
                ${protocol.active_plan_type ? `<span class="pill">${escapeHtml(protocol.active_plan_type)}</span>` : ""}
                ${focusTags.map((tag) => `<span class="pill">${escapeHtml(tag)}</span>`).join("")}
            </div>
            <div class="stack-list">
                ${(protocol.steps || []).map((step) => `
                    <article class="stack-item stack-item--static">
                        <div class="protocol-step__index">${step.sequence}</div>
                        <div class="stack-item__content">
                            <strong>${escapeHtml(step.title)}</strong>
                            <div class="stack-item__meta">${escapeHtml(step.action || "")}</div>
                            ${step.why ? `<div class="stack-item__meta">为什么：${escapeHtml(step.why)}</div>` : ""}
                            ${step.duration_hint ? `<div class="stack-item__meta">建议时长：${escapeHtml(step.duration_hint)}</div>` : ""}
                        </div>
                    </article>
                `).join("")}
            </div>
            <div class="repair-protocol__grid">
                <div class="panel">
                    <div class="panel__header"><div><p class="panel__eyebrow">AVOID</p><h4>这时候别做</h4></div></div>
                    ${renderBulletList(protocol.do_not || [], "先避免让局面继续升级。")}
                </div>
                <div class="panel">
        <div class="panel__header"><div><p class="panel__eyebrow">后续</p><h4>修复完成后</h4></div></div>
                    ${renderBulletList(protocol.follow_up || [], "等情绪回落后，再决定是否进入下一轮沟通。")}
                </div>
            </div>
            ${renderSafetyStatusPanel({
    risk_level: protocol.level || "none",
    why_now: protocol.summary || "",
    evidence_summary: protocol.evidence_summary || [],
    limitation_note: protocol.limitation_note || "",
    recommended_action: ((_a = (protocol.steps || [])[0]) == null ? void 0 : _a.action) || "",
    handoff_recommendation: protocol.safety_handoff || ""
  }, {
    compact: true,
    title: protocol.safety_handoff ? "这次更该先止损与转介" : "这组修复步骤基于什么"
  })}
        </section>
    `;
}
async function openCrisisDetail() {
  var _a;
  if (!ensurePairContext("请先进入一段已激活的关系")) {
    return;
  }
  openModal(`
        <h3>冲突修复协议</h3>
        <p class="muted-copy">正在结合当前风险、关系画像和干预计划，整理一份更适合现在的修复协议。</p>
        <div class="empty-state">正在生成修复步骤，请稍候。</div>
    `);
  try {
    const [protocolResult, safetyResult] = await Promise.allSettled([
      isDemoMode() ? Promise.resolve(deepClone(getDemoFixture("repairProtocol") || {})) : api.getRepairProtocol(state.currentPair.id),
      isDemoMode() ? Promise.resolve(deepClone(getDemoFixture("safetyStatus") || {})) : api.getSafetyStatus(state.currentPair.id)
    ]);
    const protocol = unwrapResult(protocolResult, null);
    const safetyStatus = unwrapResult(safetyResult, null);
    if (protocol && safetyStatus && !protocol.safety_handoff) {
      protocol.safety_handoff = safetyStatus.handoff_recommendation || "";
      protocol.evidence_summary = ((_a = protocol.evidence_summary) == null ? void 0 : _a.length) ? protocol.evidence_summary : safetyStatus.evidence_summary || [];
      protocol.limitation_note = protocol.limitation_note || safetyStatus.limitation_note || "";
    }
    openModal(`
            <h3>冲突修复协议</h3>
            ${renderRepairProtocol(protocol)}
            ${renderContestModalReturn("showPage('timeline')", "最后看证据复盘")}
        `);
  } catch (error) {
    openModal(`
            <h3>冲突修复协议</h3>
            <div class="empty-state">${escapeHtml(error.message || "暂时无法生成修复协议，请稍后重试。")}</div>
            <div class="hero-actions">
                <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
            </div>
            ${renderContestModalReturn()}
        `);
  }
}
async function ensureTimelineEventDetail(eventId) {
  const key = String(eventId || "").trim();
  if (!key) {
    return null;
  }
  if (isDemoMode()) {
    if (state.timelineEventDetails[key]) {
      return state.timelineEventDetails[key];
    }
    const detail = deepClone(getDemoFixture(`timelineEventDetails.${key}`));
    if (detail) {
      state.timelineEventDetails = {
        ...state.timelineEventDetails,
        [key]: detail
      };
      if (String(state.timelineSelectedEventId || "") === key) {
        setTimeout(() => {
          if (String(state.timelineSelectedEventId || "") === key) {
            rerenderTimelinePage();
          }
        }, 0);
      }
      return detail;
    }
    return null;
  }
  if (!api.isLoggedIn()) {
    return null;
  }
  if (state.timelineEventDetails[key] || state.timelineEventLoadingId === key) {
    return state.timelineEventDetails[key] || null;
  }
  state.timelineEventLoadingId = key;
  rerenderTimelinePage();
  try {
    const payload = await api.getRelationshipTimelineEventDetail(key);
    state.timelineEventDetails = {
      ...state.timelineEventDetails,
      [key]: payload
    };
    return payload;
  } catch (error) {
    state.timelineEventDetails = {
      ...state.timelineEventDetails,
      [key]: {
        error: error.message || "当前暂时无法加载这个节点的详细证据。"
      }
    };
    return null;
  } finally {
    if (state.timelineEventLoadingId === key) {
      state.timelineEventLoadingId = null;
    }
    rerenderTimelinePage();
  }
}
function renderTimelineBranchOverlay(snapshot = {}) {
  var _a, _b;
  const playbook = snapshot.playbook || null;
  const scorecard = snapshot.scorecard || null;
  const schedule = snapshot.schedule || null;
  const policyAudit = snapshot.policyAudit || null;
  const latestReport = snapshot.latestReport || null;
  const safetyStatus = snapshot.safetyStatus || null;
  const latestTransition = (playbook == null ? void 0 : playbook.latest_transition) || null;
  const currentStage = (schedule == null ? void 0 : schedule.current_stage) || null;
  const focusText = (playbook == null ? void 0 : playbook.branch_reason) || (currentStage == null ? void 0 : currentStage.summary) || (scorecard == null ? void 0 : scorecard.primary_goal) || "系统正在结合最近事件和反馈，判断更稳妥的下一步。";
  const reportContent = (latestReport == null ? void 0 : latestReport.content) || {};
  const latestInsight = reportContent.insight || reportContent.executive_summary || reportContent.self_insight || reportContent.trend_description || "";
  return `
        <div class="timeline-branch-panel">
            <article class="timeline-branch-panel__hero">
                <p class="panel__eyebrow">分支视图</p>
                <h4>${escapeHtml((playbook == null ? void 0 : playbook.active_branch_label) || (currentStage == null ? void 0 : currentStage.phase_label) || "观察中")}</h4>
                <p>${escapeHtml(focusText)}</p>
                <div class="timeline-branch-panel__meta">
                    ${(playbook == null ? void 0 : playbook.current_day) ? `<span class="pill">第 ${escapeHtml(playbook.current_day)}/${escapeHtml(playbook.total_days || 7)} 天</span>` : ""}
                    ${(playbook == null ? void 0 : playbook.transition_count) ? `<span class="pill">${escapeHtml(String(playbook.transition_count))} 次切换</span>` : ""}
                    ${(currentStage == null ? void 0 : currentStage.checkpoint_date) ? `<span class="pill">检查点 ${escapeHtml(formatDateOnly(currentStage.checkpoint_date))}</span>` : ""}
                    ${(scorecard == null ? void 0 : scorecard.momentum) ? `<span class="pill">${escapeHtml(planMomentumLabel(scorecard.momentum))}</span>` : ""}
                </div>
                <div class="timeline-branch-panel__actions">
                    ${snapshot.isSolo ? '<button class="button button--ghost" type="button" onclick="openMethodologyExplainer()">方法说明</button>' : '<button class="button button--secondary" type="button" onclick="openMessageSimulator()">聊天前预演</button><button class="button button--ghost" type="button" onclick="openNarrativeAlignment()">双视角对齐</button>'}
                </div>
            </article>
            <article class="timeline-note-card">
                <p class="panel__eyebrow">最近切换</p>
                <h4>${escapeHtml((latestTransition == null ? void 0 : latestTransition.label) || (latestTransition == null ? void 0 : latestTransition.to_branch_label) || "近期没有新的分支切换")}</h4>
                <p>${escapeHtml((latestTransition == null ? void 0 : latestTransition.trigger_summary) || latestInsight || "最近还没有记录到新的分支切换，因此系统仍沿着当前路径继续观察。")}</p>
                <div class="stack-item__meta">${escapeHtml((latestTransition == null ? void 0 : latestTransition.created_at) ? formatDate(latestTransition.created_at) : "持续观察中")}</div>
            </article>
            <article class="timeline-note-card timeline-note-card--soft">
                <p class="panel__eyebrow">当前策略</p>
                <h4>${escapeHtml(((_a = schedule == null ? void 0 : schedule.current_policy) == null ? void 0 : _a.title) || "当前策略")}</h4>
                <p>${escapeHtml((policyAudit == null ? void 0 : policyAudit.selection_reason) || (currentStage == null ? void 0 : currentStage.summary) || ((_b = scorecard == null ? void 0 : scorecard.next_actions) == null ? void 0 : _b[0]) || "系统会继续根据事件流和反馈回路微调当前策略。")}</p>
            </article>
            ${safetyStatus ? renderSafetyStatusPanel(safetyStatus, { compact: true, title: "这一轮判断的边界" }) : ""}
            ${renderPolicyAuditPeek(policyAudit)}
        </div>
    `;
}
async function loadTimelinePage() {
  var _a, _b, _c, _d, _e, _f, _g;
  if (!api.isLoggedIn() && !isDemoMode()) {
    safeSetHtml("#timeline-main", '<div class="empty-state">请先登录后再查看关系时间轴。</div>');
    return;
  }
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const isSolo = !pairId;
  const reportType = isSolo ? "daily" : state.selectedReportType;
  safeSetHtml("#timeline-main", `
        <section class="timeline-stage timeline-stage--loading">
            <div class="empty-state">正在整理最近这段时间的事件轨道、分支迁移和策略线索，请稍候。</div>
        </section>
    `);
  if (isDemoMode()) {
    state.timelinePageSnapshot = {
      isSolo: false,
      timeline: deepClone(getDemoFixture("timeline") || { event_count: 0, latest_event_at: null, events: [], highlights: [] }),
      playbook: deepClone(getDemoFixture("playbook") || null),
      scorecard: deepClone(getDemoFixture("scorecard") || null),
      schedule: deepClone(getDemoFixture("policySchedule") || null),
      policyAudit: deepClone(getDemoFixture("policyAudit") || null),
      latestReport: deepClone(getDemoFixture("latestReport") || null),
      safetyStatus: deepClone(getDemoFixture("safetyStatus") || null)
    };
    state.timelineSelectedEventId = ((_d = (_c = (_b = state.timelinePageSnapshot.timeline) == null ? void 0 : _b.events) == null ? void 0 : _c[0]) == null ? void 0 : _d.id) || null;
    state.timelineEventDetails = deepClone(getDemoFixture("timelineEventDetails") || {});
    state.timelineEventLoadingId = null;
    rerenderTimelinePage();
    return;
  }
  const [timelineResult, playbookResult, scorecardResult, scheduleResult, policyAuditResult, reportResult, safetyResult] = await Promise.allSettled([
    api.getRelationshipTimeline(pairId, 36),
    api.getRelationshipPlaybook(pairId),
    api.getInterventionScorecard(pairId),
    api.getPolicySchedule(pairId),
    api.getPolicyDecisionAudit(pairId),
    api.getLatestReport(pairId, reportType),
    api.getSafetyStatus(pairId)
  ]);
  state.timelinePageSnapshot = {
    isSolo,
    timeline: unwrapResult(timelineResult, { event_count: 0, latest_event_at: null, events: [], highlights: [] }),
    playbook: unwrapResult(playbookResult, null),
    scorecard: unwrapResult(scorecardResult, null),
    schedule: unwrapResult(scheduleResult, null),
    policyAudit: unwrapResult(policyAuditResult, null),
    latestReport: unwrapResult(reportResult, null),
    safetyStatus: unwrapResult(safetyResult, null)
  };
  state.timelineSelectedEventId = ((_g = (_f = (_e = state.timelinePageSnapshot.timeline) == null ? void 0 : _e.events) == null ? void 0 : _f[0]) == null ? void 0 : _g.id) || null;
  state.timelineEventDetails = {};
  state.timelineEventLoadingId = null;
  rerenderTimelinePage();
}
async function generateReport() {
  var _a;
  if (isDemoMode()) {
    showToast("当前是样例查看，不会触发真实简报生成。");
    return;
  }
  if (!ensureLoginContext()) {
    return;
  }
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const reportType = pairId ? state.selectedReportType : "daily";
  const button = $("#report-generate-btn");
  if (button) {
    button.disabled = true;
    button.textContent = "生成中...";
  }
  try {
    await api.generateReport(pairId, reportType);
    showToast("已提交报告生成请求，稍后刷新即可查看。");
    await loadReportPage();
  } catch (error) {
    showToast(error.message || "生成失败，请稍后重试。");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = pairId ? "生成这一期简报" : "更新个人简报";
    }
  }
}
function initHealthTest() {
  healthTestState = { current: 0, answers: [] };
  $("#ht-result").classList.add("hidden");
  $("#ht-question-area").classList.remove("hidden");
  safeSetHtml("#ht-assessment-trend", "");
  renderHealthQuestion();
}
async function showHealthTestResult() {
  var _a, _b;
  $("#ht-question-area").classList.add("hidden");
  $("#ht-result").classList.remove("hidden");
  $("#ht-progress-bar").style.width = "100%";
  $("#ht-progress-text").textContent = `${HEALTH_TEST_QUESTIONS.length}/${HEALTH_TEST_QUESTIONS.length}`;
  const total = Math.round(healthTestState.answers.reduce((sum, item) => sum + item.score, 0) / healthTestState.answers.length);
  $("#ht-gauge").style.setProperty("--score", total);
  $("#ht-score").textContent = total;
  const level = total >= 80 ? ["关系非常健康", "你们已经具备很好的互动基础，重点是保持稳定节奏。"] : total >= 60 ? ["关系总体不错", "主要提升空间在表达细节和修复速度。"] : total >= 40 ? ["关系需要关注", "建议把“说清楚需求”和“及时回应”作为短期目标。"] : ["关系需要干预", "当前已经出现较多低分维度，建议尽快建立支持性对话机制。"];
  $("#ht-level").textContent = level[0];
  $("#ht-desc").textContent = level[1];
  $("#ht-dimensions").innerHTML = healthTestState.answers.map((entry) => `
    <article class="stack-item">
      <div>${svgIcon("i-chart")}</div>
      <div>
        <strong>${escapeHtml(entry.dim)}</strong>
        <div class="stack-item__meta">评分 ${entry.score}</div>
      </div>
    </article>`).join("");
  const weakPoints = healthTestState.answers.filter((entry) => entry.score < 50);
  $("#ht-suggestion-list").innerHTML = weakPoints.length ? weakPoints.map((entry) => `<div class="stack-item"><div>${svgIcon("i-spark")}</div><div><strong>${escapeHtml(entry.dim)}</strong><div class="stack-item__meta">建议围绕这个维度安排一次具体对话和一个行动。</div></div></div>`).join("") : '<div class="empty-state">当前各维度没有明显短板，可以继续保持记录与复盘。</div>';
  try {
    let trend;
    if (isDemoMode()) {
      trend = deepClone(getDemoFixture("assessmentTrend") || null);
    } else {
      await api.submitWeeklyAssessment(((_a = state.currentPair) == null ? void 0 : _a.id) || null, {
        answers: healthTestState.answers,
        submitted_at: new Date().toISOString()
      });
      trend = await api.getWeeklyAssessmentTrend(((_b = state.currentPair) == null ? void 0 : _b.id) || null);
    }
    safeSetHtml("#ht-assessment-trend", renderAssessmentTrendCard(trend, {
      title: isDemoMode() ? "近 4 次关系体检趋势（样例）" : "近 4 次关系体检趋势"
    }));
  } catch (error) {
    safeSetHtml("#ht-assessment-trend", `<div class="empty-state">${escapeHtml(error.message || "体检趋势暂时无法同步，请稍后再试。")}</div>`);
  }
}
document.addEventListener("DOMContentLoaded", async () => {
  switchAuthMode("login");
  switchAuthMethod("email");
  updateSendCodeButton();
  bindOptionEvents();
  bindStaticEvents();
  exposeGlobals();
  await initClientAIServices().catch(() => false);
  renderCheckinPage();
  loadCheckinAgentState();
  syncTopbar();
  syncNotifications();
  await bootstrapSession();
  renderCheckinClientAIPanel(state.lastClientPrecheck);
  if (!api.isLoggedIn()) {
    await showPage("auth");
  }
});
