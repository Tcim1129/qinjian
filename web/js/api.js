/**
 * 亲健 API 客户端 (Phase 2 增强)
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

    // ── 打卡 ──
    async submitCheckin(pairId, content, moodTags = [], imageUrl = null, voiceUrl = null) {
        return this.request('POST', '/checkins/', {
            pair_id: pairId,
            content,
            mood_tags: moodTags.length ? moodTags : null,
            image_url: imageUrl,
            voice_url: voiceUrl,
        });
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
}

const api = new ApiClient();
