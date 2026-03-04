/**
 * 亲健 · Web 原型主逻辑 (Phase 2 增强 + Phase 1.4 设计重构)
 * ──────────────────────────────────────────────────
 * 变更说明:
 *   - modal 使用 .active 类切换 (1.4a)
 *   - 所有 style.display 切换改为 .hidden 类 (1.4b)
 *   - .mood-tag 选择器 → .tag[data-mood] (1.4c)
 *   - 旧 CSS 变量名全部替换为新设计系统变量 (1.4d)
 *   - 所有 render 函数的 inline style / emoji 替换为 CSS 类 + SVG 图标 (1.4e-n)
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
    pairPollingTimer: null,
};

// ── 工具函数：显示/隐藏元素 ──
function show(el) {
    if (el) el.classList.remove('hidden');
}
function hide(el) {
    if (el) el.classList.add('hidden');
}

/** 生成内联 SVG 图标引用 */
function svgIcon(id, cls = '') {
    const extra = cls ? ` ${cls}` : '';
    return `<svg class="icon${extra}"><use href="#${id}"/></svg>`;
}

// ── 通用模态框 (1.4a) ──
function openModal(html) {
    const overlay = document.getElementById('modal-overlay');
    const body = document.getElementById('modal-body');
    if (!overlay || !body) return;
    body.innerHTML = html;
    overlay.classList.add('active');
}
function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) overlay.classList.remove('active');
}

/**
 * 显示带输入框的模态框，返回 Promise<object|null> (1.4l)
 * fields: [{ key, label, type, placeholder, defaultValue }]
 */
function openInputModal(title, fields) {
    return new Promise(resolve => {
        const fieldHtml = fields.map(f => `
            <div class="form-group">
                <label class="form-label">${f.label}</label>
                <input id="modal-input-${f.key}" class="form-input w-full"
                    type="${f.type || 'text'}"
                    placeholder="${f.placeholder || ''}"
                    value="${f.defaultValue || ''}">
            </div>
        `).join('');
        openModal(`
            <div class="modal-title text-center">${title}</div>
            ${fieldHtml}
            <div class="flex gap-2 mt-4">
                <button class="btn btn-secondary flex-1" onclick="closeModal();window._modalResolve(null)">取消</button>
                <button class="btn btn-primary flex-1" onclick="
                    var result = {};
                    ${fields.map(f => `result['${f.key}'] = document.getElementById('modal-input-${f.key}').value;`).join('')}
                    closeModal();
                    window._modalResolve(result);
                ">确认</button>
            </div>
        `);
        window._modalResolve = resolve;
        setTimeout(() => {
            const first = document.getElementById(`modal-input-${fields[0].key}`);
            if (first) first.focus();
        }, 100);
    });
}

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

    // Phase 2 页面加载钩子
    if (typeof onPageEnter === 'function') onPageEnter(pageId);

    // B6: 配对等待页面轮询
    if (pageId === 'pair-waiting') {
        startPairPolling();
    } else {
        stopPairPolling();
    }
}

// ── 配对等待轮询 (B6) ──
function startPairPolling() {
    stopPairPolling();
    state.pairPollingTimer = setInterval(async () => {
        try {
            const pairs = await api.getMyPair();
            const activePairs = (pairs || []).filter(p => p.status === 'active');
            if (activePairs.length > 0) {
                stopPairPolling();
                state.currentPair = activePairs[0];
                state.currentPairs = pairs;
                show(document.getElementById('tab-bar'));
                showPage('home');
                showToast('对方已加入，配对成功！');
            }
        } catch (err) {
            console.log('轮询配对状态失败:', err.message);
        }
    }, 5000);
}
function stopPairPolling() {
    if (state.pairPollingTimer) {
        clearInterval(state.pairPollingTimer);
        state.pairPollingTimer = null;
    }
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
            const nicknameGroup = document.getElementById('auth-nickname-group');
            if (isLogin) { hide(nicknameGroup); } else { show(nicknameGroup); }
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
                showToast('登录成功');
            } else {
                const nickname = document.getElementById('auth-nickname').value.trim();
                if (!nickname) { showToast('请输入昵称'); btn.disabled = false; return; }
                await api.register(email, nickname, password);
                showToast('注册成功');
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

        const activePairs = state.currentPairs.filter(p => p.status === 'active');
        const pendingPairs = state.currentPairs.filter(p => p.status === 'pending');

        if (activePairs.length > 0) {
            state.currentPair = activePairs[0];
            show(document.getElementById('tab-bar'));
            showPage('home');
        } else if (pendingPairs.length > 0) {
            state.currentPair = pendingPairs[0];
            showPage('pair-waiting');
            document.getElementById('waiting-invite-code').textContent = state.currentPair.invite_code;
        } else {
            showPage('pair');
        }
    } catch (err) {
        console.error('checkPairAndRoute 失败:', err);
        if (err.message && (err.message.includes('认证') || err.message.includes('401') || err.message.includes('无效'))) {
            api.clearToken();
            showPage('auth');
        } else {
            showPage('pair');
        }
    }
}

// ── 配对 ──
function initPair() {
    renderExistingPairs();

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
            show(document.getElementById('tab-bar'));
            showPage('home');
            showToast('配对成功！');
        } catch (err) { showToast(err.message); }
    });
}

/** 渲染已有配对列表 (1.4e) */
function renderExistingPairs() {
    const existingSection = document.getElementById('existing-pairs');
    const pairsList = document.getElementById('pairs-list');
    const createHeader = document.getElementById('pair-create-header');

    if (!existingSection || !pairsList) return;

    const activePairs = state.pairs.filter(p => p.status === 'active');

    if (activePairs.length === 0) {
        hide(existingSection);
        show(createHeader);
        return;
    }

    show(existingSection);
    hide(createHeader);

    const typeMap = { couple: '情侣', spouse: '夫妻', bestfriend: '挚友', parent: '育儿夫妻' };
    const typeIcons = { couple: 'i-couple', spouse: 'i-ring', bestfriend: 'i-fist-bump', parent: 'i-baby' };

    pairsList.innerHTML = activePairs.map(p => `
        <div class="option-card mb-2 cursor-pointer" onclick="switchPair('${p.id}')">
            <div class="option-card__icon">
                ${svgIcon(typeIcons[p.type] || 'i-couple')}
            </div>
            <span class="option-card__label">${typeMap[p.type] || p.type}</span>
            <span class="text-xs text-muted ml-auto">${p.id === state.currentPair?.id ? '当前' : '切换 →'}</span>
        </div>
    `).join('');
}

function switchPair(pairId) {
    const pair = state.pairs.find(p => p.id === pairId);
    if (pair) {
        state.currentPair = pair;
        show(document.getElementById('tab-bar'));
        showPage('home');
        showToast('已切换关系');
    }
}

// ── 首页 ──
async function loadHome() {
    if (!state.currentPair) return;

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

    const activePairs = state.pairs.filter(p => p.status === 'active');
    if (activePairs.length <= 1) {
        hide(selector);
        return;
    }

    show(selector);

    const typeMap = { couple: '情侣', spouse: '夫妻', bestfriend: '挚友', parent: '育儿夫妻' };
    select.innerHTML = activePairs.map(p =>
        `<option value="${p.id}" ${p.id === state.currentPair?.id ? 'selected' : ''}>${typeMap[p.type] || p.type}</option>`
    ).join('');

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

/** 渲染关系树 (1.4f) */
function renderTree(tree) {
    const card = document.getElementById('tree-card');
    if (!card) return;
    show(card);

    // 树的可视化：根据 level 选择不同 SVG 图标
    const treeVisual = document.getElementById('tree-visual');
    const levelIcons = { '种子': 'i-sprout', '幼苗': 'i-sprout', '小树': 'i-tree', '大树': 'i-tree' };
    const iconId = levelIcons[tree.level_name] || 'i-sprout';
    treeVisual.innerHTML = svgIcon(iconId, 'icon-2xl');

    document.getElementById('tree-level').textContent = tree.level_name || '种子';
    document.getElementById('tree-points').textContent = tree.growth_points || 0;

    const bar = document.getElementById('tree-progress-bar');
    bar.style.width = `${tree.progress_percent || 0}%`;

    const btn = document.getElementById('tree-water-btn');
    if (tree.can_water) {
        btn.disabled = false;
        btn.innerHTML = `${svgIcon('i-droplet', 'icon-sm')} 浇水`;
        btn.onclick = waterTree;
    } else {
        btn.disabled = true;
        btn.innerHTML = `${svgIcon('i-check-circle', 'icon-sm')} 今日已浇水`;
    }
}

async function waterTree() {
    if (!state.currentPair) return;
    const btn = document.getElementById('tree-water-btn');
    btn.disabled = true;
    btn.textContent = '浇水中...';
    try {
        const result = await api.waterTree(state.currentPair.id);
        showToast(`+${result.points_added} 成长值${result.level_up ? ' 升级了！' : ''}`);
        loadTree();
    } catch (err) {
        showToast(err.message);
        btn.disabled = false;
        btn.innerHTML = `${svgIcon('i-droplet', 'icon-sm')} 浇水`;
    }
}

// ── 危机预警 (1.4g) ──
async function loadCrisisStatus() {
    if (!state.currentPair) return;
    try {
        const crisis = await api.getCrisisStatus(state.currentPair.id);
        state.crisisStatus = crisis;
        renderCrisisCard(crisis);
    } catch { /* 静默失败 */ }
}

function renderCrisisCard(crisis) {
    const card = document.getElementById('crisis-card');
    if (!card) return;

    const level = crisis.crisis_level || 'none';
    if (level === 'none') {
        hide(card);
        return;
    }

    show(card);
    const badge = document.getElementById('crisis-badge');
    const levelMap = {
        mild:     { text: '轻度预警', cls: 'crisis-badge--mild' },
        moderate: { text: '中度预警', cls: 'crisis-badge--moderate' },
        severe:   { text: '重度预警', cls: 'crisis-badge--severe' },
    };
    const info = levelMap[level] || levelMap.mild;
    badge.textContent = info.text;
    badge.className = `crisis-badge ${info.cls}`;
    // 边框颜色通过 data 属性或直接 class 控制
    card.style.borderLeft = '';
    card.setAttribute('data-level', level);

    const intervention = crisis.intervention;
    const interventionDiv = document.getElementById('crisis-intervention');
    if (intervention && intervention.type !== 'none') {
        show(interventionDiv);
        document.getElementById('crisis-intervention-title').textContent = intervention.title || '干预建议';
        document.getElementById('crisis-intervention-desc').textContent = intervention.description || '';
        const items = intervention.action_items || [];
        document.getElementById('crisis-action-items').innerHTML = items.map(i => `<div>• ${i}</div>`).join('');
    } else {
        hide(interventionDiv);
    }

    // 操作按钮状态
    const ackBtn = document.getElementById('crisis-ack-btn');
    const actionsDiv = document.getElementById('crisis-actions');
    show(actionsDiv);
    if (ackBtn) {
        if (crisis.alert_status === 'acknowledged' || crisis.alert_status === 'resolved') {
            ackBtn.textContent = '已确认';
            ackBtn.disabled = true;
        } else {
            ackBtn.textContent = '已知悉';
            ackBtn.disabled = false;
        }
    }
}

async function handleCrisisAcknowledge() {
    const crisis = state.crisisStatus;
    if (!crisis || !crisis.alert_id) { showToast('无可操作的预警'); return; }
    try {
        await api.acknowledgeCrisisAlert(crisis.alert_id);
        showToast('已确认知悉预警');
        const btn = document.getElementById('crisis-ack-btn');
        if (btn) { btn.textContent = '已确认'; btn.disabled = true; }
        state.crisisStatus.alert_status = 'acknowledged';
    } catch (err) { showToast(err.message); }
}

async function showCrisisResources() {
    try {
        const data = await api.getCrisisResources();
        const hotlines = (data.hotlines || []).map(h => `
            <div class="notification-item">
                <div class="flex-1">
                    <div class="text-sm font-semibold">${h.name}</div>
                    <div class="text-xs text-muted">${h.hours}</div>
                </div>
                <a href="tel:${h.number}" class="text-sm font-semibold text-brand no-underline">${h.number}</a>
            </div>
        `).join('');
        const online = (data.online || []).map(o => `
            <div class="notification-item">
                <a href="${o.url}" target="_blank" class="font-semibold text-accent no-underline">${o.name}</a>
                <span class="text-xs text-muted ml-2">${o.desc}</span>
            </div>
        `).join('');
        const tips = (data.tips || []).map(t => `<div class="text-sm text-secondary py-1">• ${t}</div>`).join('');

        openModal(`
            <div class="modal-title text-center">专业帮助资源</div>
            <div class="mb-4">
                <div class="text-sm font-semibold mb-2">${svgIcon('i-phone', 'icon-sm')} 热线电话</div>
                ${hotlines}
            </div>
            <div class="mb-4">
                <div class="text-sm font-semibold mb-2">${svgIcon('i-external-link', 'icon-sm')} 在线咨询平台</div>
                ${online}
            </div>
            <div class="mb-4">
                <div class="text-sm font-semibold mb-2">${svgIcon('i-lightbulb', 'icon-sm')} 温馨提示</div>
                ${tips}
            </div>
            ${state.crisisStatus?.alert_id ? `<button class="btn btn-primary btn-block mt-2" onclick="handleCrisisEscalate()">升级为专业求助</button>` : ''}
            <button class="btn btn-secondary btn-block mt-2" onclick="closeModal()">关闭</button>
        `);
    } catch (err) { showToast(err.message); }
}

async function handleCrisisEscalate() {
    const crisis = state.crisisStatus;
    if (!crisis || !crisis.alert_id) return;
    try {
        await api.escalateCrisisAlert(crisis.alert_id, '用户主动寻求专业帮助');
        showToast('已标记为专业求助');
        closeModal();
        loadCrisisStatus();
    } catch (err) { showToast(err.message); }
}

async function showCrisisDetail() {
    if (!state.currentPair) return;
    try {
        const [history, alerts] = await Promise.all([
            api.getCrisisHistory(state.currentPair.id, 30).catch(() => ({ history: [] })),
            api.getCrisisAlerts(state.currentPair.id, null, 10).catch(() => []),
        ]);
        renderCrisisDetailModal(history, alerts);
    } catch (err) { showToast(err.message); }
}

function renderCrisisDetailModal(historyData, alerts) {
    const history = historyData.history || [];
    const crisis = state.crisisStatus || {};

    const levelColor = { none: 'var(--success-400)', mild: 'var(--warning-400)', moderate: '#F97316', severe: 'var(--danger-400)' };
    const levelLabel = { none: '正常', mild: '轻度', moderate: '中度', severe: '重度' };
    const statusLabel = { active: '活跃', acknowledged: '已确认', resolved: '已解决', escalated: '已升级' };

    // 趋势图（简易 SVG）
    let trendSvg = '';
    const validHistory = history.filter(h => h.health_score != null).slice(0, 14).reverse();
    if (validHistory.length >= 2) {
        const w = 300, h = 80, pad = 10;
        const coords = validHistory.map((p, i) => {
            const x = pad + (i / (validHistory.length - 1)) * (w - 2 * pad);
            const y = h - pad - ((p.health_score || 50) / 100) * (h - 2 * pad);
            return `${x},${y}`;
        });
        const levelDots = validHistory.map((p, i) => {
            const [x, y] = coords[i].split(',');
            const c = levelColor[p.crisis_level] || levelColor.none;
            return `<circle cx="${x}" cy="${y}" r="4" fill="${c}" stroke="white" stroke-width="1.5"/>`;
        }).join('');

        trendSvg = `
            <div class="mb-4">
                <div class="text-sm font-semibold mb-2">健康趋势 (近${validHistory.length}次)</div>
                <svg viewBox="0 0 ${w} ${h}" class="trend-chart-svg">
                    <polyline points="${coords.join(' ')}" fill="none" stroke="var(--primary-400)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    ${levelDots}
                </svg>
                <div class="flex gap-3 justify-center mt-2">
                    ${Object.entries(levelLabel).map(([k, v]) => `<span class="text-xs" style="color:${levelColor[k]}">● ${v}</span>`).join('')}
                </div>
            </div>`;
    }

    // 预警历史列表
    const alertsList = alerts.length > 0
        ? alerts.map(a => `
            <div class="notification-item ${a.status === 'active' ? 'notification-item--unread' : ''} mb-1">
                <div class="crisis-dot" style="background:${levelColor[a.level] || levelColor.none}"></div>
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-semibold">${levelLabel[a.level] || a.level}预警</div>
                    <div class="text-xs text-muted">${a.intervention_title || '无干预建议'}</div>
                </div>
                <div class="text-right flex-shrink-0">
                    <div class="text-xs" style="color:${levelColor[a.level]}">${statusLabel[a.status] || a.status}</div>
                    <div class="notification-item__time">${a.created_at ? new Date(a.created_at).toLocaleDateString() : ''}</div>
                </div>
            </div>
        `).join('')
        : '<div class="text-center text-muted text-sm p-3">暂无预警记录</div>';

    // 当前状态
    const currentLevel = crisis.crisis_level || 'none';
    const currentInfo = { text: levelLabel[currentLevel] || '正常', color: levelColor[currentLevel] || levelColor.none };
    const levelIconId = { severe: 'i-alert-triangle', moderate: 'i-alert-circle', mild: 'i-info', none: 'i-check-circle' };

    // 操作区
    let actionButtons = '';
    if (crisis.alert_id && crisis.alert_status === 'active') {
        actionButtons = `
            <div class="flex gap-2 mt-4">
                <button class="btn btn-sm btn-secondary flex-1" onclick="handleCrisisAcknowledge();closeModal()">确认知悉</button>
                <button class="btn btn-sm btn-outline flex-1" onclick="handleCrisisResolve()">标记解决</button>
            </div>`;
    } else if (crisis.alert_id && crisis.alert_status === 'acknowledged') {
        actionButtons = `
            <div class="flex gap-2 mt-4">
                <button class="btn btn-sm btn-outline flex-1" onclick="handleCrisisResolve()">标记解决</button>
                <button class="btn btn-sm btn-outline flex-1 text-brand" onclick="showCrisisResources()">专业帮助</button>
            </div>`;
    }

    openModal(`
        <div class="modal-title text-center">危机预警详情</div>
        <div class="text-center mb-4">
            <div class="crisis-status-circle" style="background:${currentInfo.color}20">
                <span style="color:${currentInfo.color}">${svgIcon(levelIconId[currentLevel] || 'i-info', 'icon-lg')}</span>
            </div>
            <div class="text-base font-semibold" style="color:${currentInfo.color}">${currentInfo.text}${currentLevel !== 'none' ? '预警' : ''}</div>
            ${crisis.health_score != null ? `<div class="text-xs text-muted mt-1">健康指数 ${crisis.health_score}</div>` : ''}
            ${crisis.previous_level && crisis.previous_level !== currentLevel ? `<div class="text-xs text-muted mt-1">上次: ${levelLabel[crisis.previous_level] || crisis.previous_level}</div>` : ''}
        </div>
        ${trendSvg}
        <div class="mb-2">
            <div class="text-sm font-semibold mb-2">预警记录</div>
            ${alertsList}
        </div>
        ${actionButtons}
        <button class="btn btn-secondary btn-block mt-3" onclick="closeModal()">关闭</button>
    `);
}

async function handleCrisisResolve() {
    const crisis = state.crisisStatus;
    if (!crisis || !crisis.alert_id) { showToast('无可操作的预警'); return; }
    closeModal();
    const result = await openInputModal('标记预警已解决', [
        { key: 'note', label: '解决备注（选填）', type: 'text', placeholder: '简要描述如何解决的' }
    ]);
    if (result === null) return;
    try {
        await api.resolveCrisisAlert(crisis.alert_id, result.note || '');
        showToast('预警已标记为解决');
        loadCrisisStatus();
    } catch (err) { showToast(err.message); }
}

// ── 每日任务 (1.4h) ──
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
        hide(card);
        return;
    }

    show(card);

    // 依恋类型标签
    const attachLabel = document.getElementById('tasks-attachment-label');
    const typeLabels = { secure: '安全型', anxious: '焦虑型', avoidant: '回避型', fearful: '恐惧型' };
    if (data.attachment_a || data.attachment_b) {
        attachLabel.textContent = `${typeLabels[data.attachment_a] || '待分析'} + ${typeLabels[data.attachment_b] || '待分析'}`;
    }

    // 任务列表
    const list = document.getElementById('tasks-list');
    const categoryIcons = { communication: 'i-message-circle', activity: 'i-zap', reflection: 'i-lightbulb' };
    list.innerHTML = tasks.map(t => `
        <div id="task-${t.id}" class="task-item${t.status === 'completed' ? ' task-item--done' : ''}" onclick="completeTaskItem('${t.id}')">
            <div class="task-item__icon">
                ${t.status === 'completed'
                    ? svgIcon('i-check-circle', 'icon-sm')
                    : svgIcon(categoryIcons[t.category] || 'i-target', 'icon-sm')}
            </div>
            <div class="task-item__content">
                <div class="task-item__title">${t.title}</div>
                <div class="task-item__desc">${t.description}</div>
            </div>
        </div>
    `).join('');

    // 组合洞察
    const insight = document.getElementById('tasks-insight');
    if (data.combination_insight) {
        insight.innerHTML = `${svgIcon('i-lightbulb', 'icon-sm')} ${data.combination_insight}`;
    }
}

async function completeTaskItem(taskId) {
    try {
        await api.completeTask(taskId);
        const el = document.getElementById(`task-${taskId}`);
        if (el) {
            el.classList.add('task-item--done');
            const iconEl = el.querySelector('.task-item__icon');
            if (iconEl) iconEl.innerHTML = svgIcon('i-check-circle', 'icon-sm');
        }
        showToast('任务完成');
    } catch (err) { showToast(err.message); }
}

// ── 社群技巧 ──
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
    show(card);
    const tip = tips[Math.floor(Math.random() * tips.length)];
    document.getElementById('tip-title').textContent = tip.title;
    document.getElementById('tip-text').textContent = tip.content;
}

// ── 里程碑 (1.4i) ──
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
    show(card);
    const list = document.getElementById('milestones-list');
    if (!milestones.length) {
        list.innerHTML = '<div class="text-center text-muted text-sm p-3">还没有里程碑，点击右上角添加一个吧</div>';
        return;
    }
    const typeIcons = { anniversary: 'i-heart', proposal: 'i-ring', wedding: 'i-ring', friendship_day: 'i-handshake', custom: 'i-star' };
    list.innerHTML = milestones.map(m => `
        <div class="milestone-item" onclick="viewMilestoneReport('${m.id}')">
            <div class="milestone-item__icon">
                ${svgIcon(typeIcons[m.type] || 'i-star', 'icon-sm')}
            </div>
            <div class="milestone-item__content">
                <div class="milestone-item__title">${m.title}</div>
                <div class="milestone-item__date">${m.date}</div>
            </div>
            <span class="milestone-item__action">查看回顾 ${svgIcon('i-chevron-right', 'icon-xs')}</span>
        </div>
    `).join('');
}

async function viewMilestoneReport(milestoneId) {
    try {
        showToast('正在生成回顾报告...');
        const data = await api.getMilestoneReport(milestoneId);
        const r = data.report || {};
        const strengths = (r.strengths_discovered || []).map(s => `<div class="text-sm text-secondary py-half">• ${s}</div>`).join('');
        openModal(`
            <div class="modal-title text-center">${svgIcon('i-book-open', 'icon-sm')} 里程碑回顾</div>
            <div class="text-sm text-secondary mb-4 leading-tall">${r.growth_story || '回忆正在生成中...'}</div>
            ${strengths ? `<div class="mb-4"><div class="text-sm font-semibold mb-2">${svgIcon('i-target', 'icon-sm')} 发现的优势</div>${strengths}</div>` : ''}
            ${r.blessing ? `<div class="report-insight text-center italic">${svgIcon('i-heart', 'icon-sm')} ${r.blessing}</div>` : ''}
            <button class="btn btn-secondary btn-block mt-4" onclick="closeModal()">关闭</button>
        `);
    } catch (err) { showToast(err.message); }
}

// ── 通知中心 (1.4j) ──
async function loadNotifications() {
    const bell = document.getElementById('notification-bell');
    if (!bell) return;
    try {
        const data = await api.getNotifications();
        const notifications = data || [];
        if (notifications.length > 0) {
            show(bell);
            const unread = notifications.filter(n => !n.is_read).length;
            const badge = document.getElementById('notification-badge');
            if (unread > 0 && badge) {
                show(badge);
                badge.textContent = unread > 9 ? '9+' : unread;
            }
            state.notifications = notifications;
        }
    } catch { /* 静默 */ }
}

function renderNotificationPanel() {
    const panel = document.getElementById('notification-panel');
    if (!panel) return;
    const isVisible = !panel.classList.contains('hidden');
    if (isVisible) { hide(panel); return; }
    show(panel);
    const list = document.getElementById('notification-list');
    const notifications = state.notifications || [];
    if (!notifications.length) {
        list.innerHTML = `<div class="text-center text-muted text-sm p-3">暂无通知</div>`;
        return;
    }
    const typeIcons = { crisis: 'i-alert-triangle', task: 'i-target', tip: 'i-lightbulb', milestone: 'i-trophy' };
    list.innerHTML = notifications.slice(0, 20).map(n => `
        <div class="notification-item${n.is_read ? '' : ' notification-item--unread'}">
            ${svgIcon(typeIcons[n.type] || 'i-bell', 'icon-sm')}
            <div class="flex-1">
                <div>${n.content}</div>
                <div class="notification-item__time">${new Date(n.created_at).toLocaleDateString()}</div>
            </div>
        </div>
    `).join('');
}

function renderHomeStatus(status, streak) {
    const myDot = document.getElementById('status-my-dot');
    const partnerDot = document.getElementById('status-partner-dot');

    myDot.className = `status-dot ${status.my_done ? 'done' : ''}`;
    partnerDot.className = `status-dot ${status.partner_done ? 'done' : status.my_done ? 'waiting' : ''}`;

    document.getElementById('status-my-label').textContent = status.my_done ? '已打卡' : '未打卡';
    document.getElementById('status-partner-label').textContent = status.partner_done ? '已打卡' : '等待中...';

    const checkinBtn = document.getElementById('home-checkin-btn');
    if (status.my_done) {
        checkinBtn.textContent = '今日已打卡';
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
        show(reportBtn);
        if (status.has_report) {
            reportBtn.textContent = '查看今日报告';
            reportBtn.onclick = () => showPage('report');
        } else {
            reportBtn.textContent = 'AI 正在生成报告...';
            _pollForReport();
        }
    } else if (status.my_done && !status.partner_done) {
        show(reportBtn);
        if (status.has_solo_report) {
            reportBtn.textContent = '查看个人情感日记';
            reportBtn.onclick = () => { state.viewSolo = true; showPage('report'); };
        } else {
            reportBtn.textContent = '个人日记生成中...';
            _pollForSoloReport();
        }
    } else {
        hide(reportBtn);
    }
}

async function _pollForReport() {
    for (let i = 0; i < 10; i++) {
        await new Promise(r => setTimeout(r, 3000));
        try {
            const status = await api.getTodayStatus(state.currentPair.id);
            if (status.has_report) {
                const btn = document.getElementById('home-report-btn');
                btn.textContent = '查看今日报告';
                btn.onclick = () => showPage('report');
                showToast('AI 报告已生成');
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
                btn.textContent = '查看个人情感日记';
                btn.onclick = () => { state.viewSolo = true; showPage('report'); };
                showToast('你的个人日记已生成');
                return;
            }
        } catch { break; }
    }
}

// ── 打卡 (1.4c) ──
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

    // 情绪标签 (1.4c: .mood-tag → .tag[data-mood])
    document.querySelectorAll('.tag[data-mood]').forEach(tag => {
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
            imagePreview.innerHTML = `<img src="${API_BASE.replace('/api/v1', '')}${result.url}" class="media-preview__img">`;
            showToast('图片已添加');
        } catch (err) { showToast(err.message); }
    });

    // 语音上传 (1.4d: var(--mint-light) → var(--success-50), var(--mint) → var(--success-500))
    const voiceInput = document.getElementById('checkin-voice-input');
    document.getElementById('checkin-voice-btn')?.addEventListener('click', () => voiceInput.click());
    voiceInput?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
            showToast('上传中...');
            const result = await api.uploadFile('voice', file);
            state.uploadedVoiceUrl = result.url;
            document.getElementById('checkin-voice-preview').innerHTML = `
                <div class="media-preview media-preview--voice">
                    ${svgIcon('i-mic', 'icon-sm')} 语音已添加 (${(file.size / 1024).toFixed(0)}KB)
                </div>`;
            showToast('语音已添加');
        } catch (err) { showToast(err.message); }
    });

    // 提交打卡
    document.getElementById('checkin-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const content = document.getElementById('checkin-content').value.trim();
        if (!content) { showToast('写点什么吧'); return; }

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
            showToast('打卡成功！');
            // 重置表单
            state.selectedMoods = [];
            state.uploadedImageUrl = null;
            state.uploadedVoiceUrl = null;
            document.querySelectorAll('.tag[data-mood]').forEach(t => t.classList.remove('selected'));
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

// ── 报告 (1.4k) ──
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
                    <div class="empty-icon">${svgIcon('i-bar-chart', 'icon-xl')}</div>
                    <div class="empty-title">暂无报告</div>
                    <div class="empty-desc">每次打卡即可生成个人日记，双方完成后还有关系健康报告</div>
                </div>`;
        }
    } catch (err) {
        console.error('加载报告失败', err);
    }
}

function getMoodEmoji(score) {
    if (!score) return svgIcon('i-meh', 'icon-lg');
    if (score >= 8) return svgIcon('i-smile', 'icon-lg');
    if (score >= 6) return svgIcon('i-smile', 'icon-lg');
    if (score >= 4) return svgIcon('i-meh', 'icon-lg');
    if (score >= 2) return svgIcon('i-frown', 'icon-lg');
    return svgIcon('i-frown', 'icon-lg');
}

function renderReport(report, trendData) {
    const c = report.content;
    const container = document.getElementById('report-content');

    // 趋势图 SVG (1.4d: var(--coral-500) → var(--primary-500))
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
        const directionIcon = trendData.direction === 'improving' ? svgIcon('i-trending-up', 'icon-sm') : trendData.direction === 'declining' ? svgIcon('i-trending-down', 'icon-sm') : svgIcon('i-activity', 'icon-sm');
        const directionText = trendData.direction === 'improving' ? '持续上升' : trendData.direction === 'declining' ? '需要关注' : '保持稳定';

        trendSvg = `
            <div class="card mt-4">
                <div class="card__header">
                    <div class="card__header-title">${directionIcon} 健康趋势</div>
                    <span class="text-xs text-muted">${directionText} · 近${points.length}天</span>
                </div>
                <svg viewBox="0 0 ${w} ${h}" class="trend-chart-svg">
                    <defs>
                        <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="var(--primary-500)" stop-opacity="0.3"/>
                            <stop offset="100%" stop-color="var(--primary-500)" stop-opacity="0"/>
                        </linearGradient>
                    </defs>
                    <polygon points="${coords.join(' ')} ${w - pad},${h - pad} ${pad},${h - pad}" fill="url(#trendGrad)"/>
                    <polyline points="${coords.join(' ')}" fill="none" stroke="var(--primary-500)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    ${points.map((p, i) => {
                        const [x, y] = coords[i].split(',');
                        return `<circle cx="${x}" cy="${y}" r="3" fill="var(--primary-500)"/>`;
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

        <div class="card mt-4">
            <h3 class="text-base mb-3">情绪分析</h3>
            <div class="checkin-status">
                <div class="status-item">
                    <div class="mb-1">${getMoodEmoji(c.mood_a?.score)}</div>
                    <div class="text-sm text-secondary">A方: ${c.mood_a?.label || '--'}</div>
                    <div class="text-xl font-semibold mt-1 mono">${c.mood_a?.score || '--'}/10</div>
                </div>
                <div class="status-item">
                    <div class="mb-1">${getMoodEmoji(c.mood_b?.score)}</div>
                    <div class="text-sm text-secondary">B方: ${c.mood_b?.label || '--'}</div>
                    <div class="text-xl font-semibold mt-1 mono">${c.mood_b?.score || '--'}/10</div>
                </div>
            </div>
        </div>

        ${c.communication_quality ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-message-circle', 'icon-sm')} 沟通质量 ${c.communication_quality.score || '--'}/10</h3>
                <p class="text-sm text-secondary">${c.communication_quality.note || ''}</p>
            </div>` : ''}

        ${c.emotional_sync ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-activity', 'icon-sm')} 情绪同步度 ${c.emotional_sync.score || '--'}/100</h3>
                <p class="text-sm text-secondary">${c.emotional_sync.note || ''}</p>
            </div>` : ''}

        ${c.interaction_balance ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-handshake', 'icon-sm')} 互动平衡度 ${c.interaction_balance.score || '--'}/100</h3>
                <p class="text-sm text-secondary">${c.interaction_balance.note || ''}</p>
            </div>` : ''}

        ${c.highlights?.length ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-star', 'icon-sm')} 今日亮点</h3>
                ${c.highlights.map(h => `<div class="text-sm text-secondary py-1">• ${h}</div>`).join('')}
            </div>` : ''}

        ${c.concerns?.length ? `
            <div class="report-warning">
                <h3 class="text-base mb-2">${svgIcon('i-alert-triangle', 'icon-sm')} 需要关注</h3>
                ${c.concerns.map(con => `<div class="text-sm text-secondary py-1">• ${con}</div>`).join('')}
            </div>` : ''}

        ${c.risk_signals?.length ? `
            <div class="report-danger">
                <h3 class="text-base mb-2">${svgIcon('i-alert-circle', 'icon-sm')} 风险信号</h3>
                ${c.risk_signals.map(r => `<div class="text-sm text-danger py-1">• ${r}</div>`).join('')}
                <p class="text-xs text-muted mt-2">建议关注戈特曼「末日四骑士」模型，必要时寻求专业咨询</p>
            </div>` : ''}

        ${c.theory_tag ? `
            <div class="text-center mt-3">
                <span class="privacy-badge">${svgIcon('i-book-open', 'icon-xs')} ${c.theory_tag}</span>
            </div>` : ''}

        <!-- 周报/月报按钮 -->
        <div class="flex gap-2 mt-4">
            <button onclick="generateWeekly()" class="btn btn-outline flex-1">
                ${svgIcon('i-clipboard', 'icon-sm')} 生成周报
            </button>
            <button onclick="generateMonthly()" class="btn btn-outline flex-1">
                ${svgIcon('i-pie-chart', 'icon-sm')} 生成月报
            </button>
        </div>

        <div class="text-center mt-4">
            <span class="privacy-badge">${svgIcon('i-lock', 'icon-xs')} 数据已加密 · 仅AI可见原始内容</span>
        </div>
        <div class="text-center mt-2">
            <span class="text-xs text-muted">本报告由AI生成，仅供参考</span>
        </div>
    `;
}

function renderSoloReport(report) {
    const c = report.content;
    const container = document.getElementById('report-content');

    container.innerHTML = `
        <div class="text-center mb-4">
            <span class="btn btn-sm btn-secondary cursor-pointer" onclick="state.viewSolo=false;loadReports()">${svgIcon('i-arrow-left', 'icon-xs')} 查看关系报告</span>
        </div>

        <div class="health-gauge">
            <div class="gauge-circle" style="--score: ${c.health_score || 50}">
                <span class="gauge-score">${c.health_score || '--'}</span>
                <span class="gauge-label">个人情绪指数</span>
            </div>
        </div>

        <div class="card card--accent text-center">
            <div class="text-2xl mb-2">${getMoodEmoji(c.mood?.score)} ${c.mood?.label || ''}</div>
            <div class="text-sm opacity-90">情绪得分 ${c.mood?.score || '--'}/10</div>
        </div>

        ${c.self_insight ? `<div class="report-insight">${c.self_insight}</div>` : ''}

        ${c.emotional_pattern ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-brain', 'icon-sm')} 情绪模式解读</h3>
                <p class="text-sm text-secondary leading-relaxed">${c.emotional_pattern}</p>
                ${c.theory_tag ? `<div class="text-xs text-muted mt-2">${svgIcon('i-book-open', 'icon-xs')} ${c.theory_tag}</div>` : ''}
            </div>` : ''}

        ${c.self_care_tip ? `<div class="report-suggestion">${c.self_care_tip}</div>` : ''}

        ${c.relationship_note ? `
            <div class="card text-center">
                <div class="text-sm text-secondary leading-relaxed">${svgIcon('i-heart', 'icon-sm')} ${c.relationship_note}</div>
            </div>` : ''}

        <div class="text-center mt-4">
            <span class="privacy-badge">${svgIcon('i-lock', 'icon-xs')} 仅你可见 · 对方无法查看你的个人日记</span>
        </div>
        <div class="text-center mt-2">
            <span class="text-xs text-muted">本日记由AI生成，仅供参考</span>
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
            showToast('AI生成中，预计需等几十秒', 5000);
            _pollReportStatus('daily', btn, '查看今日报告', () => showPage('report'));
        } else {
            showToast('报告已生成');
            showPage('report');
            btn.disabled = false;
            btn.textContent = '查看今日报告';
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
            showToast('大模型深入汇总中，请耐心等候...', 5000);
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
            showToast('计算月度长周期趋势，请稍候...', 5000);
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
                showToast('分析完成');
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
    const dirIcon = c.trend === 'improving' ? svgIcon('i-trending-up', 'icon-sm') : c.trend === 'declining' ? svgIcon('i-trending-down', 'icon-sm') : svgIcon('i-activity', 'icon-sm');

    container.innerHTML = `
        <div class="text-center mb-4">
            <span class="btn btn-sm btn-secondary cursor-pointer" onclick="loadReports()">${svgIcon('i-arrow-left', 'icon-xs')} 返回日报</span>
        </div>
        <div class="health-gauge">
            <div class="gauge-circle" style="--score: ${c.overall_health_score || 50}">
                <span class="gauge-score">${c.overall_health_score || '--'}</span>
                <span class="gauge-label">周健康指数</span>
            </div>
        </div>
        <div class="card card--accent text-center">
            <div class="text-sm opacity-90">${dirIcon} 本周趋势</div>
            <div class="text-base mt-2">${c.trend_description || ''}</div>
        </div>
        ${c.encouragement ? `<div class="report-insight">${c.encouragement}</div>` : ''}
        ${c.weekly_highlights?.length ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-star', 'icon-sm')} 本周亮点</h3>
                ${c.weekly_highlights.map(h => `<div class="text-sm text-secondary py-1">• ${h}</div>`).join('')}
            </div>` : ''}
        ${c.action_plan?.length ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-sparkles', 'icon-sm')} 行动建议</h3>
                ${c.action_plan.map(a => `<div class="report-suggestion my-1">${a}</div>`).join('')}
            </div>` : ''}
        <div class="text-center mt-4">
            <span class="text-xs text-muted">本周报由AI生成，仅供参考</span>
        </div>
    `;
}

function showMonthlyReport(report) {
    const c = report.content;
    const container = document.getElementById('report-content');

    container.innerHTML = `
        <div class="text-center mb-4">
            <span class="btn btn-sm btn-secondary cursor-pointer" onclick="loadReports()">${svgIcon('i-arrow-left', 'icon-xs')} 返回日报</span>
        </div>
        <div class="health-gauge">
            <div class="gauge-circle" style="--score: ${c.overall_health_score || 50}">
                <span class="gauge-score">${c.overall_health_score || '--'}</span>
                <span class="gauge-label">月健康指数</span>
            </div>
        </div>
        ${c.executive_summary ? `<div class="card card--accent"><div class="text-sm leading-relaxed">${c.executive_summary}</div></div>` : ''}
        ${c.strengths?.length ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-trophy', 'icon-sm')} 关系优势</h3>
                ${c.strengths.map(s => `<div class="text-sm text-secondary py-1">• ${s}</div>`).join('')}
            </div>` : ''}
        ${c.growth_areas?.length ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-sprout', 'icon-sm')} 成长空间</h3>
                ${c.growth_areas.map(g => `<div class="text-sm text-secondary py-1">• ${g}</div>`).join('')}
            </div>` : ''}
        ${c.next_month_goals?.length ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-target', 'icon-sm')} 下月目标</h3>
                ${c.next_month_goals.map(g => `<div class="report-suggestion my-1">${g}</div>`).join('')}
            </div>` : ''}
        ${c.professional_note ? `<div class="report-insight">${c.professional_note}</div>` : ''}
        <div class="text-center mt-4">
            <span class="text-xs text-muted">本月报由AI生成，仅供参考</span>
        </div>
    `;
}

// ── 个人中心 (1.4m) ──
async function loadProfile() {
    // 显示昵称 — 使用新的 .profile-card__name 选择器
    const nicknameEl = document.querySelector('#page-profile .profile-card__name');
    if (nicknameEl) {
        try {
            const me = await api.request('GET', '/auth/me');
            nicknameEl.textContent = me.nickname || '用户';
        } catch { /* ignore */ }
    }

    if (!state.currentPair) {
        document.getElementById('profile-pair-type').textContent = '未配对';
        document.getElementById('profile-pair-status').textContent = '去配对页面建立关系吧';
        const unbindSection = document.getElementById('unbind-section');
        hide(unbindSection);
        return;
    }

    const typeMap = { couple: '情侣', spouse: '夫妻', bestfriend: '挚友', parent: '育儿夫妻' };
    document.getElementById('profile-pair-type').textContent = typeMap[state.currentPair.type] || state.currentPair.type;
    document.getElementById('profile-pair-status').textContent = '已配对';

    await loadUnbindStatus();
}

async function loadUnbindStatus() {
    const section = document.getElementById('unbind-section');
    const statusText = document.getElementById('unbind-status-text');
    const actions = document.getElementById('unbind-actions');
    if (!section || !state.currentPair) return;

    try {
        const status = await api.getUnbindStatus(state.currentPair.id);
        if (!status.has_request) {
            show(section);
            statusText.textContent = '解除配对后双方将无法继续打卡和查看报告';
            actions.innerHTML = `<button class="btn btn-outline btn-sm btn--unbind" onclick="handleRequestUnbind()">发起解绑</button>`;
        } else {
            show(section);
            if (status.requested_by_me) {
                statusText.textContent = `你已发起解绑请求，冷静期剩余 ${status.days_remaining} 天。对方确认后立即生效，或冷静期结束后你可强制解绑。`;
                if (status.can_force_unbind) {
                    actions.innerHTML = `
                        <button class="btn btn-outline btn-sm btn--unbind" onclick="handleConfirmUnbind()">确认解绑</button>
                        <button class="btn btn-outline btn-sm" onclick="handleCancelUnbind()">撤回请求</button>
                    `;
                } else {
                    actions.innerHTML = `<button class="btn btn-outline btn-sm" onclick="handleCancelUnbind()">撤回请求</button>`;
                }
            } else {
                statusText.textContent = '对方已发起解绑请求，确认后立即解除配对关系。';
                actions.innerHTML = `
                    <button class="btn btn-outline btn-sm btn--unbind" onclick="handleConfirmUnbind()">确认解绑</button>
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
        await api.requestUnbind(state.currentPair.id);
        showToast('解绑请求已发起');
        loadUnbindStatus();
    } catch (err) { showToast(err.message); }
}

async function handleConfirmUnbind() {
    if (!confirm('确定要解除配对吗？此操作不可撤销。')) return;
    try {
        const result = await api.confirmUnbind(state.currentPair.id);
        showToast(result.message);
        state.currentPair = null;
        hide(document.getElementById('tab-bar'));
        showPage('pair');
    } catch (err) { showToast(err.message); }
}

async function handleCancelUnbind() {
    try {
        await api.cancelUnbind(state.currentPair.id);
        showToast('解绑请求已撤回');
        loadUnbindStatus();
    } catch (err) { showToast(err.message); }
}

// ══════════════════════════════════════
// Phase 2: 新功能页面逻辑
// ══════════════════════════════════════

// ── 异地恋模式 ──
async function loadLongDistance() {
    if (!state.currentPair) return;
    try {
        const data = await api.getLongDistanceDashboard(state.currentPair.id);
        const card = document.getElementById('ld-status-card');
        const daysEl = document.getElementById('ld-days-apart');
        const distEl = document.getElementById('ld-distance');

        if (data.days_since_last_meet != null) {
            daysEl.textContent = data.days_since_last_meet + ' 天';
        }
        if (data.distance) {
            distEl.textContent = data.distance;
        }

        // 渲染已完成活动
        const completedEl = document.getElementById('ld-completed');
        const activities = data.completed_activities || data.recent_activities || [];
        if (activities.length > 0) {
            completedEl.innerHTML = activities.slice(0, 5).map(a => `
                <div class="notification-item mb-1">
                    ${svgIcon('i-check-circle', 'icon-sm text-brand')}
                    <div class="flex-1">
                        <div class="text-sm">${a.title || a.name || '活动'}</div>
                        <div class="text-xs text-muted">${a.completed_at ? new Date(a.completed_at).toLocaleDateString() : ''}</div>
                    </div>
                </div>
            `).join('');
        } else {
            completedEl.innerHTML = '<div class="text-sm text-muted text-center p-3">还没有完成的活动</div>';
        }

        // 渲染当前活动
        if (data.current_activity) {
            renderLdActivity(data.current_activity);
        }
    } catch (err) {
        console.error('加载异地恋数据失败', err);
    }
}

async function suggestLdActivity() {
    if (!state.currentPair) return;
    const btn = document.getElementById('ld-suggest-btn');
    btn.disabled = true;
    try {
        const data = await api.suggestActivity(state.currentPair.id);
        renderLdActivity(data);
    } catch (err) {
        showToast(err.message);
    } finally {
        btn.disabled = false;
    }
}

function renderLdActivity(activity) {
    const el = document.getElementById('ld-activity');
    el.innerHTML = `
        <div class="card--inner text-center">
            <div class="text-base font-semibold mb-2">${activity.title || activity.name || '同步活动'}</div>
            <div class="text-sm text-secondary mb-3 leading-relaxed">${activity.description || ''}</div>
            ${activity.id ? `<button class="btn btn-primary btn-sm" onclick="completeLdActivity('${activity.id}')">
                ${svgIcon('i-check', 'icon-sm')} 标记完成
            </button>` : ''}
        </div>
    `;
}

async function completeLdActivity(activityId) {
    try {
        await api.completeActivity(activityId);
        showToast('活动已完成');
        loadLongDistance();
    } catch (err) { showToast(err.message); }
}

// ── 依恋风格测试 ──
async function startAttachmentTest() {
    if (!state.currentPair) { showToast('请先完成配对'); return; }
    const btn = document.getElementById('attachment-start-btn');
    btn.disabled = true;
    btn.innerHTML = `${svgIcon('i-refresh', 'icon-sm spin')} AI 分析中...`;

    try {
        const data = await api.triggerAttachmentAnalysis(state.currentPair.id);
        renderAttachmentResult(data);
    } catch (err) {
        showToast(err.message);
        btn.disabled = false;
        btn.innerHTML = `${svgIcon('i-sparkles', 'icon-sm')} 开始AI分析`;
    }
}

function renderAttachmentResult(data) {
    const intro = document.getElementById('attachment-intro');
    const result = document.getElementById('attachment-result');
    const content = document.getElementById('attachment-result-content');

    hide(intro);
    show(result);

    const a = data.analysis || data;
    const styleNames = {
        secure: '安全型', anxious: '焦虑型', avoidant: '回避型',
        fearful: '恐惧型', 'anxious-preoccupied': '焦虑-沉迷型',
        'dismissive-avoidant': '疏离-回避型', 'fearful-avoidant': '恐惧-回避型'
    };
    const styleColors = {
        secure: 'var(--success-500)', anxious: 'var(--warning-500)',
        avoidant: 'var(--accent-400)', fearful: 'var(--danger-500)'
    };

    const styleName = styleNames[a.attachment_style] || a.attachment_style || '分析中';
    const styleColor = styleColors[a.attachment_style] || 'var(--primary-500)';

    content.innerHTML = `
        <div class="health-gauge">
            <div class="gauge-circle" style="--score:${a.confidence || 75}">
                <span class="gauge-score gauge-score--label" style="color:${styleColor}">${styleName}</span>
                <span class="gauge-label">依恋风格</span>
            </div>
        </div>

        ${a.description ? `<div class="card card--accent"><div class="text-sm leading-relaxed">${a.description}</div></div>` : ''}

        ${a.strengths?.length ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-star', 'icon-sm')} 你的优势</h3>
                ${a.strengths.map(s => `<div class="text-sm text-secondary py-1">• ${s}</div>`).join('')}
            </div>` : ''}

        ${a.growth_areas?.length ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-sprout', 'icon-sm')} 成长空间</h3>
                ${a.growth_areas.map(g => `<div class="text-sm text-secondary py-1">• ${g}</div>`).join('')}
            </div>` : ''}

        ${a.suggestions?.length ? `
            <div class="card">
                <h3 class="text-base mb-2">${svgIcon('i-lightbulb', 'icon-sm')} 改善建议</h3>
                ${a.suggestions.map(s => `<div class="report-suggestion my-1">${s}</div>`).join('')}
            </div>` : ''}

        <div class="text-center mt-3">
            <span class="privacy-badge">${svgIcon('i-lock', 'icon-xs')} 分析结果仅你可见</span>
        </div>
        <button class="btn btn-secondary btn-block mt-3" onclick="resetAttachmentTest()">重新分析</button>
    `;
}

function resetAttachmentTest() {
    const intro = document.getElementById('attachment-intro');
    const result = document.getElementById('attachment-result');
    const btn = document.getElementById('attachment-start-btn');
    show(intro);
    hide(result);
    btn.disabled = false;
    btn.innerHTML = `${svgIcon('i-sparkles', 'icon-sm')} 开始AI分析`;
}

// ── 关系快速体检 (纯前端问卷) ──
const healthTestQuestions = [
    { q: '你觉得和TA之间的沟通质量如何？', dim: '沟通质量', options: ['非常好', '较好', '一般', '较差', '很差'] },
    { q: '你是否经常感受到TA的关心和支持？', dim: '情感支持', options: ['总是', '经常', '有时', '偶尔', '从不'] },
    { q: '你们之间的信任程度如何？', dim: '信任程度', options: ['完全信任', '比较信任', '一般', '有些怀疑', '缺乏信任'] },
    { q: '你对你们的亲密程度满意吗？', dim: '亲密程度', options: ['非常满意', '比较满意', '一般', '不太满意', '很不满意'] },
    { q: '你们处理冲突的方式是否健康？', dim: '冲突处理', options: ['非常健康', '比较健康', '一般', '不太健康', '很不健康'] },
    { q: '你是否觉得在关系中被尊重？', dim: '相互尊重', options: ['完全被尊重', '大部分时候', '一般', '偶尔不被尊重', '经常不被尊重'] },
    { q: '你们是否有共同的生活目标？', dim: '共同愿景', options: ['非常一致', '比较一致', '部分一致', '不太一致', '完全不一致'] },
    { q: '你在关系中是否保持了个人空间？', dim: '个人空间', options: ['非常好', '比较好', '一般', '不太够', '完全没有'] },
    { q: '你们在一起时是否经常感到快乐？', dim: '幸福感', options: ['总是', '经常', '有时', '偶尔', '从不'] },
    { q: '总体来说，你对这段关系的满意度如何？', dim: '总体满意', options: ['非常满意', '比较满意', '一般', '不太满意', '很不满意'] },
];

let htState = { current: 0, answers: [] };

function initHealthTest() {
    htState = { current: 0, answers: [] };
    show(document.getElementById('ht-question-area'));
    hide(document.getElementById('ht-result'));
    renderHealthQuestion();
}

function renderHealthQuestion() {
    const q = healthTestQuestions[htState.current];
    const total = healthTestQuestions.length;

    document.getElementById('ht-question-num').textContent = `问题 ${htState.current + 1}/${total}`;
    document.getElementById('ht-question-text').textContent = q.q;
    document.getElementById('ht-progress-bar').style.width = `${(htState.current / total) * 100}%`;
    document.getElementById('ht-progress-text').textContent = `${htState.current}/${total}`;

    document.getElementById('ht-options').innerHTML = q.options.map((opt, i) => `
        <button class="option-card" onclick="answerHealthQuestion(${i})">
            <span class="option-card__label">${opt}</span>
            <svg class="icon icon-sm text-muted"><use href="#i-chevron-right"/></svg>
        </button>
    `).join('');
}

function answerHealthQuestion(optIndex) {
    const score = [100, 75, 50, 25, 0][optIndex];
    htState.answers.push({ dim: healthTestQuestions[htState.current].dim, score });
    htState.current++;

    if (htState.current < healthTestQuestions.length) {
        renderHealthQuestion();
    } else {
        showHealthTestResult();
    }
}

function showHealthTestResult() {
    hide(document.getElementById('ht-question-area'));
    show(document.getElementById('ht-result'));

    const total = Math.round(htState.answers.reduce((s, a) => s + a.score, 0) / htState.answers.length);
    document.getElementById('ht-gauge').style.setProperty('--score', total);
    document.getElementById('ht-score').textContent = total;
    document.getElementById('ht-progress-bar').style.width = '100%';
    document.getElementById('ht-progress-text').textContent = `${healthTestQuestions.length}/${healthTestQuestions.length}`;

    const levels = [
        { min: 80, label: '关系非常健康', desc: '你们的关系状态很棒！继续保持良好的互动模式。', cls: 'text-brand' },
        { min: 60, label: '关系比较健康', desc: '整体不错，但有些方面可以进一步提升。', cls: 'text-accent' },
        { min: 40, label: '关系需要关注', desc: '存在一些需要改善的地方，建议多沟通和互相理解。', cls: 'text-warning' },
        { min: 0, label: '关系需要干预', desc: '建议认真对待当前问题，可考虑寻求专业帮助。', cls: 'text-danger' },
    ];
    const level = levels.find(l => total >= l.min);
    document.getElementById('ht-level').className = `text-lg font-semibold mb-2 ${level.cls}`;
    document.getElementById('ht-level').textContent = level.label;
    document.getElementById('ht-desc').textContent = level.desc;

    // 维度详情
    const dimEl = document.getElementById('ht-dimensions');
    dimEl.innerHTML = htState.answers.map(a => `
        <div class="card">
            <div class="flex justify-between items-center mb-2">
                <span class="text-sm font-semibold">${a.dim}</span>
                <span class="text-sm font-bold ${a.score >= 75 ? 'text-brand' : a.score >= 50 ? 'text-accent' : 'text-danger'}">${a.score}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-bar__fill" style="width:${a.score}%"></div>
            </div>
        </div>
    `).join('');

    // 建议
    const weak = htState.answers.filter(a => a.score < 50).map(a => a.dim);
    const sugEl = document.getElementById('ht-suggestion-list');
    const suggestions = {
        '沟通质量': '尝试每天花15分钟做"无手机深度对话"，倾听对方的感受而非急于给建议。',
        '情感支持': '在对方需要时给予陪伴，一个拥抱胜过千言万语。学会说"我在"比"你应该"更有力量。',
        '信任程度': '信任需要时间建立。保持透明沟通，遵守承诺，避免隐瞒。必要时可以坦诚讨论边界。',
        '亲密程度': '安排定期的"二人时间"，尝试新的共同体验。身体接触和眼神交流都能增加亲密感。',
        '冲突处理': '学习"暂停"技巧——争吵激烈时先冷静20分钟再沟通。关注问题本身而非攻击对方。',
        '相互尊重': '尊重对方的想法和选择，即使不同意。避免在公共场合批评对方，保持基本的礼貌和感恩。',
        '共同愿景': '找时间一起讨论未来规划，将个人目标和共同目标对齐。定期检视并调整方向。',
        '个人空间': '健康的关系需要独立的个人空间。支持对方的兴趣爱好，保持各自的社交圈。',
        '幸福感': '有意识地制造快乐时刻——小惊喜、一起做饭、散步。记录"感恩日记"关注积极面。',
        '总体满意': '关系满意度低时，先检查自身需求是否清楚表达。考虑做一次深度对话，或寻求专业咨询。',
    };
    if (weak.length > 0) {
        sugEl.innerHTML = weak.map(d => `<div class="report-suggestion my-1">${svgIcon('i-lightbulb', 'icon-sm')} <strong>${d}：</strong>${suggestions[d] || '建议与伴侣深入沟通这个话题。'}</div>`).join('');
    } else {
        sugEl.innerHTML = '<div class="report-suggestion my-1">你们的关系各维度都很不错！保持现有的良好互动模式，继续相互关爱。</div>';
    }
}

function resetHealthTest() {
    initHealthTest();
}

// ── 关系社区 ──
async function loadCommunityTips() {
    try {
        const data = await api.getCommunityTips(state.currentPair?.type);
        const tips = data.tips || data || [];
        const list = document.getElementById('community-tips-list');
        if (tips.length > 0) {
            list.innerHTML = tips.map(t => `
                <div class="card">
                    <div class="text-sm leading-relaxed">${t.content || t.tip || t}</div>
                    ${t.author ? `<div class="text-xs text-muted mt-2">— ${t.author}</div>` : ''}
                    ${t.category ? `<span class="tag tag--muted mt-2">${t.category}</span>` : ''}
                </div>
            `).join('');
        } else {
            list.innerHTML = '<div class="text-sm text-muted text-center p-3">暂无内容</div>';
        }
    } catch (err) {
        console.error('加载社区内容失败', err);
    }
}

async function generateCommunityTip() {
    if (!state.currentPair) { showToast('请先完成配对'); return; }
    const btn = document.getElementById('community-generate-btn');
    btn.disabled = true;
    btn.innerHTML = `${svgIcon('i-refresh', 'icon-sm spin')} 生成中...`;

    try {
        const data = await api.generateTip(state.currentPair?.type);
        const el = document.getElementById('community-generated');
        show(el);
        el.innerHTML = `
            <div class="card card--accent">
                <div class="text-sm leading-relaxed">${data.tip || data.content || '暂无建议'}</div>
            </div>
        `;
    } catch (err) {
        showToast(err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `${svgIcon('i-sparkles', 'icon-sm')} 生成专属建议`;
    }
}

// ── 关系挑战赛 ──
async function loadChallenges() {
    if (!state.currentPair) return;
    try {
        const data = await api.getDailyTasks(state.currentPair.id);
        const tasks = data.tasks || data || [];
        const completed = tasks.filter(t => t.completed || t.status === 'completed');
        const total = tasks.length;

        // 进度
        const pct = total > 0 ? Math.round((completed.length / total) * 100) : 0;
        document.getElementById('challenge-progress-bar').style.width = `${pct}%`;
        document.getElementById('challenge-progress-text').textContent = `已完成 ${completed.length}/${total} 个任务`;

        // 统计
        document.getElementById('stat-total').textContent = total;
        document.getElementById('stat-completed').textContent = completed.length;

        // 任务列表
        const taskEl = document.getElementById('challenge-tasks');
        if (tasks.length > 0) {
            taskEl.innerHTML = tasks.map(t => {
                const done = t.completed || t.status === 'completed';
                return `
                    <div class="option-card ${done ? 'option-card--completed' : ''} mb-1">
                        <div class="option-card__icon">
                            ${done ? svgIcon('i-check-circle', 'icon-sm') : svgIcon('i-target', 'icon-sm')}
                        </div>
                        <div class="flex-1">
                            <div class="text-sm ${done ? 'text-muted' : 'font-semibold'}">${t.title || t.task || '任务'}</div>
                            ${t.description ? `<div class="text-xs text-muted">${t.description}</div>` : ''}
                        </div>
                        ${!done && t.id ? `<button class="btn btn-sm btn-primary" onclick="completeChallenge('${t.id}')">完成</button>` : ''}
                        ${done ? `<span class="text-xs text-brand">已完成</span>` : ''}
                    </div>
                `;
            }).join('');
        } else {
            taskEl.innerHTML = '<div class="text-sm text-muted text-center p-3">暂无任务</div>';
        }

        // 连续天数从 streak 接口获取
        try {
            const streak = await api.getCheckinStreak(state.currentPair.id);
            document.getElementById('stat-streak').textContent = streak.streak || 0;
        } catch (e) { /* 忽略 */ }

    } catch (err) {
        console.error('加载挑战赛失败', err);
    }
}

async function completeChallenge(taskId) {
    try {
        await api.completeTask(taskId);
        showToast('任务已完成！');
        loadChallenges();
    } catch (err) { showToast(err.message); }
}

// ── 情感课程 (mock) ──
function showCourseDetail(courseId) {
    const courses = {
        communication: {
            title: '高效沟通技巧',
            lessons: 8,
            desc: '学会非暴力沟通，掌握倾听和表达的艺术。课程涵盖：积极倾听技巧、"我"语句表达法、情绪觉察与表达、边界设定与协商、冲突中的沟通策略等。',
            price: '¥99',
            outline: ['认识沟通模式', '倾听的艺术', '"我"语句练习', '非暴力沟通四步法', '情绪表达技巧', '设定健康边界', '冲突中的沟通', '实战演练与总结']
        },
        conflict: {
            title: '冲突管理大师',
            lessons: 6,
            desc: '将冲突转化为亲密的契机。基于戈特曼研究方法，学会识别"末日四骑士"并运用修复对话技巧。',
            price: '¥99',
            outline: ['认识冲突的本质', '识别"末日四骑士"', '情绪调节技巧', '修复对话方法', '创建安全对话空间', '长期冲突管理策略']
        },
        intimacy: {
            title: '亲密关系升级',
            lessons: 10,
            desc: '从相爱到深爱的完整指南。涵盖情感联结、身体亲密、精神共鸣三个维度的深度提升。',
            price: '¥99',
            outline: ['亲密关系的五个阶段', '情感联结的秘密', '爱的五种语言', '创造仪式感', '共同成长的路径', '重燃激情的方法', '精神亲密的培养', '日常亲密小习惯', '长期关系的保鲜', '打造专属亲密蓝图']
        },
        attachment: {
            title: '依恋理论与实践',
            lessons: 5,
            desc: '深入了解四种依恋风格如何影响你的亲密关系，学会与不同依恋风格的伴侣和谐相处。',
            price: '¥99',
            outline: ['依恋理论基础', '四种依恋风格详解', '识别自己的依恋模式', '与不同风格相处策略', '走向安全型依恋']
        },
        intro: {
            title: '关系健康入门指南',
            lessons: 3,
            desc: '免费入门课程，带你了解关系健康的基础知识和「亲健」的使用方法。',
            price: '免费',
            outline: ['什么是关系健康', '每日打卡的意义', '如何阅读AI报告']
        }
    };

    const c = courses[courseId];
    if (!c) return;

    openModal(`
        <div class="modal-title text-center">${c.title}</div>
        <div class="text-sm text-secondary leading-relaxed mb-4">${c.desc}</div>
        <div class="card mb-3">
            <div class="text-sm font-semibold mb-2">${svgIcon('i-clipboard', 'icon-sm')} 课程大纲（${c.lessons}节）</div>
            ${c.outline.map((l, i) => `<div class="text-sm text-secondary py-1">${i + 1}. ${l}</div>`).join('')}
        </div>
        <div class="text-center mb-3">
            <span class="text-2xl font-bold">${c.price}</span>
        </div>
        <button class="btn ${c.price === '免费' ? 'btn-primary' : 'btn-outline'} btn-block" onclick="showToast('课程功能开发中，敬请期待');closeModal()">
            ${c.price === '免费' ? '立即学习' : '购买课程'}
        </button>
        <button class="btn btn-secondary btn-block mt-2" onclick="closeModal()">返回</button>
    `);
}

// ── 专家咨询 (mock) ──
function showExpertDetail(expertId) {
    const experts = {
        zhang: {
            name: '张心怡', title: '国家二级心理咨询师',
            exp: '10年', price: '¥150/50分钟',
            specialties: ['婚恋关系', '情感修复', '亲密关系提升'],
            bio: '毕业于北京师范大学心理学系，拥有10年婚恋咨询经验。擅长运用情绪聚焦疗法(EFT)和戈特曼方法帮助伴侣重建情感联结。已帮助500+对伴侣改善关系质量。',
            rating: 4.9, reviews: 328
        },
        li: {
            name: '李明辉', title: '家庭治疗师',
            exp: '8年', price: '¥120/50分钟',
            specialties: ['沟通障碍', '亲子关系', '家庭系统治疗'],
            bio: '中国心理学会会员，系统式家庭治疗师。专注家庭关系动力学研究，擅长帮助家庭成员理解彼此的互动模式，建立更健康的沟通方式。',
            rating: 4.8, reviews: 256
        },
        wang: {
            name: '王婷婷', title: '情感教练',
            exp: '6年', price: '¥80/50分钟',
            specialties: ['恋爱指导', '自我成长', '分手修复'],
            bio: '认证情感教练，心理学硕士。以温暖、务实的风格陪伴来访者探索内心，特别擅长帮助年轻人建立健康的恋爱观和沟通习惯。',
            rating: 4.7, reviews: 189
        }
    };

    const e = experts[expertId];
    if (!e) return;

    openModal(`
        <div class="text-center mb-4">
            <div class="avatar avatar--lg mx-auto mb-2">${e.name[0]}</div>
            <div class="text-lg font-semibold">${e.name}</div>
            <div class="text-sm text-muted">${e.title} · ${e.exp}经验</div>
            <div class="flex justify-center gap-2 mt-2">
                ${e.specialties.map(s => `<span class="tag tag--muted">${s}</span>`).join('')}
            </div>
        </div>
        <div class="card mb-3">
            <div class="text-sm text-secondary leading-relaxed">${e.bio}</div>
        </div>
        <div class="flex justify-between mb-4">
            <div class="text-center flex-1">
                <div class="text-lg font-bold text-warning">${e.rating}</div>
                <div class="text-xs text-muted">评分</div>
            </div>
            <div class="text-center flex-1">
                <div class="text-lg font-bold">${e.reviews}</div>
                <div class="text-xs text-muted">评价</div>
            </div>
            <div class="text-center flex-1">
                <div class="text-lg font-bold text-brand">${e.price.split('/')[0]}</div>
                <div class="text-xs text-muted">/50分钟</div>
            </div>
        </div>
        <button class="btn btn-primary btn-block" onclick="showToast('预约功能开发中，敬请期待');closeModal()">
            ${svgIcon('i-calendar', 'icon-sm')} 预约咨询
        </button>
        <button class="btn btn-secondary btn-block mt-2" onclick="closeModal()">返回</button>
    `);
}

// ── 页面加载路由钩子 ──
function onPageEnter(pageId) {
    switch (pageId) {
        case 'longdistance': loadLongDistance(); break;
        case 'attachment-test':
            // 如果已有分析结果则加载，否则显示介绍
            if (state.currentPair) {
                api.getAttachmentAnalysis(state.currentPair.id)
                    .then(data => { if (data && data.attachment_style) renderAttachmentResult(data); })
                    .catch(() => { /* 无历史结果，显示介绍 */ });
            }
            break;
        case 'health-test': initHealthTest(); break;
        case 'community': loadCommunityTips(); break;
        case 'challenges': loadChallenges(); break;
    }
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
                showToast('今天已经打过卡了');
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

    // Phase 2 事件绑定
    document.getElementById('ld-suggest-btn')?.addEventListener('click', suggestLdActivity);
    document.getElementById('attachment-start-btn')?.addEventListener('click', startAttachmentTest);
    document.getElementById('community-refresh-btn')?.addEventListener('click', loadCommunityTips);
    document.getElementById('community-generate-btn')?.addEventListener('click', generateCommunityTip);

    document.getElementById('add-milestone-btn')?.addEventListener('click', async () => {
        const result = await openInputModal('添加里程碑', [
            { key: 'title', label: '里程碑名称', type: 'text', placeholder: '如：在一起100天' },
            { key: 'date', label: '日期', type: 'date', defaultValue: new Date().toISOString().split('T')[0] }
        ]);
        if (!result || !result.title) return;
        const dateStr = result.date || new Date().toISOString().split('T')[0];
        try {
            await api.createMilestone(state.currentPair.id, { title: result.title, date: dateStr, type: 'custom' });
            showToast('里程碑已添加');
            loadMilestones();
        } catch (err) { showToast(err.message); }
    });

    if (api.isLoggedIn()) {
        checkPairAndRoute();
    } else {
        showPage('auth');
    }
});
