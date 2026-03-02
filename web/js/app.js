/**
 * 亲健 · Web 原型主逻辑 (Phase 2 增强)
 */

// ── 状态管理 ──
const state = {
    currentPage: 'auth',
    pairs: [],           // 所有配对列表
    currentPair: null,   // 当前选中的配对
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
    if (pageId === 'profile') loadProfile();
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
        const pairs = await api.getMyPair();
        state.currentPairs = pairs || [];

        // 有活跃配对
        const activePairs = state.currentPairs.filter(p => p.status === 'active');
        const pendingPairs = state.currentPairs.filter(p => p.status === 'pending');

        if (activePairs.length > 0) {
            // 默认选择第一个活跃配对，或恢复上次选择的
            state.currentPair = activePairs[0];
            document.getElementById('tab-bar').style.display = 'flex';
            showPage('home');
        } else if (pendingPairs.length > 0) {
            // 有待处理的配对
            state.currentPair = pendingPairs[0];
            showPage('pair-waiting');
            document.getElementById('waiting-invite-code').textContent = state.currentPair.invite_code;
        } else {
            showPage('pair');
        }
    } catch {
        showPage('pair');
    }
}

// ── 配对 ──
function initPair() {
    // 渲染已有配对列表
    renderExistingPairs();

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
            state.currentPair = pair;
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
            state.currentPair = pair;
            document.getElementById('tab-bar').style.display = 'flex';
            showPage('home');
            showToast('配对成功！🎉');
        } catch (err) { showToast(err.message); }
    });
}

function renderExistingPairs() {
    const existingSection = document.getElementById('existing-pairs');
    const pairsList = document.getElementById('pairs-list');
    const createHeader = document.getElementById('pair-create-header');

    if (!existingSection || !pairsList) return;

    const activePairs = state.pairs.filter(p => p.status === 'active');

    if (activePairs.length === 0) {
        existingSection.style.display = 'none';
        if (createHeader) createHeader.style.display = 'block';
        return;
    }

    // 有配对时显示列表
    existingSection.style.display = 'block';
    if (createHeader) createHeader.style.display = 'none';

    const typeMap = { couple: '情侣', spouse: '夫妻', bestfriend: '挚友', parent: '育儿夫妻' };

    pairsList.innerHTML = activePairs.map(p => `
        <div class="card" style="padding: 14px; margin-bottom: 10px; cursor: pointer; display: flex; justify-content: space-between; align-items: center;"
             onclick="switchPair('${p.id}')">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 20px;">${typeMap[p.type] === '情侣' ? '💕' : typeMap[p.type] === '夫妻' ? '💍' : '🤜🤛'}</span>
                <span style="font-weight: 500;">${typeMap[p.type] || p.type}</span>
            </div>
            <span style="font-size: 13px; color: var(--text-muted);">${p.id === state.currentPair?.id ? '当前' : '切换 →'}</span>
        </div>
    `).join('');
}

function switchPair(pairId) {
    const pair = state.pairs.find(p => p.id === pairId);
    if (pair) {
        state.currentPair = pair;
        document.getElementById('tab-bar').style.display = 'flex';
        showPage('home');
        showToast('已切换关系');
    }
}

// ── 首页 ──
async function loadHome() {
    if (!state.currentPair) return;

    // 渲染配对选择器
    renderPairSelector();

    try {
        const [status, streak] = await Promise.all([
            api.getTodayStatus(state.currentPair.id),
            api.getCheckinStreak(state.currentPair.id).catch(() => ({ streak: 0 })),
        ]);
        state.todayStatus = status;
        renderHomeStatus(status, streak);
    } catch (err) {
        console.error('加载首页失败', err);
    }

    // 独立加载，不阻塞主流程
    loadTree();
    loadCrisisStatus();
    loadDailyTasks();
    loadTips();
    loadMilestones();
    loadNotifications();
}

function renderPairSelector() {
    const selector = document.getElementById('pair-selector');
    const select = document.getElementById('pair-select');
    if (!selector || !select) return;

    // 只有多个配对时才显示选择器
    const activePairs = state.pairs.filter(p => p.status === 'active');
    if (activePairs.length <= 1) {
        selector.style.display = 'none';
        return;
    }

    selector.style.display = 'block';

    // 填充选项
    const typeMap = { couple: '情侣', spouse: '夫妻', bestfriend: '挚友', parent: '育儿夫妻' };
    select.innerHTML = activePairs.map(p =>
        `<option value="${p.id}" ${p.id === state.currentPair?.id ? 'selected' : ''}>${typeMap[p.type] || p.type}</option>`
    ).join('');

    // 监听切换
    select.onchange = (e) => {
        const selectedId = e.target.value;
        state.currentPair = state.pairs.find(p => p.id === selectedId);
        loadHome();
        showToast('已切换关系');
    };
}

async function loadTree() {
    if (!state.currentPair) return;
    try {
        const tree = await api.getTreeStatus(state.currentPair.id);
        renderTree(tree);
    } catch { /* 静默失败 */ }
}

function renderTree(tree) {
    const card = document.getElementById('tree-card');
    if (!card) return;
    card.style.display = 'block';

    document.getElementById('tree-visual').textContent = tree.level_emoji || '🌰';
    document.getElementById('tree-level').textContent = tree.level_name || '种子';
    document.getElementById('tree-points').textContent = tree.growth_points || 0;

    const bar = document.getElementById('tree-progress-bar');
    bar.style.width = `${tree.progress_percent || 0}%`;

    const btn = document.getElementById('tree-water-btn');
    if (tree.can_water) {
        btn.disabled = false;
        btn.textContent = '💧 浇水';
        btn.onclick = waterTree;
    } else {
        btn.disabled = true;
        btn.textContent = '✅ 今日已浇水';
    }
}

async function waterTree() {
    if (!state.currentPair) return;
    const btn = document.getElementById('tree-water-btn');
    btn.disabled = true;
    btn.textContent = '浇水中...';
    try {
        const result = await api.waterTree(state.currentPair.id);
        showToast(`${result.level_emoji} +${result.points_added} 成长值${result.level_up ? ' 🎉 升级了！' : ''}`);
        loadTree();
    } catch (err) {
        showToast(err.message);
        btn.disabled = false;
        btn.textContent = '💧 浇水';
    }
}

// ── 危机预警（Phase 4） ──
async function loadCrisisStatus() {
    if (!state.currentPair) return;
    try {
        const crisis = await api.getCrisisStatus(state.currentPair.id);
        renderCrisisCard(crisis);
    } catch { /* 静默失败 */ }
}

function renderCrisisCard(crisis) {
    const card = document.getElementById('crisis-card');
    if (!card) return;

    const level = crisis.crisis_level || 'none';
    if (level === 'none') {
        card.style.display = 'none';
        return;
    }

    card.style.display = 'block';
    const badge = document.getElementById('crisis-badge');
    const levelMap = {
        mild: { text: '轻度预警', color: '#F59E0B', bg: '#FEF3C7' },
        moderate: { text: '中度预警', color: '#F97316', bg: '#FFF7ED' },
        severe: { text: '重度预警', color: '#EF4444', bg: '#FEF2F2' },
    };
    const info = levelMap[level] || levelMap.mild;
    badge.textContent = info.text;
    badge.style.background = info.bg;
    badge.style.color = info.color;
    card.style.borderLeft = `3px solid ${info.color}`;

    const intervention = crisis.intervention;
    const interventionDiv = document.getElementById('crisis-intervention');
    if (intervention && intervention.type !== 'none') {
        interventionDiv.style.display = 'block';
        document.getElementById('crisis-intervention-title').textContent = intervention.title || '干预建议';
        document.getElementById('crisis-intervention-desc').textContent = intervention.description || '';
        const items = intervention.action_items || [];
        document.getElementById('crisis-action-items').innerHTML = items.map(i => `<div>• ${i}</div>`).join('');
    } else {
        interventionDiv.style.display = 'none';
    }
}

// ── 每日任务（Phase 4） ──
async function loadDailyTasks() {
    if (!state.currentPair) return;
    try {
        const data = await api.getDailyTasks(state.currentPair.id);
        renderDailyTasks(data);
    } catch { /* 静默失败 */ }
}

function renderDailyTasks(data) {
    const card = document.getElementById('tasks-card');
    if (!card) return;

    const tasks = data.tasks || [];
    if (tasks.length === 0) {
        card.style.display = 'none';
        return;
    }

    card.style.display = 'block';

    // 依恋类型标签
    const attachLabel = document.getElementById('tasks-attachment-label');
    const typeLabels = { secure: '安全型', anxious: '焦虑型', avoidant: '回避型', fearful: '恐惧型' };
    if (data.attachment_a || data.attachment_b) {
        attachLabel.textContent = `${typeLabels[data.attachment_a] || '待分析'} + ${typeLabels[data.attachment_b] || '待分析'}`;
    }

    // 任务列表
    const list = document.getElementById('tasks-list');
    const categoryIcons = { communication: '💬', activity: '🎮', reflection: '🧘' };
    list.innerHTML = tasks.map(t => `
        <div id="task-${t.id}" style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--bg-primary);border-radius:var(--radius-md);cursor:pointer;
            ${t.status === 'completed' ? 'opacity:0.6;' : ''}" onclick="completeTaskItem('${t.id}')">
            <span style="font-size:18px">${t.status === 'completed' ? '✅' : (categoryIcons[t.category] || '🎯')}</span>
            <div style="flex:1">
                <div style="font-size:14px;font-weight:500;${t.status === 'completed' ? 'text-decoration:line-through;' : ''}">${t.title}</div>
                <div style="font-size:12px;color:var(--text-muted)">${t.description}</div>
            </div>
        </div>
    `).join('');

    // 组合洞察
    const insight = document.getElementById('tasks-insight');
    if (data.combination_insight) {
        insight.textContent = `💡 ${data.combination_insight}`;
    }
}

async function completeTaskItem(taskId) {
    try {
        await api.completeTask(taskId);
        const el = document.getElementById(`task-${taskId}`);
        if (el) {
            el.style.opacity = '0.6';
            el.querySelector('span').textContent = '✅';
            const title = el.querySelector('div > div');
            if (title) title.style.textDecoration = 'line-through';
        }
        showToast('任务完成 🎉');
    } catch (err) { showToast(err.message); }
}

// ── 社群技巧（Phase 4） ──
async function loadTips() {
    if (!state.currentPair) return;
    try {
        const data = await api.getCommunityTips(state.currentPair.type);
        renderTips(data.tips || []);
    } catch { /* 静默 */ }
}

function renderTips(tips) {
    const card = document.getElementById('tips-card');
    if (!card || !tips.length) return;
    card.style.display = 'block';
    const tip = tips[Math.floor(Math.random() * tips.length)];
    document.getElementById('tip-title').textContent = tip.title;
    document.getElementById('tip-text').textContent = tip.content;
}

// ── 里程碑（Phase 4） ──
async function loadMilestones() {
    if (!state.currentPair) return;
    try {
        const data = await api.getMilestones(state.currentPair.id);
        renderMilestones(data.milestones || []);
    } catch { /* 静默 */ }
}

function renderMilestones(milestones) {
    const card = document.getElementById('milestones-card');
    if (!card) return;
    card.style.display = 'block';
    const list = document.getElementById('milestones-list');
    if (!milestones.length) {
        list.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:13px;padding:12px">还没有里程碑，点击右上角添加一个吧 🌟</div>';
        return;
    }
    const typeEmoji = { anniversary: '💑', proposal: '💍', wedding: '💒', friendship_day: '🤝', custom: '⭐' };
    list.innerHTML = milestones.map(m => `
        <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--bg-card);border-radius:10px;cursor:pointer" onclick="viewMilestoneReport('${m.id}')">
            <span style="font-size:24px">${typeEmoji[m.type] || '⭐'}</span>
            <div style="flex:1">
                <div style="font-weight:500;font-size:13px">${m.title}</div>
                <div style="font-size:11px;color:var(--text-muted)">${m.date}</div>
            </div>
            <span style="font-size:11px;color:var(--text-muted)">查看回顾 →</span>
        </div>
    `).join('');
}

async function viewMilestoneReport(milestoneId) {
    try {
        showToast('正在生成回顾报告...');
        const data = await api.getMilestoneReport(milestoneId);
        const r = data.report || {};
        const msg = `📖 ${r.growth_story || '回忆正在生成中...'}\n\n🎯 优势: ${(r.strengths_discovered || []).join('、')}\n\n💌 ${r.blessing || ''}`;
        alert(msg);
    } catch (err) { showToast(err.message); }
}

// ── 通知中心（Phase 4） ──
async function loadNotifications() {
    const bell = document.getElementById('notification-bell');
    if (!bell) return;
    try {
        const data = await api.getNotifications();
        const notifications = data || [];
        if (notifications.length > 0) {
            bell.style.display = 'block';
            const unread = notifications.filter(n => !n.is_read).length;
            const badge = document.getElementById('notification-badge');
            if (unread > 0 && badge) {
                badge.style.display = 'flex';
                badge.textContent = unread > 9 ? '9+' : unread;
            }
            state.notifications = notifications;
        }
    } catch { /* 静默 */ }
}

function renderNotificationPanel() {
    const panel = document.getElementById('notification-panel');
    if (!panel) return;
    const isVisible = panel.style.display !== 'none';
    panel.style.display = isVisible ? 'none' : 'block';
    if (isVisible) return;
    const list = document.getElementById('notification-list');
    const notifications = state.notifications || [];
    if (!notifications.length) {
        list.innerHTML = '<div style="text-align:center;color:var(--text-muted);font-size:13px;padding:12px">暂无通知 🔕</div>';
        return;
    }
    const typeIcon = { crisis: '⚠️', task: '🎯', tip: '💡', milestone: '🎉' };
    list.innerHTML = notifications.slice(0, 20).map(n => `
        <div style="padding:8px 10px;border-radius:8px;background:${n.is_read ? 'transparent' : 'rgba(79,172,254,0.08)'};font-size:13px">
            <span>${typeIcon[n.type] || '📌'}</span> ${n.content}
            <div style="font-size:10px;color:var(--text-muted);margin-top:2px">${new Date(n.created_at).toLocaleDateString()}</div>
        </div>
    `).join('');
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

    // 报告按钮逻辑
    const reportBtn = document.getElementById('home-report-btn');
    if (status.both_done) {
        reportBtn.style.display = 'block';
        if (status.has_report) {
            reportBtn.textContent = '查看今日报告 📊';
            reportBtn.onclick = () => showPage('report');
        } else {
            reportBtn.textContent = 'AI 正在生成报告...✨';
            _pollForReport();
        }
    } else if (status.my_done && !status.partner_done) {
        // 单方打卡 → 显示个人情感日记入口
        reportBtn.style.display = 'block';
        if (status.has_solo_report) {
            reportBtn.textContent = '查看个人情感日记 📖';
            reportBtn.onclick = () => { state.viewSolo = true; showPage('report'); };
        } else {
            reportBtn.textContent = '个人日记生成中...📖';
            _pollForSoloReport();
        }
    } else {
        reportBtn.style.display = 'none';
    }
}

async function _pollForReport() {
    for (let i = 0; i < 10; i++) {
        await new Promise(r => setTimeout(r, 3000));
        try {
            const status = await api.getTodayStatus(state.currentPair.id);
            if (status.has_report) {
                const btn = document.getElementById('home-report-btn');
                btn.textContent = '查看今日报告 📊';
                btn.onclick = () => showPage('report');
                showToast('AI 报告已生成 🎉');
                return;
            }
        } catch { break; }
    }
}

async function _pollForSoloReport() {
    for (let i = 0; i < 10; i++) {
        await new Promise(r => setTimeout(r, 3000));
        try {
            const status = await api.getTodayStatus(state.currentPair.id);
            if (status.has_solo_report) {
                const btn = document.getElementById('home-report-btn');
                btn.textContent = '查看个人情感日记 📖';
                btn.onclick = () => { state.viewSolo = true; showPage('report'); };
                showToast('你的个人日记已生成 📖');
                return;
            }
        } catch { break; }
    }
}

// ── 打卡 ──
function initCheckin() {
    // 结构化选项通用处理（单选组）
    const radioGroups = [
        { selector: '.mood-score-option', groupClass: 'mood-score-option' },
        { selector: '.initiative-option', groupClass: 'initiative-option' },
        { selector: '.deep-conv-option', groupClass: 'deep-conv-option' },
        { selector: '.task-option', groupClass: 'task-option' },
    ];
    radioGroups.forEach(({ selector, groupClass }) => {
        document.querySelectorAll(selector).forEach(opt => {
            opt.addEventListener('click', () => {
                document.querySelectorAll(`.${groupClass}`).forEach(o => o.classList.remove('selected'));
                opt.classList.add('selected');
                const radio = opt.querySelector('input[type="radio"]');
                if (radio) radio.checked = true;
            });
        });
    });

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

        // 收集结构化字段
        const moodScoreEl = document.querySelector('input[name="mood-score"]:checked');
        const initiativeEl = document.querySelector('input[name="initiative"]:checked');
        const deepConvEl = document.querySelector('input[name="deep-conv"]:checked');
        const taskDoneEl = document.querySelector('input[name="task-done"]:checked');
        const interactionFreq = parseInt(document.getElementById('checkin-interaction-freq')?.value) || null;

        const btn = document.getElementById('checkin-submit-btn');
        btn.disabled = true;
        btn.textContent = '提交中...';

        try {
            await api.submitCheckin(
                state.currentPair.id, content, state.selectedMoods,
                state.uploadedImageUrl, state.uploadedVoiceUrl,
                moodScoreEl ? parseInt(moodScoreEl.value) : null,
                interactionFreq,
                initiativeEl ? initiativeEl.value : null,
                deepConvEl ? deepConvEl.value === 'true' : null,
                taskDoneEl ? taskDoneEl.value === 'true' : null,
            );
            showToast('打卡成功！💪');
            // 重置表单
            state.selectedMoods = [];
            state.uploadedImageUrl = null;
            state.uploadedVoiceUrl = null;
            document.querySelectorAll('.mood-tag').forEach(t => t.classList.remove('selected'));
            document.querySelectorAll('.mood-score-option, .initiative-option, .deep-conv-option, .task-option').forEach(t => t.classList.remove('selected'));
            document.querySelectorAll('#checkin-form input[type="radio"]').forEach(r => r.checked = false);
            document.getElementById('checkin-content').value = '';
            document.getElementById('checkin-image-preview').innerHTML = '';
            document.getElementById('checkin-voice-preview').innerHTML = '';
            if (document.getElementById('checkin-interaction-freq')) document.getElementById('checkin-interaction-freq').value = '';
            showPage('home');
        } catch (err) { showToast(err.message); }
        btn.disabled = false;
        btn.textContent = '提交打卡';
    });
}

// ── 报告 ──
async function loadReports() {
    if (!state.currentPair) return;
    const container = document.getElementById('report-content');

    // 如果从首页点击了 solo 日记入口
    if (state.viewSolo) {
        state.viewSolo = false;
        try {
            const soloReport = await api.getLatestReport(state.currentPair.id, 'solo').catch(() => null);
            if (soloReport && soloReport.status === 'completed') {
                renderSoloReport(soloReport);
                return;
            }
        } catch { }
    }

    try {
        const [dailyReport, soloReport, trendData] = await Promise.all([
            api.getLatestReport(state.currentPair.id, 'daily').catch(() => null),
            api.getLatestReport(state.currentPair.id, 'solo').catch(() => null),
            api.getHealthTrend(state.currentPair.id, 14).catch(() => ({ trend: [], direction: 'insufficient_data' })),
        ]);

        if (dailyReport && dailyReport.status === 'completed') {
            state.latestReport = dailyReport;
            renderReport(dailyReport, trendData);
        } else if (soloReport && soloReport.status === 'completed') {
            renderSoloReport(soloReport);
        } else {
            container.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📊</div>
          <div class="empty-title">暂无报告</div>
          <div class="empty-desc">每次打卡即可生成个人日记，双方完成后还有关系健康报告</div>
        </div>`;
        }
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

    ${c.emotional_sync ? `
    <div class="card">
      <h3 style="font-size: 15px; margin-bottom: 8px">💫 情绪同步度 ${c.emotional_sync.score || '--'}/100</h3>
      <p style="font-size: 14px; color: var(--text-secondary)">${c.emotional_sync.note || ''}</p>
    </div>` : ''}

    ${c.interaction_balance ? `
    <div class="card">
      <h3 style="font-size: 15px; margin-bottom: 8px">⚖️ 互动平衡度 ${c.interaction_balance.score || '--'}/100</h3>
      <p style="font-size: 14px; color: var(--text-secondary)">${c.interaction_balance.note || ''}</p>
    </div>` : ''}

    ${c.highlights?.length ? `
    <div class="card">
      <h3 style="font-size: 15px; margin-bottom: 10px">🌟 今日亮点</h3>
      ${c.highlights.map(h => `<div style="font-size: 14px; color: var(--text-secondary); padding: 4px 0">• ${h}</div>`).join('')}
    </div>` : ''}

    ${c.concerns?.length ? `
    <div class="card" style="border-left: 3px solid var(--warm-yellow)">
      <h3 style="font-size: 15px; margin-bottom: 10px; color: #8B6914">⚠️ 需要关注</h3>
      ${c.concerns.map(con => `<div style="font-size: 14px; color: var(--text-secondary); padding: 4px 0">• ${con}</div>`).join('')}
    </div>` : ''}

    ${c.risk_signals?.length ? `
    <div class="card" style="border-left: 3px solid var(--coral-500); background: var(--coral-50)">
      <h3 style="font-size: 15px; margin-bottom: 10px; color: var(--coral-600)">🚨 风险信号</h3>
      ${c.risk_signals.map(r => `<div style="font-size: 14px; color: var(--coral-600); padding: 4px 0">• ${r}</div>`).join('')}
      <p style="font-size: 12px; color: var(--text-muted); margin-top: 8px">建议关注戈特曼「末日四骑士」模型，必要时寻求专业咨询</p>
    </div>` : ''}

    ${c.theory_tag ? `
    <div style="text-align: center; margin: 12px 0">
      <span style="font-size: 12px; color: var(--text-muted); background: var(--bg-primary); padding: 4px 12px; border-radius: var(--radius-full)">📚 ${c.theory_tag}</span>
    </div>` : ''}

    <!-- 周报/月报按钮 -->
    <div style="display: flex; gap: 10px; margin-top: 16px">
      <button onclick="generateWeekly()" class="btn btn-outline" style="flex: 1; font-size: 13px">📋 生成周报</button>
      <button onclick="generateMonthly()" class="btn btn-outline" style="flex: 1; font-size: 13px">📑 生成月报</button>
    </div>

    <div style="text-align: center; margin-top: 16px">
      <span class="privacy-badge">🔒 数据已加密 · 仅AI可见原始内容</span>
    </div>
    <div style="text-align: center; margin-top: 8px">
      <span style="font-size: 11px; color: var(--text-muted)">🤖 本报告由AI生成，仅供参考</span>
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

function renderSoloReport(report) {
    const c = report.content;
    const container = document.getElementById('report-content');

    container.innerHTML = `
    <div style="text-align:center;margin-bottom:16px">
      <span class="btn-sm btn-secondary" onclick="state.viewSolo=false;loadReports()" style="cursor:pointer;border-radius:var(--radius-full);padding:6px 16px;font-size:12px">← 查看关系报告</span>
    </div>

    <div class="health-gauge">
      <div class="gauge-circle" style="--score: ${c.health_score || 50}">
        <span class="gauge-score">${c.health_score || '--'}</span>
        <span class="gauge-label">个人情绪指数</span>
      </div>
    </div>

    <div class="card card-accent" style="text-align:center;">
      <div style="font-size:28px;margin-bottom:8px">${getMoodEmoji(c.mood?.score)} ${c.mood?.label || ''}</div>
      <div style="font-size:14px;opacity:0.9">情绪得分 ${c.mood?.score || '--'}/10</div>
    </div>

    ${c.self_insight ? `<div class="report-insight">${c.self_insight}</div>` : ''}

    ${c.emotional_pattern ? `
    <div class="card">
      <h3 style="font-size: 15px; margin-bottom: 8px">🧠 情绪模式解读</h3>
      <p style="font-size: 14px; color: var(--text-secondary); line-height: 1.6">${c.emotional_pattern}</p>
      ${c.theory_tag ? `<div style="font-size:12px;color:var(--text-muted);margin-top:8px">📚 ${c.theory_tag}</div>` : ''}
    </div>` : ''}

    ${c.self_care_tip ? `<div class="report-suggestion">${c.self_care_tip}</div>` : ''}

    ${c.relationship_note ? `
    <div class="card" style="text-align:center">
      <div style="font-size:14px;line-height:1.6;color:var(--text-secondary)">💕 ${c.relationship_note}</div>
    </div>` : ''}

<div style="text-align: center; margin-top: 16px">
      <span class="privacy-badge">🔒 仅你可见 · 对方无法查看你的个人日记</span>
    </div>
    <div style="text-align: center; margin-top: 8px">
      <span style="font-size: 11px; color: var(--text-muted)">🤖 本日记由AI生成，仅供参考</span>
    </div>
  `;
}

// ── 报告生成 ──
async function triggerReport() {
    if (!state.currentPair) return;
    const btn = document.getElementById('home-report-btn');
    btn.disabled = true;
    btn.textContent = '深度分析中...';

    try {
        const report = await api.generateDailyReport(state.currentPair.id);
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
    if (!state.currentPair) return;
    try {
        showToast('提取周报特征...');
        const report = await api.generateWeeklyReport(state.currentPair.id);
        if (report.status === 'pending') {
            showToast('大模型深入汇总中，请耐心等候...⏳', 5000);
            _pollReportStatus('weekly', null, null, showWeeklyReport);
        } else {
            showWeeklyReport(report);
        }
    } catch (err) { showToast(err.message); }
}

async function generateMonthly() {
    if (!state.currentPair) return;
    try {
        showToast('提取月报特征...');
        const report = await api.generateMonthlyReport(state.currentPair.id);
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
            const r = await api.getLatestReport(state.currentPair.id, type);
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
    <div style="text-align: center; margin-top: 16px">
      <span style="font-size: 11px; color: var(--text-muted)">🤖 本周报由AI生成，仅供参考</span>
    </div>
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
    <div style="text-align: center; margin-top: 16px">
      <span style="font-size: 11px; color: var(--text-muted)">🤖 本月报由AI生成，仅供参考</span>
    </div>
`;
}

// ── 个人中心 ──
async function loadProfile() {
    if (!state.currentPair) return;

    // 显示昵称（Mod 8）
    const nicknameEl = document.querySelector('#page-profile .card:first-of-type div[style*="font-size: 18px"]');
    if (nicknameEl) {
        try {
            const me = await api.request('GET', '/auth/me');
            nicknameEl.textContent = me.nickname || '用户';
        } catch { /* ignore */ }
    }

    // 配对类型显示
    const typeMap = { couple: '情侣', spouse: '夫妻', bestfriend: '挚友' };
    document.getElementById('profile-pair-type').textContent = typeMap[state.currentPair.type] || state.currentPair.type;
    document.getElementById('profile-pair-status').textContent = '已配对';

    // 解绑状态（Mod 5）
    await loadUnbindStatus();
}

async function loadUnbindStatus() {
    const section = document.getElementById('unbind-section');
    const statusText = document.getElementById('unbind-status-text');
    const actions = document.getElementById('unbind-actions');
    if (!section || !state.currentPair) return;

    try {
        const status = await api.getUnbindStatus();
        if (!status.has_request) {
            section.style.display = 'block';
            statusText.textContent = '解除配对后双方将无法继续打卡和查看报告';
            actions.innerHTML = `<button class="btn btn-outline btn-sm" style="color:var(--coral-500);border-color:var(--coral-400)" onclick="handleRequestUnbind()">发起解绑</button>`;
        } else {
            section.style.display = 'block';
            if (status.requested_by_me) {
                statusText.textContent = `你已发起解绑请求，冷静期剩余 ${status.days_remaining} 天。对方确认后立即生效，或冷静期结束后你可强制解绑。`;
                if (status.can_force_unbind) {
                    actions.innerHTML = `
                        <button class="btn btn-outline btn-sm" style="color:var(--coral-500)" onclick="handleConfirmUnbind()">确认解绑</button>
                        <button class="btn btn-outline btn-sm" onclick="handleCancelUnbind()">撤回请求</button>
                    `;
                } else {
                    actions.innerHTML = `<button class="btn btn-outline btn-sm" onclick="handleCancelUnbind()">撤回请求</button>`;
                }
            } else {
                statusText.textContent = '对方已发起解绑请求，确认后立即解除配对关系。';
                actions.innerHTML = `
                    <button class="btn btn-outline btn-sm" style="color:var(--coral-500)" onclick="handleConfirmUnbind()">确认解绑</button>
                `;
            }
        }
    } catch (err) {
        console.error('加载解绑状态失败', err);
    }
}

async function handleRequestUnbind() {
    if (!confirm('确定要发起解绑吗？对方确认后立即生效，或等待7天冷静期后你可强制解绑。')) return;
    try {
        await api.requestUnbind();
        showToast('解绑请求已发起');
        loadUnbindStatus();
    } catch (err) { showToast(err.message); }
}

async function handleConfirmUnbind() {
    if (!confirm('确定要解除配对吗？此操作不可撤销。')) return;
    try {
        const result = await api.confirmUnbind();
        showToast(result.message);
        state.currentPair = null;
        document.getElementById('tab-bar').style.display = 'none';
        showPage('pair');
    } catch (err) { showToast(err.message); }
}

async function handleCancelUnbind() {
    try {
        await api.cancelUnbind();
        showToast('解绑请求已撤回');
        loadUnbindStatus();
    } catch (err) { showToast(err.message); }
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
    // Phase 4 事件绑定
    document.getElementById('notification-btn')?.addEventListener('click', renderNotificationPanel);
    document.getElementById('read-all-btn')?.addEventListener('click', async () => {
        await api.markNotificationsRead(); showToast('已全部标记为已读'); loadNotifications();
    });
    document.getElementById('tips-refresh-btn')?.addEventListener('click', loadTips);
    document.getElementById('add-milestone-btn')?.addEventListener('click', () => {
        const title = prompt('里程碑名称（如：在一起100天）');
        if (!title) return;
        const dateStr = prompt('日期（YYYY-MM-DD）', new Date().toISOString().split('T')[0]);
        if (!dateStr) return;
        api.createMilestone(state.currentPair.id, { title, date: dateStr, type: 'custom' })
            .then(() => { showToast('里程碑已添加 🎉'); loadMilestones(); })
            .catch(err => showToast(err.message));
    });

    if (api.isLoggedIn()) {
        checkPairAndRoute();
    } else {
        showPage('auth');
    }
});
