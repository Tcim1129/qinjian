/**
 * 亲健 · Web 原型主逻辑 (Phase 2 增强)
 */

// ── 状态管理 ──
const state = {
    currentPage: 'auth',
    pair: null,
    todayStatus: null,
    latestReport: null,
    selectedMoods: [],
    uploadedImageUrl: null,
    uploadedVoiceUrl: null,
};

// ── 页面路由 ──
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = document.getElementById(`page-${pageId}`);
    if (page) {
        page.classList.add('active');
        state.currentPage = pageId;
    }
    document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
    const tab = document.querySelector(`[data-page="${pageId}"]`);
    if (tab) tab.classList.add('active');

    if (pageId === 'home') loadHome();
    if (pageId === 'report') loadReports();
}

// ── Toast ──
function showToast(msg, duration = 2500) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

// ── 认证 ──
function initAuth() {
    const form = document.getElementById('auth-form');
    let isLogin = true;

    document.addEventListener('click', (e) => {
        if (e.target.id === 'auth-toggle-link') {
            e.preventDefault();
            isLogin = !isLogin;
            document.getElementById('auth-title').textContent = isLogin ? '欢迎回来' : '加入亲健';
            document.getElementById('auth-nickname-group').style.display = isLogin ? 'none' : 'block';
            document.getElementById('auth-submit-btn').textContent = isLogin ? '登录' : '注册';
            document.getElementById('auth-toggle-text').innerHTML = isLogin
                ? '还没有账号？<a href="#" id="auth-toggle-link">立即注册</a>'
                : '已有账号？<a href="#" id="auth-toggle-link">登录</a>';
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('auth-email').value.trim();
        const password = document.getElementById('auth-password').value;
        const btn = document.getElementById('auth-submit-btn');
        btn.disabled = true;

        try {
            if (isLogin) {
                await api.login(email, password);
                showToast('登录成功 🎉');
            } else {
                const nickname = document.getElementById('auth-nickname').value.trim();
                if (!nickname) { showToast('请输入昵称'); btn.disabled = false; return; }
                await api.register(email, nickname, password);
                showToast('注册成功 🎉');
            }
            await checkPairAndRoute();
        } catch (err) {
            showToast(err.message);
        }
        btn.disabled = false;
    });
}

// ── 路由 ──
async function checkPairAndRoute() {
    try {
        const pair = await api.getMyPair();
        state.pair = pair;
        if (pair && pair.status === 'active') {
            document.getElementById('tab-bar').style.display = 'flex';
            showPage('home');
        } else if (pair && pair.status === 'pending') {
            showPage('pair-waiting');
            document.getElementById('waiting-invite-code').textContent = pair.invite_code;
        } else {
            showPage('pair');
        }
    } catch {
        showPage('pair');
    }
}

// ── 配对 ──
function initPair() {
    // 关系类型选择
    document.querySelectorAll('input[name="pair-type"]').forEach(radio => {
        radio.addEventListener('change', () => {
            document.querySelectorAll('.pair-type-option').forEach(opt => opt.classList.remove('selected'));
            radio.closest('.pair-type-option').classList.add('selected');
        });
    });

    document.getElementById('pair-create-btn').addEventListener('click', async () => {
        const type = document.querySelector('input[name="pair-type"]:checked')?.value || 'couple';
        try {
            const pair = await api.createPair(type);
            state.pair = pair;
            showPage('pair-waiting');
            document.getElementById('waiting-invite-code').textContent = pair.invite_code;
            showToast('配对已创建，分享邀请码给对方');
        } catch (err) { showToast(err.message); }
    });

    document.getElementById('pair-join-btn').addEventListener('click', async () => {
        const code = document.getElementById('pair-join-code').value.trim();
        if (!code) { showToast('请输入邀请码'); return; }
        try {
            const pair = await api.joinPair(code);
            state.pair = pair;
            document.getElementById('tab-bar').style.display = 'flex';
            showPage('home');
            showToast('配对成功！🎉');
        } catch (err) { showToast(err.message); }
    });
}

// ── 首页 ──
async function loadHome() {
    if (!state.pair) return;

    try {
        const [status, streak] = await Promise.all([
            api.getTodayStatus(state.pair.id),
            api.getCheckinStreak(state.pair.id).catch(() => ({ streak: 0 })),
        ]);
        state.todayStatus = status;
        renderHomeStatus(status, streak);
    } catch (err) {
        console.error('加载首页失败', err);
    }
}

function renderHomeStatus(status, streak) {
    const myDot = document.getElementById('status-my-dot');
    const partnerDot = document.getElementById('status-partner-dot');

    myDot.className = `status-dot ${status.my_done ? 'done' : ''}`;
    partnerDot.className = `status-dot ${status.partner_done ? 'done' : status.my_done ? 'waiting' : ''}`;

    document.getElementById('status-my-label').textContent = status.my_done ? '已打卡 ✓' : '未打卡';
    document.getElementById('status-partner-label').textContent = status.partner_done ? '已打卡 ✓' : '等待中...';

    const checkinBtn = document.getElementById('home-checkin-btn');
    if (status.my_done) {
        checkinBtn.textContent = '今日已打卡 ✓';
        checkinBtn.disabled = true;
    } else {
        checkinBtn.textContent = '开始打卡';
        checkinBtn.disabled = false;
    }

    // 连续打卡天数
    const streakEl = document.getElementById('streak-count');
    if (streakEl) streakEl.textContent = streak.streak || 0;

    // 双方都完成 → 显示报告按钮
    const reportBtn = document.getElementById('home-report-btn');
    if (status.both_done) {
        reportBtn.style.display = 'block';
        if (status.has_report) {
            reportBtn.textContent = '查看今日报告 📊';
        } else {
            reportBtn.textContent = 'AI 正在生成报告...✨';
            // 轮询检查报告
            _pollForReport();
        }
    } else {
        reportBtn.style.display = 'none';
    }
}

async function _pollForReport() {
    for (let i = 0; i < 10; i++) {
        await new Promise(r => setTimeout(r, 3000));
        try {
            const status = await api.getTodayStatus(state.pair.id);
            if (status.has_report) {
                const btn = document.getElementById('home-report-btn');
                btn.textContent = '查看今日报告 📊';
                showToast('AI 报告已生成 🎉');
                return;
            }
        } catch { break; }
    }
}

// ── 打卡 ──
function initCheckin() {
    // 情绪标签
    document.querySelectorAll('.mood-tag').forEach(tag => {
        tag.addEventListener('click', () => {
            tag.classList.toggle('selected');
            const mood = tag.dataset.mood;
            if (state.selectedMoods.includes(mood)) {
                state.selectedMoods = state.selectedMoods.filter(m => m !== mood);
            } else {
                state.selectedMoods.push(mood);
            }
        });
    });

    // 图片上传
    const imageInput = document.getElementById('checkin-image-input');
    const imagePreview = document.getElementById('checkin-image-preview');
    document.getElementById('checkin-image-btn')?.addEventListener('click', () => imageInput.click());
    imageInput?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (file.size > 10 * 1024 * 1024) { showToast('图片不能超过10MB'); return; }

        try {
            showToast('上传中...');
            const result = await api.uploadFile('image', file);
            state.uploadedImageUrl = result.url;
            imagePreview.innerHTML = `<img src="${API_BASE.replace('/api/v1', '')}${result.url}" style="width:100%;border-radius:var(--radius-md);margin-top:8px">`;
            showToast('图片已添加 📷');
        } catch (err) { showToast(err.message); }
    });

    // 语音上传
    const voiceInput = document.getElementById('checkin-voice-input');
    document.getElementById('checkin-voice-btn')?.addEventListener('click', () => voiceInput.click());
    voiceInput?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
            showToast('上传中...');
            const result = await api.uploadFile('voice', file);
            state.uploadedVoiceUrl = result.url;
            document.getElementById('checkin-voice-preview').innerHTML = `<div style="padding:8px;background:var(--mint-light);border-radius:var(--radius-md);margin-top:8px;font-size:13px;color:var(--mint)">🎤 语音已添加 (${(file.size / 1024).toFixed(0)}KB)</div>`;
            showToast('语音已添加 🎤');
        } catch (err) { showToast(err.message); }
    });

    // 提交打卡
    document.getElementById('checkin-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const content = document.getElementById('checkin-content').value.trim();
        if (!content) { showToast('写点什么吧 ✍️'); return; }

        const btn = document.getElementById('checkin-submit-btn');
        btn.disabled = true;
        btn.textContent = '提交中...';

        try {
            await api.submitCheckin(state.pair.id, content, state.selectedMoods, state.uploadedImageUrl, state.uploadedVoiceUrl);
            showToast('打卡成功！💪');
            // 重置表单
            state.selectedMoods = [];
            state.uploadedImageUrl = null;
            state.uploadedVoiceUrl = null;
            document.querySelectorAll('.mood-tag').forEach(t => t.classList.remove('selected'));
            document.getElementById('checkin-content').value = '';
            document.getElementById('checkin-image-preview').innerHTML = '';
            document.getElementById('checkin-voice-preview').innerHTML = '';
            showPage('home');
        } catch (err) { showToast(err.message); }
        btn.disabled = false;
        btn.textContent = '提交打卡';
    });
}

// ── 报告 ──
async function loadReports() {
    if (!state.pair) return;
    const container = document.getElementById('report-content');

    try {
        const [dailyReport, trendData] = await Promise.all([
            api.getLatestReport(state.pair.id, 'daily').catch(() => null),
            api.getHealthTrend(state.pair.id, 14).catch(() => ({ trend: [], direction: 'insufficient_data' })),
        ]);

        if (!dailyReport) {
            container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📊</div>
          <div class="empty-title">暂无报告</div>
          <div class="empty-desc">双方完成打卡后即可生成 AI 健康报告</div>
        </div>`;
            return;
        }

        state.latestReport = dailyReport;
        renderReport(dailyReport, trendData);
    } catch (err) {
        console.error('加载报告失败', err);
    }
}

function renderReport(report, trendData) {
    const c = report.content;
    const container = document.getElementById('report-content');

    // 趋势图 SVG
    let trendSvg = '';
    if (trendData?.trend?.length >= 2) {
        const points = trendData.trend;
        const w = 320, h = 80, pad = 10;
        const maxScore = 100, minScore = 0;
        const coords = points.map((p, i) => {
            const x = pad + (i / (points.length - 1)) * (w - 2 * pad);
            const y = h - pad - ((p.score - minScore) / (maxScore - minScore)) * (h - 2 * pad);
            return `${x},${y}`;
        });
        const directionEmoji = trendData.direction === 'improving' ? '📈' : trendData.direction === 'declining' ? '📉' : '➡️';
        const directionText = trendData.direction === 'improving' ? '持续上升' : trendData.direction === 'declining' ? '需要关注' : '保持稳定';

        trendSvg = `
      <div class="card" style="margin-top: 16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <h3 style="font-size: 15px">${directionEmoji} 健康趋势</h3>
          <span style="font-size:12px;color:var(--text-muted)">${directionText} · 近${points.length}天</span>
        </div>
        <svg viewBox="0 0 ${w} ${h}" style="width:100%;height:80px">
          <defs>
            <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="var(--coral-500)" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="var(--coral-500)" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <polygon points="${coords.join(' ')} ${w - pad},${h - pad} ${pad},${h - pad}" fill="url(#trendGrad)"/>
          <polyline points="${coords.join(' ')}" fill="none" stroke="var(--coral-500)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          ${points.map((p, i) => {
            const [x, y] = coords[i].split(',');
            return `<circle cx="${x}" cy="${y}" r="3" fill="var(--coral-500)"/>`;
        }).join('')}
        </svg>
      </div>`;
    }

    container.innerHTML = `
    <div class="health-gauge">
      <div class="gauge-circle" style="--score: ${c.health_score || 50}">
        <span class="gauge-score">${c.health_score || '--'}</span>
        <span class="gauge-label">健康指数</span>
      </div>
    </div>

    ${c.insight ? `<div class="report-insight">${c.insight}</div>` : ''}
    ${c.suggestion ? `<div class="report-suggestion">${c.suggestion}</div>` : ''}

    ${trendSvg}

    <div class="card" style="margin-top: 16px">
      <h3 style="font-size: 15px; margin-bottom: 12px">情绪分析</h3>
      <div class="checkin-status">
        <div class="status-item">
          <div style="font-size: 24px; margin-bottom: 4px">${getMoodEmoji(c.mood_a?.score)}</div>
          <div style="font-size: 13px; color: var(--text-secondary)">A方: ${c.mood_a?.label || '--'}</div>
          <div style="font-size: 20px; font-weight: 600; margin-top: 4px">${c.mood_a?.score || '--'}/10</div>
        </div>
        <div class="status-item">
          <div style="font-size: 24px; margin-bottom: 4px">${getMoodEmoji(c.mood_b?.score)}</div>
          <div style="font-size: 13px; color: var(--text-secondary)">B方: ${c.mood_b?.label || '--'}</div>
          <div style="font-size: 20px; font-weight: 600; margin-top: 4px">${c.mood_b?.score || '--'}/10</div>
        </div>
      </div>
    </div>

    ${c.communication_quality ? `
    <div class="card">
      <h3 style="font-size: 15px; margin-bottom: 8px">💬 沟通质量 ${c.communication_quality.score || '--'}/10</h3>
      <p style="font-size: 14px; color: var(--text-secondary)">${c.communication_quality.note || ''}</p>
    </div>` : ''}

    ${c.highlights?.length ? `
    <div class="card">
      <h3 style="font-size: 15px; margin-bottom: 10px">🌟 今日亮点</h3>
      ${c.highlights.map(h => `<div style="font-size: 14px; color: var(--text-secondary); padding: 4px 0">• ${h}</div>`).join('')}
    </div>` : ''}

    <!-- 周报/月报按钮 -->
    <div style="display: flex; gap: 10px; margin-top: 16px">
      <button onclick="generateWeekly()" class="btn btn-outline" style="flex: 1; font-size: 13px">📋 生成周报</button>
      <button onclick="generateMonthly()" class="btn btn-outline" style="flex: 1; font-size: 13px">📑 生成月报</button>
    </div>

    <div style="text-align: center; margin-top: 16px">
      <span class="privacy-badge">🔒 数据已加密 · 仅AI可见原始内容</span>
    </div>
  `;
}

function getMoodEmoji(score) {
    if (!score) return '😐';
    if (score >= 8) return '😊';
    if (score >= 6) return '🙂';
    if (score >= 4) return '😐';
    if (score >= 2) return '😔';
    return '😢';
}

// ── 报告生成 ──
async function triggerReport() {
    if (!state.pair) return;
    const btn = document.getElementById('home-report-btn');
    btn.disabled = true;
    btn.textContent = '深度分析中...';

    try {
        const report = await api.generateDailyReport(state.pair.id);
        if (report.status === 'pending') {
            showToast('AI生成中，预计需等几十秒 ⏳', 5000);
            _pollReportStatus('daily', btn, '查看今日报告 📊', () => showPage('report'));
        } else {
            showToast('报告已生成 📊');
            showPage('report');
            btn.disabled = false;
            btn.textContent = '查看今日报告 📊';
        }
    } catch (err) {
        showToast(err.message);
        btn.disabled = false;
        btn.textContent = '重新生成报告';
    }
}

async function generateWeekly() {
    if (!state.pair) return;
    try {
        showToast('提取周报特征...');
        const report = await api.generateWeeklyReport(state.pair.id);
        if (report.status === 'pending') {
            showToast('大模型深入汇总中，请耐心等候...⏳', 5000);
            _pollReportStatus('weekly', null, null, showWeeklyReport);
        } else {
            showWeeklyReport(report);
        }
    } catch (err) { showToast(err.message); }
}

async function generateMonthly() {
    if (!state.pair) return;
    try {
        showToast('提取月报特征...');
        const report = await api.generateMonthlyReport(state.pair.id);
        if (report.status === 'pending') {
            showToast('计算月度长周期趋势，请稍候...⏳', 5000);
            _pollReportStatus('monthly', null, null, showMonthlyReport);
        } else {
            showMonthlyReport(report);
        }
    } catch (err) { showToast(err.message); }
}

function _pollReportStatus(type, btn, btnText, callback) {
    let attempts = 0;
    const interval = setInterval(async () => {
        attempts++;
        try {
            const r = await api.getLatestReport(state.pair.id, type);
            if (r && r.status === 'completed') {
                clearInterval(interval);
                showToast(`分析完成 🎉`);
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = btnText;
                }
                if (callback) callback(r);
            } else if (r && r.status === 'failed') {
                clearInterval(interval);
                showToast('AI 分析失败，可能有网络波动', 4000);
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = '重新生成报告';
                }
            }
        } catch { /* 忽略瞬时断网错误 */ }

        if (attempts > 30) { // 90 秒超时
            clearInterval(interval);
            showToast('请求超时，请稍后刷新页面查看');
            if (btn) {
                btn.disabled = false;
                btn.textContent = '查看/重新生成';
            }
        }
    }, 3000);
}

function showWeeklyReport(report) {
    const c = report.content;
    const container = document.getElementById('report-content');
    const dirEmoji = c.trend === 'improving' ? '📈' : c.trend === 'declining' ? '📉' : '➡️';

    container.innerHTML = `
    <div style="text-align:center;margin-bottom:16px">
      <span class="btn-sm btn-secondary" onclick="loadReports()" style="cursor:pointer;border-radius:var(--radius-full);padding:6px 16px;font-size:12px">← 返回日报</span>
    </div>
    <div class="health-gauge">
      <div class="gauge-circle" style="--score: ${c.overall_health_score || 50}">
        <span class="gauge-score">${c.overall_health_score || '--'}</span>
        <span class="gauge-label">周健康指数</span>
      </div>
    </div>
    <div class="card card-accent" style="text-align:center;">
      <div style="font-size:14px;opacity:0.9">${dirEmoji} 本周趋势</div>
      <div style="font-size:15px;margin-top:8px">${c.trend_description || ''}</div>
    </div>
    ${c.encouragement ? `<div class="report-insight">${c.encouragement}</div>` : ''}
    ${c.weekly_highlights?.length ? `
    <div class="card">
      <h3 style="font-size:15px;margin-bottom:10px">🌟 本周亮点</h3>
      ${c.weekly_highlights.map(h => `<div style="font-size:14px;color:var(--text-secondary);padding:4px 0">• ${h}</div>`).join('')}
    </div>` : ''}
    ${c.action_plan?.length ? `
    <div class="card">
      <h3 style="font-size:15px;margin-bottom:10px">✨ 行动建议</h3>
      ${c.action_plan.map(a => `<div class="report-suggestion" style="margin:6px 0">${a}</div>`).join('')}
    </div>` : ''}
  `;
}

function showMonthlyReport(report) {
    const c = report.content;
    const container = document.getElementById('report-content');

    container.innerHTML = `
    <div style="text-align:center;margin-bottom:16px">
      <span class="btn-sm btn-secondary" onclick="loadReports()" style="cursor:pointer;border-radius:var(--radius-full);padding:6px 16px;font-size:12px">← 返回日报</span>
    </div>
    <div class="health-gauge">
      <div class="gauge-circle" style="--score: ${c.overall_health_score || 50}">
        <span class="gauge-score">${c.overall_health_score || '--'}</span>
        <span class="gauge-label">月健康指数</span>
      </div>
    </div>
    ${c.executive_summary ? `<div class="card card-accent"><div style="font-size:14px;line-height:1.6">${c.executive_summary}</div></div>` : ''}
    ${c.strengths?.length ? `
    <div class="card">
      <h3 style="font-size:15px;margin-bottom:10px">💪 关系优势</h3>
      ${c.strengths.map(s => `<div style="font-size:14px;color:var(--text-secondary);padding:4px 0">• ${s}</div>`).join('')}
    </div>` : ''}
    ${c.growth_areas?.length ? `
    <div class="card">
      <h3 style="font-size:15px;margin-bottom:10px">🌱 成长空间</h3>
      ${c.growth_areas.map(g => `<div style="font-size:14px;color:var(--text-secondary);padding:4px 0">• ${g}</div>`).join('')}
    </div>` : ''}
    ${c.next_month_goals?.length ? `
    <div class="card">
      <h3 style="font-size:15px;margin-bottom:10px">🎯 下月目标</h3>
      ${c.next_month_goals.map(g => `<div class="report-suggestion" style="margin:6px 0">${g}</div>`).join('')}
    </div>` : ''}
    ${c.professional_note ? `<div class="report-insight">${c.professional_note}</div>` : ''}
  `;
}

// ── 初始化 ──
document.addEventListener('DOMContentLoaded', () => {
    initAuth();
    initPair();
    initCheckin();

    document.querySelectorAll('.tab-item').forEach(tab => {
        tab.addEventListener('click', () => {
            const page = tab.dataset.page;
            if (page === 'checkin' && state.todayStatus?.my_done) {
                showToast('今天已经打过卡了 ✓');
                return;
            }
            showPage(page);
        });
    });

    document.getElementById('home-checkin-btn')?.addEventListener('click', () => showPage('checkin'));
    document.getElementById('home-report-btn')?.addEventListener('click', triggerReport);

    if (api.isLoggedIn()) {
        checkPairAndRoute();
    } else {
        showPage('auth');
    }
});
