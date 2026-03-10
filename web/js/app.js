const state = {
    currentPage: 'auth',
    authMode: 'login',
    authMethod: 'email',
    me: null,
    pairs: [],
    currentPair: null,
    profileFeedback: null,
    selectedPairType: 'couple',
    selectedReportType: 'daily',
    selectedMoods: [],
    uploadedImageUrl: null,
    uploadedVoiceUrl: null,
    todayStatus: null,
    notifications: [],
    homeSnapshot: null,
    phoneCodeCooldown: 0,
};

const DEMO = {
    me: { nickname: '演示用户', email: 'demo@qinjian.local' },
    pair: { id: 'demo-pair', type: 'couple', partner_nickname: '演示伴侣', status: 'active', invite_code: '381624' },
    todayStatus: { my_done: true, partner_done: false, both_done: false, has_report: false, has_solo_report: true },
    streak: { streak: 12 },
    tree: { level_name: '小树', growth_points: 368, progress_percent: 72, can_water: true },
    crisis: { crisis_level: 'mild', health_score: 68, intervention: { title: '建议今天安排一次不被打断的 20 分钟对话', description: '重点不是解决问题，而是先对齐彼此的感受。', action_items: ['先说事实，不先下判断', '轮流说完再回应', '结束前给出一个可执行小动作'] } },
    tasks: {
        attachment_a: 'secure', attachment_b: 'anxious', tasks: [
            { id: 'demo-task-1', title: '今天说一次具体的感谢', description: '不要泛泛而谈，指出一个具体瞬间。', category: 'communication', status: 'pending' },
            { id: 'demo-task-2', title: '安排 15 分钟无手机聊天', description: '只聊今天的情绪和真实感受。', category: 'activity', status: 'completed' },
        ], combination_insight: '一方更稳定，一方更需要回应时，最有效的是“及时确认”而不是“讲道理”。'
    },
    tips: {
        tips: [
            { title: '今天的经营提示', content: '当对方表达情绪时，先复述感受，再给建议。先被理解，才会愿意继续沟通。' },
            { title: '小动作比大承诺更值钱', content: '关系改善最怕只在情绪高点说漂亮话，最有用的是每天一个真实的小动作。' },
        ]
    },
    report: {
        daily: {
            status: 'completed',
            report_date: '2026-03-06',
            content: {
                health_score: 74,
                insight: '今天的关系状态并不差，但存在轻微节奏错位：你更愿意表达，对方更倾向于延后回应。',
                suggestion: '今晚不讨论对错，只同步各自今天最在意的一件事。',
                highlights: ['你们都保持了联系，没有完全回避', '冲突强度可控，仍有修复空间'],
                concerns: ['回应时机不一致，容易被解读为忽视'],
            },
        },
        weekly: {
            status: 'completed',
            report_date: '2026-03-06',
            content: {
                overall_health_score: 76,
                trend_description: '过去一周整体稳定，情绪波动主要集中在沟通延迟。',
                encouragement: '稳定关系的关键不是没有摩擦，而是出现摩擦后还能回到连接。',
                weekly_highlights: ['连续 5 天保持互动', '冲突后的恢复速度变快'],
                action_plan: ['建立固定的晚间同步时间', '减少“你总是”式表达'],
            },
        },
        monthly: {
            status: 'completed',
            report_date: '2026-03-06',
            content: {
                overall_health_score: 79,
                executive_summary: '这段关系具备稳定基础，主要提升空间在沟通效率和需求表达的清晰度。',
                strengths: ['持续记录习惯正在形成', '遇到问题仍愿意继续交流'],
                growth_areas: ['边界表达还不够具体', '对“被理解”的期待高于实际回应能力'],
                next_month_goals: ['每周一次长对话', '建立冲突暂停机制'],
            },
        },
    },
    history: [
        { report_date: '2026-03-06', status: 'completed' },
        { report_date: '2026-03-05', status: 'completed' },
        { report_date: '2026-03-04', status: 'completed' },
    ],
    trend: {
        trend: [
            { date: '2026-02-28', score: 61 },
            { date: '2026-03-01', score: 63 },
            { date: '2026-03-02', score: 66 },
            { date: '2026-03-03', score: 67 },
            { date: '2026-03-04', score: 69 },
            { date: '2026-03-05', score: 72 },
            { date: '2026-03-06', score: 74 },
        ],
        direction: 'improving',
    },
    notifications: [
        { id: 'n1', type: 'tip', content: '今天适合做一次低防御沟通。', is_read: false, created_at: '2026-03-06T08:30:00' },
        { id: 'n2', type: 'task', content: '你们今日任务已生成，建议晚饭后完成。', is_read: true, created_at: '2026-03-06T09:10:00' },
    ],
    longdistance: {
        health_index: 71.5,
        communication_timeliness: 64,
        expression_frequency: 78,
        deep_conversation_rate: 69,
        overlap_days: 8,
        checkin_days_a: 11,
        checkin_days_b: 9,
        activities: [
            { id: 'a1', type: 'movie', title: '周末一起看电影', status: 'pending', created_at: '2026-03-05T18:00:00' },
            { id: 'a2', type: 'chat', title: '晚间视频深聊', status: 'completed', created_at: '2026-03-03T20:30:00' },
        ],
    },
    milestones: [
        { id: 'm1', type: 'anniversary', title: '恋爱一周年', date: '2026-03-12', days_until: 6, days_since: 0, reminder_sent: false },
        { id: 'm2', type: 'custom', title: '第一次一起旅行', date: '2025-11-03', days_until: null, days_since: 123, reminder_sent: true },
    ],
    attachment: { pair_id: 'demo-pair', attachment_a: { type: 'secure', label: '安全型' }, attachment_b: { type: 'anxious', label: '焦虑型' }, analyzed_at: '2026-03-05 22:00:00' },
};

const MOOD_TAGS = ['开心', '平静', '感动', '期待', '焦虑', '委屈', '生气', '疲惫'];
const TYPE_LABELS = { couple: '情侣', spouse: '夫妻', bestfriend: '挚友', parent: '育儿夫妻' };
const ATTACHMENT_LABELS = { secure: '安全型', anxious: '焦虑型', avoidant: '回避型', fearful: '恐惧型', unknown: '未分析' };
const ACTIVITY_LABELS = { movie: '一起看电影', meal: '共享一顿饭', chat: '视频深聊', gift: '寄一份礼物', exercise: '同步运动' };
const HEALTH_TEST_QUESTIONS = [
    { q: '你觉得和 TA 的沟通质量如何？', dim: '沟通质量', options: ['非常好', '比较好', '一般', '较差', '很差'] },
    { q: '你是否经常感受到 TA 的支持？', dim: '情感支持', options: ['总是', '经常', '有时', '偶尔', '从不'] },
    { q: '你们之间的信任程度如何？', dim: '信任程度', options: ['完全信任', '比较信任', '一般', '较弱', '很弱'] },
    { q: '你们能否说出自己的真实需求？', dim: '表达能力', options: ['总是可以', '大多可以', '有时可以', '不太可以', '几乎不能'] },
    { q: '冲突过后你们能修复关系吗？', dim: '修复能力', options: ['很快修复', '大多能修复', '有时能', '很难', '几乎不能'] },
    { q: '你是否觉得自己被尊重？', dim: '尊重感', options: ['非常强', '比较强', '一般', '较弱', '很弱'] },
    { q: '你们是否有共同生活目标？', dim: '共同愿景', options: ['非常一致', '比较一致', '一般', '较少一致', '几乎没有'] },
    { q: '这段关系是否给你带来稳定感？', dim: '安全感', options: ['非常强', '比较强', '一般', '较弱', '很弱'] },
    { q: '你们相处时是否能感到轻松？', dim: '幸福感', options: ['总是', '经常', '有时', '偶尔', '从不'] },
    { q: '总体而言，你对这段关系满意吗？', dim: '总体满意', options: ['非常满意', '比较满意', '一般', '不太满意', '很不满意'] },
];

let healthTestState = { current: 0, answers: [] };

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function svgIcon(id, className = '') {
    const extra = className ? ` ${className}` : '';
    return `<svg class="icon${extra}"><use href="#${id}"></use></svg>`;
}

function showToast(message, duration = 2400) {
    const toast = $('#toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.remove('show'), duration);
}

function openModal(html) {
    const overlay = $('#modal-overlay');
    const body = $('#modal-body');
    if (!overlay || !body) return;
    body.innerHTML = html;
    overlay.classList.remove('hidden');
}

function closeModal() {
    $('#modal-overlay')?.classList.add('hidden');
}

function isLiveMode() {
    return api.isLoggedIn() && Boolean(state.currentPair);
}

function getPairSnapshot() {
    return state.currentPair || DEMO.pair;
}

function getPartnerDisplayName(pair) {
    if (!pair) return '关系对象';
    return pair.custom_partner_nickname || pair.partner_nickname || pair.partner_email || pair.partner_phone || '关系对象';
}

function resolveAssetUrl(path) {
    if (!path) return '';
    if (/^https?:\/\//i.test(path)) return path;
    const origin = window.API_ROOT ? window.API_ROOT.replace(/\/api\/v1$/, '') : window.location.origin;
    return `${origin}${path}`;
}

function setCurrentPair(pairId) {
    const match = state.pairs.find((pair) => pair.id === pairId);
    if (!match) return;
    state.currentPair = match;
    localStorage.setItem('qj_current_pair', pairId);
}

function upsertPair(updatedPair) {
    state.pairs = state.pairs.map((pair) => pair.id === updatedPair.id ? updatedPair : pair);
    if (state.currentPair?.id === updatedPair.id) {
        state.currentPair = updatedPair;
    }
}

function syncTopbar() {
    const titleMap = {
        auth: '关系健康工作台',
        pair: '创建或加入关系',
        'pair-waiting': '等待对方加入',
        home: '关系首页',
        checkin: '每日打卡',
        discover: '发现与扩展',
        report: 'AI 报告中心',
        profile: '账户与设置',
        milestones: '关系里程碑',
        longdistance: '异地关系模式',
        'attachment-test': '依恋分析',
        'health-test': '关系体检',
        community: '社群技巧',
        challenges: '关系挑战',
        courses: '内容展示',
        experts: '咨询服务',
        membership: '会员方案',
    };
    $('#topbar-title').textContent = titleMap[state.currentPage] || '关系健康工作台';
    $('#topbar-demo-badge').textContent = isLiveMode() ? '已连接后端' : '演示态';
}

function syncTabBar() {
    const visible = api.isLoggedIn() && Boolean(state.currentPair);
    $('#tab-bar')?.classList.toggle('hidden', !visible);
}

function syncTabSelection(pageId) {
    $$('.tab-item').forEach((button) => {
        button.classList.toggle('tab-item--active', button.dataset.page === pageId);
    });
}

async function showPage(pageId) {
    $$('.page').forEach((page) => page.classList.remove('active'));
    $(`#page-${pageId}`)?.classList.add('active');
    state.currentPage = pageId;
    syncTopbar();
    syncTabSelection(pageId);

    switch (pageId) {
        case 'pair':
            renderPairPage();
            break;
        case 'pair-waiting':
            renderWaitingPage();
            break;
        case 'home':
            await loadHomePage();
            break;
        case 'checkin':
            renderCheckinPage();
            break;
        case 'report':
            await loadReportPage();
            break;
        case 'profile':
            await loadProfilePage();
            break;
        case 'milestones':
            await loadMilestonesPage();
            break;
        case 'longdistance':
            await loadLongDistancePage();
            break;
        case 'attachment-test':
            await loadAttachmentPage();
            break;
        case 'health-test':
            initHealthTest();
            break;
        case 'community':
            await loadCommunityPage();
            break;
        case 'challenges':
            await loadChallengesPage();
            break;
        default:
            break;
    }
}

async function bootstrapSession() {
    if (!api.isLoggedIn()) {
        state.me = null;
        state.pairs = [];
        state.currentPair = null;
        syncTabBar();
        return false;
    }

    try {
        const [me, pairs] = await Promise.all([api.getMe(), api.getMyPairs()]);
        state.me = me;
        state.pairs = pairs;

        const storedPairId = localStorage.getItem('qj_current_pair');
        const activePairs = pairs.filter((pair) => pair.status === 'active');
        const pendingPairs = pairs.filter((pair) => pair.status === 'pending');
        state.currentPair = activePairs.find((pair) => pair.id === storedPairId)
            || pendingPairs.find((pair) => pair.id === storedPairId)
            || activePairs[0]
            || pendingPairs[0]
            || null;

        syncTabBar();

        if (activePairs.length > 0) {
            await showPage('home');
            return true;
        }

        if (pendingPairs.length > 0) {
            await showPage('pair-waiting');
            return true;
        }

        await showPage('pair');
        return true;
    } catch (error) {
        api.clearToken();
        state.me = null;
        state.pairs = [];
        state.currentPair = null;
        syncTabBar();
        showToast(error.message || '登录状态已失效');
        await showPage('auth');
        return false;
    }
}

function switchAuthMode(mode) {
    state.authMode = mode;
    $('#auth-mode-login').classList.toggle('segmented__item--active', mode === 'login');
    $('#auth-mode-register').classList.toggle('segmented__item--active', mode === 'register');
    syncAuthForm();
}

function switchAuthMethod(method) {
    state.authMethod = method;
    $('#auth-method-email').classList.toggle('segmented__item--active', method === 'email');
    $('#auth-method-phone').classList.toggle('segmented__item--active', method === 'phone');
    syncAuthForm();
}

function syncAuthForm() {
    const isEmail = state.authMethod === 'email';
    const isRegister = state.authMode === 'register';

    $('#auth-nickname-wrap').classList.toggle('hidden', !isEmail || !isRegister);
    $('#auth-email-wrap').classList.toggle('hidden', !isEmail);
    $('#auth-password-wrap').classList.toggle('hidden', !isEmail);
    $('#auth-phone-wrap').classList.toggle('hidden', isEmail);
    $('#auth-phone-code-wrap').classList.toggle('hidden', isEmail);
    $('#auth-phone-note').classList.toggle('hidden', isEmail);

    $('#auth-email').disabled = !isEmail;
    $('#auth-password').disabled = !isEmail;
    $('#auth-phone').disabled = isEmail;
    $('#auth-phone-code').disabled = isEmail;
    $('#auth-nickname').disabled = !isEmail || !isRegister;

    $('#auth-email').required = isEmail;
    $('#auth-password').required = isEmail;
    $('#auth-phone').required = !isEmail;
    $('#auth-phone-code').required = !isEmail;
    $('#auth-nickname').required = isEmail && isRegister;

    $('#auth-submit').textContent = isEmail
        ? (isRegister ? '创建并进入' : '进入工作台')
        : '验证码进入';
}

function validatePhone(phone) {
    return /^1\d{10}$/.test(phone);
}

function updateSendCodeButton() {
    const button = $('#auth-send-code');
    if (!button) return;
    if (state.phoneCodeCooldown > 0) {
        button.disabled = true;
        button.textContent = `${state.phoneCodeCooldown}s 后重试`;
        return;
    }

    button.disabled = false;
    button.textContent = '获取验证码';
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
    }, 1000);
}

async function handleSendPhoneCode() {
    const phone = $('#auth-phone').value.trim();
    if (!validatePhone(phone)) {
        showToast('请输入正确的 11 位手机号');
        return;
    }

    try {
        const payload = await api.sendPhoneCode(phone);
        startPhoneCodeCooldown(60);
        showToast(payload.debug_code ? `验证码已发送：${payload.debug_code}` : '验证码已发送');
    } catch (error) {
        const message = error.message || '发送失败';
        const match = String(message).match(/(\d+)\s*秒/);
        if (match) {
            startPhoneCodeCooldown(Number(match[1]));
        }
        showToast(message);
    }
}

async function handleAuthSubmit(event) {
    event.preventDefault();
    const email = $('#auth-email').value.trim();
    const password = $('#auth-password').value;
    const nickname = $('#auth-nickname').value.trim();
    const phone = $('#auth-phone').value.trim();
    const phoneCode = $('#auth-phone-code').value.trim();
    const submit = $('#auth-submit');

    if (state.authMethod === 'phone') {
        if (!validatePhone(phone)) {
            showToast('请输入正确的 11 位手机号');
            return;
        }

        if (!/^\d{6}$/.test(phoneCode)) {
            showToast('请输入 6 位验证码');
            return;
        }

        submit.disabled = true;
        submit.textContent = '登录中...';

        try {
            await api.phoneLogin(phone, phoneCode);
            showToast('登录成功');
            await bootstrapSession();
        } catch (error) {
            showToast(error.message || '提交失败');
        } finally {
            submit.disabled = false;
            syncAuthForm();
        }
        return;
    }

    if (!email || !password) {
        showToast('请填写邮箱和密码');
        return;
    }

    if (state.authMode === 'register' && !nickname) {
        showToast('注册时请填写昵称');
        return;
    }

    submit.disabled = true;
    submit.textContent = state.authMode === 'login' ? '登录中...' : '注册中...';

    try {
        if (state.authMode === 'login') {
            await api.login(email, password);
            showToast('登录成功');
        } else {
            await api.register(email, nickname, password);
            showToast('注册成功');
        }

        await bootstrapSession();
    } catch (error) {
        if (state.authMode === 'login' && String(error.message || '').includes('尚未注册')) {
            showToast('这个邮箱还没注册，请先注册新账号');
        } else if (state.authMode === 'login' && String(error.message || '').includes('密码错误')) {
            showToast('密码错误，请重新输入');
        } else {
            showToast(error.message || '提交失败');
        }
    } finally {
        submit.disabled = false;
        submit.textContent = state.authMode === 'login' ? '进入工作台' : '创建并进入';
    }
}

function renderPairPage() {
    const list = $('#pair-existing-list');
    const activePairs = state.pairs.filter((pair) => pair.status === 'active');
    const pendingPairs = state.pairs.filter((pair) => pair.status === 'pending');
    const allPairs = [...activePairs, ...pendingPairs];

    if (!allPairs.length) {
        list.innerHTML = '<div class="empty-state">你还没有建立任何关系。这里会显示你已经创建或加入的配对。</div>';
        return;
    }

    list.innerHTML = allPairs.map((pair) => {
        const label = TYPE_LABELS[pair.type] || pair.type;
        const partner = pair.status === 'active' ? getPartnerDisplayName(pair) : (pair.partner_nickname || pair.partner_email || pair.partner_phone || '等待对方加入');
        const activeText = state.currentPair?.id === pair.id ? '当前关系' : '切换到此关系';
        return `
      <button class="stack-item" type="button" onclick="handleSwitchPair('${pair.id}')">
        <div>
          <strong>${escapeHtml(label)}</strong>
          <div class="stack-item__meta">${escapeHtml(partner)} · ${pair.status === 'active' ? '已配对' : '等待加入'}</div>
        </div>
        <span class="pill">${activeText}</span>
      </button>`;
    }).join('');
}

async function handleCreatePair() {
    const button = $('#pair-create-btn');
    button.disabled = true;
    button.textContent = '创建中...';

    try {
        if (state.selectedPairType === 'solo') {
            const pair = { id: 'solo', type: 'solo', status: 'active', partner_nickname: '自己' };
            state.pairs = [...state.pairs.filter((item) => item.id !== 'solo'), pair];
            state.currentPair = pair;
            showToast('已进入单人模式');
            await bootstrapSession();
            return;
        }

        const pair = await api.createPair(state.selectedPairType);
        state.pairs = [...state.pairs.filter((item) => item.id !== pair.id), pair];
        state.currentPair = pair;
        showToast('邀请码已生成');
        await showPage('pair-waiting');
    } catch (error) {
        showToast(error.message || '创建失败');
    } finally {
        button.disabled = false;
        button.textContent = '创建邀请码';
    }
}

async function handleJoinPair() {
    const code = $('#pair-join-code').value.trim();
    if (!code) {
        showToast('请输入邀请码');
        return;
    }

    const button = $('#pair-join-btn');
    button.disabled = true;
    button.textContent = '加入中...';

    try {
        await api.joinPair(code);
        showToast('加入成功');
        await bootstrapSession();
    } catch (error) {
        showToast(error.message || '加入失败');
    } finally {
        button.disabled = false;
        button.textContent = '加入关系';
    }
}

function renderWaitingPage() {
    $('#waiting-invite-code').textContent = state.currentPair?.invite_code || DEMO.pair.invite_code;
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

async function loadHomePage() {
    const pair = getPairSnapshot();
    const greetingName = state.me?.nickname || DEMO.me.nickname;
    $('#home-greeting').textContent = `${greetingName}，今天也适合把关系照顾好`;
    renderPairSelect();

    if (!isLiveMode()) {
        renderHome({
            pair,
            todayStatus: DEMO.todayStatus,
            streak: DEMO.streak,
            tree: DEMO.tree,
            crisis: DEMO.crisis,
            tasks: DEMO.tasks,
            notifications: DEMO.notifications,
            milestones: [],
        }, true);
        return;
    }

    const results = await Promise.allSettled([
        api.getTodayStatus(pair.id),
        api.getCheckinStreak(pair.id),
        api.getTreeStatus(pair.id),
        api.getCrisisStatus(pair.id),
        api.getDailyTasks(pair.id),
        api.getNotifications(),
        api.getMilestones(pair.id),
    ]);

    renderHome({
        pair,
        todayStatus: unwrapResult(results[0], DEMO.todayStatus),
        streak: unwrapResult(results[1], DEMO.streak),
        tree: unwrapResult(results[2], DEMO.tree),
        crisis: unwrapResult(results[3], DEMO.crisis),
        tasks: unwrapResult(results[4], DEMO.tasks),
        notifications: unwrapResult(results[5], []),
        milestones: unwrapResult(results[6], []),
    }, false);
}

function unwrapResult(result, fallback) {
    return result.status === 'fulfilled' ? result.value : fallback;
}

function renderPairSelect() {
    const select = $('#home-pair-select');
    const source = isLiveMode() ? state.pairs.filter((pair) => pair.status === 'active') : [DEMO.pair];
    select.innerHTML = source.map((pair) => `<option value="${pair.id}">${escapeHtml(TYPE_LABELS[pair.type] || pair.type)} · ${escapeHtml(getPartnerDisplayName(pair))}</option>`).join('');
    select.value = getPairSnapshot().id;
}

function renderHome(payload, isDemo) {
    state.homeSnapshot = payload;
    const pairName = getPartnerDisplayName(payload.pair);
    $('#home-overview').innerHTML = `
        <p class="eyebrow">${isDemo ? 'DEMO MODE' : 'CONNECTED'}</p>
        <h3>${escapeHtml(TYPE_LABELS[payload.pair.type] || payload.pair.type)} · ${escapeHtml(pairName)}</h3>
        <p>${isDemo ? '当前为演示数据，只展示核心功能状态。' : '当前展示的是这段关系的核心功能状态。'}</p>
    `;

    $('#home-metrics').innerHTML = [
        demoMetric('连续打卡', `${payload.streak.streak || 0} 天`),
        demoMetric('关系树', `${payload.tree.level_name || '种子'}`),
        demoMetric('成长值', `${payload.tree.growth_points || 0}`),
        demoMetric('当前预警', crisisLabel(payload.crisis.crisis_level || 'none')),
    ].join('');

    $('#home-status-panel').innerHTML = `
    <div class="panel__header"><div><p class="panel__eyebrow">TODAY</p><h4>今日打卡状态</h4></div></div>
    <div class="stack-list">
      <div class="stack-item"><div><strong>我</strong><div class="stack-item__meta">${payload.todayStatus.my_done ? '已完成今日打卡' : '今天还没有提交'}</div></div><span class="pill">${payload.todayStatus.my_done ? '完成' : '待办'}</span></div>
      <div class="stack-item"><div><strong>对方</strong><div class="stack-item__meta">${payload.todayStatus.partner_done ? '对方已经完成' : '对方尚未完成'}</div></div><span class="pill">${payload.todayStatus.partner_done ? '完成' : '等待中'}</span></div>
    </div>
    <div class="hero-actions">
      <button class="button button--primary" type="button" onclick="showPage('checkin')">去打卡</button>
      <button class="button button--ghost" type="button" onclick="showPage('report')">看报告</button>
    </div>`;

    $('#home-report-panel').innerHTML = `
    <div class="panel__header"><div><p class="panel__eyebrow">REPORT</p><h4>报告入口</h4></div></div>
    <div class="empty-state">
      ${payload.todayStatus.both_done ? '双方都已完成打卡，可以生成正式关系报告。' : '双方未全部完成时，网页端优先展示状态与下一步建议。'}
    </div>
    <div class="hero-actions">
      <button class="button button--secondary" type="button" onclick="showPage('report')">进入报告页</button>
    </div>`;

    $('#home-tree-panel').innerHTML = `
    <div class="panel__header"><div><p class="panel__eyebrow">TREE</p><h4>关系树成长</h4></div></div>
    <div class="stack-item"><div>${svgIcon('i-tree')}</div><div><strong>${escapeHtml(payload.tree.level_name || '种子')}</strong><div class="stack-item__meta">当前成长值 ${payload.tree.growth_points || 0}</div></div></div>
    <div class="progress-track"><span class="progress-track__fill" style="width:${payload.tree.progress_percent || 0}%"></span></div>
    <div class="hero-actions">
      <button class="button button--ghost" type="button" ${payload.tree.can_water ? '' : 'disabled'} onclick="handleWaterTree()">${payload.tree.can_water ? '浇水 +5' : '今日已浇水'}</button>
    </div>`;

    const crisis = payload.crisis || { crisis_level: 'none' };
    const crisisIntervention = crisis.intervention ? `<div class="stack-item__meta">${escapeHtml(crisis.intervention.title || crisis.intervention.description || '')}</div>` : '<div class="stack-item__meta">暂无需要立即介入的强预警。</div>';
    $('#home-crisis-panel').innerHTML = `
    <div class="panel__header"><div><p class="panel__eyebrow">CRISIS</p><h4>危机预警</h4></div></div>
    <div class="stack-item"><div>${svgIcon('i-alert')}</div><div><strong>${crisisLabel(crisis.crisis_level || 'none')}</strong>${crisisIntervention}</div></div>
    <div class="hero-actions">
      <button class="button button--ghost" type="button" onclick="openCrisisDetail()">查看详情</button>
    </div>`;

    const milestones = payload.milestones || [];
    $('#home-milestones-panel').innerHTML = `
        <div class="panel__header"><div><p class="panel__eyebrow">MILESTONES</p><h4>关键节点</h4></div></div>
        ${milestones.length ? `<div class="stack-list">${milestones.slice(0, 2).map((item) => renderMilestoneItem(item, { isDemo, compact: true })).join('')}</div>` : '<div class="empty-state">还没有记录关系里程碑。</div>'}
        <div class="hero-actions">
            <button class="button button--ghost" type="button" onclick="showPage('milestones')">进入里程碑页</button>
        </div>`;

    const tasks = payload.tasks.tasks || [];
    $('#home-tasks-panel').innerHTML = `
    <div class="panel__header"><div><p class="panel__eyebrow">TASKS</p><h4>今日关系任务</h4></div></div>
    <div class="stack-list">
      ${tasks.length ? tasks.slice(0, 3).map((task) => renderTaskItem(task)).join('') : '<div class="empty-state">今天还没有生成任务。</div>'}
    </div>`;

    state.notifications = Array.isArray(payload.notifications) ? payload.notifications : payload.notifications || [];
    syncNotifications();
}

function renderTaskItem(task) {
    const done = task.status === 'completed';
    return `
    <div class="challenge-item">
      <div>${done ? svgIcon('i-check') : svgIcon('i-target')}</div>
      <div>
        <strong>${escapeHtml(task.title)}</strong>
        <div class="stack-item__meta">${escapeHtml(task.description || '')}</div>
      </div>
      ${done ? '<span class="pill">已完成</span>' : `<button class="text-button" type="button" onclick="completeTask('${task.id}')">完成</button>`}
    </div>`;
}

function crisisLabel(level) {
    return { none: '正常', mild: '轻度预警', moderate: '中度预警', severe: '严重预警' }[level] || '正常';
}

function syncNotifications() {
    const button = $('#notification-toggle');
    const count = $('#notification-count');
    const list = $('#notification-drawer-list');
    const notifications = state.notifications || [];
    if (!notifications.length) {
        button.classList.add('hidden');
        list.innerHTML = '<div class="empty-state">暂无通知。</div>';
        return;
    }

    button.classList.remove('hidden');
    const unread = notifications.filter((item) => !item.is_read).length;
    count.classList.toggle('hidden', unread === 0);
    count.textContent = unread > 9 ? '9+' : String(unread);
    list.innerHTML = notifications.map((item) => `
    <article class="notification-item">
      <div>${svgIcon('i-bell')}</div>
      <div>
        <strong>${escapeHtml(item.content)}</strong>
        <div class="notification-item__meta">${formatDate(item.created_at)}</div>
      </div>
    </article>`).join('');
}

function formatDate(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return `${date.getMonth() + 1}-${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function formatDateOnly(value) {
    if (!value) return '未设置';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function maskPhone(phone) {
    if (!phone) return '未绑定';
    return String(phone).replace(/^(\d{3})\d+(\d{4})$/, '$1****$2');
}

function getAccountChannels(me) {
    const channels = [];
    if (me.email && !me.email.endsWith('@qinjian.local')) channels.push('邮箱账号');
    if (me.phone) channels.push('手机号账号');
    if (me.wechat_openid) channels.push('微信已绑定');
    return channels.length ? channels.join(' / ') : '基础邮箱账号';
}

function milestoneTypeLabel(type) {
    return {
        anniversary: '纪念日',
        proposal: '重要承诺',
        wedding: '婚礼 / 领证',
        friendship_day: '关系节点',
        custom: '自定义',
    }[type] || '里程碑';
}

function milestoneTimeText(item) {
    if (typeof item.days_until === 'number' && item.days_until > 0) {
        return `${item.days_until} 天后到来`;
    }
    if (typeof item.days_until === 'number' && item.days_until === 0) {
        return '就是今天';
    }
    if (typeof item.days_since === 'number') {
        return item.days_since === 0 ? '今天发生' : `已过去 ${item.days_since} 天`;
    }
    return '时间待确认';
}

function renderMilestoneItem(item, { isDemo = false, compact = false } = {}) {
    return `
    <article class="${compact ? 'stack-item' : 'timeline-card'}">
      <div class="${compact ? '' : 'timeline-card__head'}">
        <div>
          <strong>${escapeHtml(item.title || '未命名里程碑')}</strong>
          <div class="stack-item__meta">${escapeHtml(milestoneTypeLabel(item.type))} · ${escapeHtml(formatDateOnly(item.date))}</div>
          <div class="stack-item__meta">${escapeHtml(milestoneTimeText(item))}</div>
        </div>
        <span class="pill">${item.reminder_sent ? '已提醒' : '待提醒'}</span>
      </div>
      ${compact ? '' : `<div class="timeline-card__actions">${isDemo ? '<span class="pill">演示态不可生成回顾</span>' : `<button class="button button--ghost" type="button" data-milestone-review="${item.id}">生成成长回顾</button>`}</div>`}
    </article>`;
}

function renderCheckinPage() {
    renderMoods();
    renderOptionGroup('#mood-score-options', [1, 2, 3, 4].map((value) => ({ label: `${value} 分`, value: String(value), name: 'mood_score' })));
    renderOptionGroup('#initiative-options', [
        { label: '我更主动', value: 'me', name: 'interaction_initiative' },
        { label: '对方更主动', value: 'partner', name: 'interaction_initiative' },
        { label: '差不多', value: 'equal', name: 'interaction_initiative' },
    ]);
    renderOptionGroup('#deep-conversation-options', [
        { label: '有', value: 'true', name: 'deep_conversation' },
        { label: '没有', value: 'false', name: 'deep_conversation' },
    ]);
    renderOptionGroup('#task-completed-options', [
        { label: '完成了', value: 'true', name: 'task_completed' },
        { label: '还没有', value: 'false', name: 'task_completed' },
    ]);
}

function renderMoods() {
    const container = $('#mood-tags');
    container.innerHTML = MOOD_TAGS.map((mood) => `<button class="tag${state.selectedMoods.includes(mood) ? ' is-selected' : ''}" type="button" data-mood="${mood}">${mood}</button>`).join('');
}

function renderOptionGroup(selector, options) {
    const container = $(selector);
    container.innerHTML = options.map((option) => `<button class="select-card" type="button" data-option-name="${option.name}" data-option-value="${option.value}">${option.label}</button>`).join('');
}

async function handleCheckinSubmit(event) {
    event.preventDefault();
    if (!isLiveMode()) {
        showToast('演示态下不写入数据，请先登录并建立关系');
        return;
    }

    const content = $('#checkin-content').value.trim();
    if (!content) {
        showToast('请先写下今天的感受');
        return;
    }

    const payload = {
        content,
        mood_tags: state.selectedMoods,
        image_url: state.uploadedImageUrl,
        voice_url: state.uploadedVoiceUrl,
        mood_score: parseNullableInt(getSelectedValue('mood_score')),
        interaction_freq: parseNullableInt($('#interaction-frequency').value),
        interaction_initiative: getSelectedValue('interaction_initiative'),
        deep_conversation: parseNullableBool(getSelectedValue('deep_conversation')),
        task_completed: parseNullableBool(getSelectedValue('task_completed')),
    };

    const button = $('#checkin-submit-btn');
    button.disabled = true;
    button.textContent = '提交中...';

    try {
        await api.submitCheckin(state.currentPair.id, payload);
        showToast('今日打卡已提交');
        resetCheckinForm();
        await showPage('home');
    } catch (error) {
        showToast(error.message || '提交失败');
    } finally {
        button.disabled = false;
        button.textContent = '提交今日打卡';
    }
}

function getSelectedValue(name) {
    return document.querySelector(`[data-selected-name="${name}"]`)?.dataset.selectedValue || null;
}

function parseNullableInt(value) {
    if (value === null || value === undefined || value === '') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
}

function parseNullableBool(value) {
    if (value === null || value === undefined || value === '') return null;
    return value === 'true';
}

function resetCheckinForm() {
    $('#checkin-form').reset();
    state.selectedMoods = [];
    state.uploadedImageUrl = null;
    state.uploadedVoiceUrl = null;
    renderCheckinPage();
    $('#image-upload-preview').innerHTML = '';
    $('#voice-upload-preview').innerHTML = '';
    $$('[data-selected-name]').forEach((item) => {
        delete item.dataset.selectedName;
        delete item.dataset.selectedValue;
        item.classList.remove('select-card--active');
    });
}

async function handleUpload(type, file) {
    if (!isLiveMode()) {
        showToast('演示态下不上传文件');
        return;
    }

    try {
        const result = await api.uploadFile(type, file);
        if (type === 'image') {
            state.uploadedImageUrl = result.url;
            $('#image-upload-preview').innerHTML = `<img class="upload-preview__image" src="${resolveAssetUrl(result.url)}" alt="上传图片预览">`;
        } else {
            state.uploadedVoiceUrl = result.url;
            $('#voice-upload-preview').innerHTML = `<div class="upload-preview__chip">${svgIcon('i-mic')} 已上传语音附件</div>`;
        }
        showToast(type === 'image' ? '图片已上传' : '语音已上传');
    } catch (error) {
        showToast(error.message || '上传失败');
    }
}

async function loadReportPage() {
    if (!isLiveMode()) {
        renderReport(DEMO.report[state.selectedReportType], DEMO.history, DEMO.trend, true);
        return;
    }

    const pairId = state.currentPair.id;
    const [latest, history, trend] = await Promise.allSettled([
        api.getLatestReport(pairId, state.selectedReportType),
        api.getReportHistory(pairId, state.selectedReportType, 6),
        state.selectedReportType === 'daily' ? api.getHealthTrend(pairId, 14) : Promise.resolve({ trend: [] }),
    ]);

    renderReport(
        unwrapResult(latest, null),
        unwrapResult(history, []),
        unwrapResult(trend, { trend: [] }),
        false,
    );
}

function renderReport(report, history, trendData, isDemo) {
    const container = $('#report-main');

    if (report && report.status === 'pending') {
        container.innerHTML = `
            <div class="empty-state">
                当前${formatReportType(state.selectedReportType)}正在后台生成中。页面会在拿到结果后刷新；如果网络波动，也可以稍后再次进入本页查看。
            </div>`;
    } else if (report && report.status === 'failed') {
        container.innerHTML = `
            <div class="empty-state">
                当前${formatReportType(state.selectedReportType)}生成失败，请稍后重试。
            </div>`;
    } else if (!report || report.status !== 'completed') {
        container.innerHTML = `
      <div class="empty-state">
        当前还没有可展示的${state.selectedReportType === 'daily' ? '日报' : state.selectedReportType === 'weekly' ? '周报' : '月报'}。${isDemo ? '你现在看到的是演示状态。' : '完成打卡并触发生成后，这里会显示最新报告。'}
      </div>`;
    } else {
        const content = report.content || {};
        const score = content.health_score || content.overall_health_score || 72;
        const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
        const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);
        container.innerHTML = `
      <div class="score-ring" style="--score:${Math.max(1, Math.min(100, score))}"><span>${score}</span></div>
      <h4>${state.selectedReportType === 'daily' ? '今日关系指数' : state.selectedReportType === 'weekly' ? '周关系指数' : '月关系指数'}</h4>
      <p class="muted-copy">${escapeHtml(content.insight || content.encouragement || content.executive_summary || '系统已经生成当前阶段的关系洞察。')}</p>
      ${content.suggestion || content.trend_description ? `<div class="hero-card hero-card--accent"><strong>本阶段建议</strong><p>${escapeHtml(content.suggestion || content.trend_description)}</p></div>` : ''}
            ${renderAttachmentSignals(content)}
      ${renderTrend(trendData)}
      <div class="layout-grid">
        <div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">HIGHLIGHTS</p><h4>积极信号</h4></div></div>${renderBulletList(highlights, '当前没有高亮项')}</div>
        <div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">FOCUS</p><h4>需要关注</h4></div></div>${renderBulletList(concerns, '当前没有额外提醒')}</div>
      </div>`;
    }

    const list = $('#report-history-list');
    if (!history.length) {
        list.innerHTML = '<div class="empty-state">当前没有历史报告记录。</div>';
        return;
    }

    list.innerHTML = history.map((item) => `
    <article class="stack-item">
      <div>
        <strong>${formatReportType(state.selectedReportType)} · ${escapeHtml(item.report_date || '未命名')}</strong>
        <div class="stack-item__meta">状态：${escapeHtml(item.status || 'completed')}</div>
      </div>
      <span class="pill">已生成</span>
    </article>`).join('');
}

function renderTrend(trendData) {
    const points = trendData?.trend || [];
    if (points.length < 2) return '';
    const width = 280;
    const height = 90;
    const pad = 10;
    const coords = points.map((point, index) => {
        const x = pad + (index / (points.length - 1)) * (width - pad * 2);
        const y = height - pad - ((point.score || 0) / 100) * (height - pad * 2);
        return `${x},${y}`;
    });
    return `
    <div class="panel">
      <div class="panel__header"><div><p class="panel__eyebrow">TREND</p><h4>近阶段变化</h4></div></div>
      <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto">
        <polyline points="${coords.join(' ')}" fill="none" stroke="#d76848" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
      </svg>
    </div>`;
}

function renderBulletList(items, emptyText) {
    if (!items.length) {
        return `<div class="empty-state">${emptyText}</div>`;
    }
    return `<div class="stack-list">${items.map((item) => `<div class="stack-item"><div>${svgIcon('i-check')}</div><div>${escapeHtml(item)}</div></div>`).join('')}</div>`;
}

function renderAttachmentSignals(content) {
    const signals = content?.attachment_signals;
    if (!signals) {
        return '';
    }

    const buildItems = (data) => {
        if (!data) {
            return [];
        }

        const items = [];
        if (data.image) {
            items.push(`图片情绪：${data.image.mood || 'unknown'}`);
            items.push(`图片信号：${data.image.social_signal || '无'}`);
            items.push(`图片评分：${data.image.score ?? '--'}`);
        }
        if (data.voice) {
            items.push(`语音语气：${data.voice.tone || 'unknown'}`);
            items.push(`背景声音：${data.voice.background_sound || '未知'}`);
            items.push(`关系线索：${data.voice.relationship_signal || '无'}`);
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
            cards.push(`<div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">ATTACHMENT</p><h4>A 方附件线索</h4></div></div>${renderBulletList(aItems, '当前没有附件分析结果')}</div>`);
        }
        if (bItems.length) {
            cards.push(`<div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">ATTACHMENT</p><h4>B 方附件线索</h4></div></div>${renderBulletList(bItems, '当前没有附件分析结果')}</div>`);
        }
    } else {
        const items = buildItems(signals);
        if (items.length) {
            cards.push(`<div class="panel"><div class="panel__header"><div><p class="panel__eyebrow">ATTACHMENT</p><h4>附件线索</h4></div></div>${renderBulletList(items, '当前没有附件分析结果')}</div>`);
        }
    }

    if (!cards.length) {
        return '';
    }

    return `<div class="layout-grid">${cards.join('')}</div>`;
}

function formatReportType(type) {
    return { daily: '日报', weekly: '周报', monthly: '月报' }[type] || '报告';
}

async function generateReport() {
    if (!isLiveMode()) {
        showToast('演示态下不触发真实生成');
        return;
    }

    const button = $('#report-generate-btn');
    button.disabled = true;
    button.textContent = '生成中...';
    const reportType = state.selectedReportType;

    try {
        if (reportType === 'daily') {
            await api.generateDailyReport(state.currentPair.id);
        } else if (reportType === 'weekly') {
            await api.generateWeeklyReport(state.currentPair.id);
        } else {
            await api.generateMonthlyReport(state.currentPair.id);
        }

        button.textContent = '等待结果...';
        showToast('已触发报告生成，正在等待结果');

        const report = await api.waitForReport(state.currentPair.id, reportType);
        await loadReportPage();

        if (report?.status === 'completed') {
            showToast(`${formatReportType(reportType)}已生成完成`);
        } else if (report?.status === 'failed') {
            showToast(`${formatReportType(reportType)}生成失败，请稍后重试`);
        } else {
            showToast(`${formatReportType(reportType)}仍在后台生成，可稍后刷新查看`);
        }
    } catch (error) {
        showToast(error.message || '生成失败');
    } finally {
        button.disabled = false;
        button.textContent = '生成当前报告';
    }
}

async function loadProfilePage() {
    if (!api.isLoggedIn()) {
        $('#profile-summary').innerHTML = `<p class="eyebrow">PROFILE</p><h3>当前处于演示态</h3><p>登录后这里会显示你的账号、关系状态和解绑入口。</p>`;
        $('#profile-account-panel').innerHTML = '<div class="empty-state">演示态下不显示真实账户资料。</div>';
        $('#profile-pair-panel').innerHTML = '<div class="empty-state">演示态下不显示真实账户信息。</div>';
        return;
    }

    const me = state.me || await api.getMe();
    state.me = me;
    const pair = state.currentPair;
    const allPairs = state.pairs || [];
    const activePairs = allPairs.filter((item) => item.status === 'active');
    const pendingPairs = allPairs.filter((item) => item.status === 'pending');
    const unbindStatus = pair
        ? await api.getUnbindStatus(pair.id).catch(() => ({ has_request: false }))
        : { has_request: false };

    $('#profile-summary').innerHTML = `
    <p class="eyebrow">ACCOUNT</p>
    <h3>${escapeHtml(me.nickname || '用户')}</h3>
        <p>${escapeHtml(me.email || '未填写邮箱')} · ${pair ? '已绑定关系' : '未绑定关系'}</p>
        ${state.profileFeedback ? `<div class="profile-banner"><strong>已同步更新</strong><div>${escapeHtml(state.profileFeedback)}</div></div>` : ''}
        <div class="metric-strip">
            <article class="mini-stat"><span>活跃关系</span><strong>${activePairs.length}</strong></article>
            <article class="mini-stat"><span>待加入关系</span><strong>${pendingPairs.length}</strong></article>
            <article class="mini-stat"><span>当前对象</span><strong>${escapeHtml(pair ? getPartnerDisplayName(pair) : '未设置')}</strong></article>
        </div>`;

    $('#profile-account-panel').innerHTML = `
        <div class="panel__header"><div><p class="panel__eyebrow">ACCOUNT DETAIL</p><h4>账户信息</h4></div></div>
        <div class="detail-list">
            <div class="detail-list__item"><span>昵称</span><strong>${escapeHtml(me.nickname || '未设置')}</strong></div>
            <div class="detail-list__item"><span>邮箱</span><strong>${escapeHtml(me.email || '未绑定')}</strong></div>
            <div class="detail-list__item"><span>手机号</span><strong>${escapeHtml(maskPhone(me.phone))}</strong></div>
            <div class="detail-list__item"><span>登录渠道</span><strong>${escapeHtml(getAccountChannels(me))}</strong></div>
            <div class="detail-list__item"><span>账户创建时间</span><strong>${escapeHtml(formatDateOnly(me.created_at))}</strong></div>
            <div class="detail-list__item"><span>账户 ID</span><strong>${escapeHtml(String(me.id).slice(0, 8).toUpperCase())}</strong></div>
        </div>`;

    $('#profile-pair-panel').innerHTML = pair
        ? `<div class="panel__header"><div><p class="panel__eyebrow">RELATION</p><h4>当前关系</h4></div></div>
                 <p class="panel-inline-hint">直接点击下面的条目即可处理备注或解绑，不再需要额外找按钮。</p>
             <div class="metric-strip">
                 <article class="mini-stat"><span>关系类型</span><strong>${escapeHtml(TYPE_LABELS[pair.type] || pair.type)}</strong></article>
                 <article class="mini-stat"><span>当前状态</span><strong>${pair.status === 'active' ? '已激活' : '等待加入'}</strong></article>
                 <article class="mini-stat"><span>邀请码</span><strong>${escapeHtml(pair.invite_code || '无')}</strong></article>
             </div>
                 <div class="stack-item stack-item--static"><div>${svgIcon('i-link')}</div><div class="stack-item__content"><strong>${escapeHtml(getPartnerDisplayName(pair))}</strong><div class="stack-item__meta">创建于 ${escapeHtml(formatDateOnly(pair.created_at))} · ${pair.status === 'active' ? '你们已经在共享关系数据' : '对方加入后会开始共享数据'}</div></div></div>
                 <button class="stack-item stack-item--action" type="button" onclick="openPartnerNicknameEditor()" aria-label="编辑对方备注">
                     <div>${svgIcon('i-edit')}</div>
                     <div class="stack-item__content"><strong>对方备注</strong><div class="stack-item__meta">${escapeHtml(pair.custom_partner_nickname || '尚未设置，当前默认显示系统昵称')}</div></div>
                     <div class="stack-item__aside"><span class="stack-item__hint">点击修改</span>${svgIcon('i-arrow-right', 'icon-sm')}</div>
                 </button>
                 <button class="stack-item stack-item--action" type="button" onclick="openUnbindPanel()" aria-label="管理解绑状态">
                     <div>${svgIcon('i-refresh')}</div>
                     <div class="stack-item__content"><strong>解绑状态</strong><div class="stack-item__meta">${unbindStatus.has_request ? (unbindStatus.requested_by_me ? `你已发起解绑，剩余 ${unbindStatus.days_remaining} 天。` : '对方已发起解绑，等待你确认。') : '当前没有进行中的解绑申请。'}</div></div>
                     <div class="stack-item__aside"><span class="stack-item__hint">点击处理</span>${svgIcon('i-arrow-right', 'icon-sm')}</div>
                 </button>`
        : '<div class="empty-state">当前没有激活关系。</div>';
}

async function openUnbindPanel() {
    if (!isLiveMode()) {
        showToast('演示态下不可操作解绑');
        return;
    }
    try {
        const status = await api.getUnbindStatus(state.currentPair.id);
        const html = status.has_request
            ? `<h3>解绑状态</h3><p>${status.requested_by_me ? `你已发起解绑，剩余 ${status.days_remaining} 天。` : '对方已经发起解绑，你可以确认解除。'}</p>
         <div class="hero-actions">
           ${status.requested_by_me && status.days_remaining > 0 ? `<button class="button button--ghost" type="button" onclick="cancelUnbind()">撤回</button>` : ''}
           <button class="button button--danger" type="button" onclick="confirmUnbind()">确认解绑</button>
         </div>`
            : `<h3>发起解绑</h3><p>解绑后将无法继续共享打卡和报告。</p><div class="hero-actions"><button class="button button--danger" type="button" onclick="requestUnbind()">发起解绑</button></div>`;
        openModal(html);
    } catch (error) {
        showToast(error.message || '读取解绑状态失败');
    }
}

function openPartnerNicknameEditor() {
    if (!isLiveMode()) {
        showToast('演示态下不可修改备注');
        return;
    }

    const pair = state.currentPair;
    if (!pair) {
        showToast('当前没有可编辑的关系');
        return;
    }

    openModal(`
      <h3>编辑对方备注</h3>
      <p class="muted-copy">备注名会优先显示在首页、配对列表和个人中心，方便你在多段关系之间切换。</p>
      <label class="field">
        <span>备注名</span>
        <input id="partner-nickname-input" class="input" type="text" maxlength="24" placeholder="例如：宝宝 / 搭子 / 育儿搭档" value="${escapeHtml(pair.custom_partner_nickname || '')}">
      </label>
      <div class="hero-actions">
        <button class="button button--ghost" type="button" onclick="closeModal()">取消</button>
        <button class="button button--primary" type="button" onclick="savePartnerNickname()">保存备注</button>
      </div>
    `);
}

async function savePartnerNickname() {
    if (!isLiveMode() || !state.currentPair) {
        showToast('当前不可修改备注');
        return;
    }

    const input = $('#partner-nickname-input');
    const customNickname = input?.value.trim() || '';

    try {
        const updatedPair = await api.updatePartnerNickname(state.currentPair.id, customNickname);
        upsertPair(updatedPair);
        state.profileFeedback = customNickname
            ? `“${customNickname}” 已同步到首页、当前关系列表和个人中心。`
            : '备注名已清空，页面已恢复显示默认对象名称。';
        closeModal();
        showToast(customNickname ? '备注已更新' : '备注已清空');

        if (state.currentPage === 'profile') {
            await loadProfilePage();
        }

        if (state.currentPage === 'home') {
            renderPairSelect();
            await loadHomePage();
        } else {
            renderPairPage();
        }
    } catch (error) {
        showToast(error.message || '保存失败');
    }
}

async function requestUnbind() {
    try {
        await api.requestUnbind(state.currentPair.id);
        closeModal();
        showToast('解绑请求已发起');
    } catch (error) {
        showToast(error.message || '操作失败');
    }
}

async function confirmUnbind() {
    try {
        await api.confirmUnbind(state.currentPair.id);
        closeModal();
        showToast('配对已解除');
        await bootstrapSession();
    } catch (error) {
        showToast(error.message || '操作失败');
    }
}

async function cancelUnbind() {
    try {
        await api.cancelUnbind(state.currentPair.id);
        closeModal();
        showToast('解绑请求已撤回');
    } catch (error) {
        showToast(error.message || '操作失败');
    }
}

async function loadMilestonesPage() {
    if (!isLiveMode()) {
        renderMilestones(DEMO.milestones, true);
        return;
    }

    try {
        const milestones = await api.getMilestones(state.currentPair.id);
        renderMilestones(milestones, false);
    } catch (error) {
        $('#milestone-summary').innerHTML = `
        <p class="eyebrow">LIVE DATA</p>
        <h3>里程碑暂时不可用</h3>
        <p>${escapeHtml(error.message || '读取失败，请稍后重试。')}</p>`;
        $('#milestone-list').innerHTML = '<div class="timeline-empty">当前无法读取里程碑，请稍后刷新。</div>';
    }
}

function renderMilestones(milestones, isDemo) {
    const list = Array.isArray(milestones) ? milestones : [];
    const upcoming = list.filter((item) => typeof item.days_until === 'number' && item.days_until >= 0);
    const past = list.filter((item) => typeof item.days_since === 'number' && item.days_since > 0);
    const nextMilestone = upcoming[0] || list[0] || null;

    $('#milestone-summary').innerHTML = `
    <p class="eyebrow">${isDemo ? 'DEMO TIMELINE' : 'PAIR TIMELINE'}</p>
    <h3>${nextMilestone ? escapeHtml(nextMilestone.title) : '还没有记录关键节点'}</h3>
    <p>${nextMilestone ? `${escapeHtml(milestoneTypeLabel(nextMilestone.type))} · ${escapeHtml(milestoneTimeText(nextMilestone))}` : '从纪念日、重要承诺或育儿关键事件开始，让系统记住你们的重要时刻。'}</p>
    <div class="metric-strip">
      <article class="mini-stat"><span>总节点数</span><strong>${list.length}</strong></article>
      <article class="mini-stat"><span>待到来</span><strong>${upcoming.length}</strong></article>
      <article class="mini-stat"><span>已纪念</span><strong>${past.length}</strong></article>
    </div>`;

    $('#milestone-list').innerHTML = list.length
        ? list.map((item) => renderMilestoneItem(item, { isDemo })).join('')
        : '<div class="timeline-empty">还没有里程碑，先补一个对你们最重要的时间点。</div>';
}

async function handleMilestoneSubmit(event) {
    event.preventDefault();
    if (!isLiveMode()) {
        showToast('演示态下不写入里程碑');
        return;
    }

    const type = $('#milestone-type-input').value;
    const title = $('#milestone-title-input').value.trim();
    const milestoneDate = $('#milestone-date-input').value;
    if (!title || !milestoneDate) {
        showToast('请填写标题和日期');
        return;
    }

    const button = $('#milestone-submit-btn');
    button.disabled = true;
    button.textContent = '保存中...';

    try {
        await api.createMilestone(state.currentPair.id, type, title, milestoneDate);
        $('#milestone-form').reset();
        showToast('里程碑已保存');
        await Promise.all([loadMilestonesPage(), loadHomePage()]);
    } catch (error) {
        showToast(error.message || '保存失败');
    } finally {
        button.disabled = false;
        button.textContent = '保存里程碑';
    }
}

async function openMilestoneReview(milestoneId) {
    if (!isLiveMode()) {
        showToast('演示态下不生成真实回顾');
        return;
    }

    openModal('<h3>生成中</h3><p class="muted-copy">正在汇总历史报告并生成这个节点的成长回顾，请稍候。</p>');
    try {
        const payload = await api.generateMilestoneReview(milestoneId);
        const review = payload.review || {};
        openModal(`
        <h3>关系成长回顾</h3>
        <p class="muted-copy">${escapeHtml(review.growth_story || review.summary || review.executive_summary || '系统已生成该里程碑对应的关系回顾。')}</p>
        ${review.highlights?.length ? `<div class="stack-list">${review.highlights.map((item) => `<div class="stack-item"><div>${svgIcon('i-check')}</div><div>${escapeHtml(item)}</div></div>`).join('')}</div>` : ''}
        ${review.blessing ? `<div class="hero-card hero-card--accent"><strong>祝福语</strong><p>${escapeHtml(review.blessing)}</p></div>` : ''}
        ${(review.suggestions || review.action_plan || []).length ? `<div class="hero-card hero-card--accent"><strong>下一步建议</strong><p>${escapeHtml((review.suggestions || review.action_plan).join('；'))}</p></div>` : ''}
        <div class="hero-actions"><button class="button button--ghost" type="button" onclick="closeModal()">关闭</button></div>`);
    } catch (error) {
        openModal(`
        <h3>生成失败</h3>
        <p class="muted-copy">${escapeHtml(error.message || '暂时无法生成回顾，请稍后重试。')}</p>
        <div class="hero-actions"><button class="button button--ghost" type="button" onclick="closeModal()">关闭</button></div>`);
    }
}

async function loadLongDistancePage() {
    if (!isLiveMode()) {
        renderLongDistance(DEMO.longdistance, true);
        return;
    }

    const [health, activities] = await Promise.allSettled([
        api.getLongDistanceHealth(state.currentPair.id),
        api.getLongDistanceActivities(state.currentPair.id),
    ]);
    renderLongDistance({
        ...unwrapResult(health, DEMO.longdistance),
        activities: unwrapResult(activities, DEMO.longdistance.activities),
    }, false);
}

function renderLongDistance(data, isDemo) {
    $('#longdistance-health').innerHTML = `
    <p class="eyebrow">${isDemo ? 'DEMO' : 'LIVE'} HEALTH</p>
    <h3>异地关系健康指数 ${data.health_index ?? '--'}</h3>
    <p>沟通及时性 ${data.communication_timeliness ?? '--'} · 表达频率 ${data.expression_frequency ?? '--'} · 深聊率 ${data.deep_conversation_rate ?? '--'}</p>`;

    const list = $('#longdistance-activities');
    const activities = data.activities || [];
    if (!activities.length) {
        list.innerHTML = '<div class="empty-state">还没有创建异地互动活动。</div>';
        return;
    }

    list.innerHTML = activities.map((item) => `
    <article class="stack-item">
      <div>${svgIcon(item.status === 'completed' ? 'i-check' : 'i-spark')}</div>
      <div>
        <strong>${escapeHtml(item.title || ACTIVITY_LABELS[item.type] || '活动')}</strong>
        <div class="stack-item__meta">${item.status === 'completed' ? '已完成' : '待完成'} · ${formatDate(item.created_at)}</div>
      </div>
      ${item.status === 'completed' || isDemo ? '' : `<button class="text-button" type="button" onclick="completeLongDistanceActivity('${item.id}')">完成</button>`}
    </article>`).join('');
}

async function createLongDistanceActivity(type) {
    if (!isLiveMode()) {
        showToast('演示态下不写入活动');
        return;
    }
    try {
        await api.createLongDistanceActivity(state.currentPair.id, type, ACTIVITY_LABELS[type]);
        showToast('活动已创建');
        await loadLongDistancePage();
    } catch (error) {
        showToast(error.message || '创建失败');
    }
}

async function completeLongDistanceActivity(activityId) {
    try {
        await api.completeLongDistanceActivity(activityId);
        showToast('活动已标记完成');
        await loadLongDistancePage();
    } catch (error) {
        showToast(error.message || '操作失败');
    }
}

async function loadAttachmentPage() {
    if (!isLiveMode()) {
        renderAttachment(DEMO.attachment, true);
        return;
    }

    try {
        const data = await api.getAttachmentAnalysis(state.currentPair.id);
        renderAttachment(data, false);
    } catch (error) {
        renderAttachment({ attachment_a: { type: 'unknown', label: '未分析' }, attachment_b: { type: 'unknown', label: '未分析' }, analyzed_at: null }, false);
    }
}

function renderAttachment(data, isDemo) {
    $('#attachment-summary').innerHTML = `
    <p class="eyebrow">${isDemo ? 'DEMO' : 'PAIR DATA'}</p>
    <h3>依恋风格不是标签，而是理解互动方式的入口</h3>
    <p>${data.analyzed_at ? `上次分析时间：${escapeHtml(data.analyzed_at)}` : '当前还没有完成真实分析，可以直接点击按钮触发。'}</p>`;

    $('#attachment-result').innerHTML = [
        renderAttachmentCard('A 方', data.attachment_a),
        renderAttachmentCard('B 方', data.attachment_b),
    ].join('');
}

function renderAttachmentCard(title, entry = {}) {
    const label = entry.label || ATTACHMENT_LABELS[entry.type] || '未分析';
    return `
    <article class="compare-card">
      <h5>${title}</h5>
      <div class="pill">${escapeHtml(label)}</div>
      <p class="muted-copy">${attachmentDescription(entry.type)}</p>
    </article>`;
}

function attachmentDescription(type) {
    return {
        secure: '倾向稳定回应和明确表达，是关系中的安全锚点。',
        anxious: '更需要确定性和及时反馈，容易放大回应延迟。',
        avoidant: '更重视独立空间，面对压力时可能选择后撤。',
        fearful: '既渴望亲近也担心受伤，需要更细腻的安全感建设。',
    }[type] || '当前还没有足够数据形成稳定画像。';
}

async function runAttachmentAnalysis() {
    if (!isLiveMode()) {
        showToast('演示态下不触发真实分析');
        return;
    }
    const button = $('#attachment-run-btn');
    button.disabled = true;
    button.textContent = '分析中...';
    try {
        await api.triggerAttachmentAnalysis(state.currentPair.id);
        showToast('依恋分析已触发');
        await loadAttachmentPage();
    } catch (error) {
        showToast(error.message || '分析失败');
    } finally {
        button.disabled = false;
        button.textContent = '开始分析';
    }
}

function initHealthTest() {
    healthTestState = { current: 0, answers: [] };
    $('#ht-result').classList.add('hidden');
    $('#ht-question-area').classList.remove('hidden');
    renderHealthQuestion();
}

function renderHealthQuestion() {
    const item = HEALTH_TEST_QUESTIONS[healthTestState.current];
    $('#ht-question-num').textContent = `问题 ${healthTestState.current + 1}/${HEALTH_TEST_QUESTIONS.length}`;
    $('#ht-progress-text').textContent = `${healthTestState.current}/${HEALTH_TEST_QUESTIONS.length}`;
    $('#ht-progress-bar').style.width = `${(healthTestState.current / HEALTH_TEST_QUESTIONS.length) * 100}%`;
    $('#ht-question-text').textContent = item.q;
    $('#ht-options').innerHTML = item.options.map((option, index) => `<button type="button" onclick="answerHealthQuestion(${index})">${escapeHtml(option)}</button>`).join('');
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
    $('#ht-question-area').classList.add('hidden');
    $('#ht-result').classList.remove('hidden');
    $('#ht-progress-bar').style.width = '100%';
    $('#ht-progress-text').textContent = `${HEALTH_TEST_QUESTIONS.length}/${HEALTH_TEST_QUESTIONS.length}`;
    const total = Math.round(healthTestState.answers.reduce((sum, item) => sum + item.score, 0) / healthTestState.answers.length);
    $('#ht-gauge').style.setProperty('--score', total);
    $('#ht-score').textContent = total;

    const level = total >= 80 ? ['关系非常健康', '你们已经具备很好的互动基础，重点是保持稳定节奏。']
        : total >= 60 ? ['关系总体不错', '主要提升空间在表达细节和修复速度。']
            : total >= 40 ? ['关系需要关注', '建议你们把“说清楚需求”和“及时回应”作为短期目标。']
                : ['关系需要干预', '当前已经出现较多低分维度，建议尽快建立支持性对话机制。'];

    $('#ht-level').textContent = level[0];
    $('#ht-desc').textContent = level[1];
    $('#ht-dimensions').innerHTML = healthTestState.answers.map((entry) => `
    <article class="stack-item">
      <div>${svgIcon('i-chart')}</div>
      <div>
        <strong>${escapeHtml(entry.dim)}</strong>
        <div class="stack-item__meta">评分 ${entry.score}</div>
      </div>
    </article>`).join('');

    const weakPoints = healthTestState.answers.filter((entry) => entry.score < 50);
    $('#ht-suggestion-list').innerHTML = weakPoints.length
        ? weakPoints.map((entry) => `<div class="stack-item"><div>${svgIcon('i-spark')}</div><div><strong>${escapeHtml(entry.dim)}</strong><div class="stack-item__meta">建议围绕这个维度安排一次具体对话和一个行动。</div></div></div>`).join('')
        : '<div class="empty-state">当前各维度没有明显短板，可以继续保持记录与复盘。</div>';
}

function resetHealthTest() {
    initHealthTest();
}

async function loadCommunityPage() {
    if (!isLiveMode()) {
        renderCommunity(DEMO.tips, DEMO.notifications, true);
        return;
    }

    const [tips, notifications] = await Promise.allSettled([
        api.getCommunityTips(state.currentPair.type),
        api.getNotifications(),
    ]);
    renderCommunity(unwrapResult(tips, DEMO.tips), unwrapResult(notifications, DEMO.notifications), false);
}

function renderCommunity(tipsPayload, notificationsPayload, isDemo) {
    const tips = tipsPayload.tips || tipsPayload || [];
    const notifications = Array.isArray(notificationsPayload) ? notificationsPayload : notificationsPayload || [];
    $('#community-highlight').innerHTML = `
    <p class="eyebrow">${isDemo ? 'DEMO' : 'LIVE CONTENT'}</p>
    <h3>${escapeHtml(tips[0]?.title || '社群技巧')}</h3>
    <p>${escapeHtml(tips[0]?.content || '这里会显示关系经营建议与运营型内容。')}</p>`;
    $('#community-tips-list').innerHTML = tips.length
        ? tips.map((tip) => `<article class="stack-item"><div>${svgIcon('i-star')}</div><div><strong>${escapeHtml(tip.title || '建议')}</strong><div class="stack-item__meta">${escapeHtml(tip.content || '')}</div></div></article>`).join('')
        : '<div class="empty-state">暂无技巧内容。</div>';
    $('#community-notification-list').innerHTML = notifications.length
        ? notifications.map((item) => `<article class="stack-item"><div>${svgIcon('i-bell')}</div><div><strong>${escapeHtml(item.content)}</strong><div class="stack-item__meta">${formatDate(item.created_at)}</div></div></article>`).join('')
        : '<div class="empty-state">暂无通知内容。</div>';
}

async function generateCommunityTip() {
    if (!isLiveMode()) {
        showToast('演示态下不生成真实建议');
        return;
    }
    try {
        await api.generateTip(state.currentPair.type);
        showToast('已生成一条新建议');
        await loadCommunityPage();
    } catch (error) {
        showToast(error.message || '生成失败');
    }
}

async function loadChallengesPage() {
    if (!isLiveMode()) {
        renderChallenges(DEMO.tasks, DEMO.streak, true);
        return;
    }

    const [tasks, streak] = await Promise.allSettled([
        api.getDailyTasks(state.currentPair.id),
        api.getCheckinStreak(state.currentPair.id),
    ]);
    renderChallenges(unwrapResult(tasks, DEMO.tasks), unwrapResult(streak, DEMO.streak), false);
}

function renderChallenges(tasksPayload, streakPayload, isDemo) {
    const tasks = tasksPayload.tasks || [];
    const completed = tasks.filter((item) => item.status === 'completed').length;
    const percent = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;
    $('#challenge-overview').innerHTML = `
    <p class="eyebrow">${isDemo ? 'DEMO' : 'LIVE TASKS'}</p>
    <h3>今日完成率 ${percent}%</h3>
    <p>连续打卡 ${streakPayload.streak || 0} 天 · 今日已完成 ${completed}/${tasks.length} 项任务。</p>
    <div class="progress-track"><span class="progress-track__fill" style="width:${percent}%"></span></div>`;
    $('#challenge-task-list').innerHTML = tasks.length
        ? tasks.map((task) => renderTaskItem(task)).join('')
        : '<div class="empty-state">当前还没有挑战任务。</div>';
}

async function completeTask(taskId) {
    if (!isLiveMode()) {
        showToast('演示态下不写入任务状态');
        return;
    }
    try {
        await api.completeTask(taskId);
        showToast('任务已完成');
        if (state.currentPage === 'home') {
            await loadHomePage();
        } else {
            await loadChallengesPage();
        }
    } catch (error) {
        showToast(error.message || '操作失败');
    }
}

async function handleWaterTree() {
    if (!isLiveMode()) {
        showToast('演示态下不写入成长值');
        return;
    }
    try {
        await api.waterTree(state.currentPair.id);
        showToast('关系树已浇水');
        await loadHomePage();
    } catch (error) {
        showToast(error.message || '操作失败');
    }
}

function openCrisisDetail() {
    const current = state.homeSnapshot?.crisis || DEMO.crisis;
    const intervention = current.intervention || {};
    openModal(`
    <h3>${crisisLabel(current.crisis_level || 'none')}</h3>
    <p>${escapeHtml(intervention.title || intervention.description || '当前没有额外说明。')}</p>
    ${(intervention.action_items || []).length ? `<div class="stack-list">${intervention.action_items.map((item) => `<div class="stack-item"><div>${svgIcon('i-check')}</div><div>${escapeHtml(item)}</div></div>`).join('')}</div>` : ''}
    <div class="hero-actions">
      <button class="button button--secondary" type="button" onclick="openCrisisResources()">查看专业资源</button>
      <button class="button button--ghost" type="button" onclick="closeModal()">关闭</button>
    </div>`);
}

async function openCrisisResources() {
    const resources = isLiveMode()
        ? await api.getCrisisResources().catch(() => ({ hotlines: [], tips: [] }))
        : { hotlines: [{ name: '全国心理援助热线', number: '400-161-9995', hours: '24 小时' }], tips: ['先把沟通目标收窄到“让彼此听懂”，而不是立刻解决所有问题。'] };
    openModal(`
    <h3>专业帮助资源</h3>
    <div class="stack-list">
      ${(resources.hotlines || []).map((item) => `<div class="stack-item"><div>${svgIcon('i-phone')}</div><div><strong>${escapeHtml(item.name)}</strong><div class="stack-item__meta">${escapeHtml(item.number)} · ${escapeHtml(item.hours || '')}</div></div></div>`).join('')}
      ${(resources.tips || []).map((item) => `<div class="stack-item"><div>${svgIcon('i-spark')}</div><div>${escapeHtml(item)}</div></div>`).join('')}
    </div>
    <div class="hero-actions"><button class="button button--ghost" type="button" onclick="closeModal()">关闭</button></div>`);
}

function handleSwitchPair(pairId) {
    setCurrentPair(pairId);
    bootstrapSession();
}

function handleLogout() {
    api.clearToken();
    localStorage.removeItem('qj_current_pair');
    state.me = null;
    state.pairs = [];
    state.currentPair = null;
    state.profileFeedback = null;
    syncTabBar();
    showToast('已退出登录');
    showPage('auth');
}

function bindOptionEvents() {
    document.addEventListener('click', (event) => {
        const moodButton = event.target.closest('[data-mood]');
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

        const optionButton = event.target.closest('[data-option-name]');
        if (optionButton) {
            const { optionName, optionValue } = optionButton.dataset;
            $$(`[data-option-name="${optionName}"]`).forEach((button) => {
                button.classList.remove('select-card--active');
                delete button.dataset.selectedName;
                delete button.dataset.selectedValue;
            });
            optionButton.classList.add('select-card--active');
            optionButton.dataset.selectedName = optionName;
            optionButton.dataset.selectedValue = optionValue;
            return;
        }

        const pairTypeButton = event.target.closest('[data-pair-type]');
        if (pairTypeButton) {
            state.selectedPairType = pairTypeButton.dataset.pairType;
            $$('[data-pair-type]').forEach((button) => button.classList.remove('select-card--active'));
            pairTypeButton.classList.add('select-card--active');
            return;
        }

        const reportButton = event.target.closest('[data-report-type]');
        if (reportButton) {
            state.selectedReportType = reportButton.dataset.reportType;
            $$('[data-report-type]').forEach((button) => button.classList.remove('segmented__item--active'));
            reportButton.classList.add('segmented__item--active');
            loadReportPage();
            return;
        }

        const jumpButton = event.target.closest('[data-jump-page]');
        if (jumpButton) {
            showPage(jumpButton.dataset.jumpPage);
            return;
        }

        const reviewButton = event.target.closest('[data-milestone-review]');
        if (reviewButton) {
            openMilestoneReview(reviewButton.dataset.milestoneReview);
            return;
        }

        const activityButton = event.target.closest('[data-ld-type]');
        if (activityButton) {
            createLongDistanceActivity(activityButton.dataset.ldType);
            return;
        }
    });
}

function bindStaticEvents() {
    $('#auth-mode-login').addEventListener('click', () => switchAuthMode('login'));
    $('#auth-mode-register').addEventListener('click', () => switchAuthMode('register'));
    $('#auth-method-email').addEventListener('click', () => switchAuthMethod('email'));
    $('#auth-method-phone').addEventListener('click', () => switchAuthMethod('phone'));
    $('#auth-send-code').addEventListener('click', handleSendPhoneCode);
    $('#auth-form').addEventListener('submit', handleAuthSubmit);
    $('#pair-create-btn').addEventListener('click', handleCreatePair);
    $('#pair-join-btn').addEventListener('click', handleJoinPair);
    $('#waiting-copy-btn').addEventListener('click', async () => {
        const code = $('#waiting-invite-code').textContent;
        try {
            await navigator.clipboard.writeText(code);
            showToast('邀请码已复制');
        } catch (error) {
            showToast('复制失败，请手动复制');
        }
    });
    $('#waiting-refresh-btn').addEventListener('click', refreshPairStatus);
    $('#home-pair-select').addEventListener('change', (event) => {
        setCurrentPair(event.target.value);
        loadHomePage();
    });
    $('#checkin-form').addEventListener('submit', handleCheckinSubmit);
    $('#image-upload-trigger').addEventListener('click', () => $('#image-upload-input').click());
    $('#voice-upload-trigger').addEventListener('click', () => $('#voice-upload-input').click());
    $('#image-upload-input').addEventListener('change', (event) => {
        const file = event.target.files?.[0];
        if (file) handleUpload('image', file);
    });
    $('#voice-upload-input').addEventListener('change', (event) => {
        const file = event.target.files?.[0];
        if (file) handleUpload('voice', file);
    });
    $('#report-generate-btn').addEventListener('click', generateReport);
    $('#logout-btn').addEventListener('click', handleLogout);
    $('#milestone-form').addEventListener('submit', handleMilestoneSubmit);
    $('#attachment-run-btn').addEventListener('click', runAttachmentAnalysis);
    $('#community-refresh-btn').addEventListener('click', loadCommunityPage);
    $('#community-generate-btn').addEventListener('click', generateCommunityTip);
    $('#notification-toggle').addEventListener('click', () => $('#notification-drawer').classList.toggle('hidden'));
    $('#notification-read-all').addEventListener('click', async () => {
        if (!isLiveMode()) {
            showToast('演示态下不写入通知状态');
            return;
        }
        await api.markNotificationsRead();
        showToast('通知已全部标记为已读');
        await loadHomePage();
    });
    $('#modal-overlay').addEventListener('click', (event) => {
        if (event.target.id === 'modal-overlay') closeModal();
    });
    $('#modal-close').addEventListener('click', closeModal);
    $('#longdistance-refresh').addEventListener('click', loadLongDistancePage);

    $$('.tab-item').forEach((button) => {
        button.addEventListener('click', () => showPage(button.dataset.page));
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
    window.handleWaterTree = handleWaterTree;
    window.openCrisisDetail = openCrisisDetail;
    window.openCrisisResources = openCrisisResources;
    window.requestUnbind = requestUnbind;
    window.confirmUnbind = confirmUnbind;
    window.cancelUnbind = cancelUnbind;
    window.openMilestoneReview = openMilestoneReview;
    window.completeLongDistanceActivity = completeLongDistanceActivity;
}

document.addEventListener('DOMContentLoaded', async () => {
    switchAuthMode('login');
    switchAuthMethod('email');
    updateSendCodeButton();
    bindOptionEvents();
    bindStaticEvents();
    exposeGlobals();
    renderCheckinPage();
    syncTopbar();
    syncNotifications();
    await bootstrapSession();
    if (!api.isLoggedIn()) {
        await showPage('auth');
    }
});
