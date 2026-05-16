function handmadeLedger(items = []) {
  if (!items.length)
    return '<div class="section-empty">这里还没有可展示的内容。</div>';
  return `<div class="ledger-strip">${items.map((item) => `
        <article class="ledger-item">
            <span class="ledger-item__label">${escapeHtml(item.label || "")}</span>
            <strong class="ledger-item__value">${escapeHtml(item.value || "")}</strong>
            ${item.meta ? `<p class="ledger-item__meta">${escapeHtml(item.meta)}</p>` : ""}
        </article>
    `).join("")}</div>`;
}
function handmadeRows(rows = [], emptyText = "这里还没有内容。") {
  if (!rows.length)
    return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
  return `<div class="editorial-rows">${rows.map((row) => `
        <article class="editorial-row">
            <span class="editorial-row__label">${escapeHtml(row.label || "")}</span>
            <div class="editorial-row__body">
                <strong class="editorial-row__value">${escapeHtml(row.value || "")}</strong>
                ${row.meta ? `<p class="editorial-row__meta">${escapeHtml(row.meta)}</p>` : ""}
            </div>
            ${row.side ? `<span class="editorial-row__side">${escapeHtml(row.side)}</span>` : ""}
        </article>
    `).join("")}</div>`;
}
function handmadeList(items = [], emptyText = "这里还没有内容。") {
  if (!items.length)
    return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
  return `<ul class="brief-bullets">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}
function handmadeLedgerBand(items = [], emptyText = "这里还没有可展示的内容。") {
  if (!items.length)
    return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
  return `
        <section class="home-ledger-ribbon">
            ${items.map((item) => `
                <article class="home-ledger-ribbon__item">
                    <span class="home-ledger-ribbon__label">${escapeHtml(item.label || "")}</span>
                    <div class="home-ledger-ribbon__body">
                        <strong class="home-ledger-ribbon__value">${escapeHtml(item.value || "")}</strong>
                        ${item.meta ? `<p class="home-ledger-ribbon__meta">${escapeHtml(item.meta)}</p>` : ""}
                    </div>
                </article>
            `).join("")}
        </section>
    `;
}
function handmadeSignalRun(items = [], emptyText = "这里还没有可展示的内容。") {
  if (!items.length)
    return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
  return `
        <section class="home-signal-run">
            ${items.map((item, index) => `
                <article class="home-signal-run__item">
                    <span class="home-signal-run__index">${String(index + 1).padStart(2, "0")}</span>
                    <div class="home-signal-run__body">
                        <p class="home-signal-run__label">${escapeHtml(item.label || "")}</p>
                        <strong class="home-signal-run__value">${escapeHtml(item.value || "")}</strong>
                        ${item.meta ? `<p class="home-signal-run__meta">${escapeHtml(item.meta)}</p>` : ""}
                    </div>
                </article>
            `).join("")}
        </section>
    `;
}
function handmadeEditorialFacts(rows = [], emptyText = "这里还没有内容。") {
  if (!rows.length)
    return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
  return `
        <div class="home-facts">
            ${rows.map((row) => `
                <article class="home-facts__item">
                    <span class="home-facts__label">${escapeHtml(row.label || "")}</span>
                    <div class="home-facts__body">
                        <strong>${escapeHtml(row.value || "")}</strong>
                        ${row.meta ? `<p>${escapeHtml(row.meta)}</p>` : ""}
                    </div>
                    ${row.side ? `<span class="home-facts__side">${escapeHtml(row.side)}</span>` : ""}
                </article>
            `).join("")}
        </div>
    `;
}
function trimHandmadeCopy(value, max = 36, fallback = "") {
  const text = getPreferredText(value, fallback).replace(/\s+/g, " ").trim();
  if (!text)
    return fallback;
  if (text.length <= max)
    return text;
  return `${text.slice(0, Math.max(1, max - 1)).trim()}…`;
}
function renderHomeCoverTitle(text = "") {
  const chars = Array.from(String(text || "").trim());
  if (!chars.length)
    return "<span>关系</span><span>总览</span>";
  if (chars.length === 1)
    return `<span>${escapeHtml(chars[0])}</span>`;
  const firstLen = chars.length <= 2 ? 1 : Math.ceil(chars.length / 2);
  const lines = [
    chars.slice(0, firstLen).join(""),
    chars.slice(firstLen).join("")
  ].filter(Boolean);
  return lines.map((line) => `<span>${escapeHtml(line)}</span>`).join("");
}
function clientIntentLabel(intent) {
  return {
    daily: "日常",
    emergency: "急救",
    crisis: "高风险",
    reflection: "复盘"
  }[intent] || "日常";
}
function handmadeCoverVisual({ score = "--", scene = "calm", mode = "home", caption = "关系片段", marker = "QJ" } = {}) {
  const paletteMap = {
    calm: {
      bgA: "#fff9f2",
      bgB: "#f4e9de",
      paperA: "#f3d5c3",
      paperB: "#d7e5db",
      paperC: "#fffaf6",
      accent: "#cb7a59",
      soft: "#7fa193",
      glow: "#ffffff"
    },
    watch: {
      bgA: "#fff8f1",
      bgB: "#f4e5da",
      paperA: "#f0c4ab",
      paperB: "#ecd6bf",
      paperC: "#fff9f5",
      accent: "#be6b48",
      soft: "#b28958",
      glow: "#fff4ea"
    },
    repair: {
      bgA: "#fff8f3",
      bgB: "#efe7e0",
      paperA: "#efc6bc",
      paperB: "#d6e2da",
      paperC: "#fffaf7",
      accent: "#b8604c",
      soft: "#7c9d90",
      glow: "#fff7f0"
    }
  };
  const palette = paletteMap[scene] || paletteMap.calm;
  const scoreLabel = mode === "report" ? "本期得分" : "当前节奏";
  return `
        <div class="paper-scene paper-scene--${escapeHtml(mode)} paper-scene--${escapeHtml(scene)}" aria-hidden="true">
            <svg class="paper-scene__art" viewBox="0 0 460 320" role="presentation">
                <defs>
                    <linearGradient id="paper-scene-bg-${mode}-${scene}" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stop-color="${palette.bgA}"></stop>
                        <stop offset="100%" stop-color="${palette.bgB}"></stop>
                    </linearGradient>
                    <radialGradient id="paper-scene-glow-${mode}-${scene}" cx="72%" cy="18%" r="62%">
                        <stop offset="0%" stop-color="${palette.glow}" stop-opacity="0.95"></stop>
                        <stop offset="100%" stop-color="${palette.glow}" stop-opacity="0"></stop>
                    </radialGradient>
                </defs>
                <rect x="16" y="16" width="428" height="288" rx="38" fill="url(#paper-scene-bg-${mode}-${scene})" stroke="rgba(159,121,100,0.14)"></rect>
                <circle cx="334" cy="94" r="112" fill="url(#paper-scene-glow-${mode}-${scene})"></circle>
                <rect x="86" y="76" width="132" height="154" rx="30" transform="rotate(-8 86 76)" fill="${palette.paperA}" opacity="0.96"></rect>
                <rect x="224" y="62" width="142" height="168" rx="34" transform="rotate(8 224 62)" fill="${palette.paperB}" opacity="0.92"></rect>
                <rect x="152" y="54" width="144" height="182" rx="32" fill="${palette.paperC}" stroke="rgba(159,121,100,0.14)"></rect>
                <path d="M78 246C136 178 188 146 238 146C292 146 348 178 390 246" stroke="${palette.accent}" stroke-width="8" stroke-linecap="round"></path>
                <circle cx="224" cy="138" r="38" fill="#fff3ea" stroke="rgba(198,124,90,0.18)"></circle>
                <path d="M224 118v40" stroke="${palette.accent}" stroke-width="4" stroke-linecap="round"></path>
                <path d="M204 138h40" stroke="${palette.accent}" stroke-width="4" stroke-linecap="round"></path>
                <circle cx="224" cy="224" r="22" fill="#fffaf6" stroke="rgba(159,121,100,0.12)"></circle>
                <path d="M212 224h24" stroke="${palette.soft}" stroke-width="4" stroke-linecap="round"></path>
            </svg>
            <div class="paper-scene__stamp">
                <img src="assets/brand-logo.jpg" alt="">
                <span>${escapeHtml(caption)}</span>
            </div>
            <div class="paper-scene__score">
                <span>${escapeHtml(scoreLabel)}</span>
                <strong>${escapeHtml(String(score))}</strong>
            </div>
            <div class="paper-scene__marker">${escapeHtml(marker)}</div>
        </div>
    `;
}
function resolveEditorialScene({ riskLevel = "none", hasReport = false, bothDone = false, myDone = false } = {}) {
  if (riskLevel === "high" || riskLevel === "watch")
    return "watch";
  if (hasReport || bothDone)
    return "repair";
  if (myDone)
    return "calm";
  return "calm";
}
function buildHomePosterTitle({ hasReport = false, bothDone = false, myDone = false, riskLevel = "none", solo = false } = {}) {
  if (riskLevel === "high" || riskLevel === "watch")
    return solo ? "先缓下来。" : "先缓下来。";
  if (hasReport)
    return solo ? "先读懂，再往下走。" : "先读懂，再靠近。";
  if (bothDone)
    return "判断已经开始成形。";
  if (myDone)
    return "你已经先走了一步。";
  return solo ? "先写下今天。" : "先留下这一句。";
}
function buildHomePosterLead({ hasReport = false, bothDone = false, myDone = false, latestInsight = "", nextAction = "", solo = false } = {}) {
  if (hasReport)
    return trimHandmadeCopy(latestInsight, 24, solo ? "先回看今天。" : "先把主结论读清楚。");
  if (bothDone)
    return "材料已经够了，判断会开始成形。";
  if (myDone)
    return solo ? "你已经开始了，接着补一句就够。" : "你已经先走了一步，现在先别急着一次说完。";
  return trimHandmadeCopy(nextAction, 22, solo ? "哪怕只写一句，也够开始。" : "先留下一句真实的话。");
}
function renderStatusLine(items = []) {
  const validItems = items.filter(Boolean);
  if (!validItems.length)
    return "";
  return `
        <section class="editorial-statusline">
            ${validItems.map((item) => `
                <article class="editorial-statusline__item">
                    <span>${escapeHtml(item.label || "")}</span>
                    <strong>${escapeHtml(item.value || "")}</strong>
                </article>
            `).join("")}
        </section>
    `;
}
function renderHomeRiver(items = [], { primaryAction = "", primaryLabel = "进入时间线", secondaryAction = "", secondaryLabel = "" } = {}) {
  const moments = Array.isArray(items) ? items.filter(Boolean).slice(0, 3) : [];
  const [featured, ...rest] = moments;
  if (!featured) {
    return `
            <section class="mono-river mono-river--empty">
                <p class="mono-river__eyebrow">最近发生了什么</p>
                <strong class="mono-river__headline">先留下今天这一句，这条线就会开始出现。</strong>
                <div class="stage-surface__actions mono-river__actions">
                    <button class="button button--primary" type="button" onclick="showPage('checkin')">去写今天</button>
                </div>
            </section>
        `;
  }
  return `
        <section class="mono-river">
            <div class="mono-river__header">
                <p class="mono-river__eyebrow">最近发生了什么</p>
                <strong class="mono-river__headline">${escapeHtml(trimHandmadeCopy(featured.title || "", 24, "最近事件"))}</strong>
            </div>
            <div class="mono-river__line">
                <article class="mono-river__moment mono-river__moment--featured">
                    <span>${escapeHtml(featured.date || "最近")}</span>
                    <p>${escapeHtml(trimHandmadeCopy(featured.meta || "", 34, "先把这一段看清楚。"))}</p>
                </article>
                ${rest.map((item, index) => `
                    <article class="mono-river__moment">
                        <span>${escapeHtml(item.date || `0${index + 2}`)}</span>
                        <strong>${escapeHtml(trimHandmadeCopy(item.title || "", 14, "继续看下去"))}</strong>
                    </article>
                `).join("")}
            </div>
            <div class="stage-surface__actions mono-river__actions">
                <button class="button button--secondary" type="button" onclick="${primaryAction}">${escapeHtml(primaryLabel)}</button>
                ${secondaryAction && secondaryLabel ? `<button class="button button--ghost" type="button" onclick="${secondaryAction}">${escapeHtml(secondaryLabel)}</button>` : ""}
            </div>
        </section>
    `;
}
function renderReportEvidenceLine(timelineData = {}, evidenceSummary = []) {
  const events = Array.isArray(timelineData == null ? void 0 : timelineData.events) ? timelineData.events.slice(0, 3) : [];
  const items = events.length ? events.map((event) => ({
    date: (event == null ? void 0 : event.occurred_at) || (event == null ? void 0 : event.created_at) || (event == null ? void 0 : event.date) ? formatDateOnly(event.occurred_at || event.created_at || event.date) : (event == null ? void 0 : event.relative_time) || "最近",
    title: (event == null ? void 0 : event.title) || (event == null ? void 0 : event.headline) || (event == null ? void 0 : event.summary) || "关系事件",
    meta: (event == null ? void 0 : event.impact_summary) || (event == null ? void 0 : event.description) || (event == null ? void 0 : event.next_step) || ""
  })) : (evidenceSummary || []).slice(0, 3).map((item, index) => ({
    date: `0${index + 1}`,
    title: item,
    meta: ""
  }));
  if (!items.length) {
    return '<div class="section-empty">还没有足够的证据回放，继续记录后这里会出现真正的线索。</div>';
  }
  const featuredMeta = trimHandmadeCopy(items[0].meta || "", 44, "先把这个节点放回时间里看。");
  return `
        <div class="mono-evidence">
            <article class="mono-evidence__featured">
                <span>${escapeHtml(items[0].date || "最近")}</span>
                <strong>${escapeHtml(trimHandmadeCopy(items[0].title || "", 24, "关系片段"))}</strong>
                <p>${escapeHtml(featuredMeta)}</p>
            </article>
            <div class="mono-evidence__trail">
                ${items.slice(1).map((item) => `
                    <article class="mono-evidence__item">
                        <span>${escapeHtml(item.date || "随后")}</span>
                        <strong>${escapeHtml(trimHandmadeCopy(item.title || "", 16, "继续看下去"))}</strong>
                    </article>
                `).join("")}
            </div>
        </div>
    `;
}
function handmadeCompactClientGlance() {
  const precheck = state == null ? void 0 : state.lastClientPrecheck;
  const prefs = typeof currentProductPrefs === "function" ? currentProductPrefs() : { privacyMode: "cloud", aiAssistEnabled: true };
  const summary = precheck ? trimHandmadeCopy(typeof buildClientGuidance === "function" ? buildClientGuidance(precheck) : "", 34, "本地预检已完成。") : trimHandmadeCopy((state == null ? void 0 : state.lastClientPrecheckGuidance) || "", 34, "输入后会先做本地保护。");
  const piiItems = typeof summarizeClientPii === "function" ? summarizeClientPii((precheck == null ? void 0 : precheck.pii_summary) || {}) : [];
  const pills = [];
  pills.push(`路径 ${clientIntentLabel((precheck == null ? void 0 : precheck.intent) || "daily")}`);
  pills.push(`隐私 ${prefs.privacyMode === "local_first" ? "本地优先" : "云端保护"}`);
  if ((precheck == null ? void 0 : precheck.risk_level) && precheck.risk_level !== "none") {
    pills.push(`风险 ${precheck.risk_level}`);
  } else if (piiItems.length) {
    pills.push(`脱敏 ${trimHandmadeCopy(piiItems[0], 10)}`);
  } else if (Number((state == null ? void 0 : state.localDraftCount) || 0) > 0) {
    pills.push(`草稿 ${state.localDraftCount} 条`);
  }
  return `
        <section class="home-client-glance">
            <p class="home-client-glance__eyebrow">本地即时判断</p>
            <strong class="home-client-glance__title">${escapeHtml((precheck == null ? void 0 : precheck.degraded) ? "已切换云端保护" : precheck ? "先替你看一眼" : "等待输入")}</strong>
            <p class="home-client-glance__summary">${escapeHtml(summary)}</p>
            <div class="home-client-glance__pills">
                ${pills.slice(0, 3).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
            </div>
        </section>
    `;
}
function formatArchiveStatusLabel(status) {
  if (!status || status === "completed")
    return "已完成";
  if (status === "pending")
    return "生成中";
  if (status === "failed")
    return "失败";
  return status;
}
function handmadeTrend(trendData, options = {}) {
  const isSolo = Boolean(options.solo);
  const points = (trendData == null ? void 0 : trendData.trend) || [];
  if (points.length < 2) {
    return `<div class="section-empty">${isSolo ? "再多记录几次，个人趋势就会出现。" : "再多记录几次，关系趋势就会出现。"}</div>`;
  }
  const width = 320;
  const height = 110;
  const pad = 12;
  const coords = points.map((point, index) => {
    const x = pad + index / Math.max(points.length - 1, 1) * (width - pad * 2);
    const y = height - pad - (point.score || 0) / 100 * (height - pad * 2);
    return { x, y };
  });
  const line = coords.map((point) => `${point.x},${point.y}`).join(" ");
  const directionLabel = {
    improving: "慢慢变好",
    stable: "整体平稳",
    declining: "需要留意",
    insufficient_data: "还在形成中"
  }[trendData == null ? void 0 : trendData.direction] || "还在形成中";
  return `
        <div class="trend-ribbon">
            <div class="trend-ribbon__meta">
                <span>${isSolo ? "情绪走势" : "关系走势"}</span>
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
                ${coords.map((point) => `<circle cx="${point.x}" cy="${point.y}" r="4.5" fill="#fff8f2" stroke="#d68463" stroke-width="2"></circle>`).join("")}
            </svg>
        </div>
    `;
}
function renderHandmadeReportHero(report, options = {}) {
  const isSolo = Boolean(options.solo);
  const reportType = options.reportType || state.selectedReportType;
  const reportLabel = formatReportType(reportType, { solo: isSolo });
  const content = (report == null ? void 0 : report.content) || {};
  const score = Math.max(1, Math.min(100, content.health_score || content.overall_health_score || 72));
  const primaryInsight = content.insight || content.self_insight || content.executive_summary || "系统已经整理好这段时间最值得先读的一句判断。";
  const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || "";
  const encouragement = content.encouragement || content.relationship_note || "";
  const focusText = content.focus || content.current_focus || content.key_question || content.problem_statement || "先把这段关系里最容易被忽略的一件事看清楚。";
  const reportDate = formatDateOnly((report == null ? void 0 : report.report_date) || new Date().toISOString());
  const nextAction = suggestion || "先把最想说的一句话说清楚，再决定要不要继续展开。";
  const trimmedInsight = trimHandmadeCopy(primaryInsight, 42, "这期简报已经整理好最值得先读的一句。");
  const trimmedFocus = trimHandmadeCopy(focusText, 20, "先看清这一步。");
  const trimmedAction = trimHandmadeCopy(nextAction, 20, "先把一句话说清楚。");
  const actionButtons = isSolo ? `<button class="button button--secondary" type="button" onclick="showPage('checkin')">今日记录</button>
           <button class="button button--ghost" type="button" onclick="showPage('timeline')">时间轴</button>` : `<button class="button button--secondary" type="button" onclick="openMessageSimulator()">预演</button>
           <button class="button button--ghost" type="button" onclick="openNarrativeAlignment()">对齐</button>
           <button class="button button--ghost" type="button" onclick="showPage('timeline')">时间轴</button>`;
  return `
        <section class="report-cover">
            <div class="report-cover__score">
                <span>${score}</span>
                <small>/100</small>
            </div>
            <div class="report-cover__body">
                <div class="report-cover__topline">
                    <p class="report-cover__eyebrow">${isSolo ? "个人简报" : "关系简报"}</p>
                    <span class="report-cover__date">${escapeHtml(reportDate)}</span>
                </div>
                <h3>${escapeHtml(reportLabel)}</h3>
                <p class="report-cover__lead">${escapeHtml(trimmedInsight)}</p>
                <div class="report-cover__summary-strip">
                    <span>现在</span>
                    <strong>${escapeHtml(trimmedFocus)}</strong>
                </div>
                <div class="report-cover__summary-strip report-cover__summary-strip--secondary">
                    <span>下一步</span>
                    <strong>${escapeHtml(trimmedAction)}</strong>
                </div>
                ${encouragement ? `<blockquote class="report-cover__note">${escapeHtml(encouragement)}</blockquote>` : ""}
                <div class="report-cover__actions">
                    ${actionButtons}
                </div>
            </div>
        </section>
    `;
}
function getPreferredText(value, fallback = "") {
  const raw = String(value != null ? value : "").trim();
  if (!raw || /^[?？]+$/.test(raw))
    return fallback;
  return raw;
}
function getPreferredUserName(user) {
  const emailPrefix = getPreferredText(((user == null ? void 0 : user.email) || "").split("@")[0], "");
  const phoneDigits = String((user == null ? void 0 : user.phone) || "").replace(/\D/g, "");
  return getPreferredText(user == null ? void 0 : user.nickname, "") || emailPrefix || (phoneDigits.length >= 4 ? `用户${phoneDigits.slice(-4)}` : "你");
}
function getVisibleEmailLabel(user, fallback = "未填写邮箱") {
  const raw = getPreferredText(user == null ? void 0 : user.email, "");
  if (isDemoMode() && raw)
    return "样例邮箱已隐藏";
  return raw || fallback;
}
function setHandmadePanelVisibility(selector, visible) {
  const el = $(selector);
  if (el)
    el.classList.toggle("handmade-panel-hidden", !visible);
}
function handmadeRoute({ eyebrow = "今日路线", title = "", lead = "", badge = "", steps = [], note = "" } = {}) {
  return `
        <section class="route-board">
            <div class="route-board__head">
                <div>
                    <p class="editorial-section__eyebrow">${escapeHtml(eyebrow)}</p>
                    <h4 class="route-board__title">${escapeHtml(title)}</h4>
                </div>
                ${badge ? `<span class="route-board__badge">${escapeHtml(badge)}</span>` : ""}
            </div>
            ${lead ? `<p class="route-board__lead">${escapeHtml(lead)}</p>` : ""}
            <div class="route-board__steps">
                ${steps.map((step, index) => `
                    <article class="route-step route-step--${escapeHtml(step.status || "pending")}">
                        <span class="route-step__index">${index + 1}</span>
                        <div class="route-step__body">
                            ${step.label ? `<span class="route-step__label">${escapeHtml(step.label)}</span>` : ""}
                            <strong class="route-step__title">${escapeHtml(step.title || "")}</strong>
                            ${step.meta ? `<p class="route-step__meta">${escapeHtml(step.meta)}</p>` : ""}
                        </div>
                    </article>
                `).join("")}
            </div>
            ${note ? `<div class="route-board__note">${escapeHtml(note)}</div>` : ""}
        </section>
    `;
}
function handmadeTimeline(items = [], emptyText = "这里还没有时间线内容。") {
  if (!items.length)
    return `<div class="section-empty">${escapeHtml(emptyText)}</div>`;
  return `<div class="timeline-river">${items.map((item) => `
        <article class="timeline-river__item">
            <span class="timeline-river__date">${escapeHtml(item.date || item.kicker || "")}</span>
            <div class="timeline-river__body">
                <strong>${escapeHtml(item.title || "")}</strong>
                ${item.meta ? `<p>${escapeHtml(item.meta)}</p>` : ""}
            </div>
        </article>
    `).join("")}</div>`;
}
function handmadeSheet(eyebrow, title, rows = []) {
  return `
        <section class="profile-sheet">
            <p class="profile-sheet__eyebrow">${escapeHtml(eyebrow)}</p>
            <h5 class="profile-sheet__title">${escapeHtml(title)}</h5>
            <div class="profile-sheet__rows">
                ${rows.map((row) => `
                    <article class="profile-sheet__row">
                        <span>${escapeHtml(row.label || "")}</span>
                        <strong>${escapeHtml(row.value || "")}</strong>
                        ${row.meta ? `<p>${escapeHtml(row.meta)}</p>` : ""}
                    </article>
                `).join("")}
            </div>
        </section>
    `;
}
function handmadeHeroPanel({ eyebrow = "", title = "", body = "", rows = [] } = {}) {
  return `
        <aside class="stage-surface__panel">
            ${eyebrow ? `<p class="stage-surface__panel-eyebrow">${escapeHtml(eyebrow)}</p>` : ""}
            ${title ? `<h4 class="stage-surface__panel-title">${escapeHtml(title)}</h4>` : ""}
            ${body ? `<p class="stage-surface__panel-body">${escapeHtml(body)}</p>` : ""}
            ${rows.length ? `<div class="stage-surface__panel-list">${rows.map((row) => `
                <article class="stage-surface__panel-item">
                    <span>${escapeHtml(row.label || "")}</span>
                    <strong>${escapeHtml(row.value || "")}</strong>
                </article>
            `).join("")}</div>` : ""}
        </aside>
    `;
}
function buildHomeTimelineItems(payload = {}) {
  var _a;
  const events = Array.isArray((_a = payload.timeline) == null ? void 0 : _a.events) ? payload.timeline.events : [];
  if (events.length) {
    return events.slice(0, 5).map((event) => ({
      date: (event == null ? void 0 : event.occurred_at) || (event == null ? void 0 : event.created_at) || (event == null ? void 0 : event.date) ? formatDateOnly(event.occurred_at || event.created_at || event.date) : (event == null ? void 0 : event.relative_time) || "最近",
      title: (event == null ? void 0 : event.title) || (event == null ? void 0 : event.headline) || (event == null ? void 0 : event.summary) || (event == null ? void 0 : event.category_label) || "关系事件",
      meta: (event == null ? void 0 : event.impact_summary) || (event == null ? void 0 : event.next_step) || (event == null ? void 0 : event.description) || (event == null ? void 0 : event.tone_label) || "系统会继续把这条线索沉淀进后续判断里。"
    }));
  }
  const milestones = Array.isArray(payload.milestones) ? payload.milestones : [];
  return milestones.slice(0, 4).map((item) => ({
    date: (item == null ? void 0 : item.date) || (item == null ? void 0 : item.target_date) ? formatDateOnly(item.date || item.target_date) : "最近",
    title: (item == null ? void 0 : item.title) || "未命名节点",
    meta: milestoneTypeLabel(item == null ? void 0 : item.type)
  }));
}
function renderNoPairHome(payload = {}) {
  var _a;
  const todayStatus = payload.todayStatus || {};
  const myCheckin = todayStatus.my_checkin || {};
  const latestReport = payload.latestReport || null;
  const latestContent = (latestReport == null ? void 0 : latestReport.content) || {};
  const reportState = getSoloReportButtonState(todayStatus, latestReport);
  const hasCheckin = Boolean(todayStatus == null ? void 0 : todayStatus.my_done);
  const hasReadyReport = reportState.tone === "ready";
  const streakDays = ((_a = payload.streak) == null ? void 0 : _a.streak) || 0;
  const moodText = myCheckin.mood_score ? `${myCheckin.mood_score}/4` : "未记录";
  const interactionText = myCheckin.interaction_freq || myCheckin.interaction_freq === 0 ? `${myCheckin.interaction_freq} 次` : "未记录";
  const latestInsight = latestContent.insight || latestContent.self_insight || latestContent.encouragement || "先把今天的情绪留下一句，你就已经在认真照顾自己。";
  const latestSuggestion = latestContent.suggestion || latestContent.self_care_tip || "等你想好了，再把今天补成一句更完整的话。";
  const userName = getPreferredUserName(state.me);
  const scene = resolveEditorialScene({ hasReport: hasReadyReport, myDone: hasCheckin, bothDone: false, riskLevel: "none" });
  const posterTitle = buildHomePosterTitle({ hasReport: hasReadyReport, myDone: hasCheckin, solo: true });
  const posterLead = buildHomePosterLead({
    hasReport: hasReadyReport,
    myDone: hasCheckin,
    latestInsight,
    nextAction: latestSuggestion,
    solo: true
  });
  const riverItems = [
    {
      date: hasCheckin ? "今天" : "现在",
      title: hasCheckin ? "第一条记录已经落下" : "先留下一句真正的话",
      meta: hasCheckin ? "接下来可以继续补一句心里话，或者直接去读个人简报。" : "你不需要先绑定关系，先把自己照顾好也成立。"
    },
    {
      date: hasReadyReport ? "随后" : "记录后",
      title: hasReadyReport ? "个人简报已经可读" : "系统会自动整理成一页",
      meta: hasReadyReport ? trimHandmadeCopy(latestInsight, 42, "去读一遍，你会更清楚自己现在在哪。") : "不用额外准备，材料够了它就会出现。"
    },
    {
      date: "准备好时",
      title: "再把关系接进来",
      meta: "等你愿意，再邀请对方进入共享空间。"
    }
  ];
  safeSetText("#home-greeting", `${userName}，今天也适合把自己照顾好`);
  safeSetHtml("#home-overview", `
        <section class="home-poster home-poster--solo home-poster--${escapeHtml(scene)}">
            <div class="home-poster__copy">
                <p class="home-poster__kicker">单人模式 · 先照顾自己</p>
                <h3 class="home-poster__title">${escapeHtml(posterTitle)}</h3>
                <p class="home-poster__lead">${escapeHtml(posterLead)}</p>
                <div class="stage-surface__actions home-poster__actions">
                    <button class="button button--primary" type="button" onclick="${hasReadyReport ? "showPage('report')" : "openCheckinMode('form')"}">${hasReadyReport ? "去读个人简报" : "开始今日记录"}</button>
                    <button class="button button--ghost" type="button" onclick="${hasCheckin ? "openCheckinMode('voice')" : "showPage('pair')"}">${hasCheckin ? "语音补一句" : "准备好后再绑定"}</button>
                </div>
                <div class="home-poster__statusline">
                    ${renderStatusLine([
    { label: "连续记录", value: `${streakDays} 天` },
    { label: "当前状态", value: hasReadyReport ? "个人简报已就绪" : reportState.label }
  ])}
                </div>
            </div>
            <aside class="home-poster__visual">
                ${handmadeCoverVisual({ score: hasReadyReport ? latestContent.health_score || latestContent.overall_health_score || 76 : streakDays || "--", scene, mode: "home", caption: "个人阶段", marker: "SELF" })}
            </aside>
        </section>
    `);
  safeSetHtml("#home-metrics", "");
  safeSetHtml("#home-milestones-panel", renderHomeRiver(riverItems, {
    primaryAction: hasReadyReport ? "showPage('report')" : "openCheckinMode('form')",
    primaryLabel: hasReadyReport ? "去读个人简报" : "继续写今天",
    secondaryAction: hasCheckin ? "showPage('timeline')" : "showPage('pair')",
    secondaryLabel: hasCheckin ? "打开时间线" : "准备好后绑定"
  }));
  setHandmadePanelVisibility("#home-status-panel", true);
  setHandmadePanelVisibility("#home-report-panel", true);
  setHandmadePanelVisibility("#home-milestones-panel", true);
  setHandmadePanelVisibility("#home-tree-panel", false);
  setHandmadePanelVisibility("#home-crisis-panel", false);
  setHandmadePanelVisibility("#home-tasks-panel", false);
  state.notifications = Array.isArray(payload.notifications) ? payload.notifications : [];
  syncNotifications();
}
function renderHome(payload) {
  var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r, _s, _t, _u, _v, _w, _x, _y;
  state.homeSnapshot = payload;
  const pairName = getPartnerDisplayName(payload.pair);
  const focus = getHomeFocusConfig(payload);
  const playbook = payload.playbook || null;
  const crisis = payload.crisis || { crisis_level: "none" };
  const milestones = Array.isArray(payload.milestones) ? payload.milestones : [];
  const tasks = ((_a = payload.tasks) == null ? void 0 : _a.tasks) || [];
  const nextMilestone = milestones[0] || null;
  const latestContent = ((_b = payload.latestReport) == null ? void 0 : _b.content) || {};
  const latestScore = latestContent.health_score || latestContent.overall_health_score || "--";
  const latestInsight = latestContent.insight || latestContent.encouragement || latestContent.executive_summary || "等今天的记录足够完整，这里会出现真正有内容的简报结论。";
  const focusText = latestContent.suggestion || (playbook == null ? void 0 : playbook.branch_reason) || focus.description;
  const myStatusText = ((_c = payload.todayStatus) == null ? void 0 : _c.my_done) ? "你已完成今日记录" : "你还没开始";
  const cycleText = (playbook == null ? void 0 : playbook.current_day) && (playbook == null ? void 0 : playbook.total_days) ? `第 ${playbook.current_day}/${playbook.total_days} 天` : "待启动";
  const timelineItems = buildHomeTimelineItems(payload);
  const nextAction = focusText || "先把今天的原始片段留住，再决定下一步要不要推进。";
  const scene = resolveEditorialScene({
    riskLevel: crisis.crisis_level || "none",
    hasReport: Boolean((_d = payload.todayStatus) == null ? void 0 : _d.has_report),
    bothDone: Boolean((_e = payload.todayStatus) == null ? void 0 : _e.both_done),
    myDone: Boolean((_f = payload.todayStatus) == null ? void 0 : _f.my_done)
  });
  const relationLabel = `${TYPE_LABELS[payload.pair.type] || payload.pair.type} · ${pairName}`;
  const posterTitle = buildHomePosterTitle({
    hasReport: Boolean((_g = payload.todayStatus) == null ? void 0 : _g.has_report),
    bothDone: Boolean((_h = payload.todayStatus) == null ? void 0 : _h.both_done),
    myDone: Boolean((_i = payload.todayStatus) == null ? void 0 : _i.my_done),
    riskLevel: crisis.crisis_level || "none"
  });
  const posterLead = buildHomePosterLead({
    hasReport: Boolean((_j = payload.todayStatus) == null ? void 0 : _j.has_report),
    bothDone: Boolean((_k = payload.todayStatus) == null ? void 0 : _k.both_done),
    myDone: Boolean((_l = payload.todayStatus) == null ? void 0 : _l.my_done),
    latestInsight,
    nextAction
  });
  const secondaryAction = ((_m = payload.todayStatus) == null ? void 0 : _m.has_report) ? "showPage('timeline')" : ((_n = payload.todayStatus) == null ? void 0 : _n.my_done) ? "openCheckinMode('voice')" : "showPage('discover')";
  const secondaryLabel = ((_o = payload.todayStatus) == null ? void 0 : _o.has_report) ? "打开时间线" : ((_p = payload.todayStatus) == null ? void 0 : _p.my_done) ? "语音补一句" : "看总览";
  const currentStateLine = ((_q = payload.todayStatus) == null ? void 0 : _q.has_report) ? "这一期已经可以读了。" : ((_r = payload.todayStatus) == null ? void 0 : _r.both_done) ? "判断正在开始成形。" : myStatusText;
  const riverItems = timelineItems.length ? timelineItems : [
    {
      date: ((_s = payload.todayStatus) == null ? void 0 : _s.my_done) ? "今天" : "现在",
      title: ((_t = payload.todayStatus) == null ? void 0 : _t.my_done) ? "你已经把自己的这一句留下了" : "先把今天这一句留下来",
      meta: ((_u = payload.todayStatus) == null ? void 0 : _u.my_done) ? "接下来不用一次谈完全部问题，先看系统会把什么整理出来。" : "哪怕只写一句，也比空白更有用。"
    },
    {
      date: ((_v = payload.todayStatus) == null ? void 0 : _v.has_report) ? "随后" : "接着",
      title: ((_w = payload.todayStatus) == null ? void 0 : _w.has_report) ? "这一期简报已经可读" : ((_x = payload.todayStatus) == null ? void 0 : _x.both_done) ? "系统会开始生成判断" : "等材料继续补齐",
      meta: ((_y = payload.todayStatus) == null ? void 0 : _y.has_report) ? trimHandmadeCopy(latestInsight, 42, "现在最适合先把主结论读清楚。") : trimHandmadeCopy(nextAction, 42, "页面会继续沿着这些材料推断。")
    },
    {
      date: "之后",
      title: "回到时间轴里看它怎么变成现在",
      meta: "把判断、证据和动作放回同一条线里去读。"
    }
  ];
  safeSetText("#home-greeting", "关系总览");
  safeSetHtml("#home-overview", `
        <section class="mono-home mono-home--${escapeHtml(scene)}">
            <div class="mono-home__copy">
                <p class="mono-home__kicker">${escapeHtml(relationLabel)}</p>
                <h3 class="mono-home__title">${escapeHtml(posterTitle)}</h3>
                <p class="mono-home__lead">${escapeHtml(posterLead)}</p>
                <div class="stage-surface__actions mono-home__actions">
                    <button class="button button--primary" type="button" onclick="${focus.primaryAction}">${focus.primaryLabel}</button>
                    <button class="button button--ghost" type="button" onclick="${secondaryAction}">${secondaryLabel}</button>
                </div>
                <div class="mono-home__glance">
                    <article>
                        <span>现在</span>
                        <strong>${escapeHtml(currentStateLine)}</strong>
                    </article>
                    <article>
                        <span>下一步</span>
                        <strong>${escapeHtml(trimHandmadeCopy(nextAction, 18, "先把一句话说清楚。"))}</strong>
                    </article>
                </div>
            </div>
            <aside class="mono-home__visual">
                ${handmadeCoverVisual({
    score: latestScore,
    scene,
    mode: "home",
    caption: cycleText,
    marker: (TYPE_LABELS[payload.pair.type] || payload.pair.type || "PAIR").slice(0, 4).toUpperCase()
  })}
            </aside>
        </section>
    `);
  safeSetHtml("#home-metrics", "");
  safeSetHtml("#home-tasks-panel", "");
  safeSetHtml("#home-milestones-panel", renderHomeRiver(riverItems, {
    primaryAction: "showPage('timeline')",
    primaryLabel: "进入时间线",
    secondaryAction: "openNarrativeAlignment()",
    secondaryLabel: "双视角对齐"
  }));
  setHandmadePanelVisibility("#home-status-panel", true);
  setHandmadePanelVisibility("#home-report-panel", true);
  setHandmadePanelVisibility("#home-tasks-panel", false);
  setHandmadePanelVisibility("#home-milestones-panel", true);
  setHandmadePanelVisibility("#home-tree-panel", false);
  setHandmadePanelVisibility("#home-crisis-panel", false);
  state.notifications = Array.isArray(payload.notifications) ? payload.notifications : payload.notifications || [];
  syncNotifications();
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
  const [latest, history, trend, today, policyAudit] = await Promise.allSettled([
    api.getLatestReport(pairId, reportType),
    api.getReportHistory(pairId, reportType, 6),
    api.getHealthTrend(pairId, 14),
    api.getTodayStatus(pairId),
    api.getPolicyDecisionAudit(pairId)
  ]);
  const latestReport = unwrapResult(latest, null);
  const todayStatus = unwrapResult(today, {});
  const planPolicyAudit = unwrapResult(policyAudit, null);
  const button = $("#report-generate-btn");
  const soloButton = getSoloReportButtonState(todayStatus, latestReport);
  state.reportSnapshot = { isSolo, reportType, latestReport, todayStatus, planPolicyAudit };
  if (button) {
    button.textContent = isSolo ? soloButton.label : "刷新这期";
    button.disabled = isSolo ? soloButton.disabled : false;
  }
  renderReport(latestReport, unwrapResult(history, []), unwrapResult(trend, { trend: [] }), { solo: isSolo, reportType, planPolicyAudit });
}
function renderReport(report, history, trendData, options = {}) {
  const isSolo = Boolean(options.solo);
  const reportType = options.reportType || state.selectedReportType;
  const reportLabel = formatReportType(reportType, { solo: isSolo });
  const policyAuditPanel = renderPolicyDecisionAudit(options.planPolicyAudit, { solo: isSolo });
  if (report && report.status === "pending") {
    safeSetHtml("#report-main", `<section class="editorial-section"><div class="section-empty">${reportLabel} 正在后台生成中。它会比即时结果更像一份能回看的编辑稿。</div></section>`);
  } else if (report && report.status === "failed") {
    safeSetHtml("#report-main", `<section class="editorial-section"><div class="section-empty">${reportLabel} 这次生成失败了。稍后再试一次，通常就会恢复。</div></section>`);
  } else if (!report || report.status !== "completed") {
    safeSetHtml("#report-main", `<section class="editorial-section"><div class="section-empty">这里还没有可展示的${reportLabel}。先把今天写清楚，再回来读一份真正有内容的简报。</div></section>`);
  } else {
    const content = report.content || {};
    const score = content.health_score || content.overall_health_score || 72;
    const primaryInsight = content.insight || content.self_insight || content.executive_summary || "系统已经替你把这一阶段的关系脉络整理好了。";
    const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || "";
    const encouragement = content.encouragement || content.relationship_note || "";
    const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
    const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);
    safeSetHtml("#report-main", `
            <section class="brief-stage">
                <div class="brief-stage__score"><span>${Math.max(1, Math.min(100, score))}</span><small>/100</small></div>
                <div class="brief-stage__copy">
                    <p class="brief-stage__eyebrow">${isSolo ? "个人简报" : "关系简报"}</p>
                    <h4>${reportLabel}</h4>
                    <p>${escapeHtml(primaryInsight)}</p>
                </div>
            </section>
            ${handmadeLedger([
      { label: "一句结论", value: primaryInsight, meta: "这是一份给人读的，不只是给系统看的分数。" },
      { label: "下一步动作", value: suggestion || concerns[0] || "继续把真实感受说清楚", meta: "越小的动作，越容易在日常里持续。" },
      { label: "报告日期", value: report.report_date || formatDateOnly(new Date().toISOString()), meta: isSolo ? "个人视角" : "双人关系视角" }
    ])}
            <section class="brief-columns">
                <div class="brief-column">
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">高光</p><h4 class="editorial-section__title">积极信号</h4></div></div>
                        ${handmadeList(highlights, "目前还没有明显高亮项，继续记录会让这部分更清楚。")}
                    </section>
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">留意</p><h4 class="editorial-section__title">需要关注</h4></div></div>
                        ${handmadeList(concerns, "目前没有额外提醒，继续保持稳定节奏就好。")}
                    </section>
                </div>
                <div class="brief-column">
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">趋势</p><h4 class="editorial-section__title">近阶段走势</h4></div></div>
                        ${handmadeTrend(trendData, { solo: isSolo })}
                    </section>
                    ${suggestion ? `<div class="note-ribbon note-ribbon--warm"><strong>现在最适合做的</strong><p>${escapeHtml(suggestion)}</p></div>` : ""}
                </div>
            </section>
            ${encouragement ? `<blockquote class="brief-note">${escapeHtml(encouragement)}</blockquote>` : ""}
        `);
  }
  const list = $("#report-history-list");
  if (!list)
    return;
  if (!history.length) {
    list.innerHTML = '<div class="section-empty">现在还没有历史简报记录。</div>';
    return;
  }
  list.innerHTML = `<div class="archive-ledger">${history.map((item, index) => {
    const status = String(item.status || "pending").toLowerCase();
    const statusLabel = formatArchiveStatusLabel(item.status);
    const reportDate = item.report_date ? formatDateOnly(item.report_date) : "未命名日期";
    return `
        <article class="archive-ledger__item archive-ledger__item--${escapeHtml(status)}">
            <div class="archive-ledger__body">
                <span class="archive-ledger__index">附录 ${escapeHtml(String(index + 1).padStart(2, "0"))}</span>
                <strong>${formatReportType(item.type || reportType, { solo: isSolo })}</strong>
                <p>${escapeHtml(reportDate)}</p>
            </div>
            <span class="archive-ledger__status">${escapeHtml(statusLabel)}</span>
        </article>
    `;
  }).join("")}</div>`;
}
async function loadProfilePage() {
  if (!api.isLoggedIn()) {
    safeSetHtml("#profile-summary", `<section class="stage-surface"><p class="stage-surface__eyebrow">我的</p><h3 class="stage-surface__title">请先登录</h3><p class="stage-surface__body">登录后这里会显示你的账号信息和当前关系状态。</p></section>`);
    safeSetHtml("#profile-account-panel", '<div class="section-empty">登录后可查看账户资料。</div>');
    safeSetHtml("#profile-pair-panel", '<div class="section-empty">登录后可查看当前关系状态。</div>');
    safeSetHtml("#profile-relations-panel", '<div class="section-empty">登录后可查看全部关系列表和多关系切换入口。</div>');
    setHandmadePanelVisibility("#profile-account-panel", true);
    setHandmadePanelVisibility("#profile-pair-panel", false);
    setHandmadePanelVisibility("#profile-relations-panel", true);
    return;
  }
  const me = state.me || await api.getMe();
  state.me = me;
  const pair = state.currentPair;
  const allPairs = state.pairs || [];
  const activePairs = allPairs.filter((item) => item.status === "active");
  const pendingPairs = allPairs.filter((item) => item.status === "pending");
  const unbindStatus = pair ? await api.getUnbindStatus(pair.id).catch(() => ({ has_request: false })) : { has_request: false };
  const userName = getPreferredUserName(me);
  safeSetHtml("#profile-summary", `
        <section class="stage-surface stage-surface--profile">
            <p class="stage-surface__eyebrow">我的</p>
            <h3 class="stage-surface__title">${escapeHtml(userName)}</h3>
            <p class="stage-surface__body">${escapeHtml(getVisibleEmailLabel(me))} · ${pair ? "当前已在一段关系里" : "当前还没有绑定关系"}</p>
            ${handmadeLedger([
    { label: "活跃关系", value: String(activePairs.length), meta: "可以在这里切换当前关系。" },
    { label: "待加入", value: String(pendingPairs.length), meta: "还在等待对方进入的关系。" },
    { label: "当前对象", value: pair ? getPartnerDisplayName(pair) : "未设置", meta: pair ? "这会影响首页和报告的默认视角。" : "准备好了再建立连接。" }
  ])}
            ${state.profileFeedback ? `<div class="note-ribbon"><strong>已同步更新</strong><p>${escapeHtml(state.profileFeedback)}</p></div>` : ""}
        </section>
    `);
  safeSetHtml("#profile-account-panel", `
        <section class="editorial-section editorial-section--profile-grid">
            <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">身份</p><h4 class="editorial-section__title">身份与关系</h4></div></div>
            <div class="profile-columns">
                ${handmadeSheet("账户", "账户", [
    { label: "昵称", value: userName, meta: "三端会共用这份名称。" },
    { label: "邮箱", value: getVisibleEmailLabel(me, "未绑定"), meta: "当前主登录方式。" },
    { label: "手机号", value: maskPhone(me.phone), meta: "用于验证码登录时显示。" },
    { label: "登录渠道", value: getAccountChannels(me), meta: "决定你从哪里进入。" },
    { label: "创建时间", value: formatDateOnly(me.created_at), meta: `账户编号：${String(me.id).slice(0, 8).toUpperCase()}` }
  ])}
                ${handmadeSheet("关系", pair ? "当前关系" : "关系状态", pair ? [
    { label: "对象", value: getPartnerDisplayName(pair), meta: `创建于 ${formatDateOnly(pair.created_at)}` },
    { label: "关系类型", value: TYPE_LABELS[pair.type] || pair.type, meta: pair.status === "active" ? "当前已激活" : "还在等待加入" },
    { label: "邀请码", value: pair.invite_code || "无", meta: "可以直接发给对方。" },
    { label: "解绑状态", value: unbindStatus.has_request ? unbindStatus.requested_by_me ? `你已发起，还剩 ${unbindStatus.days_remaining} 天` : "对方已发起解绑" : "当前没有进行中申请", meta: "边界感和关系管理都应在这里被看见。" }
  ] : [
    { label: "当前状态", value: "未绑定关系", meta: "你可以继续用单人模式，不必被流程推着走。" },
    { label: "下一步", value: "准备好再邀请对方", meta: "真正愿意时，再把关系接进来。" }
  ])}
            </div>
            <div class="profile-action-list">
                <button class="profile-action" type="button" onclick="openProfileEditor()" aria-label="修改名称"><span>${svgIcon("i-edit")}</span><div><strong>修改名称</strong><p>当前昵称：${escapeHtml(userName)}</p></div><span>进入</span></button>
                <button class="profile-action" type="button" onclick="openPasswordEditor()" aria-label="修改密码"><span>${svgIcon("i-lock")}</span><div><strong>修改密码</strong><p>保护关系数据和账号安全，建议定期更新。</p></div><span>进入</span></button>
                ${pair ? `<button class="profile-action" type="button" onclick="openPartnerNicknameEditor()" aria-label="编辑对方备注"><span>${svgIcon("i-heart")}</span><div><strong>设置对方备注</strong><p>${escapeHtml(pair.custom_partner_nickname || "现在还没有备注名")}</p></div><span>进入</span></button>
                       <button class="profile-action" type="button" onclick="openUnbindPanel()" aria-label="管理解绑状态"><span>${svgIcon("i-refresh")}</span><div><strong>解绑与边界</strong><p>把取消、确认和等待都放到清楚的流程里。</p></div><span>进入</span></button>` : `<button class="profile-action" type="button" onclick="showPage('pair')" aria-label="建立关系"><span>${svgIcon("i-link")}</span><div><strong>去建立关系</strong><p>继续单人模式也可以，准备好了再邀请对方。</p></div><span>进入</span></button>`}
            </div>
        </section>
    `);
  safeSetHtml("#profile-pair-panel", "");
  safeSetHtml("#profile-relations-panel", `
        <section class="editorial-section">
            <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">关系</p><h4 class="editorial-section__title">全部关系</h4></div></div>
            <p class="editorial-section__note">所有关系都放在这里切换和管理。换一个关系，首页、记录和简报都会一起跟着切过去。</p>
            ${renderRelationManagementList(allPairs, (pair == null ? void 0 : pair.id) || null)}
            <div class="stage-surface__actions">
                <button class="button button--primary" type="button" onclick="showPage('pair')">新增或加入关系</button>
                <button class="button button--ghost" type="button" onclick="showPage('home')">回到首页</button>
            </div>
        </section>
    `);
  setHandmadePanelVisibility("#profile-account-panel", true);
  setHandmadePanelVisibility("#profile-pair-panel", false);
  setHandmadePanelVisibility("#profile-relations-panel", true);
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
  const [latest, history, trend, today, policyAudit] = await Promise.allSettled([
    api.getLatestReport(pairId, reportType),
    api.getReportHistory(pairId, reportType, 6),
    api.getHealthTrend(pairId, 14),
    api.getTodayStatus(pairId),
    api.getPolicyDecisionAudit(pairId)
  ]);
  const latestReport = unwrapResult(latest, null);
  const todayStatus = unwrapResult(today, {});
  const planPolicyAudit = unwrapResult(policyAudit, null);
  const button = $("#report-generate-btn");
  const soloButton = getSoloReportButtonState(todayStatus, latestReport);
  state.reportSnapshot = { isSolo, reportType, latestReport, todayStatus, planPolicyAudit };
  if (button) {
    button.textContent = isSolo ? soloButton.label : "刷新这期";
    button.disabled = isSolo ? soloButton.disabled : false;
  }
  renderReport(
    latestReport,
    unwrapResult(history, []),
    unwrapResult(trend, { trend: [] }),
    { solo: isSolo, reportType, planPolicyAudit }
  );
}
function renderReport(report, history, trendData, options = {}) {
  const isSolo = Boolean(options.solo);
  const reportType = options.reportType || state.selectedReportType;
  const reportLabel = formatReportType(reportType, { solo: isSolo });
  const policyAuditPanel = renderPolicyDecisionAudit(options.planPolicyAudit, { solo: isSolo });
  if (report && report.status === "pending") {
    safeSetHtml("#report-main", `<section class="editorial-section"><div class="section-empty">${reportLabel} 正在后台生成中，下方策略审计已经先整理出当前路径。</div></section>${policyAuditPanel}`);
  } else if (report && report.status === "failed") {
    safeSetHtml("#report-main", `<section class="editorial-section"><div class="section-empty">${reportLabel} 这次生成失败了。稍后再试，下方策略审计仍会说明当前策略。</div></section>${policyAuditPanel}`);
  } else if (!report || report.status !== "completed") {
    safeSetHtml("#report-main", `<section class="editorial-section"><div class="section-empty">当前还没有可展示的${reportLabel}，下方策略审计会先说明为什么系统正在维持或调整当前策略。</div></section>${policyAuditPanel}`);
  } else {
    const content = report.content || {};
    const score = content.health_score || content.overall_health_score || 72;
    const primaryInsight = content.insight || content.self_insight || content.executive_summary || "系统已经把这一阶段整理成一份可读的简报。";
    const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || "";
    const encouragement = content.encouragement || content.relationship_note || "";
    const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 4);
    const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 4);
    safeSetHtml("#report-main", `
            <section class="brief-stage">
                <div class="brief-stage__score"><span>${Math.max(1, Math.min(100, score))}</span><small>/100</small></div>
                <div class="brief-stage__copy">
                    <p class="brief-stage__eyebrow">${isSolo ? "个人简报" : "关系简报"}</p>
                    <h4>${reportLabel}</h4>
                    <p>${escapeHtml(primaryInsight)}</p>
                </div>
            </section>
            ${handmadeLedger([
      { label: "一句结论", value: primaryInsight, meta: "给人读的总结，而不只是给系统看的分数。" },
      { label: "下一步动作", value: suggestion || concerns[0] || "继续把真实感受说清楚", meta: "越小的动作，越容易在日常里持续。" },
      { label: "报告日期", value: report.report_date || formatDateOnly(new Date().toISOString()), meta: isSolo ? "个人视角" : "双人关系视角" }
    ])}
            <section class="brief-columns">
                <div class="brief-column">
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">高光</p><h4 class="editorial-section__title">积极信号</h4></div></div>
                        ${handmadeList(highlights, "目前还没有明显高亮项，继续记录会让这里更清楚。")}
                    </section>
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">留意</p><h4 class="editorial-section__title">需要关注</h4></div></div>
                        ${handmadeList(concerns, "目前没有额外提醒，继续保持稳定节奏就好。")}
                    </section>
                </div>
                <div class="brief-column">
                    <section class="editorial-section">
                        <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">趋势</p><h4 class="editorial-section__title">近阶段走势</h4></div></div>
                        ${handmadeTrend(trendData, { solo: isSolo })}
                    </section>
                    ${suggestion ? `<div class="note-ribbon note-ribbon--warm"><strong>现在最适合做的</strong><p>${escapeHtml(suggestion)}</p></div>` : ""}
                </div>
            </section>
            ${encouragement ? `<blockquote class="brief-note">${escapeHtml(encouragement)}</blockquote>` : ""}
            ${policyAuditPanel}
        `);
  }
  const list = $("#report-history-list");
  if (!list)
    return;
  if (!history.length) {
    list.innerHTML = '<div class="section-empty">现在还没有历史简报记录。</div>';
    return;
  }
  list.innerHTML = `<div class="archive-ledger">${history.map((item, index) => {
    const status = String(item.status || "pending").toLowerCase();
    const statusLabel = formatArchiveStatusLabel(item.status);
    const reportDate = item.report_date ? formatDateOnly(item.report_date) : "未命名日期";
    return `
        <article class="archive-ledger__item archive-ledger__item--${escapeHtml(status)}">
            <div class="archive-ledger__body">
                <span class="archive-ledger__index">附录 ${escapeHtml(String(index + 1).padStart(2, "0"))}</span>
                <strong>${formatReportType(item.type || reportType, { solo: isSolo })}</strong>
                <p>${escapeHtml(reportDate)}</p>
            </div>
            <span class="archive-ledger__status">${escapeHtml(statusLabel)}</span>
        </article>
    `;
  }).join("")}</div>`;
}
syncTopbar = function() {
  const compactPages = /* @__PURE__ */ new Set([
    "home",
    "checkin",
    "discover",
    "report",
    "profile",
    "milestones",
    "longdistance",
    "attachment-test",
    "health-test",
    "community",
    "challenges",
    "courses",
    "experts",
    "membership"
  ]);
  const compactTitleMap = {
    home: "总览",
    checkin: "记录",
    discover: "总览",
    report: "关系简报",
    profile: "我的",
    milestones: "时间线",
    longdistance: "异地",
    "attachment-test": "依恋",
    "health-test": "体检",
    community: "技巧",
    challenges: "挑战",
    courses: "课程",
    experts: "咨询",
    membership: "会员"
  };
  const fullTitleMap = {
    auth: "关系记录与提醒",
    pair: "先把关系连起来",
    "pair-waiting": "等待对方加入"
  };
  const fullSubtitleMap = {
    auth: "先看见关系，再决定怎么开口。",
    pair: "先把彼此放进同一个空间，再开始共同记录。",
    "pair-waiting": "邀请码已经准备好，差最后一步。"
  };
  const page = state.currentPage;
  const isCompact = compactPages.has(page);
  safeSetText("#topbar-title", isCompact ? compactTitleMap[page] || "亲健" : fullTitleMap[page] || "关系记录与提醒");
  safeSetText("#topbar-subtitle", isCompact ? "" : fullSubtitleMap[page] || "先看见关系，再决定怎么开口。");
  safeSetText("#topbar-caption", "亲健");
  const ritualButton = document.querySelector(".pill-button[data-jump-page], .pill-button");
  if (ritualButton) {
    const hiddenPages = /* @__PURE__ */ new Set(["auth", "pair", "pair-waiting"]);
    ritualButton.classList.toggle("hidden", hiddenPages.has(page));
    ritualButton.textContent = page === "checkin" ? "回总览" : "写记录";
    ritualButton.dataset.jumpPage = page === "checkin" ? "home" : "checkin";
  }
};
async function loadReportPage() {
  var _a;
  const pairId = ((_a = state.currentPair) == null ? void 0 : _a.id) || null;
  const isSolo = !pairId;
  if (isSolo && state.selectedReportType !== "daily") {
    state.selectedReportType = "daily";
  }
  syncReportTypeAvailability(isSolo);
  const reportType = isSolo ? "daily" : state.selectedReportType;
  const button = $("#report-generate-btn");
  if (isDemoMode()) {
    const latestReport2 = deepClone(getDemoFixture("latestReport") || null);
    const history2 = deepClone(getDemoFixture("reportHistory") || []);
    const trend2 = deepClone(getDemoFixture("healthTrend") || { trend: [] });
    const safetyStatus = deepClone(getDemoFixture("safetyStatus") || null);
    const assessmentTrend2 = deepClone(getDemoFixture("assessmentTrend") || null);
    const planPolicyAudit2 = deepClone(getDemoFixture("policyAudit") || null);
    const planScorecard = deepClone(getDemoFixture("scorecard") || null);
    const planPolicySchedule = deepClone(getDemoFixture("policySchedule") || null);
    const timeline2 = deepClone(getDemoFixture("timeline") || null);
    state.reportSnapshot = {
      isSolo,
      reportType,
      latestReport: latestReport2,
      todayStatus: { can_generate: false },
      planPolicyAudit: planPolicyAudit2,
      planScorecard,
      planPolicySchedule,
      safetyStatus,
      assessmentTrend: assessmentTrend2,
      timeline: timeline2
    };
    if (button) {
      button.textContent = "样例";
      button.disabled = true;
    }
    renderReport(latestReport2, history2, trend2, {
      solo: false,
      reportType,
      planPolicyAudit: planPolicyAudit2,
      planScorecard,
      planPolicySchedule,
      safetyStatus,
      assessmentTrend: assessmentTrend2,
      timeline: timeline2
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
    api.getRelationshipTimeline(pairId, 12)
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
    timeline: unwrapResult(timeline, { event_count: 0, latest_event_at: null, events: [], highlights: [] })
  };
  if (button) {
    button.textContent = isSolo ? soloButton.label : "刷新这期";
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
      timeline: state.reportSnapshot.timeline
    }
  );
}
function renderReport(report, history, trendData, options = {}) {
  var _a, _b, _c, _d, _e, _f, _g;
  const isSolo = Boolean(options.solo);
  const reportType = options.reportType || state.selectedReportType;
  const reportLabel = formatReportType(reportType, { solo: isSolo });
  const safetyPanel = renderSafetyStatusPanel(options.safetyStatus || {
    risk_level: ((_a = report == null ? void 0 : report.content) == null ? void 0 : _a.crisis_level) || "none",
    why_now: ((_b = report == null ? void 0 : report.content) == null ? void 0 : _b.insight) || ((_c = report == null ? void 0 : report.content) == null ? void 0 : _c.executive_summary) || "",
    evidence_summary: (report == null ? void 0 : report.evidence_summary) || [],
    limitation_note: (report == null ? void 0 : report.limitation_note) || "",
    recommended_action: ((_d = report == null ? void 0 : report.content) == null ? void 0 : _d.suggestion) || "",
    handoff_recommendation: (report == null ? void 0 : report.safety_handoff) || ""
  }, { title: "信任与边界" });
  const assessmentPanel = renderAssessmentTrendCard(options.assessmentTrend, { title: "近 4 次关系体检趋势" });
  const scorecardPanel = renderInterventionScorecard(options.planScorecard, { solo: isSolo });
  const policyAuditPanel = renderPolicyDecisionAudit(options.planPolicyAudit, { solo: isSolo });
  const schedulePanel = renderPolicySchedule(options.planPolicySchedule, { solo: isSolo });
  let reportSections = `
        <section class="mono-report mono-report--empty">
            <section class="mono-report__hero">
                <div class="mono-report__copy">
                    <p class="mono-report__kicker">${escapeHtml(reportLabel)}</p>
                    <h3 class="mono-report__title">先写一句，再来读这一期。</h3>
                    <p class="mono-report__lead">简报会把判断、证据和下一步压成一条线。</p>
                    <div class="stage-surface__actions mono-report__actions">
                        <button class="button button--primary" type="button" onclick="showPage('checkin')">去写今天</button>
                        <button class="button button--ghost" type="button" onclick="showPage('timeline')">看时间线</button>
                    </div>
                </div>
                <aside class="mono-report__visual">
                    ${handmadeCoverVisual({ score: "--", scene: "calm", mode: "report", caption: "简报未生成", marker: isSolo ? "SELF" : "PAIR" })}
                </aside>
            </section>
        </section>
    `;
  if ((report == null ? void 0 : report.status) === "pending") {
    reportSections = `
            <section class="mono-report mono-report--empty">
                <section class="mono-report__hero">
                    <div class="mono-report__copy">
                        <p class="mono-report__kicker">生成中</p>
                        <h3 class="mono-report__title">${escapeHtml(reportLabel)} 正在排版。</h3>
                        <p class="mono-report__lead">系统正在把最近的记录压成一页更好读的主线。</p>
                    </div>
                    <aside class="mono-report__visual">
                        ${handmadeCoverVisual({ score: "…", scene: "repair", mode: "report", caption: "排版中", marker: "WAIT" })}
                    </aside>
                </section>
            </section>
        `;
  } else if ((report == null ? void 0 : report.status) === "failed") {
    reportSections = `
            <section class="mono-report mono-report--empty">
                <section class="mono-report__hero">
                    <div class="mono-report__copy">
                        <p class="mono-report__kicker">重试</p>
                        <h3 class="mono-report__title">${escapeHtml(reportLabel)} 这次没有排出来。</h3>
                        <p class="mono-report__lead">你可以先看时间线，稍后再刷新这一期。</p>
                    </div>
                    <aside class="mono-report__visual">
                        ${handmadeCoverVisual({ score: "!", scene: "watch", mode: "report", caption: "重试", marker: "RETRY" })}
                    </aside>
                </section>
            </section>
        `;
  } else if ((report == null ? void 0 : report.status) === "completed") {
    const content = report.content || {};
    const score = content.health_score || content.overall_health_score || 72;
    const primaryInsight = content.insight || content.self_insight || content.executive_summary || "系统已经把这一阶段整理成一份可读的简报。";
    const suggestion = content.suggestion || content.self_care_tip || content.trend_description || content.professional_note || "";
    const encouragement = content.encouragement || content.relationship_note || "";
    const highlights = (content.highlights || content.weekly_highlights || content.strengths || []).slice(0, 2);
    const concerns = (content.concerns || content.growth_areas || content.action_plan || []).slice(0, 2);
    const reportDate = report.report_date || formatDateOnly(new Date().toISOString());
    const nextAction = suggestion || concerns[0] || "继续把真实感受说清楚，再决定要不要进入下一步讨论。";
    const evidenceSummary = (report.evidence_summary || content.evidence_summary || []).slice(0, 3);
    const boundaryNote = getPreferredText(
      ((_e = options.safetyStatus) == null ? void 0 : _e.limitation_note) || ((_f = options.safetyStatus) == null ? void 0 : _f.recommended_action) || (report == null ? void 0 : report.safety_handoff) || (report == null ? void 0 : report.limitation_note),
      "这份判断只负责帮你看清这阶段发生了什么，不替代真正的沟通和决定。"
    );
    const posterHeadline = trimHandmadeCopy(primaryInsight, 14, "先读这一句。");
    const posterLead = posterHeadline === primaryInsight ? encouragement || boundaryNote : primaryInsight;
    const actionHeadline = trimHandmadeCopy(nextAction, 18, "先把一句话说清楚。");
    const scene = resolveEditorialScene({
      riskLevel: ((_g = options.safetyStatus) == null ? void 0 : _g.risk_level) || content.crisis_level || "none",
      hasReport: true,
      bothDone: true,
      myDone: true
    });
    const actionButtons = isSolo ? `<button class="button button--primary" type="button" onclick="showPage('checkin')">回到今日记录</button><button class="button button--ghost" type="button" onclick="showPage('timeline')">打开时间轴</button>` : `<button class="button button--primary" type="button" onclick="openMessageSimulator()">聊天前预演</button><button class="button button--ghost" type="button" onclick="showPage('timeline')">打开时间轴</button>`;
    const appendixNotesPanel = highlights.length || concerns.length ? `
            <section class="editorial-section editorial-section--appendix">
                <div class="editorial-section__head">
                    <div>
                        <p class="editorial-section__eyebrow">附录</p>
                        <h4 class="editorial-section__title">补充线索</h4>
                    </div>
                </div>
                <div class="report-appendix-notes">
                    ${highlights.length ? `
                        <section>
                            <span>积极信号</span>
                            ${handmadeList(highlights, "继续记录，这里的亮点会慢慢更清楚。")}
                        </section>
                    ` : ""}
                    ${concerns.length ? `
                        <section>
                            <span>需要关注</span>
                            ${handmadeList(concerns, "现在没有额外提醒，保持稳定节奏就好。")}
                        </section>
                    ` : ""}
                </div>
            </section>
        ` : "";
    reportSections = `
            <section class="mono-report mono-report--${escapeHtml(scene)}">
                <section class="mono-report__hero">
                    <div class="mono-report__copy">
                        <p class="mono-report__kicker">${isSolo ? "第一幕 · 个人简报" : "第一幕 · 关系简报"} · ${escapeHtml(reportDate)}</p>
                        <h3 class="mono-report__title">${escapeHtml(posterHeadline)}</h3>
                        <p class="mono-report__lead">${escapeHtml(posterLead)}</p>
                    <div class="mono-report__current">
                        <span>现在先做</span>
                        <strong>${escapeHtml(actionHeadline)}</strong>
                    </div>
                </div>
                    <aside class="mono-report__visual">
                        ${handmadeCoverVisual({ score, scene, mode: "report", caption: isSolo ? "个人阶段" : "关系阶段", marker: isSolo ? "SELF" : "PAIR" })}
                    </aside>
                </section>
                <section class="mono-report__act mono-report__act--evidence">
                    <div class="mono-report__head">
                        <p class="mono-report__eyebrow">第二幕</p>
                        <h4>证据回放</h4>
                    </div>
                ${renderReportEvidenceLine(options.timeline, evidenceSummary)}
                </section>
                <section class="mono-report__act mono-report__act--action">
                    <div class="mono-report__head">
                        <p class="mono-report__eyebrow">第三幕</p>
                        <h4>现在先做什么</h4>
                    </div>
                    <article class="mono-report__callout">
                        <span>当前动作</span>
                        <strong>${escapeHtml(actionHeadline)}</strong>
                    </article>
                    <div class="stage-surface__actions mono-report__actions">
                        ${actionButtons}
                    </div>
                    <details class="mono-report__appendix">
                        <summary>展开附录</summary>
                        <div class="mono-report__appendix-grid">
                            ${appendixNotesPanel}
                            ${assessmentPanel}
                            ${safetyPanel}
                            ${scorecardPanel}
                            ${policyAuditPanel}
                            ${schedulePanel}
                            <section class="editorial-section editorial-section--appendix">
                                <div class="editorial-section__head">
                                    <div>
                                        <p class="editorial-section__eyebrow">趋势</p>
                                        <h4 class="editorial-section__title">近阶段走势</h4>
                                    </div>
                                </div>
                                ${handmadeTrend(trendData, { solo: isSolo })}
                            </section>
                        </div>
                    </details>
                </section>
            </section>
        `;
  }
  safeSetHtml("#report-main", reportSections);
  const list = $("#report-history-list");
  if (!list)
    return;
  if (!history.length) {
    list.innerHTML = '<div class="section-empty">现在还没有历史简报记录。</div>';
    return;
  }
  list.innerHTML = `<div class="mono-report__archive">${history.map((item, index) => {
    const status = String(item.status || "pending").toLowerCase();
    const statusLabel = formatArchiveStatusLabel(item.status);
    const reportDate = item.report_date ? formatDateOnly(item.report_date) : "未命名日期";
    return `
        <article class="mono-report__archive-item mono-report__archive-item--${escapeHtml(status)}">
            <span class="mono-report__archive-index">${escapeHtml(String(index + 1).padStart(2, "0"))}</span>
            <strong>${formatReportType(item.type || reportType, { solo: isSolo })}</strong>
            <p>${escapeHtml(reportDate)}</p>
            <span>${escapeHtml(statusLabel)}</span>
        </article>
    `;
  }).join("")}</div>`;
}
async function loadProfilePage() {
  if (!state.me && !isDemoMode()) {
    safeSetHtml("#profile-summary", '<div class="empty-state">请先登录。</div>');
    safeSetHtml("#profile-account-panel", "");
    safeSetHtml("#profile-pair-panel", "");
    safeSetHtml("#profile-relations-panel", "");
    return;
  }
  const me = state.me || deepClone(getDemoFixture("me")) || {};
  const allPairs = state.pairs || deepClone(getDemoFixture("pairs")) || [];
  const pair = state.currentPair || allPairs[0] || null;
  const userName = me.nickname || me.email || "亲健用户";
  const activePairs = allPairs.filter((item) => item.status === "active");
  const pendingPairs = allPairs.filter((item) => item.status === "pending");
  const unbindStatus = isDemoMode() ? { has_request: false } : pair ? await getCurrentUnbindStatus(pair.id).catch(() => ({ has_request: false })) : { has_request: false };
  if (!isDemoMode()) {
    try {
      await loadAdminPolicies();
    } catch (error) {
    }
  }
  safeSetHtml("#profile-summary", `
        <section class="cockpit-shell cockpit-shell--profile-hero">
            <div class="cockpit-shell__head">
                <div>
                    <p class="panel__eyebrow">我的概况</p>
                    <h3>${escapeHtml(userName)}</h3>
                </div>
                <span class="pill">${isDemoMode() ? "样例模式" : "在线模式"}</span>
            </div>
            <p>${escapeHtml(getVisibleEmailLabel(me))}，${pair ? "当前已经进入一段关系" : "当前还没有绑定关系"}。</p>
            ${handmadeLedger([
    { label: "活跃关系", value: String(activePairs.length), meta: "决定首页、简报和时间轴默认读取哪一段关系。" },
    { label: "待加入", value: String(pendingPairs.length), meta: "还在等待对方进入的关系会留在这里。" },
    { label: "当前对象", value: pair ? getPartnerDisplayName(pair) : "未设置", meta: pair ? "你现在看到的系统判断都围绕这段关系展开。" : "先保持单人模式也完全可以。" }
  ])}
        </section>
    `);
  safeSetHtml("#profile-account-panel", `
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
                        ${handmadeSheet("账户", "账户信息", [
    { label: "昵称", value: userName, meta: "三端会共用这份名称。" },
    { label: "邮箱", value: getVisibleEmailLabel(me, "未绑定"), meta: "当前主登录方式。" },
    { label: "手机号", value: maskPhone(me.phone), meta: "验证码登录时展示。" },
    { label: "登录渠道", value: getAccountChannels(me), meta: "决定你从哪里进入。" },
    { label: "创建时间", value: formatDateOnly(me.created_at), meta: `账户编号：${String(me.id || "").slice(0, 8).toUpperCase()}` }
  ])}
                        ${handmadeSheet("关系", pair ? "当前关系" : "关系状态", pair ? [
    { label: "对象", value: getPartnerDisplayName(pair), meta: `创建于 ${formatDateOnly(pair.created_at)}` },
    { label: "关系类型", value: TYPE_LABELS[pair.type] || pair.type, meta: pair.status === "active" ? "当前已激活" : "还在等待加入" },
    { label: "邀请码", value: pair.invite_code || "无", meta: "可以直接发给对方。" },
    { label: "解绑状态", value: unbindStatus.has_request ? unbindStatus.requested_by_me ? `你已发起，还剩 ${unbindStatus.days_remaining} 天` : "对方已发起解绑" : "当前没有进行中申请", meta: "边界感和关系管理都应该在这里被看见。" }
  ] : [
    { label: "当前状态", value: "未绑定关系", meta: "你可以继续用单人模式，不必被流程推着走。" },
    { label: "下一步", value: "准备好再邀请对方", meta: "真正愿意时，再把关系接进来。" }
  ])}
                    </div>
                    ${isDemoMode() ? '<section class="safety-panel safety-panel--compact"><div class="safety-panel__head"><div><p class="panel__eyebrow">查看模式</p><h4>样例模式不会改真实数据</h4></div></div><p class="safety-panel__summary">当前页面只展示结构和内容，不开放改名、解绑或策略调整等修改操作。</p></section>' : ""}
                </div>
                <div class="cockpit-grid__side">
                    ${isDemoMode() ? '<section class="cockpit-shell cockpit-shell--actions"><div class="cockpit-shell__head"><div><p class="panel__eyebrow">策略概览</p><h4>策略面板（查看）</h4></div></div><p>样例模式下只展示策略内容，不触发新增、编辑、启停或回滚。</p><div class="cockpit-action-row"><button class="button button--ghost" type="button" onclick="exitDemoMode()">退出样例</button></div></section>' : state.isAdmin ? renderPolicyWorkbenchLauncher(state.adminPolicies || []) : renderPolicyWorkbenchErrorNotice(state.policyWorkbenchError || "当前账号没有管理员权限，策略面板不会显示写入口。")}
                </div>
            </div>
        </section>
    `);
  safeSetHtml("#profile-pair-panel", "");
  safeSetHtml("#profile-relations-panel", `
        <section class="cockpit-shell cockpit-shell--actions">
            <div class="cockpit-shell__head">
                <div>
                    <p class="panel__eyebrow">动作</p>
                    <h4>关系切换与账户动作</h4>
                </div>
                <p>切换关系后，首页、时间轴和简报都会一起跟着切过去。</p>
            </div>
            <div class="profile-action-list">
                ${isDemoMode() ? `<button class="profile-action" type="button" onclick="showPage('report')"><span>→</span><div><strong>返回关系简报</strong><p>继续查看当前关系状态与后续动作。</p></div><span>进入</span></button>` : `<button class="profile-action" type="button" onclick="openProfileEditor()" aria-label="修改名称"><span>${svgIcon("i-edit")}</span><div><strong>修改名称</strong><p>当前显示名：${escapeHtml(userName)}</p></div><span>进入</span></button>
                       <button class="profile-action" type="button" onclick="openPasswordEditor()" aria-label="修改密码"><span>${svgIcon("i-lock")}</span><div><strong>修改密码</strong><p>保护关系数据和账号安全，建议定期更新。</p></div><span>进入</span></button>
                       ${pair ? `<button class="profile-action" type="button" onclick="openPartnerNicknameEditor()" aria-label="编辑对方备注"><span>${svgIcon("i-heart")}</span><div><strong>设置对方备注</strong><p>${escapeHtml(pair.custom_partner_nickname || "现在还没有备注名")}</p></div><span>进入</span></button>
                               <button class="profile-action" type="button" onclick="openUnbindPanel()" aria-label="管理解绑状态"><span>${svgIcon("i-refresh")}</span><div><strong>解绑与边界</strong><p>把取消、确认和等待都放到清楚的流程里。</p></div><span>进入</span></button>` : `<button class="profile-action" type="button" onclick="showPage('pair')" aria-label="建立关系"><span>${svgIcon("i-link")}</span><div><strong>去建立关系</strong><p>继续单人模式也可以，准备好了再邀请对方。</p></div><span>进入</span></button>`}`}
            </div>
            <section class="editorial-section">
                <div class="editorial-section__head"><div><p class="editorial-section__eyebrow">关系</p><h4 class="editorial-section__title">全部关系</h4></div></div>
                <p class="editorial-section__note">所有关系都放在这里切换和管理。换一个关系，首页、记录和简报都会一起跟着切过去。</p>
                ${renderRelationManagementList(allPairs, (pair == null ? void 0 : pair.id) || null)}
                <div class="stage-surface__actions">
                    <button class="button button--primary" type="button" onclick="showPage('pair')">${isDemoMode() ? "查看关系设置页" : "新增或加入关系"}</button>
                    <button class="button button--ghost" type="button" onclick="showPage('home')">回到首页</button>
                </div>
            </section>
        </section>
    `);
  setHandmadePanelVisibility("#profile-account-panel", true);
  setHandmadePanelVisibility("#profile-pair-panel", false);
  setHandmadePanelVisibility("#profile-relations-panel", true);
}
