/**
 * 亲健 API 客户端 (Phase 4 增强：危机预警 + 任务)
 */
const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api/v1'
    : '/api/v1';

class ApiClient {
    constructor() {
        this.token = localStorage.getItem('qj_token') || '';
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('qj_token', token);
    }

    clearToken() {
        this.token = '';
        localStorage.removeItem('qj_token');
    }

    isLoggedIn() {
        return !!this.token;
    }

    async request(method, path, body = null) {
        const headers = { 'Content-Type': 'application/json' };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const opts = { method, headers };
        if (body) opts.body = JSON.stringify(body);

        const res = await fetch(`${API_BASE}${path}`, opts);
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || '请求失败');
        }
        return data;
    }

    // ── 文件上传 ──
    async uploadFile(type, file) {
        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch(`${API_BASE}/upload/${type}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.token}` },
            body: formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || '上传失败');
        return data;
    }

    // ── 认证 ──
    async register(email, nickname, password) {
        const data = await this.request('POST', '/auth/register', { email, nickname, password });
        this.setToken(data.access_token);
        return data;
    }

    async login(email, password) {
        const data = await this.request('POST', '/auth/login', { email, password });
        this.setToken(data.access_token);
        return data;
    }

    logout() {
        this.clearToken();
    }

    // ── 配对 ──
    async createPair(type) {
        return this.request('POST', '/pairs/create', { type });
    }

    async joinPair(inviteCode) {
        return this.request('POST', '/pairs/join', { invite_code: inviteCode });
    }

    async getMyPair() {
        return this.request('GET', '/pairs/me');
    }

    // ── 解绑 ──
    async requestUnbind(pairId) {
        return this.request('POST', `/pairs/request-unbind?pair_id=${pairId}`);
    }

    async confirmUnbind(pairId) {
        return this.request('POST', `/pairs/confirm-unbind?pair_id=${pairId}`);
    }

    async cancelUnbind(pairId) {
        return this.request('POST', `/pairs/cancel-unbind?pair_id=${pairId}`);
    }

    async getUnbindStatus(pairId) {
        return this.request('GET', `/pairs/unbind-status?pair_id=${pairId}`);
    }

    // ── 打卡 ──
    async submitCheckin(pairId, content, moodTags = [], imageUrl = null, voiceUrl = null, moodScore = null, interactionFreq = null, interactionInitiative = null, deepConversation = null, taskCompleted = null) {
        const body = {
            pair_id: pairId,
            content,
            mood_tags: moodTags.length ? moodTags : null,
            image_url: imageUrl,
            voice_url: voiceUrl,
        };
        if (moodScore != null) body.mood_score = moodScore;
        if (interactionFreq != null) body.interaction_freq = interactionFreq;
        if (interactionInitiative != null) body.interaction_initiative = interactionInitiative;
        if (deepConversation != null) body.deep_conversation = deepConversation;
        if (taskCompleted != null) body.task_completed = taskCompleted;
        return this.request('POST', '/checkins/', body);
    }

    async getTodayStatus(pairId) {
        return this.request('GET', `/checkins/today?pair_id=${pairId}`);
    }

    async getCheckinHistory(pairId, limit = 14) {
        return this.request('GET', `/checkins/history?pair_id=${pairId}&limit=${limit}`);
    }

    async getCheckinStreak(pairId) {
        return this.request('GET', `/checkins/streak?pair_id=${pairId}`);
    }

    // ── 报告 ──
    async generateDailyReport(pairId) {
        return this.request('POST', `/reports/generate-daily?pair_id=${pairId}`);
    }

    async generateWeeklyReport(pairId) {
        return this.request('POST', `/reports/generate-weekly?pair_id=${pairId}`);
    }

    async generateMonthlyReport(pairId) {
        return this.request('POST', `/reports/generate-monthly?pair_id=${pairId}`);
    }

    async getLatestReport(pairId, type = 'daily') {
        return this.request('GET', `/reports/latest?pair_id=${pairId}&report_type=${type}`);
    }

    async getReportHistory(pairId, type = 'daily', limit = 7) {
        return this.request('GET', `/reports/history?pair_id=${pairId}&report_type=${type}&limit=${limit}`);
    }

    async getHealthTrend(pairId, days = 14) {
        return this.request('GET', `/reports/trend?pair_id=${pairId}&days=${days}`);
    }

    // ── 关系树 ──
    async getTreeStatus(pairId) {
        return this.request('GET', `/tree/status?pair_id=${pairId}`);
    }

    async waterTree(pairId) {
        return this.request('POST', `/tree/water?pair_id=${pairId}`);
    }

    // ── 危机预警（Phase 4 + 分级系统） ──
    async getCrisisStatus(pairId) {
        return this.request('GET', `/crisis/status/${pairId}`);
    }

    async getCrisisHistory(pairId, limit = 30) {
        return this.request('GET', `/crisis/history/${pairId}?limit=${limit}`);
    }

    async getCrisisAlerts(pairId, status = null, limit = 20) {
        let path = `/crisis/alerts/${pairId}?limit=${limit}`;
        if (status) path += `&status=${status}`;
        return this.request('GET', path);
    }

    async acknowledgeCrisisAlert(alertId) {
        return this.request('POST', `/crisis/alerts/${alertId}/acknowledge`);
    }

    async resolveCrisisAlert(alertId, note = '') {
        return this.request('POST', `/crisis/alerts/${alertId}/resolve`, { note });
    }

    async escalateCrisisAlert(alertId, reason = '') {
        return this.request('POST', `/crisis/alerts/${alertId}/escalate`, { reason });
    }

    async getCrisisResources() {
        return this.request('GET', `/crisis/resources`);
    }

    // ── 关系任务（Phase 4） ──
    async getDailyTasks(pairId) {
        return this.request('GET', `/tasks/daily/${pairId}`);
    }

    async completeTask(taskId) {
        return this.request('POST', `/tasks/${taskId}/complete`);
    }

    async getAttachmentAnalysis(pairId) {
        return this.request('GET', `/tasks/attachment/${pairId}`);
    }

    async triggerAttachmentAnalysis(pairId) {
        return this.request('POST', `/tasks/attachment/${pairId}/analyze`);
    }

    // ── 异地互动（Phase 4） ──
    async getLongDistanceDashboard(pairId) {
        return this.request('GET', `/longdistance/dashboard/${pairId}`);
    }

    async suggestActivity(pairId) {
        return this.request('POST', `/longdistance/suggest/${pairId}`);
    }

    async completeActivity(activityId) {
        return this.request('POST', `/longdistance/activity/${activityId}/complete`);
    }

    // ── 里程碑（Phase 4） ──
    async getMilestones(pairId) {
        return this.request('GET', `/milestones/${pairId}`);
    }

    async createMilestone(pairId, data) {
        return this.request('POST', `/milestones/${pairId}`, data);
    }

    async getMilestoneReport(milestoneId) {
        return this.request('GET', `/milestones/${milestoneId}/report`);
    }

    // ── 社群（Phase 4） ──
    async getCommunityTips(pairType) {
        return this.request('GET', `/community/tips?pair_type=${pairType || 'couple'}`);
    }

    async generateTip(pairType) {
        return this.request('POST', `/community/tips/generate?pair_type=${pairType || 'couple'}`);
    }

    async getNotifications() {
        return this.request('GET', '/community/notifications');
    }

    async markNotificationsRead() {
        return this.request('POST', '/community/notifications/read-all');
    }
}

const api = new ApiClient();
