function handmadeLedger(items = []) {
    if (!items.length) return '<div class="section-empty">这里还没有可展示的内容。</div>';
    return `<div class="ledger-strip">${items.map((item) => `
        <article class="ledger-item">
            <span class="ledger-item__label">${escapeHtml(item.label || '')}</span>
            <strong class="ledger-item__value">${escapeHtml(item.value || '')}</strong>
            ${item.meta ? `<p class="ledger-item__meta">${escapeHtml(item.meta)}</p>` : ''}
        </article>
    `).join('')}</div>`;
}

function handmadeRows(rows = [], emptyText = '这里还没有内容。') {
    if (!rows.length) return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
    return `<div class="editorial-rows">${rows.map((row) => `
        <article class="editorial-row">
            <span class="editorial-row__label">${escapeHtml(row.label || '')}</span>
            <div class="editorial-row__body">
                <strong class="editorial-row__value">${escapeHtml(row.value || '')}</strong>
                ${row.meta ? `<p class="editorial-row__meta">${escapeHtml(row.meta)}</p>` : ''}
            </div>
            ${row.side ? `<span class="editorial-row__side">${escapeHtml(row.side)}</span>` : ''}
        </article>
    `).join('')}</div>`;
}

function handmadeList(items = [], emptyText = '这里还没有内容。') {
    if (!items.length) return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
    return `<ul class="brief-bullets">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}

function handmadeLedgerBand(items = [], emptyText = '这里还没有可展示的内容。') {
    if (!items.length) return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
    return `
        <section class="home-ledger-ribbon">
            ${items.map((item) => `
                <article class="home-ledger-ribbon__item">
                    <span class="home-ledger-ribbon__label">${escapeHtml(item.label || '')}</span>
                    <div class="home-ledger-ribbon__body">
                        <strong class="home-ledger-ribbon__value">${escapeHtml(item.value || '')}</strong>
                        ${item.meta ? `<p class="home-ledger-ribbon__meta">${escapeHtml(item.meta)}</p>` : ''}
                    </div>
                </article>
            `).join('')}
        </section>
    `;
}

function handmadeSignalRun(items = [], emptyText = '这里还没有可展示的内容。') {
    if (!items.length) return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
    return `
        <section class="home-signal-run">
            ${items.map((item, index) => `
                <article class="home-signal-run__item">
                    <span class="home-signal-run__index">${String(index + 1).padStart(2, '0')}</span>
                    <div class="home-signal-run__body">
                        <p class="home-signal-run__label">${escapeHtml(item.label || '')}</p>
                        <strong class="home-signal-run__value">${escapeHtml(item.value || '')}</strong>
                        ${item.meta ? `<p class="home-signal-run__meta">${escapeHtml(item.meta)}</p>` : ''}
                    </div>
                </article>
            `).join('')}
        </section>
    `;
}

function handmadeEditorialFacts(rows = [], emptyText = '这里还没有内容。') {
    if (!rows.length) return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
    return `
        <div class="home-facts">
            ${rows.map((row) => `
                <article class="home-facts__item">
                    <span class="home-facts__label">${escapeHtml(row.label || '')}</span>
                    <div class="home-facts__body">
                        <strong>${escapeHtml(row.value || '')}</strong>
                        ${row.meta ? `<p>${escapeHtml(row.meta)}</p>` : ''}
                    </div>
                    ${row.side ? `<span class="home-facts__side">${escapeHtml(row.side)}</span>` : ''}
                </article>
            `).join('')}
        </div>
    `;
}

function trimHandmadeCopy(value, max = 36, fallback = '') {
    const text = getPreferredText(value, fallback).replace(/\s+/g, ' ').trim();
    if (!text) return fallback;
    if (text.length <= max) return text;
    return `${text.slice(0, Math.max(1, max - 1)).trim()}…`;
}

function renderHomeCoverTitle(text = '') {
    const chars = Array.from(String(text || '').trim());
    if (!chars.length) return '<span>关系</span><span>总览</span>';
    if (chars.length === 1) return `<span>${escapeHtml(chars[0])}</span>`;
    const firstLen = chars.length <= 2 ? 1 : Math.ceil(chars.length / 2);
    const lines = [
        chars.slice(0, firstLen).join(''),
        chars.slice(firstLen).join(''),
    ].filter(Boolean);
    return lines.map((line) => `<span>${escapeHtml(line)}</span>`).join('');
}

function clientIntentLabel(intent) {
    return {
        daily: '日常',
        emergency: '急救',
        crisis: '高风险',
        reflection: '复盘',
    }[intent] || '日常';
}

function handmadeCoverVisual({ score = '--' } = {}) {
    return `
        <div class="home-cover__visual-frame" aria-hidden="true">
            <svg class="home-cover__visual" viewBox="0 0 420 320" role="presentation">
                <defs>
                    <linearGradient id="home-paper-bg" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stop-color="#fff8f2"></stop>
                        <stop offset="100%" stop-color="#f2e7dc"></stop>
                    </linearGradient>
                    <linearGradient id="home-paper-a" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stop-color="#f8d9c8"></stop>
                        <stop offset="100%" stop-color="#efc2a7"></stop>
                    </linearGradient>
                    <linearGradient id="home-paper-b" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stop-color="#d9e9df"></stop>
                        <stop offset="100%" stop-color="#bfd7c8"></stop>
                    </linearGradient>
                    <radialGradient id="home-paper-glow" cx="50%" cy="40%" r="56%">
                        <stop offset="0%" stop-color="rgba(255,255,255,0.92)"></stop>
                        <stop offset="100%" stop-color="rgba(255,244,236,0)"></stop>
                    </radialGradient>
                </defs>
                <rect x="14" y="14" width="392" height="292" rx="36" fill="url(#home-paper-bg)" stroke="rgba(160,120,98,0.16)"></rect>
                <circle cx="300" cy="96" r="92" fill="url(#home-paper-glow)"></circle>
                <path d="M40 244C92 184 154 154 212 154C270 154 332 184 380 244" stroke="#d99f84" stroke-width="8" stroke-linecap="round"></path>
                <rect x="76" y="104" width="118" height="132" rx="28" transform="rotate(-8 76 104)" fill="url(#home-paper-a)" opacity="0.92"></rect>
                <rect x="218" y="84" width="126" height="144" rx="30" transform="rotate(8 218 84)" fill="url(#home-paper-b)" opacity="0.9"></rect>
                <rect x="140" y="64" width="132" height="160" rx="32" fill="#fffaf6" stroke="rgba(160,120,98,0.12)"></rect>
                <circle cx="206" cy="144" r="34" fill="#fff2ea" stroke="rgba(214,133,98,0.26)"></circle>
                <path d="M208 126v36" stroke="#c37252" stroke-width="3.5" stroke-linecap="round"></path>
                <path d="M190 144h36" stroke="#c37252" stroke-width="3.5" stroke-linecap="round"></path>
                <circle cx="206" cy="236" r="18" fill="#fffaf6" stroke="rgba(160,120,98,0.12)"></circle>
                <path d="M196 236h20" stroke="#8aa997" stroke-width="3.5" stroke-linecap="round"></path>
            </svg>
            <div class="home-cover__visual-stamp">
                <img src="assets/brand-logo.jpg" alt="">
                <span>亲健</span>
            </div>
            <div class="home-cover__visual-score">
                <span>本期简报</span>
                <strong>${escapeHtml(String(score))}</strong>
            </div>
        </div>
    `;
}

function handmadeCompactClientGlance() {
    const precheck = state?.lastClientPrecheck;
    const prefs = typeof currentProductPrefs === 'function'
        ? currentProductPrefs()
        : { privacyMode: 'cloud', aiAssistEnabled: true };
    const summary = precheck
        ? trimHandmadeCopy(typeof buildClientGuidance === 'function' ? buildClientGuidance(precheck) : '', 34, '本地预检已完成。')
        : trimHandmadeCopy(state?.lastClientPrecheckGuidance || '', 34, '输入后会先做本地保护。');
    const piiItems = typeof summarizeClientPii === 'function'
        ? summarizeClientPii(precheck?.pii_summary || {})
        : [];
    const pills = [];

    pills.push(`路径 ${clientIntentLabel(precheck?.intent || 'daily')}`);
    pills.push(`隐私 ${prefs.privacyMode === 'local_first' ? '本地优先' : '云端保护'}`);
    if (precheck?.risk_level && precheck.risk_level !== 'none') {
        pills.push(`风险 ${precheck.risk_level}`);
    } else if (piiItems.length) {
        pills.push(`脱敏 ${trimHandmadeCopy(piiItems[0], 10)}`);
    } else if (Number(state?.localDraftCount || 0) > 0) {
        pills.push(`草稿 ${state.localDraftCount} 条`);
    }

    return `
        <section class="home-client-glance">
            <p class="home-client-glance__eyebrow">本地即时判断</p>
            <strong class="home-client-glance__title">${escapeHtml(precheck?.degraded ? '已切换云端保护' : precheck ? '先替你看一眼' : '等待输入')}</strong>
            <p class="home-client-glance__summary">${escapeHtml(summary)}</p>
            <div class="home-client-glance__pills">
                ${pills.slice(0, 3).map((item) => `<span>${escapeHtml(item)}</span>`).join('')}
            </div>
        </section>
    `;
}

function formatArchiveStatusLabel(status) {
    if (!status || status === 'completed') return '已完成';
    if (status === 'pending') return '生成中';
    if (status === 'failed') return '失败';
    return status;
}

function handmadeTrend(trendData, options = {}) {
    const isSolo = Boolean(options.solo);
    const points = trendData?.trend || [];
    if (points.length < 2) {
        return `<div class="section-empty">${isSolo ? '再多记录几次，个人趋势就会出现。' : '再多记录几次，关系趋势就会出现。'}</div>`;
    }

    const width = 320;
    const height = 110;
    const pad = 12;
    const coords = points.map((point, index) => {
        const x = pad + (index / Math.max(points.length - 1, 1)) * (width - pad * 2);
        const y = height - pad - ((point.score || 0) / 100) * (height - pad * 2);
        return { x, y };
    });
    const line = coords.map((point) => `${point.x},${point.y}`).join(' ');
    const directionLabel = {
        improving: '慢慢变好',
        stable: '整体平稳',
        declining: '需要留意',
        insufficient_data: '还在形成中',
    }[trendData?.direction] || '还在形成中';

    return `
        <div class="trend-ribbon">
            <div class="trend-ribbon__meta">
                <span>${isSolo ? '情绪走势' : '关系走势'}</span>
                <strong>${directionLabel}</strong>
            </div>
            <svg viewBox="0 0 ${width} ${height}" class="trend-ribbon__chart" aria-hidden="true">
                <defs>
                    <linearGradient id="handmade-trend-line" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stop-color="#d68463"></stop>
                        <stop offset="100%" stop-color="#5b7a6c"></stop>
                    </linearGradient>
                </defs>
                <polyline points="${line}" fill="none" stroke="url(#handmade-trend-line)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></polyline>
                ${coords.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="4.5" fill="#fff8f2" stroke="#d68463" stroke-width="2"></circle>`).join('')}
            </svg>
        </div>
    `;
}

function renderHandmadeReportHero(report, options = {}) {
    const isSolo = Boolean(options.solo);
    const reportType = options.reportType || state.selectedReportType;
    const reportLabel = formatReportType(reportType, { solo: isSolo });
    const content = report?.content || {};
    const score = Math.max(1, Math.min(100, content.health_score || content.overall_health_score || 72));
    const primaryInsight = content.insight || content.self_insight || content.executive_summary || '系统已经整理好这段时间最值得先读的一句判断。';
    const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || '';
    const encouragement = content.encouragement || content.relationship_note || '';
    const focusText = content.focus || content.current_focus || content.key_question || content.problem_statement || '先把这段关系里最容易被忽略的一件事看清楚。';
    const reportDate = formatDateOnly(report?.report_date || new Date().toISOString());
    const nextAction = suggestion || '先把最想说的一句话说清楚，再决定要不要继续展开。';
    const actionButtons = isSolo
        ? `<button class="button button--secondary" type="button" onclick="showPage('checkin')">回到今日记录</button>
           <button class="button button--ghost" type="button" onclick="showPage('timeline')">打开时间轴</button>`
        : `<button class="button button--secondary" type="button" onclick="openMessageSimulator()">聊天前预演</button>
           <button class="button button--ghost" type="button" onclick="openNarrativeAlignment()">双视角对齐</button>
           <button class="button button--ghost" type="button" onclick="showPage('timeline')">时间轴</button>`;

    return `
        <section class="report-cover">
            <div class="report-cover__score">
                <span>${score}</span>
                <small>/100</small>
            </div>
            <div class="report-cover__body">
                <div class="report-cover__topline">
                    <p class="report-cover__eyebrow">${isSolo ? '个人简报' : '关系简报'}</p>
                    <span class="report-cover__date">${escapeHtml(reportDate)}</span>
                </div>
                <h3>${escapeHtml(reportLabel)}</h3>
                <p class="report-cover__lead">${escapeHtml(primaryInsight)}</p>
                <div class="report-cover__meta">
                    <article>
                        <span>现在</span>
                        <strong>${escapeHtml(focusText)}</strong>
                    </article>
                    <article>
                        <span>下一步</span>
                        <strong>${escapeHtml(nextAction)}</strong>
                    </article>
                </div>
                ${encouragement ? `<blockquote class="report-cover__note">${escapeHtml(encouragement)}</blockquote>` : ''}
            </div>
            <div class="report-cover__actions">
                ${actionButtons}
            </div>
        </section>
    `;
}

function getPreferredText(value, fallback = '') {
    const raw = String(value ?? '').trim();
    if (!raw || /^[?？]+$/.test(raw)) return fallback;
    return raw;
}

function getPreferredUserName(user) {
    const emailPrefix = getPreferredText((user?.email || '').split('@')[0], '');
    const phoneDigits = String(user?.phone || '').replace(/\D/g, '');
    return getPreferredText(user?.nickname, '') || emailPrefix || (phoneDigits.length >= 4 ? `用户${phoneDigits.slice(-4)}` : '你');
}

function getVisibleEmailLabel(user, fallback = '未填写邮箱') {
    const raw = getPreferredText(user?.email, '');
    if (isDemoMode() && raw) return '样例邮箱已隐藏';
    return raw || fallback;
}

function setHandmadePanelVisibility(selector, visible) {
    const el = $(selector);
    if (el) el.classList.toggle('handmade-panel-hidden', !visible);
}

function handmadeRoute({ eyebrow = '今日路线', title = '', lead = '', badge = '', steps = [], note = '' } = {}) {
    return `
        <section class="route-board">
            <div class="route-board__head">
                <div>
                    <p class="editorial-section__eyebrow">${escapeHtml(eyebrow)}</p>
                    <h4 class="route-board__title">${escapeHtml(title)}</h4>
                </div>
                ${badge ? `<span class="route-board__badge">${escapeHtml(badge)}</span>` : ''}
            </div>
            ${lead ? `<p class="route-board__lead">${escapeHtml(lead)}</p>` : ''}
            <div class="route-board__steps">
                ${steps.map((step, index) => `
                    <article class="route-step route-step--${escapeHtml(step.status || 'pending')}">
                        <span class="route-step__index">${index + 1}</span>
                        <div class="route-step__body">
                            ${step.label ? `<span class="route-step__label">${escapeHtml(step.label)}</span>` : ''}
                            <strong class="route-step__title">${escapeHtml(step.title || '')}</strong>
                            ${step.meta ? `<p class="route-step__meta">${escapeHtml(step.meta)}</p>` : ''}
                        </div>
                    </article>
                `).join('')}
            </div>
            ${note ? `<div class="route-board__note">${escapeHtml(note)}</div>` : ''}
        </section>
    `;
}

function handmadeTimeline(items = [], emptyText = '这里还没有时间线内容。') {
    if (!items.length) return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
    return `<div class="timeline-river">${items.map((item) => `
        <article class="timeline-river__item">
            <span class="timeline-river__date">${escapeHtml(item.date || item.kicker || '')}</span>
            <div class="timeline-river__body">
                <strong>${escapeHtml(item.title || '')}</strong>
                ${item.meta ? `<p>${escapeHtml(item.meta)}</p>` : ''}
            </div>
        </article>
    `).join('')}</div>`;
}

function handmadeSheet(eyebrow, title, rows = []) {
    return `
        <section class="profile-sheet">
            <p class="profile-sheet__eyebrow">${escapeHtml(eyebrow)}</p>
            <h5 class="profile-sheet__title">${escapeHtml(title)}</h5>
            <div class="profile-sheet__rows">
                ${rows.map((row) => `
                    <article class="profile-sheet__row">
                        <span>${escapeHtml(row.label || '')}</span>
                        <strong>${escapeHtml(row.value || '')}</strong>
                        ${row.meta ? `<p>${escapeHtml(row.meta)}</p>` : ''}
                    </article>
                `).join('')}
            </div>
        </section>
    `;
}

function handmadeHeroPanel({ eyebrow = '', title = '', body = '', rows = [] } = {}) {
    return `
        <aside class="stage-surface__panel">
            ${eyebrow ? `<p class="stage-surface__panel-eyebrow">${escapeHtml(eyebrow)}</p>` : ''}
            ${title ? `<h4 class="stage-surface__panel-title">${escapeHtml(title)}</h4>` : ''}
            ${body ? `<p class="stage-surface__panel-body">${escapeHtml(body)}</p>` : ''}
            ${rows.length ? `<div class="stage-surface__panel-list">${rows.map((row) => `
                <article class="stage-surface__panel-item">
                    <span>${escapeHtml(row.label || '')}</span>
                    <strong>${escapeHtml(row.value || '')}</strong>
                </article>
            `).join('')}</div>` : ''}
        </aside>
    `;
}

function buildHomeTimelineItems(payload = {}) {
    const events = Array.isArray(payload.timeline?.events) ? payload.timeline.events : [];
    if (events.length) {
        return events.slice(0, 5).map((event) => ({
            date: event?.occurred_at || event?.created_at || event?.date
                ? formatDateOnly(event.occurred_at || event.created_at || event.date)
                : (event?.relative_time || '最近'),
            title: event?.title || event?.headline || event?.summary || event?.category_label || '关系事件',
            meta: event?.impact_summary || event?.next_step || event?.description || event?.tone_label || '系统会继续把这条线索沉淀进后续判断里。',
        }));
    }

    const milestones = Array.isArray(payload.milestones) ? payload.milestones : [];
    return milestones.slice(0, 4).map((item) => ({
        date: item?.date || item?.target_date ? formatDateOnly(item.date || item.target_date) : '最近',
        title: item?.title || '未命名节点',
        meta: milestoneTypeLabel(item?.type),
    }));
}

function renderNoPairHome(payload = {}) {
    const todayStatus = payload.todayStatus || {};
    const myCheckin = todayStatus.my_checkin || {};
    const latestReport = payload.latestReport || null;
    const latestContent = latestReport?.content || {};
    const reportState = getSoloReportButtonState(todayStatus, latestReport);
    const hasCheckin = Boolean(todayStatus?.my_done);
    const hasReadyReport = reportState.tone === 'ready';
    const streakDays = payload.streak?.streak || 0;
    const moodText = myCheckin.mood_score ? `${myCheckin.mood_score}/4` : '未记录';
    const interactionText = myCheckin.interaction_freq || myCheckin.interaction_freq === 0 ? `${myCheckin.interaction_freq} 次` : '未记录';
    const deepTalkText = myCheckin.deep_conversation === true ? '有' : myCheckin.deep_conversation === false ? '没有' : '未记录';
    const latestInsight = latestContent.insight || latestContent.self_insight || latestContent.encouragement || '先把今天的情绪留下一句，你就已经在认真照顾自己。';
    const latestSuggestion = latestContent.suggestion || latestContent.self_care_tip || '等你想好了，再把今天补成一句更完整的话。';
    const userName = getPreferredUserName(state.me);

    safeSetText('#home-greeting', `${userName}，今天也适合把自己照顾好`);

    safeSetHtml('#home-overview', `
        <section class="stage-surface stage-surface--solo">
            <p class="stage-surface__eyebrow">先照顾自己</p>
            <div class="stage-surface__hero-grid">
                <div class="stage-surface__hero-copy">
                    <h3 class="stage-surface__title">${hasReadyReport ? '今天已经被你整理成一份可以回看的个人简报' : hasCheckin ? '你已经开始把今天认真地记下来了' : '先照顾今天的自己，再决定什么时候进入关系空间'}</h3>
                    <p class="stage-surface__body">${hasReadyReport ? '这时候最适合读一遍自己的情绪节奏，再决定下一步要不要继续靠近别人。' : hasCheckin ? '今天的记录已经落下，接下来可以继续补充一句真心话，或者直接去读个人简报。' : '亲健不该一上来就逼你绑定。先让你有地方安放自己，再慢慢把关系接进来。'}</p>
                    <div class="inline-pills">
                        <span class="inline-pill">${hasCheckin ? '今日已记录' : '等待今日记录'}</span>
                        <span class="inline-pill">${hasReadyReport ? '个人简报已就绪' : reportState.label}</span>
                        <span class="inline-pill">${streakDays} 天连续记录</span>
                    </div>
                    <div class="stage-surface__actions">
                        <button class="button button--primary" type="button" onclick="${hasReadyReport ? "showPage('report')" : "openCheckinMode('form')"}">${hasReadyReport ? '去读个人简报' : '开始今日记录'}</button>
                        <button class="button button--ghost" type="button" onclick="${hasCheckin ? "openCheckinMode('voice')" : "showPage('pair')"}">${hasCheckin ? '继续补一句心里话' : '准备好后再绑定关系'}</button>
                    </div>
                </div>
                ${handmadeHeroPanel({
                    eyebrow: '此刻概况',
                    title: hasReadyReport ? '你今天已经有结果了' : hasCheckin ? '今天已经开始了' : '现在适合先落下第一句',
                    body: hasReadyReport ? latestInsight : latestSuggestion,
                    rows: [
                        { label: '心情', value: moodText },
                        { label: '简报', value: hasReadyReport ? '已就绪' : reportState.label },
                        { label: '节奏', value: `${streakDays} 天` },
                    ],
                })}
            </div>
        </section>
    `);

    safeSetHtml('#home-metrics', handmadeLedger([
        { label: '连续记录', value: `${streakDays} 天`, meta: '好的节奏比一时用力更重要。' },
        { label: '今日心情', value: moodText, meta: '先看见情绪，再谈解决。' },
        { label: '互动频率', value: interactionText, meta: '单人模式也能先记自己的节奏。' },
        { label: '深聊状态', value: deepTalkText, meta: '一句说清楚的话，常常比很多句表面交流更重要。' },
    ]));

    safeSetHtml('#home-status-panel', `
        <section class="editorial-section editorial-section--story">
            <div class="editorial-section__head">
                <div>
                    <p class="editorial-section__eyebrow">今日记录</p>
                    <h4 class="editorial-section__title">今天这一笔，先写给自己</h4>
                </div>
                <span class="editorial-section__badge">${hasCheckin ? '已开始' : '待开始'}</span>
            </div>
            ${handmadeRows([
                { label: '心情', value: moodText, meta: '你可以先承认今天是什么感觉。' },
                { label: '互动', value: interactionText, meta: '就算还没绑定，也能先记录自己的关系感。' },
                { label: '深聊', value: deepTalkText, meta: '这会影响之后简报对“靠近感”的判断。' },
            ], '你还没有留下今天的内容。')}
            <div class="home-journal">${escapeHtml(myCheckin.content || '今天还没有写下来的那句话，可以从“其实我现在最需要的是...”开始。')}</div>
            <div class="stage-surface__actions">
                <button class="button button--primary" type="button" onclick="openCheckinMode('form')">继续写下来</button>
                <button class="button button--ghost" type="button" onclick="openCheckinMode('voice')">换成智能陪伴</button>
            </div>
        </section>
    `);

    safeSetHtml('#home-report-panel', `
        <section class="editorial-section editorial-section--route">
            ${handmadeRoute({
                eyebrow: '今日路线',
                title: '今天的路线',
                lead: hasReadyReport ? '现在最适合回看自己的节奏。' : '先把一句话留下来，页面才会真正开始工作。',
                badge: hasReadyReport ? '已就绪' : reportState.label,
                steps: [
                    { status: hasCheckin ? 'done' : 'active', label: '记录', title: hasCheckin ? '今日内容已落下' : '留下今天的第一句', meta: hasCheckin ? '已经有了可以继续整理的材料。' : '哪怕只写一句，也比空白更有力量。' },
                    { status: hasReadyReport ? 'done' : hasCheckin ? 'active' : 'pending', label: '简报', title: hasReadyReport ? '个人简报已经可读' : '系统会把今天整理成简报', meta: hasReadyReport ? latestInsight : latestSuggestion },
                    { status: 'pending', label: '关系', title: '准备好时，再邀请对方进入', meta: '不着急，先把自己的节奏养出来。' },
                ],
                note: hasReadyReport ? '读完简报，再决定下一步要不要去关系空间。' : '亲健的第一步不该是绑定，而是让你先被安放。',
            })}
            <div class="stage-surface__actions">
                <button class="button button--primary" type="button" onclick="${hasReadyReport ? "showPage('report')" : "openCheckinMode('form')"}">${hasReadyReport ? '去读个人简报' : '继续写下今天'}</button>
                <button class="button button--ghost" type="button" onclick="showPage('discover')">去发现看看</button>
            </div>
        </section>
    `);

    safeSetHtml('#home-milestones-panel', `
        <section class="editorial-section">
            <div class="editorial-section__head">
                <div>
                    <p class="editorial-section__eyebrow">节奏</p>
                    <h4 class="editorial-section__title">从今天开始，会慢慢长出来的节奏</h4>
                </div>
            </div>
            ${handmadeTimeline([
                {
                    date: hasCheckin ? '今天' : '现在',
                    title: hasCheckin ? '第一条记录已经落下' : '先留下今天的第一句',
                    meta: hasCheckin ? '你已经不是在空白里开始了。' : '不用完整，只要真实。'
                },
                {
                    date: hasReadyReport ? '随后' : '记录后',
                    title: hasReadyReport ? '个人简报已经能回看' : '系统会自动把今天整理成简报',
                    meta: hasReadyReport ? '去看一遍，你会更清楚自己现在在哪。' : '不用额外准备，记录够了它就会出现。'
                },
                {
                    date: '准备好时',
                    title: '把关系接进来',
                    meta: '等你愿意，再邀请对方进入共享空间。'
                },
            ])}
        </section>
    `);

    setHandmadePanelVisibility('#home-status-panel', true);
    setHandmadePanelVisibility('#home-report-panel', true);
    setHandmadePanelVisibility('#home-milestones-panel', true);
    setHandmadePanelVisibility('#home-tree-panel', false);
    setHandmadePanelVisibility('#home-crisis-panel', false);
    setHandmadePanelVisibility('#home-tasks-panel', false);

    state.notifications = Array.isArray(payload.notifications) ? payload.notifications : [];
    syncNotifications();
}

function renderHome(payload) {
    state.homeSnapshot = payload;
    const pairName = getPartnerDisplayName(payload.pair);
    const focus = getHomeFocusConfig(payload);
    const playbook = payload.playbook || null;
    const crisis = payload.crisis || { crisis_level: 'none' };
    const milestones = Array.isArray(payload.milestones) ? payload.milestones : [];
    const tasks = payload.tasks?.tasks || [];
    const nextMilestone = milestones[0] || null;
    const latestContent = payload.latestReport?.content || {};
    const latestScore = latestContent.health_score || latestContent.overall_health_score || '--';
    const latestInsight = latestContent.insight || latestContent.encouragement || latestContent.executive_summary || '等今天的记录足够完整，这里会出现真正有内容的简报结论。';
    const focusText = latestContent.suggestion || playbook?.branch_reason || focus.description;
    const myCheckin = payload.todayStatus?.my_checkin || {};
    const moodText = myCheckin.mood_score ? `${myCheckin.mood_score}/4` : '未记录';
    const interactionText = myCheckin.interaction_freq || myCheckin.interaction_freq === 0 ? `${myCheckin.interaction_freq} 次` : '未记录';
    const deepTalkText = myCheckin.deep_conversation === true ? '有' : myCheckin.deep_conversation === false ? '没有' : '未记录';
    const myStatusText = payload.todayStatus?.my_done ? '你已完成今日记录' : '你还没开始';
    const partnerStatusText = payload.todayStatus?.partner_done ? '对方也已完成' : '还在等待对方';
    const reportStatusText = payload.todayStatus?.has_report ? '今日简报已可读' : payload.todayStatus?.both_done ? '已满足生成简报条件' : '先完成今天的记录';
    const branchLabel = playbook?.active_branch_label || '待识别';
    const cycleText = playbook?.current_day && playbook?.total_days ? `第 ${playbook.current_day}/${playbook.total_days} 天` : '待启动';
    const boundaryNote = payload.latestReport?.limitation_note || latestContent.professional_note || '系统提供的是关系支持建议，不替代专业判断或安全评估。';
    const handoffNote = payload.latestReport?.safety_handoff || '';
    const userName = getPreferredUserName(state.me);
    const timelineItems = buildHomeTimelineItems(payload);
    const timelineLead = timelineItems[0]?.meta || latestInsight;
    const nextAction = focusText || '先把今天的原始片段留住，再决定下一步要不要推进。';
    const compactCoverTitle = (() => {
        if (payload.todayStatus?.has_report) return '去读简报';
        if (payload.todayStatus?.both_done) return '进入判断';
        if (payload.todayStatus?.my_done) return '等对方同步';
        return '留下今天这一句';
    })();
    const coverLead = payload.todayStatus?.has_report
        ? '状态已经排好了。'
        : payload.todayStatus?.both_done
            ? '材料已经差不多齐了。'
            : payload.todayStatus?.my_done
                ? '再等一句回应。'
                : '先把今天这一句留下来。';
    const coverAsideTitle = payload.todayStatus?.has_report
        ? '本期摘要'
        : payload.todayStatus?.both_done
            ? '可以继续'
            : '仍在等待';
    const recordExcerpt = trimHandmadeCopy(myCheckin.content || '先写下一句真正的话。', 44, '先写下一句真正的话。');
    const shortInsight = trimHandmadeCopy(latestInsight, 12, '判断会成形。');
    const shortBranchReason = trimHandmadeCopy(playbook?.branch_reason || timelineLead, 12, '证据会补齐。');
    const shortBoundary = trimHandmadeCopy(boundaryNote, 10, '辅助参考');
    const coverMarkers = [
        crisisLabel(crisis.crisis_level || 'none'),
        cycleText,
        payload.todayStatus?.has_report ? '简报可读' : payload.todayStatus?.both_done ? '材料已齐' : '继续补一句',
    ].filter(Boolean);
    const featuredTimeline = timelineItems[0] || null;
    const secondaryTimeline = timelineItems.slice(1, 4);
    const compactMyStatus = payload.todayStatus?.my_done ? '你已记录' : '你还没写';
    const compactReportStatus = payload.todayStatus?.has_report ? '简报可读' : payload.todayStatus?.both_done ? '等待简报' : '还差材料';

    safeSetText('#home-greeting', '关系总览');

    safeSetHtml('#home-overview', `
        <section class="home-cover">
            <div class="home-cover__mast">
                <div class="home-cover__identity" style="position: relative;">
                    <span>当前关系</span>
                    <select id="home-pair-select" class="input" style="appearance: none; background: transparent; border: none; font-size: 15px; font-weight: bold; color: var(--ink-dark); padding: 0; padding-right: 16px; cursor: pointer; outline: none;"></select>
                    <svg style="position: absolute; right: 0; top: 18px; width: 12px; height: 12px; pointer-events: none;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"></path></svg>
                </div>
                <div class="home-cover__metrics">
                    <span class="home-cover__tag">内测</span>
                    <span class="home-cover__tag">${escapeHtml(`${payload.streak.streak || 0}天连续`)}</span>
                    <span class="home-cover__tag">${escapeHtml(crisisLabel(crisis.crisis_level || 'none'))}</span>
                </div>
            </div>
            <div class="home-cover__body">
                <div class="home-cover__main">
                    <h3 class="home-cover__title">${renderHomeCoverTitle(compactCoverTitle)}</h3>
                    <div class="home-cover__briefs">
                        <article class="home-cover__brief">
                            <span>状态</span>
                            <strong>${escapeHtml(compactReportStatus)}</strong>
                        </article>
                        <article class="home-cover__brief">
                            <span>下一步</span>
                            <strong>${escapeHtml(trimHandmadeCopy(nextAction, 12, '先做一件。'))}</strong>
                        </article>
                    </div>
                    <div class="home-cover__foot">
                        <div class="stage-surface__actions home-cover__actions">
                            <button class="button button--primary" type="button" onclick="${focus.primaryAction}">${focus.primaryLabel}</button>
                            <button class="button button--ghost" type="button" onclick="${focus.secondaryAction}">${focus.secondaryLabel}</button>
                        </div>
                    </div>
                </div>
                <aside class="home-cover__annotation">
                    ${handmadeCoverVisual({ score: latestScore })}
                    <div class="home-cover__annotation-copy">
                        <h4>${escapeHtml(coverAsideTitle)}</h4>
                    </div>
                    <div class="home-cover__annotation-pills">
                        ${coverMarkers.map((item) => `<span>${escapeHtml(item)}</span>`).join('')}
                    </div>
                </aside>
            </div>
        </section>
    `);

    safeSetHtml('#home-metrics', '');

    safeSetHtml('#home-status-panel', `
        <section class="home-reading-room">
            <div class="home-reading-room__head">
                <div>
                    <h4>今天这一句</h4>
                </div>
                <span class="home-reading-room__badge">${escapeHtml(compactMyStatus)}</span>
            </div>
            <blockquote class="home-reading-room__quote">${escapeHtml(recordExcerpt)}</blockquote>
            <div class="timeline-chip-row home-reading-room__meta">
                <span class="timeline-chip">${escapeHtml(`互动 ${interactionText}`)}</span>
                <span class="timeline-chip">${escapeHtml(`心情 ${moodText}`)}</span>
            </div>
            <div class="stage-surface__actions home-reading-room__actions">
                <button class="button button--primary" type="button" onclick="openCheckinMode('form')">继续写</button>
                <button class="button button--ghost" type="button" onclick="openCheckinMode('voice')">语音补一句</button>
            </div>
        </section>
    `);

    safeSetHtml('#home-report-panel', `
        <section class="home-desk">
            <div class="home-desk__head">
                <div>
                    <h4>现在先做哪一步</h4>
                </div>
            </div>
            <div class="home-desk__focus">
                <strong>${escapeHtml(trimHandmadeCopy(nextAction, 12, '先做一件。'))}</strong>
            </div>
            <div class="home-desk__steps">
                <article class="home-desk__step home-desk__step--${payload.todayStatus?.my_done ? 'done' : 'active'}">
                    <span>01</span>
                    <div>
                        <strong>${escapeHtml(compactMyStatus)}</strong>
                    </div>
                </article>
                <article class="home-desk__step home-desk__step--${payload.todayStatus?.has_report ? 'done' : payload.todayStatus?.both_done ? 'active' : 'pending'}">
                    <span>02</span>
                    <div>
                        <strong>${escapeHtml(compactReportStatus)}</strong>
                    </div>
                </article>
            </div>
            <div class="stage-surface__actions home-desk__actions">
                <button class="button button--primary" type="button" onclick="${payload.todayStatus?.has_report ? "showPage('report')" : focus.primaryAction}">${payload.todayStatus?.has_report ? '去简报' : focus.primaryLabel}</button>
                <button class="button button--ghost" type="button" onclick="showPage('timeline')">时间线</button>
            </div>
        </section>
    `);

    safeSetHtml('#home-tasks-panel', '');

    safeSetHtml('#home-milestones-panel', `
        <section class="home-chronicle">
            <div class="home-chronicle__head">
                <div>
                    <h4>最近发生了什么</h4>
                </div>
                <div class="home-chronicle__head-actions">
                    <span class="home-chronicle__badge">${escapeHtml(timelineItems.length ? `${timelineItems.length} 条` : '暂无')}</span>
                    <button class="button button--ghost" type="button" onclick="showPage('milestones')">进入时间线</button>
                </div>
            </div>
            ${featuredTimeline ? `
                <section class="home-chronicle__featured">
                    <div class="home-chronicle__featured-copy">
                        <span class="home-chronicle__date">${escapeHtml(featuredTimeline.date || featuredTimeline.kicker || '最近')}</span>
                        <strong>${escapeHtml(trimHandmadeCopy(featuredTimeline.title || '', 22, '最近发生了一件需要先看的事。'))}</strong>
                    </div>
                    <div class="home-chronicle__featured-mark" aria-hidden="true">
                        <span>${String(1).padStart(2, '0')}</span>
                    </div>
                </section>
            ` : '<div class="section-empty">你们还没有留下任何可回放的关系线索。</div>'}
            ${secondaryTimeline.length ? `
                <div class="home-chronicle__rail">
                    ${secondaryTimeline.map((item, index) => `
                        <article class="home-chronicle__rail-item">
                            <span class="home-chronicle__rail-index">${String(index + 2).padStart(2, '0')}</span>
                            <div class="home-chronicle__rail-body">
                                <span class="home-chronicle__date">${escapeHtml(item.date || item.kicker || '最近')}</span>
                                <strong>${escapeHtml(trimHandmadeCopy(item.title || '', 16, '继续看下一条线索。'))}</strong>
                            </div>
                        </article>
                    `).join('')}
                </div>
            ` : ''}
            ${milestones.length ? `
                <div class="timeline-chip-row">
                    ${milestones.slice(0, 3).map((item) => `<span class="timeline-chip">${escapeHtml(item.title || milestoneTypeLabel(item.type) || '关系节点')}</span>`).join('')}
                </div>
            ` : ''}
            <div class="stage-surface__actions home-chronicle__actions">
                <button class="button button--ghost" type="button" onclick="openNarrativeAlignment()">双视角对齐</button>
            </div>
        </section>
    `);

    setHandmadePanelVisibility('#home-status-panel', true);
    setHandmadePanelVisibility('#home-report-panel', true);
    setHandmadePanelVisibility('#home-tasks-panel', false);
    setHandmadePanelVisibility('#home-milestones-panel', true);
    setHandmadePanelVisibility('#home-tree-panel', false);
    setHandmadePanelVisibility('#home-crisis-panel', false);

    state.notifications = Array.isArray(payload.notifications) ? payload.notifications : payload.notifications || [];
    syncNotifications();

    if (typeof renderPairSelect === 'function') {
        renderPairSelect();
        const selectElement = $('#home-pair-select');
        if (selectElement) {
            selectElement.addEventListener('change', (event) => {
                setCurrentPair(event.target.value);
                loadHomePage();
            });
        }
    }
}

async function loadReportPage() {
    const pairId = state.currentPair?.id || null;
    const isSolo = !pairId;
    if (isSolo && state.selectedReportType !== 'daily') {
        state.selectedReportType = 'daily';
    }

    syncReportTypeAvailability(isSolo);
    const reportType = isSolo ? 'daily' : state.selectedReportType;
    const [latest, history, trend, today, policyAudit] = await Promise.allSettled([
        api.getLatestReport(pairId, reportType),
        api.getReportHistory(pairId, reportType, 6),
        api.getHealthTrend(pairId, 14),
        api.getTodayStatus(pairId),
        api.getPolicyDecisionAudit(pairId),
    ]);

    const latestReport = unwrapResult(latest, null);
    const todayStatus = unwrapResult(today, {});
    const planPolicyAudit = unwrapResult(policyAudit, null);
    const button = $('#report-generate-btn');
    const soloButton = getSoloReportButtonState(todayStatus, latestReport);
    state.reportSnapshot = { isSolo, reportType, latestReport, todayStatus, planPolicyAudit };

    if (button) {
        button.textContent = isSolo ? soloButton.label : '生成这一期简报';
        button.disabled = isSolo ? soloButton.disabled : false;
    }

    renderReport(latestReport, unwrapResult(history, []), unwrapResult(trend, { trend: [] }), { solo: isSolo, reportType, planPolicyAudit });
}

function renderReport(report, history, trendData, options = {}) {
    const isSolo = Boolean(options.solo);
    const reportType = options.reportType || state.selectedReportType;
    const reportLabel = formatReportType(reportType, { solo: isSolo });
    const policyAuditPanel = renderPolicyDecisionAudit(options.planPolicyAudit, { solo: isSolo });

    if (report && report.status === 'pending') {
        safeSetHtml('#report-main', `<section class="editorial-section"><div class="section-empty">${reportLabel} 正在后台生成中。它会比即时结果更像一份能回看的编辑稿。</div></section>`);
    } else if (report && report.status === 'failed') {
        safeSetHtml('#report-main', `<section class="editorial-section"><div class="section-empty">${reportLabel} 这次生成失败了。稍后再试一次，通常就会恢复。</div></section>`);
    } else if (!report || report.status !== 'completed') {
        safeSetHtml('#report-main', `<section class="editorial-section"><div class="section-empty">这里还没有可展示的${reportLabel}。先把今天写清楚，再回来读一份真正有内容的简报。</div></section>`);
    } else {
        const content = report.content || {};
        const score = content.health_score || content.overall_health_score || 72;
        const primaryInsight = content.insight || content.self_insight || content.executive_summary || '系统已经替你把这一阶段的关系脉络整理好了。';
        const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || '';
        const encouragement = content.encouragement || content.relationship_note || '';
        const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
        const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);

        safeSetHtml('#report-main', `
            <section class="brief-stage">
                <div class="brief-stage__score"><span>${Math.max(1, Math.min(100, score))}</span><small>/100</small></div>
                <div class="brief-stage__copy">
                    <p class="brief-stage__eyebrow">${isSolo ? '个人简报' : '关系简报'}</p>
                    <h4>${reportLabel}</h4>
                    <p>${escapeHtml(primaryInsight)}</p>
                </div>
            </section>
            ${handmadeLedger([
                { label: '一句结论', value: primaryInsight, meta: '这是一份给人读的，不只是给系统看的分数。' },
                { label: '下一步动作', value: suggestion || concerns[0] || '继续把真实感受说清楚', meta: '越小的动作，越容易在日常里持续。' },
                { label: '报告日期', value: report.report_date || formatDateOnly(new Date().toISOString()), meta: isSolo ? '个人视角' : '双人关系视角' },
            ])}
            <section class="brief-columns">
                <div class="brief-column">
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">高光</p><h4 class="editorial-section__title">积极信号</h4></div></div>
                        ${handmadeList(highlights, '目前还没有明显高亮项，继续记录会让这部分更清楚。')}
                    </section>
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">留意</p><h4 class="editorial-section__title">需要关注</h4></div></div>
                        ${handmadeList(concerns, '目前没有额外提醒，继续保持稳定节奏就好。')}
                    </section>
                </div>
                <div class="brief-column">
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">趋势</p><h4 class="editorial-section__title">近阶段走势</h4></div></div>
                        ${handmadeTrend(trendData, { solo: isSolo })}
                    </section>
                    ${suggestion ? `<div class="note-ribbon note-ribbon--warm"><strong>现在最适合做的</strong><p>${escapeHtml(suggestion)}</p></div>` : ''}
                </div>
            </section>
            ${encouragement ? `<blockquote class="brief-note">${escapeHtml(encouragement)}</blockquote>` : ''}
        `);
    }

    const list = $('#report-history-list');
    if (!list) return;
    if (!history.length) {
        list.innerHTML = '<div class="section-empty">现在还没有历史简报记录。</div>';
        return;
    }

    list.innerHTML = `<div class="archive-ledger">${history.map((item, index) => {
        const status = String(item.status || 'pending').toLowerCase();
        const statusLabel = formatArchiveStatusLabel(item.status);
        const reportDate = item.report_date ? formatDateOnly(item.report_date) : '未命名日期';
        return `
        <article class="archive-ledger__item archive-ledger__item--${escapeHtml(status)}">
            <div class="archive-ledger__body">
                <span class="archive-ledger__index">附录 ${escapeHtml(String(index + 1).padStart(2, '0'))}</span>
                <strong>${formatReportType(item.type || reportType, { solo: isSolo })}</strong>
                <p>${escapeHtml(reportDate)}</p>
            </div>
            <span class="archive-ledger__status">${escapeHtml(statusLabel)}</span>
        </article>
    `;
    }).join('')}</div>`;
}

async function loadProfilePage() {
    if (!api.isLoggedIn()) {
        safeSetHtml('#profile-summary', `<section class="stage-surface"><p class="stage-surface__eyebrow">我的</p><h3 class="stage-surface__title">请先登录</h3><p class="stage-surface__body">登录后这里会显示你的账号信息和当前关系状态。</p></section>`);
        safeSetHtml('#profile-account-panel', '<div class="section-empty">登录后可查看账户资料。</div>');
        safeSetHtml('#profile-pair-panel', '<div class="section-empty">登录后可查看当前关系状态。</div>');
        safeSetHtml('#profile-relations-panel', '<div class="section-empty">登录后可查看全部关系列表和多关系切换入口。</div>');
        setHandmadePanelVisibility('#profile-account-panel', true);
        setHandmadePanelVisibility('#profile-pair-panel', false);
        setHandmadePanelVisibility('#profile-relations-panel', true);
        return;
    }

    const me = state.me || await api.getMe();
    state.me = me;
    const pair = state.currentPair;
    const allPairs = state.pairs || [];
    const activePairs = allPairs.filter((item) => item.status === 'active');
    const pendingPairs = allPairs.filter((item) => item.status === 'pending');
    const unbindStatus = pair ? await api.getUnbindStatus(pair.id).catch(() => ({ has_request: false })) : { has_request: false };
    const userName = getPreferredUserName(me);

    safeSetHtml('#profile-summary', `
        <section class="stage-surface stage-surface--profile">
            <p class="stage-surface__eyebrow">我的</p>
            <h3 class="stage-surface__title">${escapeHtml(userName)}</h3>
            <p class="stage-surface__body">${escapeHtml(getVisibleEmailLabel(me))} · ${pair ? '当前已在一段关系里' : '当前还没有绑定关系'}</p>
            ${handmadeLedger([
                { label: '活跃关系', value: String(activePairs.length), meta: '可以在这里切换当前关系。' },
                { label: '待加入', value: String(pendingPairs.length), meta: '还在等待对方进入的关系。' },
                { label: '当前对象', value: pair ? getPartnerDisplayName(pair) : '未设置', meta: pair ? '这会影响首页和报告的默认视角。' : '准备好了再建立连接。' },
            ])}
            ${state.profileFeedback ? `<div class="note-ribbon"><strong>已同步更新</strong><p>${escapeHtml(state.profileFeedback)}</p></div>` : ''}
        </section>
    `);

    safeSetHtml('#profile-account-panel', `
        <section class="editorial-section editorial-section--profile-grid">
            <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">身份</p><h4 class="editorial-section__title">身份与关系</h4></div></div>
            <div class="profile-columns">
                ${handmadeSheet('账户', '账户', [
                    { label: '昵称', value: userName, meta: '三端会共用这份名称。' },
                    { label: '邮箱', value: getVisibleEmailLabel(me, '未绑定'), meta: '当前主登录方式。' },
                    { label: '手机号', value: maskPhone(me.phone), meta: '用于验证码登录时显示。' },
                    { label: '登录渠道', value: getAccountChannels(me), meta: '决定你从哪里进入。' },
                    { label: '创建时间', value: formatDateOnly(me.created_at), meta: `账户编号：${String(me.id).slice(0, 8).toUpperCase()}` },
                ])}
                ${handmadeSheet('关系', pair ? '当前关系' : '关系状态', pair ? [
                    { label: '对象', value: getPartnerDisplayName(pair), meta: `创建于 ${formatDateOnly(pair.created_at)}` },
                    { label: '关系类型', value: TYPE_LABELS[pair.type] || pair.type, meta: pair.status === 'active' ? '当前已激活' : '还在等待加入' },
                    { label: '邀请码', value: pair.status === 'pending' ? (pair.invite_code || '无') : '已隐藏', meta: pair.status === 'pending' ? '可以直接发给对方。' : '关系激活后不再展示邀请码。' },
                    { label: '解绑状态', value: unbindStatus.has_request ? (unbindStatus.requested_by_me ? `你已发起，还剩 ${unbindStatus.days_remaining} 天` : '对方已发起解绑') : '当前没有进行中申请', meta: '边界感和关系管理都应在这里被看见。' },
                ] : [
                    { label: '当前状态', value: '未绑定关系', meta: '你可以继续用单人模式，不必被流程推着走。' },
                    { label: '下一步', value: '准备好再邀请对方', meta: '真正愿意时，再把关系接进来。' },
                ])}
            </div>
            <div class="profile-action-list">
                <button class="profile-action" type="button" onclick="openProfileEditor()" aria-label="修改名称"><span>${svgIcon('i-edit')}</span><div><strong>修改名称</strong><p>当前昵称：${escapeHtml(userName)}</p></div><span>进入</span></button>
                <button class="profile-action" type="button" onclick="openPasswordEditor()" aria-label="修改密码"><span>${svgIcon('i-lock')}</span><div><strong>修改密码</strong><p>保护关系数据和账号安全，建议定期更新。</p></div><span>进入</span></button>
                ${pair
                    ? `<button class="profile-action" type="button" onclick="openPartnerNicknameEditor()" aria-label="编辑对方备注"><span>${svgIcon('i-heart')}</span><div><strong>设置对方备注</strong><p>${escapeHtml(pair.custom_partner_nickname || '现在还没有备注名')}</p></div><span>进入</span></button>
                       <button class="profile-action" type="button" onclick="openUnbindPanel()" aria-label="管理解绑状态"><span>${svgIcon('i-refresh')}</span><div><strong>解绑与边界</strong><p>把取消、确认和等待都放到清楚的流程里。</p></div><span>进入</span></button>`
                    : `<button class="profile-action" type="button" onclick="showPage('pair')" aria-label="建立关系"><span>${svgIcon('i-link')}</span><div><strong>去建立关系</strong><p>继续单人模式也可以，准备好了再邀请对方。</p></div><span>进入</span></button>`}
            </div>
        </section>
    `);

    safeSetHtml('#profile-pair-panel', '');

    safeSetHtml('#profile-relations-panel', `
        <section class="editorial-section">
            <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">关系</p><h4 class="editorial-section__title">全部关系</h4></div></div>
            <p class="editorial-section__note">所有关系都放在这里切换和管理。换一个关系，首页、记录和简报都会一起跟着切过去。</p>
            ${renderRelationManagementList(allPairs, pair?.id || null)}
            <div class="stage-surface__actions">
                <button class="button button--primary" type="button" onclick="showPage('pair')">新增或加入关系</button>
                <button class="button button--ghost" type="button" onclick="showPage('home')">回到首页</button>
            </div>
        </section>
    `);

    setHandmadePanelVisibility('#profile-account-panel', true);
    setHandmadePanelVisibility('#profile-pair-panel', false);
    setHandmadePanelVisibility('#profile-relations-panel', true);
}

async function loadReportPage() {
    const pairId = state.currentPair?.id || null;
    const isSolo = !pairId;
    if (isSolo && state.selectedReportType !== 'daily') {
        state.selectedReportType = 'daily';
    }

    syncReportTypeAvailability(isSolo);
    const reportType = isSolo ? 'daily' : state.selectedReportType;
    const [latest, history, trend, today, policyAudit] = await Promise.allSettled([
        api.getLatestReport(pairId, reportType),
        api.getReportHistory(pairId, reportType, 6),
        api.getHealthTrend(pairId, 14),
        api.getTodayStatus(pairId),
        api.getPolicyDecisionAudit(pairId),
    ]);

    const latestReport = unwrapResult(latest, null);
    const todayStatus = unwrapResult(today, {});
    const planPolicyAudit = unwrapResult(policyAudit, null);
    const button = $('#report-generate-btn');
    const soloButton = getSoloReportButtonState(todayStatus, latestReport);
    state.reportSnapshot = { isSolo, reportType, latestReport, todayStatus, planPolicyAudit };

    if (button) {
        button.textContent = isSolo ? soloButton.label : '生成这一期简报';
        button.disabled = isSolo ? soloButton.disabled : false;
    }

    renderReport(
        latestReport,
        unwrapResult(history, []),
        unwrapResult(trend, { trend: [] }),
        { solo: isSolo, reportType, planPolicyAudit },
    );
}

function renderReport(report, history, trendData, options = {}) {
    const isSolo = Boolean(options.solo);
    const reportType = options.reportType || state.selectedReportType;
    const reportLabel = formatReportType(reportType, { solo: isSolo });
    const policyAuditPanel = renderPolicyDecisionAudit(options.planPolicyAudit, { solo: isSolo });

    if (report && report.status === 'pending') {
        safeSetHtml('#report-main', `<section class="editorial-section"><div class="section-empty">${reportLabel} 正在后台生成中，下方策略审计已经先整理出当前路径。</div></section>${policyAuditPanel}`);
    } else if (report && report.status === 'failed') {
        safeSetHtml('#report-main', `<section class="editorial-section"><div class="section-empty">${reportLabel} 这次生成失败了。稍后再试，下方策略审计仍会说明当前策略。</div></section>${policyAuditPanel}`);
    } else if (!report || report.status !== 'completed') {
        safeSetHtml('#report-main', `<section class="editorial-section"><div class="section-empty">当前还没有可展示的${reportLabel}，下方策略审计会先说明为什么系统正在维持或调整当前策略。</div></section>${policyAuditPanel}`);
    } else {
        const content = report.content || {};
        const score = content.health_score || content.overall_health_score || 72;
    const primaryInsight = content.insight || content.self_insight || content.executive_summary || '系统已经把这一阶段整理成一份可读的简报。';
        const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || '';
        const encouragement = content.encouragement || content.relationship_note || '';
        const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
        const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);

        safeSetHtml('#report-main', `
            <section class="brief-stage">
                <div class="brief-stage__score"><span>${Math.max(1, Math.min(100, score))}</span><small>/100</small></div>
                <div class="brief-stage__copy">
                    <p class="brief-stage__eyebrow">${isSolo ? '个人简报' : '关系简报'}</p>
                    <h4>${reportLabel}</h4>
                    <p>${escapeHtml(primaryInsight)}</p>
                </div>
            </section>
            ${handmadeLedger([
                { label: '一句结论', value: primaryInsight, meta: '给人读的总结，而不只是给系统看的分数。' },
                { label: '下一步动作', value: suggestion || concerns[0] || '继续把真实感受说清楚', meta: '越小的动作，越容易在日常里持续。' },
                { label: '报告日期', value: report.report_date || formatDateOnly(new Date().toISOString()), meta: isSolo ? '个人视角' : '双人关系视角' },
            ])}
            <section class="brief-columns">
                <div class="brief-column">
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">高光</p><h4 class="editorial-section__title">积极信号</h4></div></div>
                        ${handmadeList(highlights, '目前还没有明显高亮项，继续记录会让这里更清楚。')}
                    </section>
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">留意</p><h4 class="editorial-section__title">需要关注</h4></div></div>
                        ${handmadeList(concerns, '目前没有额外提醒，继续保持稳定节奏就好。')}
                    </section>
                </div>
                <div class="brief-column">
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">趋势</p><h4 class="editorial-section__title">近阶段走势</h4></div></div>
                        ${handmadeTrend(trendData, { solo: isSolo })}
                    </section>
                    ${suggestion ? `<div class="note-ribbon note-ribbon--warm"><strong>现在最适合做的</strong><p>${escapeHtml(suggestion)}</p></div>` : ''}
                </div>
            </section>
            ${encouragement ? `<blockquote class="brief-note">${escapeHtml(encouragement)}</blockquote>` : ''}
            ${policyAuditPanel}
        `);
    }

    const list = $('#report-history-list');
    if (!list) return;
    if (!history.length) {
        list.innerHTML = '<div class="section-empty">现在还没有历史简报记录。</div>';
        return;
    }

    list.innerHTML = `<div class="archive-ledger">${history.map((item, index) => {
        const status = String(item.status || 'pending').toLowerCase();
        const statusLabel = formatArchiveStatusLabel(item.status);
        const reportDate = item.report_date ? formatDateOnly(item.report_date) : '未命名日期';
        return `
        <article class="archive-ledger__item archive-ledger__item--${escapeHtml(status)}">
            <div class="archive-ledger__body">
                <span class="archive-ledger__index">附录 ${escapeHtml(String(index + 1).padStart(2, '0'))}</span>
                <strong>${formatReportType(item.type || reportType, { solo: isSolo })}</strong>
                <p>${escapeHtml(reportDate)}</p>
            </div>
            <span class="archive-ledger__status">${escapeHtml(statusLabel)}</span>
        </article>
    `;
    }).join('')}</div>`;
}

syncTopbar = function() {
    const compactPages = new Set([
        'home',
        'checkin',
        'discover',
        'report',
        'profile',
        'milestones',
        'longdistance',
        'attachment-test',
        'health-test',
        'community',
        'challenges',
        'courses',
        'experts',
        'membership',
    ]);
    const compactTitleMap = {
        home: '把关系照顾好',
        checkin: '记录',
        discover: '发现',
        report: '关系简报',
        profile: '我的',
        milestones: '时间线',
        longdistance: '异地',
        'attachment-test': '依恋',
        'health-test': '体检',
        community: '技巧',
        challenges: '挑战',
        courses: '课程',
        experts: '咨询',
        membership: '会员',
    };
    const fullTitleMap = {
        auth: '关系支持系统',
        pair: '建立一段关系',
        'pair-waiting': '等待对方加入',
    };
    const fullSubtitleMap = {
        auth: '从今天开始，慢慢把关系养好。',
        pair: '先把彼此放进同一个空间，再开始共同记录。',
        'pair-waiting': '邀请码已经准备好，差最后一步。',
    };
    const page = state.currentPage;
    const isCompact = compactPages.has(page);

    safeSetText('#topbar-title', isCompact ? (compactTitleMap[page] || '亲健') : (fullTitleMap[page] || '关系支持系统'));
    safeSetText('#topbar-subtitle', isCompact ? '' : (fullSubtitleMap[page] || '从今天开始，慢慢把关系养好。'));
    safeSetText('#topbar-caption', '亲健');

    const ritualButton = document.querySelector('.pill-button[data-jump-page], .pill-button');
    if (ritualButton) {
        const hiddenPages = new Set(['auth', 'pair', 'pair-waiting']);
        ritualButton.classList.toggle('hidden', hiddenPages.has(page));
        ritualButton.textContent = page === 'checkin' ? '回总览' : '写记录';
        ritualButton.dataset.jumpPage = page === 'checkin' ? 'home' : 'checkin';
    }
};

async function loadReportPage() {
    const pairId = state.currentPair?.id || null;
    const isSolo = !pairId;
    if (isSolo && state.selectedReportType !== 'daily') {
        state.selectedReportType = 'daily';
    }

    syncReportTypeAvailability(isSolo);
    const reportType = isSolo ? 'daily' : state.selectedReportType;
    const button = $('#report-generate-btn');

    if (isDemoMode()) {
        const latestReport = deepClone(getDemoFixture('latestReport') || null);
        const history = deepClone(getDemoFixture('reportHistory') || []);
        const trend = deepClone(getDemoFixture('healthTrend') || { trend: [] });
        const safetyStatus = deepClone(getDemoFixture('safetyStatus') || null);
        const assessmentTrend = deepClone(getDemoFixture('assessmentTrend') || null);
        const planPolicyAudit = deepClone(getDemoFixture('policyAudit') || null);
        const planScorecard = deepClone(getDemoFixture('scorecard') || null);
        const planPolicySchedule = deepClone(getDemoFixture('policySchedule') || null);
        const timeline = deepClone(getDemoFixture('timeline') || null);

        state.reportSnapshot = {
            isSolo,
            reportType,
            latestReport,
            todayStatus: { can_generate: false },
            planPolicyAudit,
            planScorecard,
            planPolicySchedule,
            safetyStatus,
            assessmentTrend,
            timeline,
        };

        if (button) {
            button.textContent = '样例查看中';
            button.disabled = true;
        }

        renderReport(latestReport, history, trend, {
            solo: false,
            reportType,
            planPolicyAudit,
            planScorecard,
            planPolicySchedule,
            safetyStatus,
            assessmentTrend,
            timeline,
        });
        return;
    }

    const [latest, history, trend, today, policyAudit, safety, assessmentTrend, scorecard, policySchedule, timeline] = await Promise.allSettled([
        api.getLatestReport(pairId, reportType),
        api.getReportHistory(pairId, reportType, 6),
        api.getHealthTrend(pairId, 14),
        api.getTodayStatus(pairId),
        api.getPolicyDecisionAudit(pairId),
        api.getSafetyStatus(pairId),
        api.getWeeklyAssessmentTrend(pairId),
        api.getInterventionScorecard(pairId),
        api.getPolicySchedule(pairId),
        api.getRelationshipTimeline(pairId, 12),
    ]);

    const latestReport = unwrapResult(latest, null);
    const todayStatus = unwrapResult(today, {});
    const planPolicyAudit = unwrapResult(policyAudit, null);
    const soloButton = getSoloReportButtonState(todayStatus, latestReport);
    state.reportSnapshot = {
        isSolo,
        reportType,
        latestReport,
        todayStatus,
        planPolicyAudit,
        planScorecard: unwrapResult(scorecard, null),
        planPolicySchedule: unwrapResult(policySchedule, null),
        safetyStatus: unwrapResult(safety, null),
        assessmentTrend: unwrapResult(assessmentTrend, null),
        timeline: unwrapResult(timeline, { event_count: 0, latest_event_at: null, events: [], highlights: [] }),
    };

    if (button) {
        button.textContent = isSolo ? soloButton.label : '生成这一期简报';
        button.disabled = isSolo ? soloButton.disabled : false;
    }

    renderReport(
        latestReport,
        unwrapResult(history, []),
        unwrapResult(trend, { trend: [] }),
        {
            solo: isSolo,
            reportType,
            planPolicyAudit,
            planScorecard: state.reportSnapshot.planScorecard,
            planPolicySchedule: state.reportSnapshot.planPolicySchedule,
            safetyStatus: state.reportSnapshot.safetyStatus,
            assessmentTrend: state.reportSnapshot.assessmentTrend,
            timeline: state.reportSnapshot.timeline,
        },
    );
}

function renderReport(report, history, trendData, options = {}) {
    const isSolo = Boolean(options.solo);
    const reportType = options.reportType || state.selectedReportType;
    const reportLabel = formatReportType(reportType, { solo: isSolo });
    const safetyPanel = renderSafetyStatusPanel(options.safetyStatus || {
        risk_level: report?.content?.crisis_level || 'none',
        why_now: report?.content?.insight || report?.content?.executive_summary || '',
        evidence_summary: report?.evidence_summary || [],
        limitation_note: report?.limitation_note || '',
        recommended_action: report?.content?.suggestion || '',
        handoff_recommendation: report?.safety_handoff || '',
    }, { title: '信任与边界' });
    const assessmentPanel = renderAssessmentTrendCard(options.assessmentTrend, { title: '近 4 次关系体检趋势' });
    const timelineRibbon = renderRelationshipTimelineRibbon(options.timeline, { solo: isSolo });
    const scorecardPanel = renderInterventionScorecard(options.planScorecard, { solo: isSolo });
    const policyAuditPanel = renderPolicyDecisionAudit(options.planPolicyAudit, { solo: isSolo });
    const schedulePanel = renderPolicySchedule(options.planPolicySchedule, { solo: isSolo });

    let heroBlock = `
        <section class="cockpit-shell cockpit-shell--empty">
                        <p class="panel__eyebrow">${isSolo ? '个人总览' : '关系总览'}</p>
            <h3>${escapeHtml(reportLabel)}</h3>
            <p>这里还没有一份可展示的简报。先完成记录，再回来查看一张更完整的结果页。</p>
        </section>
    `;

    if (report?.status === 'pending') {
        heroBlock = `
            <section class="cockpit-shell cockpit-shell--empty">
                <p class="panel__eyebrow">生成中</p>
                <h3>${escapeHtml(reportLabel)} 正在生成</h3>
                <p>系统正在把最近的记录、风险和干预路径压缩成一份可读简报，请稍候回来查看。</p>
            </section>
        `;
    } else if (report?.status === 'failed') {
        heroBlock = `
            <section class="cockpit-shell cockpit-shell--empty">
                <p class="panel__eyebrow">重试</p>
                <h3>${escapeHtml(reportLabel)} 生成失败</h3>
                <p>这次简报没有顺利完成，但下面的证据和策略面板仍然可以帮助你读懂当前阶段。</p>
            </section>
        `;
    } else if (report?.status === 'completed') {
        heroBlock = renderHandmadeReportHero(report, options);
    }

    let reportSections = `
        ${heroBlock}
        <section class="report-chapter report-chapter--proof">
            <div class="report-chapter__head">
                <div>
                    <p class="report-chapter__eyebrow">为什么这样判断</p>
                    <h4>把风险、趋势和时间线放回同一条证据链里</h4>
                </div>
                <p>只有把输入、证据和策略放在一起读，这份简报才不是一张只有结论的卡片。</p>
            </div>
            <div class="report-proof-grid">
                <div class="report-proof-grid__main">
                    ${timelineRibbon}
                    ${assessmentPanel}
                    ${safetyPanel}
                </div>
                <div class="report-proof-grid__side">
                    ${scorecardPanel}
                    ${policyAuditPanel}
                    ${schedulePanel}
                </div>
            </div>
        </section>
        <section class="report-chapter report-chapter--actions">
            <div class="report-chapter__head">
                <div>
                    <p class="report-chapter__eyebrow">接下来做什么</p>
                    <h4>先选一件今天真的做得出来的动作</h4>
                </div>
                <p>不要一次谈完所有问题，先把最容易落地的一步做出来，再看接下来怎么推进。</p>
            </div>
            <div class="cockpit-action-row">
                ${isSolo
                    ? '<button class="button button--secondary" type="button" onclick="showPage(\'checkin\')">回到今日记录</button><button class="button button--ghost" type="button" onclick="showPage(\'timeline\')">打开时间轴</button><button class="button button--ghost" type="button" onclick="openMethodologyExplainer()">判断说明</button>'
                    : '<button class="button button--secondary" type="button" onclick="openMessageSimulator()">聊天前预演</button><button class="button button--ghost" type="button" onclick="openNarrativeAlignment()">双视角对齐</button><button class="button button--ghost" type="button" onclick="openCrisisDetail()">修复协议</button><button class="button button--ghost" type="button" onclick="showPage(\'timeline\')">时间轴</button>'}
            </div>
        </section>
    `;

    if (report?.status === 'completed') {
        const content = report.content || {};
        const primaryInsight = content.insight || content.self_insight || content.executive_summary || '系统已经把这一阶段整理成一份可读的简报。';
        const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || '';
        const encouragement = content.encouragement || content.relationship_note || '';
        const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
        const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);
        const reportDate = report.report_date || formatDateOnly(new Date().toISOString());
        const nextAction = suggestion || concerns[0] || '继续把真实感受说清楚，再决定要不要进入下一步讨论。';
        const evidenceSummary = (report.evidence_summary || content.evidence_summary || []).slice(0, 3);
        const boundaryNote = getPreferredText(
            options.safetyStatus?.limitation_note
            || options.safetyStatus?.recommended_action
            || report?.safety_handoff
            || report?.limitation_note,
            '这份判断只负责帮你看清这阶段发生了什么，不替代真正的沟通和决定。'
        );

        reportSections = `
            ${heroBlock}
            <section class="report-chapter report-chapter--read report-chapter--quiet">
                <div class="report-chapter__head report-chapter__head--compact">
                    <div>
                        <p class="report-chapter__eyebrow">主结论</p>
                        <h4>先读这三句</h4>
                    </div>
                </div>
                <div class="report-takeaway-grid">
                    <article class="report-takeaway">
                        <span>一句结论</span>
                        <strong>${escapeHtml(primaryInsight)}</strong>
                    </article>
                    <article class="report-takeaway">
                        <span>下一步</span>
                        <strong>${escapeHtml(nextAction)}</strong>
                    </article>
                    <article class="report-takeaway">
                        <span>${encouragement ? '给此刻的话' : '这期日期'}</span>
                        <strong>${escapeHtml(encouragement || reportDate)}</strong>
                    </article>
                </div>
            </section>
            <section class="report-chapter report-chapter--guide">
                <div class="report-chapter__head report-chapter__head--compact">
                    <div>
                        <p class="report-chapter__eyebrow">行动</p>
                        <h4>先把动作读明白</h4>
                    </div>
                </div>
                <div class="report-action-layout">
                    <div class="report-action-layout__main">
                        <section class="report-mini-section">
                            <span class="report-mini-section__eyebrow">积极信号</span>
                            ${handmadeList(highlights, '继续记录，这里的亮点会慢慢更清楚。')}
                        </section>
                        <section class="report-mini-section">
                            <span class="report-mini-section__eyebrow">需要关注</span>
                            ${handmadeList(concerns, '现在没有额外提醒，保持稳定节奏就好。')}
                        </section>
                    </div>
                    <div class="report-action-layout__side">
                        <div class="report-action-callout">
                            <span>现在先做</span>
                            <strong>${escapeHtml(nextAction)}</strong>
                        </div>
                        <div class="report-trend-card">
                            <span class="report-mini-section__eyebrow">近阶段趋势</span>
                            ${handmadeTrend(trendData, { solo: isSolo })}
                        </div>
                    </div>
                </div>
            </section>
            <section class="report-chapter report-chapter--proof">
                <div class="report-chapter__head report-chapter__head--compact">
                    <div>
                        <p class="report-chapter__eyebrow">证据</p>
                        <h4>为什么会这样判断</h4>
                    </div>
                </div>
                <div class="report-proof-layout">
                    <div class="report-proof-stack">
                        ${timelineRibbon}
                    </div>
                    <aside class="report-proof-note">
                        <span class="report-mini-section__eyebrow">证据摘要</span>
                        <strong>先看时间轴，再看系统为什么把这次判断落在这里。</strong>
                        ${handmadeList(evidenceSummary, '这次简报已经保留核心证据，你可以直接沿着时间线读下去。')}
                        <p>${escapeHtml(boundaryNote)}</p>
                    </aside>
                </div>
                <details class="report-appendix">
                        <summary>展开评估与策略附录</summary>
                        <div class="report-appendix__grid">
                            ${assessmentPanel}
                            ${safetyPanel}
                            ${scorecardPanel}
                            ${policyAuditPanel}
                            ${schedulePanel}
                        </div>
                    </details>
            </section>
        `;
    }

    safeSetHtml('#report-main', reportSections);

    const list = $('#report-history-list');
    if (!list) return;
    if (!history.length) {
        list.innerHTML = '<div class="section-empty">现在还没有历史简报记录。</div>';
        return;
    }

    list.innerHTML = `<div class="archive-ledger">${history.map((item, index) => {
        const status = String(item.status || 'pending').toLowerCase();
        const statusLabel = formatArchiveStatusLabel(item.status);
        const reportDate = item.report_date ? formatDateOnly(item.report_date) : '未命名日期';
        return `
        <article class="archive-ledger__item archive-ledger__item--${escapeHtml(status)}">
            <div class="archive-ledger__body">
                <span class="archive-ledger__index">附录 ${escapeHtml(String(index + 1).padStart(2, '0'))}</span>
                <strong>${formatReportType(item.type || reportType, { solo: isSolo })}</strong>
                <p>${escapeHtml(reportDate)}</p>
            </div>
            <span class="archive-ledger__status">${escapeHtml(statusLabel)}</span>
        </article>
    `;
    }).join('')}</div>`;
}

async function loadProfilePage() {
    if (!state.me && !isDemoMode()) {
        safeSetHtml('#profile-summary', '<div class="empty-state">请先登录。</div>');
        safeSetHtml('#profile-account-panel', '');
        safeSetHtml('#profile-pair-panel', '');
        safeSetHtml('#profile-relations-panel', '');
        return;
    }

    const me = state.me || deepClone(getDemoFixture('me')) || {};
    const allPairs = state.pairs || deepClone(getDemoFixture('pairs')) || [];
    const pair = state.currentPair || allPairs[0] || null;
    const userName = me.nickname || me.email || '亲健用户';
    const activePairs = allPairs.filter((item) => item.status === 'active');
    const pendingPairs = allPairs.filter((item) => item.status === 'pending');
    const unbindStatus = isDemoMode()
        ? { has_request: false }
        : (pair ? await getCurrentUnbindStatus(pair.id).catch(() => ({ has_request: false })) : { has_request: false });

    if (!isDemoMode()) {
        try {
            await loadAdminPolicies();
        } catch (error) {
            // Keep the page usable even if admin policy loading fails.
        }
    }

    safeSetHtml('#profile-summary', `
        <section class="cockpit-shell cockpit-shell--profile-hero">
            <div class="cockpit-shell__head">
                <div>
                    <p class="panel__eyebrow">我的概况</p>
                    <h3>${escapeHtml(userName)}</h3>
                </div>
                <span class="pill">${isDemoMode() ? '样例模式' : '在线模式'}</span>
            </div>
            <p>${escapeHtml(getVisibleEmailLabel(me))}，${pair ? '当前已经进入一段关系' : '当前还没有绑定关系'}。</p>
            ${handmadeLedger([
                { label: '活跃关系', value: String(activePairs.length), meta: '决定首页、简报和时间轴默认读取哪一段关系。' },
                { label: '待加入', value: String(pendingPairs.length), meta: '还在等待对方进入的关系会留在这里。' },
                { label: '当前对象', value: pair ? getPartnerDisplayName(pair) : '未设置', meta: pair ? '你现在看到的系统判断都围绕这段关系展开。' : '先保持单人模式也完全可以。' },
            ])}
        </section>
    `);

    safeSetHtml('#profile-account-panel', `
        <section class="cockpit-shell cockpit-shell--evidence">
            <div class="cockpit-shell__head">
                <div>
                    <p class="panel__eyebrow">依据</p>
                    <h4>身份、关系与策略概览</h4>
                </div>
                <p>这里把账户事实、当前关系状态和策略信息收进同一个安静视图里。</p>
            </div>
            <div class="cockpit-grid">
                <div class="cockpit-grid__main">
                    <div class="profile-columns">
                        ${handmadeSheet('账户', '账户信息', [
                            { label: '昵称', value: userName, meta: '三端会共用这份名称。' },
                            { label: '邮箱', value: getVisibleEmailLabel(me, '未绑定'), meta: '当前主登录方式。' },
                            { label: '手机号', value: maskPhone(me.phone), meta: '验证码登录时展示。' },
                            { label: '登录渠道', value: getAccountChannels(me), meta: '决定你从哪里进入。' },
                            { label: '创建时间', value: formatDateOnly(me.created_at), meta: `账户编号：${String(me.id || '').slice(0, 8).toUpperCase()}` },
                        ])}
                        ${handmadeSheet('关系', pair ? '当前关系' : '关系状态', pair ? [
                            { label: '对象', value: getPartnerDisplayName(pair), meta: `创建于 ${formatDateOnly(pair.created_at)}` },
                            { label: '关系类型', value: TYPE_LABELS[pair.type] || pair.type, meta: pair.status === 'active' ? '当前已激活' : '还在等待加入' },
                            { label: '邀请码', value: pair.status === 'pending' ? (pair.invite_code || '无') : '已隐藏', meta: pair.status === 'pending' ? '可以直接发给对方。' : '关系激活后不再展示邀请码。' },
                            { label: '解绑状态', value: unbindStatus.has_request ? (unbindStatus.requested_by_me ? `你已发起，还剩 ${unbindStatus.days_remaining} 天` : '对方已发起解绑') : '当前没有进行中申请', meta: '边界感和关系管理都应该在这里被看见。' },
                        ] : [
                            { label: '当前状态', value: '未绑定关系', meta: '你可以继续用单人模式，不必被流程推着走。' },
                            { label: '下一步', value: '准备好再邀请对方', meta: '真正愿意时，再把关系接进来。' },
                        ])}
                    </div>
                    ${isDemoMode()
                        ? '<section class="safety-panel safety-panel--compact"><div class="safety-panel__head"><div><p class="panel__eyebrow">查看模式</p><h4>样例模式不会改真实数据</h4></div></div><p class="safety-panel__summary">当前页面只展示结构和内容，不开放改名、解绑或策略调整等修改操作。</p></section>'
                        : ''}
                </div>
                <div class="cockpit-grid__side">
                    ${isDemoMode()
                        ? '<section class="cockpit-shell cockpit-shell--actions"><div class="cockpit-shell__head"><div><p class="panel__eyebrow">策略概览</p><h4>策略面板（查看）</h4></div></div><p>样例模式下只展示策略内容，不触发新增、编辑、启停或回滚。</p><div class="cockpit-action-row"><button class="button button--ghost" type="button" onclick="exitDemoMode()">退出样例</button></div></section>'
                        : (state.isAdmin ? renderPolicyWorkbenchLauncher(state.adminPolicies || []) : renderPolicyWorkbenchErrorNotice(state.policyWorkbenchError || '当前账号没有管理员权限，策略面板不会显示写入口。'))}
                </div>
            </div>
        </section>
    `);

    safeSetHtml('#profile-pair-panel', '');

    safeSetHtml('#profile-relations-panel', `
        <section class="cockpit-shell cockpit-shell--actions">
            <div class="cockpit-shell__head">
                <div>
                    <p class="panel__eyebrow">动作</p>
                    <h4>关系切换与账户动作</h4>
                </div>
                <p>切换关系后，首页、时间轴和简报都会一起跟着切过去。</p>
            </div>
            <div class="profile-action-list">
                ${isDemoMode()
                    ? '<button class="profile-action" type="button" onclick="showPage(\'report\')"><span>→</span><div><strong>返回关系简报</strong><p>继续查看当前关系状态与后续动作。</p></div><span>进入</span></button>'
                    : `<button class="profile-action" type="button" onclick="openProfileEditor()" aria-label="修改名称"><span>${svgIcon('i-edit')}</span><div><strong>修改名称</strong><p>当前显示名：${escapeHtml(userName)}</p></div><span>进入</span></button>
                       <button class="profile-action" type="button" onclick="openPasswordEditor()" aria-label="修改密码"><span>${svgIcon('i-lock')}</span><div><strong>修改密码</strong><p>保护关系数据和账号安全，建议定期更新。</p></div><span>进入</span></button>
                       ${pair
                            ? `<button class="profile-action" type="button" onclick="openPartnerNicknameEditor()" aria-label="编辑对方备注"><span>${svgIcon('i-heart')}</span><div><strong>设置对方备注</strong><p>${escapeHtml(pair.custom_partner_nickname || '现在还没有备注名')}</p></div><span>进入</span></button>
                               <button class="profile-action" type="button" onclick="openUnbindPanel()" aria-label="管理解绑状态"><span>${svgIcon('i-refresh')}</span><div><strong>解绑与边界</strong><p>把取消、确认和等待都放到清楚的流程里。</p></div><span>进入</span></button>`
                            : `<button class="profile-action" type="button" onclick="showPage('pair')" aria-label="建立关系"><span>${svgIcon('i-link')}</span><div><strong>去建立关系</strong><p>继续单人模式也可以，准备好了再邀请对方。</p></div><span>进入</span></button>`}`}
            </div>
            <section class="editorial-section">
                <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">关系</p><h4 class="editorial-section__title">全部关系</h4></div></div>
                <p class="editorial-section__note">所有关系都放在这里切换和管理。换一个关系，首页、记录和简报都会一起跟着切过去。</p>
                ${renderRelationManagementList(allPairs, pair?.id || null)}
                <div class="stage-surface__actions">
                    <button class="button button--primary" type="button" onclick="showPage('pair')">${isDemoMode() ? '查看关系设置页' : '新增或加入关系'}</button>
                    <button class="button button--ghost" type="button" onclick="showPage('home')">回到首页</button>
                </div>
            </section>
        </section>
    `);

    setHandmadePanelVisibility('#profile-account-panel', true);
    setHandmadePanelVisibility('#profile-pair-panel', false);
    setHandmadePanelVisibility('#profile-relations-panel', true);
}
