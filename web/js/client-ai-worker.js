(function () {
    const PHONE_REGEX = /(1\d{2})\d{4}(\d{4})/g;
    const EMAIL_REGEX = /\b([A-Za-z0-9._%+-]{1,3})[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b/g;
    const WECHAT_REGEX = /\b(wxid_[a-zA-Z0-9_-]{5,}|[a-zA-Z][-_a-zA-Z0-9]{5,19})\b/g;
    const NAME_REGEX = /((?:我|他|她|ta|TA|对方|对象|伴侣|朋友)?(?:叫|是))([\u4e00-\u9fa5]{2,4})/g;
    const ADDRESS_HINT_REGEX = /(地址|住在|学校|学院|大学|宿舍|公司|工位|小区|班级|学号|工号)\s*[:：]?\s*([^\n，。；]{2,18})/g;

    const HIGH_RISK_RULES = [
        { label: '自伤自杀', regex: /自杀|轻生|不想活|想死|结束生命|割腕|跳楼|自残|活着没意思/i },
        { label: '家暴暴力', regex: /家暴|动手打|扇耳光|打我|打她|打他|掐我|掐她|掐他|推我|推她|推他/i },
        { label: '人身威胁', regex: /威胁杀|威胁我|威胁她|威胁他|跟踪我|跟踪她|跟踪他|报复我|报复她|报复他/i },
    ];
    const WATCH_RISK_RULES = [
        { label: '控制限制', regex: /控制|不准我|不让我|查手机|定位我|限制我|监听/i },
        { label: '极端羞辱', regex: /羞辱|侮辱|骂我废物|骂她废物|骂他废物|贬低我|贬低她|贬低他/i },
        { label: '关系升级', regex: /冷战|分手|拉黑|删好友|不信任|失控|吵崩了|吵炸了/i },
    ];

    const POSITIVE_WORDS = ['开心', '平静', '感动', '安心', '温柔', '理解', '修复', '和好', '拥抱', '谢谢'];
    const NEGATIVE_WORDS = ['生气', '难过', '委屈', '焦虑', '失望', '崩溃', '讨厌', '吵架', '冷战', '压抑'];
    const INTENT_RULES = {
        crisis: ['自杀', '自残', '家暴', '威胁', '跟踪', '不想活'],
        emergency: ['吵架', '冷战', '分手', '怎么回', '怎么说', '要不要发', '误会', '沟通'],
        reflection: ['复盘', '总结', '为什么', '规律', '趋势', '回顾', '变化'],
    };

    function isDigit(char) {
        return /\d/.test(String(char || ''));
    }

    function isStandaloneNumberMatch(text, index, length) {
        const prev = index > 0 ? text[index - 1] : '';
        const next = text[index + length] || '';
        return !isDigit(prev) && !isDigit(next);
    }

    function collectMatches(regex, text, category) {
        const items = [];
        const localRegex = new RegExp(regex.source, regex.flags);
        let match = null;
        while ((match = localRegex.exec(text)) !== null) {
            items.push({
                category,
                match: match[0],
                index: match.index,
            });
            if (!localRegex.global) {
                break;
            }
        }
        return items;
    }

    function summarizePii(text) {
        const phoneHits = collectMatches(PHONE_REGEX, text, 'phone').filter((item) => (
            isStandaloneNumberMatch(text, item.index, String(item.match || '').length)
        ));

        const hits = [
            ...phoneHits,
            ...collectMatches(EMAIL_REGEX, text, 'email'),
            ...collectMatches(NAME_REGEX, text, 'name'),
            ...collectMatches(ADDRESS_HINT_REGEX, text, 'address_hint'),
        ];

        const wechatHits = collectMatches(WECHAT_REGEX, text, 'wechat').filter((item) => {
            const token = String(item.match || '').toLowerCase();
            return token.startsWith('wxid_') || token.includes('wechat') || token.includes('vx');
        });

        hits.push(...wechatHits);

        const categories = hits.reduce((acc, item) => {
            acc[item.category] = (acc[item.category] || 0) + 1;
            return acc;
        }, {});

        return {
            hits,
            summary: {
                total_hits: hits.length,
                categories,
            },
        };
    }

    function redactText(text) {
        return text
            .replace(PHONE_REGEX, (match, prefix, suffix, offset, source) => (
                isStandaloneNumberMatch(source, offset, match.length)
                    ? `${prefix}****${suffix}`
                    : match
            ))
            .replace(EMAIL_REGEX, '$1***@$2')
            .replace(NAME_REGEX, '$1[姓名已隐藏]')
            .replace(ADDRESS_HINT_REGEX, '$1：[位置已隐藏]')
            .replace(/\bwxid_[a-zA-Z0-9_-]{5,}\b/g, '[微信号已隐藏]')
            .replace(/\b([a-zA-Z][-_a-zA-Z0-9]{5,19})\b/g, (token) => {
                if (/^(wxid_|vx|wechat)/i.test(token)) {
                    return '[账号已隐藏]';
                }
                return token;
            });
    }

    function detectRisk(text) {
        const highHits = HIGH_RISK_RULES.filter((rule) => rule.regex.test(text)).map((rule) => rule.label);
        if (highHits.length) {
            return { level: 'high', hits: highHits };
        }
        const watchHits = WATCH_RISK_RULES.filter((rule) => rule.regex.test(text)).map((rule) => rule.label);
        if (watchHits.length) {
            return { level: 'watch', hits: watchHits };
        }
        return { level: 'none', hits: [] };
    }

    function classifyIntent(text, riskLevel) {
        if (riskLevel === 'high') {
            return 'crisis';
        }

        const normalized = String(text || '').toLowerCase();
        const reflectionScore = INTENT_RULES.reflection.filter((keyword) => normalized.includes(keyword)).length;
        const emergencyScore = INTENT_RULES.emergency.filter((keyword) => normalized.includes(keyword)).length;

        if (emergencyScore > 0) {
            return 'emergency';
        }
        if (reflectionScore > 0) {
            return 'reflection';
        }
        return 'daily';
    }

    function detectSentiment(text) {
        const positive = POSITIVE_WORDS.filter((word) => text.includes(word)).length;
        const negative = NEGATIVE_WORDS.filter((word) => text.includes(word)).length;
        if (negative > positive) {
            return 'negative';
        }
        if (positive > negative) {
            return 'positive';
        }
        return 'neutral';
    }

    function buildClientTags(text, intent, riskLevel, piiSummary, sentiment) {
        const tags = [];
        if (intent !== 'daily') tags.push(intent);
        if (riskLevel !== 'none') tags.push(`risk:${riskLevel}`);
        if ((piiSummary?.total_hits || 0) > 0) tags.push('contains_pii');
        if (sentiment !== 'neutral') tags.push(`sentiment:${sentiment}`);
        if (/截图|聊天记录|微信|消息/.test(text)) tags.push('message_context');
        if (/异地|距离|见面/.test(text)) tags.push('distance_context');
        return Array.from(new Set(tags));
    }

    function precheckText(payload) {
        const text = String(payload?.text || '').trim();
        const privacyMode = payload?.privacy_mode === 'local_first' ? 'local_first' : 'cloud';
        const aiAssistEnabled = payload?.ai_assist_enabled !== false;
        const pii = summarizePii(text);
        const risk = detectRisk(text);
        const sentiment = aiAssistEnabled ? detectSentiment(text) : 'neutral';
        const intent = aiAssistEnabled
            ? classifyIntent(text, risk.level)
            : (risk.level === 'high' ? 'crisis' : 'daily');
        const redactedText = pii.summary.total_hits > 0 ? redactText(text) : text;
        const clientTags = buildClientTags(text, intent, risk.level, pii.summary, sentiment);

        return {
            source_type: payload?.source_type || 'text',
            intent,
            risk_level: risk.level,
            risk_hits: risk.hits,
            pii_summary: pii.summary,
            privacy_mode: privacyMode,
            upload_policy: payload?.upload_policy || 'full',
            redacted_text: redactedText,
            client_tags: clientTags,
            device_meta: payload?.device_meta || null,
            ai_assist_enabled: aiAssistEnabled,
            sentiment_hint: sentiment,
        };
    }

    function describeAttachmentMeta(payload) {
        const sourceType = payload?.source_type || 'mixed';
        const meta = payload?.device_meta || {};
        const aiAssistEnabled = payload?.ai_assist_enabled !== false;
        const clientTags = [];

        if (aiAssistEnabled && sourceType === 'image') {
            if ((meta.width || 0) >= 1000) clientTags.push('high_resolution_image');
            if (String(meta.original_type || '').includes('webp') || String(meta.output_type || '').includes('jpeg')) {
                clientTags.push('compressed_image');
            }
        }

        if (aiAssistEnabled && sourceType === 'voice') {
            if ((meta.duration_seconds || 0) < 2) clientTags.push('short_voice');
            if ((meta.silence_ratio || 0) > 0.55) clientTags.push('mostly_silent_voice');
        }

        return {
            source_type: sourceType,
            intent: 'daily',
            risk_level: 'none',
            risk_hits: [],
            pii_summary: { total_hits: 0, categories: {} },
            privacy_mode: payload?.privacy_mode === 'local_first' ? 'local_first' : 'cloud',
            upload_policy: payload?.upload_policy || 'full',
            redacted_text: null,
            client_tags: clientTags,
            device_meta: meta,
            ai_assist_enabled: aiAssistEnabled,
        };
    }

    self.onmessage = (event) => {
        const { id, type, payload } = event.data || {};
        try {
            let result = null;
            if (type === 'precheck-text') {
                result = precheckText(payload);
            } else if (type === 'describe-attachment-meta') {
                result = describeAttachmentMeta(payload);
            } else if (type === 'ping') {
                result = { ok: true };
            } else {
                throw new Error(`Unsupported worker message: ${type}`);
            }
            self.postMessage({ id, ok: true, result });
        } catch (error) {
            self.postMessage({
                id,
                ok: false,
                error: error?.message || 'worker_failed',
            });
        }
    };
})();
