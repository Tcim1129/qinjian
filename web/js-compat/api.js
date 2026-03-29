const API_ROOT = (() => {
  var _a;
  if ((_a = window.QJ_CONFIG) == null ? void 0 : _a.apiRoot) {
    return window.QJ_CONFIG.apiRoot.replace(/\/$/, "");
  }
  if (window.location.protocol === "file:" || window.location.hostname === "localhost") {
    return "http://127.0.0.1:8000/api/v1";
  }
  return "/api/v1";
})();
const TOKEN_KEY = "qj_token";
function readStoredToken() {
  const sessionToken = sessionStorage.getItem(TOKEN_KEY);
  if (sessionToken) {
    return sessionToken;
  }
  const legacyToken = localStorage.getItem(TOKEN_KEY);
  if (legacyToken) {
    sessionStorage.setItem(TOKEN_KEY, legacyToken);
    localStorage.removeItem(TOKEN_KEY);
    return legacyToken;
  }
  return "";
}
class ApiClient {
  constructor() {
    this.token = readStoredToken();
  }
  async requestWithTimeout(method, path, body = null, timeoutMs = 12e3) {
    const headers = {};
    const options = { method, headers };
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }
    if (body !== null && body !== void 0) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    options.signal = controller.signal;
    let response;
    try {
      response = await fetch(`${API_ROOT}${path}`, options);
    } catch (error) {
      if ((error == null ? void 0 : error.name) === "AbortError") {
        throw new Error("请求超时");
      }
      throw new Error("无法连接后端服务");
    } finally {
      clearTimeout(timer);
    }
    const contentType = response.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const payload = isJson ? await response.json() : await response.text();
    if (!response.ok) {
      if (typeof payload === "string") {
        throw new Error(payload || "请求失败");
      }
      throw new Error(payload.detail || payload.message || "请求失败");
    }
    return payload;
  }
  setToken(token) {
    this.token = token || "";
    if (this.token) {
      sessionStorage.setItem(TOKEN_KEY, this.token);
      localStorage.removeItem(TOKEN_KEY);
      return;
    }
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_KEY);
  }
  clearToken() {
    this.setToken("");
  }
  isLoggedIn() {
    return Boolean(this.token);
  }
  async request(method, path, body = null) {
    const isDemoReadOnly = new URLSearchParams(window.location.search).get("demo") === "1";
    if (isDemoReadOnly && method !== "GET") {
      throw new Error("Demo Mode is read-only.");
    }
    const headers = {};
    const options = { method, headers };
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }
    if (body !== null && body !== void 0) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    let response;
    try {
      response = await fetch(`${API_ROOT}${path}`, options);
    } catch (error) {
      throw new Error("无法连接后端服务");
    }
    const contentType = response.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const payload = isJson ? await response.json() : await response.text();
    if (!response.ok) {
      if (typeof payload === "string") {
        throw new Error(payload || "请求失败");
      }
      throw new Error(payload.detail || payload.message || "请求失败");
    }
    return payload;
  }
  async uploadFile(type, file) {
    const formData = new FormData();
    formData.append("file", file);
    let response;
    try {
      response = await fetch(`${API_ROOT}/upload/${type}`, {
        method: "POST",
        headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
        body: formData
      });
    } catch (error) {
      throw new Error("上传失败，请检查网络连接");
    }
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || payload.message || "上传失败");
    }
    return payload;
  }
  async login(email, password) {
    const payload = await this.request("POST", "/auth/login", { email, password });
    this.setToken(payload.access_token);
    return payload;
  }
  async register(email, nickname, password) {
    const payload = await this.request("POST", "/auth/register", { email, nickname, password });
    this.setToken(payload.access_token);
    return payload;
  }
  async sendPhoneCode(phone) {
    return this.request("POST", "/auth/phone/send-code", { phone });
  }
  async phoneLogin(phone, code) {
    const payload = await this.request("POST", "/auth/phone/login", { phone, code });
    this.setToken(payload.access_token);
    return payload;
  }
  async getMe() {
    return this.request("GET", "/auth/me");
  }
  async updateMe(payload) {
    return this.request("PUT", "/auth/me", payload);
  }
  async changePassword(currentPassword, newPassword) {
    return this.request("POST", "/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword
    });
  }
  async createPair(type) {
    return this.request("POST", "/pairs/create", { type });
  }
  async joinPair(inviteCode) {
    return this.request("POST", "/pairs/join", { invite_code: inviteCode });
  }
  async getMyPairs() {
    const payload = await this.request("GET", "/pairs/me");
    return Array.isArray(payload) ? payload : [];
  }
  async getPairSummary() {
    return this.request("GET", "/pairs/summary");
  }
  async requestUnbind(pairId) {
    return this.request("POST", `/pairs/request-unbind?pair_id=${pairId}`);
  }
  async confirmUnbind(pairId) {
    return this.request("POST", `/pairs/confirm-unbind?pair_id=${pairId}`);
  }
  async cancelUnbind(pairId) {
    return this.request("POST", `/pairs/cancel-unbind?pair_id=${pairId}`);
  }
  async getUnbindStatus(pairId) {
    return this.request("GET", `/pairs/unbind-status?pair_id=${pairId}`);
  }
  async updatePartnerNickname(pairId, customNickname) {
    return this.request("POST", `/pairs/${pairId}/partner-nickname`, { custom_nickname: customNickname });
  }
  async submitCheckin(pairId, payload) {
    return this.request("POST", pairId ? "/checkins/" : "/checkins/?mode=solo", pairId ? { pair_id: pairId, ...payload } : payload);
  }
  async getTodayStatus(pairId) {
    return this.request("GET", pairId ? `/checkins/today?pair_id=${pairId}` : "/checkins/today?mode=solo");
  }
  async getCheckinHistory(pairId, limit = 14) {
    return this.request("GET", pairId ? `/checkins/history?pair_id=${pairId}&limit=${limit}` : `/checkins/history?mode=solo&limit=${limit}`);
  }
  async getCheckinStreak(pairId) {
    return this.request("GET", pairId ? `/checkins/streak?pair_id=${pairId}` : "/checkins/streak?mode=solo");
  }
  async generateDailyReport(pairId) {
    return this.request("POST", pairId ? `/reports/generate-daily?pair_id=${pairId}` : "/reports/generate-daily?mode=solo");
  }
  async generateWeeklyReport(pairId) {
    return this.request("POST", `/reports/generate-weekly?pair_id=${pairId}`);
  }
  async generateMonthlyReport(pairId) {
    return this.request("POST", `/reports/generate-monthly?pair_id=${pairId}`);
  }
  async getLatestReport(pairId, reportType = "daily") {
    return this.request("GET", pairId ? `/reports/latest?pair_id=${pairId}&report_type=${reportType}` : `/reports/latest?mode=solo&report_type=${reportType}`);
  }
  async waitForReport(pairId, reportType = "daily", retries = 10, delayMs = 1500) {
    for (let attempt = 0; attempt < retries; attempt += 1) {
      const payload = await this.getLatestReport(pairId, reportType);
      if (!payload || payload.status === "pending") {
        await new Promise((resolve) => setTimeout(resolve, delayMs));
        continue;
      }
      return payload;
    }
    return this.getLatestReport(pairId, reportType);
  }
  async getReportHistory(pairId, reportType = "daily", limit = 7) {
    return this.request("GET", pairId ? `/reports/history?pair_id=${pairId}&report_type=${reportType}&limit=${limit}` : `/reports/history?mode=solo&report_type=${reportType}&limit=${limit}`);
  }
  async getHealthTrend(pairId, days = 14) {
    return this.request("GET", pairId ? `/reports/trend?pair_id=${pairId}&days=${days}` : `/reports/trend?mode=solo&days=${days}`);
  }
  async getLatestInsightProfile(pairId, windowDays = 7, refresh = false) {
    const params = new URLSearchParams({ window_days: String(windowDays) });
    if (refresh) {
      params.set("refresh", "true");
    }
    if (pairId) {
      params.set("pair_id", pairId);
    } else {
      params.set("mode", "solo");
    }
    return this.request("GET", `/insights/profile/latest?${params.toString()}`);
  }
  async getInsightProfileHistory(pairId, windowDays = 7, limit = 10) {
    const params = new URLSearchParams({
      window_days: String(windowDays),
      limit: String(limit)
    });
    if (pairId) {
      params.set("pair_id", pairId);
    } else {
      params.set("mode", "solo");
    }
    return this.request("GET", `/insights/profile/history?${params.toString()}`);
  }
  async getRelationshipTimeline(pairId, limit = 24) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (pairId) {
      params.set("pair_id", pairId);
    } else {
      params.set("mode", "solo");
    }
    return this.request("GET", `/insights/timeline?${params.toString()}`);
  }
  async getRelationshipTimelineEventDetail(eventId) {
    return this.request("GET", `/insights/timeline/events/${eventId}`);
  }
  async getSafetyStatus(pairId) {
    return this.request("GET", pairId ? `/insights/safety/status?pair_id=${pairId}` : "/insights/safety/status?mode=solo");
  }
  async getPrivacyStatus() {
    return this.request("GET", "/privacy/status");
  }
  async getMyPrivacyAudit(limit = 20) {
    return this.request("GET", `/privacy/audit/me?limit=${limit}`);
  }
  async createPrivacyDeleteRequest() {
    return this.request("POST", "/privacy/delete-request");
  }
  async cancelPrivacyDeleteRequest() {
    return this.request("POST", "/privacy/delete-request/cancel");
  }
  async submitWeeklyAssessment(pairId, payload) {
    return this.request("POST", pairId ? `/insights/assessments/weekly?pair_id=${pairId}` : "/insights/assessments/weekly?mode=solo", payload);
  }
  async getWeeklyAssessmentLatest(pairId) {
    return this.request("GET", pairId ? `/insights/assessments/latest?pair_id=${pairId}` : "/insights/assessments/latest?mode=solo");
  }
  async getWeeklyAssessmentTrend(pairId, limit = 4) {
    return this.request("GET", pairId ? `/insights/assessments/trend?pair_id=${pairId}&limit=${limit}` : `/insights/assessments/trend?mode=solo&limit=${limit}`);
  }
  async getActiveInterventionPlan(pairId) {
    return this.request("GET", pairId ? `/insights/plans/active?pair_id=${pairId}` : "/insights/plans/active?mode=solo");
  }
  async getInterventionScorecard(pairId) {
    return this.request("GET", pairId ? `/insights/plans/scorecard?pair_id=${pairId}` : "/insights/plans/scorecard?mode=solo");
  }
  async getInterventionEvaluation(pairId) {
    return this.request("GET", pairId ? `/insights/plans/evaluation?pair_id=${pairId}` : "/insights/plans/evaluation?mode=solo");
  }
  async getInterventionExperiment(pairId) {
    return this.request("GET", pairId ? `/insights/plans/experiment?pair_id=${pairId}` : "/insights/plans/experiment?mode=solo");
  }
  async getPolicyRegistry(pairId) {
    return this.request("GET", pairId ? `/insights/plans/policy-registry?pair_id=${pairId}` : "/insights/plans/policy-registry?mode=solo");
  }
  async getPolicySchedule(pairId) {
    return this.request("GET", pairId ? `/insights/plans/policy-schedule?pair_id=${pairId}` : "/insights/plans/policy-schedule?mode=solo");
  }
  async getPolicyDecisionAudit(pairId) {
    return this.request("GET", pairId ? `/insights/plans/policy-audit?pair_id=${pairId}` : "/insights/plans/policy-audit?mode=solo");
  }
  async getRelationshipPlaybook(pairId) {
    return this.request("GET", pairId ? `/insights/playbook/active?pair_id=${pairId}` : "/insights/playbook/active?mode=solo");
  }
  async getMethodology(pairId) {
    return this.request("GET", pairId ? `/insights/methodology?pair_id=${pairId}` : "/insights/methodology?mode=solo");
  }
  async getLatestNarrativeAlignment(pairId) {
    return this.request("GET", `/insights/alignment/latest?pair_id=${pairId}`);
  }
  async getTreeStatus(pairId) {
    return this.request("GET", `/tree/status?pair_id=${pairId}`);
  }
  async waterTree(pairId) {
    return this.request("POST", `/tree/water?pair_id=${pairId}`);
  }
  async getCrisisStatus(pairId) {
    return this.request("GET", `/crisis/status/${pairId}`);
  }
  async getCrisisHistory(pairId, limit = 20) {
    return this.request("GET", `/crisis/history/${pairId}?limit=${limit}`);
  }
  async getCrisisAlerts(pairId, limit = 10) {
    return this.request("GET", `/crisis/alerts/${pairId}?limit=${limit}`);
  }
  async getRepairProtocol(pairId) {
    return this.request("GET", `/crisis/protocol/${pairId}`);
  }
  async acknowledgeCrisisAlert(alertId) {
    return this.request("POST", `/crisis/alerts/${alertId}/acknowledge`);
  }
  async resolveCrisisAlert(alertId, note = "") {
    return this.request("POST", `/crisis/alerts/${alertId}/resolve`, { note });
  }
  async escalateCrisisAlert(alertId, reason = "") {
    return this.request("POST", `/crisis/alerts/${alertId}/escalate`, { reason });
  }
  async getCrisisResources() {
    return this.request("GET", "/crisis/resources");
  }
  async getDailyTasks(pairId) {
    return this.requestWithTimeout("GET", `/tasks/daily/${pairId}`, null, 8e3);
  }
  async completeTask(taskId) {
    return this.request("POST", `/tasks/${taskId}/complete`);
  }
  async submitTaskFeedback(taskId, payload) {
    return this.request("POST", `/tasks/${taskId}/feedback`, payload);
  }
  async getAttachmentAnalysis(pairId) {
    return this.request("GET", `/tasks/attachment/${pairId}`);
  }
  async triggerAttachmentAnalysis(pairId) {
    return this.request("POST", `/tasks/attachment/${pairId}/analyze`);
  }
  async getLongDistanceHealth(pairId) {
    return this.request("GET", `/longdistance/health-index/${pairId}`);
  }
  async getLongDistanceActivities(pairId, limit = 20) {
    return this.request("GET", `/longdistance/activities/${pairId}?limit=${limit}`);
  }
  async createLongDistanceActivity(pairId, activityType, title = "") {
    const params = new URLSearchParams({ pair_id: pairId, activity_type: activityType });
    if (title) {
      params.set("title", title);
    }
    return this.request("POST", `/longdistance/activities?${params.toString()}`);
  }
  async completeLongDistanceActivity(activityId) {
    return this.request("POST", `/longdistance/activities/${activityId}/complete`);
  }
  async getMilestones(pairId) {
    return this.request("GET", `/milestones/${pairId}`);
  }
  async createMilestone(pairId, milestoneType, title, milestoneDate) {
    const params = new URLSearchParams({
      pair_id: pairId,
      milestone_type: milestoneType,
      title,
      milestone_date: milestoneDate
    });
    return this.request("POST", `/milestones/?${params.toString()}`);
  }
  async generateMilestoneReview(milestoneId) {
    return this.request("POST", `/milestones/${milestoneId}/generate-review`);
  }
  async getCommunityTips(pairType = "couple") {
    return this.request("GET", `/community/tips?pair_type=${pairType}`);
  }
  async generateTip(pairType = "couple") {
    return this.request("POST", `/community/tips/generate?pair_type=${pairType}`);
  }
  async getNotifications(limit = 20) {
    return this.request("GET", `/community/notifications?limit=${limit}`);
  }
  async markNotificationsRead() {
    return this.request("POST", "/community/notifications/read-all");
  }
  async createAgentSession(pairId = null) {
    const query = pairId ? `?pair_id=${pairId}` : "";
    return this.request("POST", `/agent/sessions${query}`);
  }
  async getAgentMessages(sessionId) {
    return this.request("GET", `/agent/sessions/${sessionId}/messages`);
  }
  async chatWithAgent(sessionId, content) {
    return this.request("POST", `/agent/sessions/${sessionId}/chat`, { content });
  }
  async simulateRelationshipMessage(pairId, draft) {
    return this.request("POST", `/agent/simulate-message?pair_id=${pairId}`, { draft });
  }
  async getAdminPolicies(planType = "", status = "") {
    const params = new URLSearchParams();
    if (planType) {
      params.set("plan_type", planType);
    }
    if (status) {
      params.set("status", status);
    }
    const query = params.toString();
    return this.request("GET", query ? `/admin/policies?${query}` : "/admin/policies");
  }
  async createAdminPolicy(payload) {
    return this.request("POST", "/admin/policies", payload);
  }
  async updateAdminPolicy(policyId, payload) {
    return this.request("PATCH", `/admin/policies/${encodeURIComponent(policyId)}`, payload);
  }
  async toggleAdminPolicy(policyId, status = "") {
    const body = status ? { status } : {};
    return this.request("POST", `/admin/policies/${encodeURIComponent(policyId)}/toggle`, body);
  }
  async getAdminPolicyAudit(policyId, limit = 12) {
    return this.request("GET", `/admin/policies/${encodeURIComponent(policyId)}/audit?limit=${limit}`);
  }
  async rollbackAdminPolicy(policyId, targetEventId, note = "") {
    return this.request("POST", `/admin/policies/${encodeURIComponent(policyId)}/rollback`, {
      target_event_id: targetEventId,
      note: note || null
    });
  }
  async reorderAdminPolicies(policyIds) {
    return this.request("POST", "/admin/policies/reorder", { policy_ids: policyIds });
  }
  async getAdminPrivacyAudits(filters = {}) {
    const params = new URLSearchParams();
    if (filters.eventType)
      params.set("event_type", filters.eventType);
    if (filters.userId)
      params.set("user_id", filters.userId);
    if (filters.pairId)
      params.set("pair_id", filters.pairId);
    if (filters.since)
      params.set("since", filters.since);
    if (filters.limit)
      params.set("limit", String(filters.limit));
    const query = params.toString();
    return this.request("GET", query ? `/admin/privacy/audits?${query}` : "/admin/privacy/audits");
  }
  async getAdminPrivacyDeleteRequests(status = "", limit = 50) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (status)
      params.set("status", status);
    return this.request("GET", `/admin/privacy/delete-requests?${params.toString()}`);
  }
  async approveAdminPrivacyDeleteRequest(requestId, note = "") {
    return this.request("POST", `/admin/privacy/delete-requests/${requestId}/approve`, {
      note: note || null
    });
  }
  async rejectAdminPrivacyDeleteRequest(requestId, note = "") {
    return this.request("POST", `/admin/privacy/delete-requests/${requestId}/reject`, {
      note: note || null
    });
  }
  async runAdminPrivacyRetentionSweep(dryRun = true) {
    return this.request("POST", `/admin/privacy/retention/sweep?dry_run=${dryRun ? "true" : "false"}`);
  }
}
window.API_ROOT = API_ROOT;
window.api = new ApiClient();
