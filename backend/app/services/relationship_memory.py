"""长期关系记忆服务 — 跨会话的人物/事件/策略/模式存储与检索

核心能力：
- store_memory:    写入记忆（去重合并同一 subject）
- recall_memories: 模糊检索（关键词匹配 + 重要度排序）
- batch_store_from_skill: 批量写入 Skill 提取的记忆
- decay_memories:  衰减低重要度且长期未引用的记忆
"""

from __future__ import annotations

import uuid
import logging
import re
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, desc, or_, cast, String, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RelationshipMemory
from app.services.memory_evidence import identifies_record

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_uuid(value: Any) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except (ValueError, TypeError):
            return None
    return None


def _content_with_evidence_ids(record):
    content = dict(record.content or {})
    if record.memory_type == 'person' and content.get('person_evidence'):
        content['person_evidence'] = [
            {**row, 'evidence_id': str(uuid.uuid5(record.id, str(row.get('source_user_message_id') or row.get('detail') or '')))}
            for row in content['person_evidence']
        ]
    return content


def fact_evidence(content):
    """兼容旧记录，在再次保存时保留每份事实和它的原文来源。"""
    content = content or {}
    if isinstance(content.get('fact_evidence'), list):
        return [dict(item) for item in content['fact_evidence'] if isinstance(item, dict)]
    fields = ('detail', 'evidence_text', 'source_user_message_id', 'authorization_user_message_id')
    return [{key: content[key] for key in fields if content.get(key)}] if content.get('detail') else []


def _bigrams(text: Any) -> set[str]:
    clean = re.sub(r'[\s，,。.！!？?、；;：:（）()“”"\'’‘「」\n]', '', str(text or ''))
    return {clean[i:i + 2] for i in range(max(0, len(clean) - 1))}


def touches_request(subject: Any, detail: Any, request_text: Any) -> bool:
    """记录内容和用户这一轮说的话有没有实打实的重合，防止删到不相干的东西。"""
    haystack = _bigrams(request_text)
    if len(haystack) < 2:
        return False
    for value in (subject, detail):
        if len(_bigrams(value) & haystack) >= 2:
            return True
    return False


async def _ordered_records(db: AsyncSession, pid: uuid.UUID, uid: uuid.UUID):
    """稳定排序的记忆列表：重要度、创建时间、编号，不随检索刷新而变化。"""
    result = await db.execute(
        select(RelationshipMemory).where(
            RelationshipMemory.pair_id == pid,
            RelationshipMemory.user_id == uid,
        ).order_by(
            desc(RelationshipMemory.importance),
            desc(RelationshipMemory.created_at),
            desc(RelationshipMemory.id),
        )
    )
    return list(result.scalars().all())


async def memory_references(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
) -> list[dict[str, Any]]:
    """给每条记忆及其当前内容一个稳定引用，不暴露数据库编号，也不依赖排序。"""
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        return []
    rows = await _ordered_records(db, pid, uid)
    return [
        {
            'ref': _record_ref(record),
            'record_id': str(record.id),
            'type': record.memory_type,
            'subject': record.subject,
        }
        for record in rows
    ]


async def _records_by_ref(db: AsyncSession, *, pair_id, user_id) -> dict[str, RelationshipMemory]:
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        return {}
    rows = await _ordered_records(db, pid, uid)
    result = {}
    for record in rows:
        reference = _record_ref(record)
        if reference in result:
            raise ValueError('记录引用发生冲突，未执行删除。')
        result[reference] = record
    return result


def _record_ref(record):
    """记录引用只跟内容和归属有关，换 SECRET_KEY 不能让待确认的停用全部失效。"""
    version = json.dumps(record.content or {}, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    material = f'memory-ref-v1:{record.pair_id}:{record.user_id}:{record.id}:{record.subject}:{record.memory_type}:{version}'.encode('utf-8')
    digest = hashlib.sha256(material).digest()[:8]
    # 只用字母，避免再次被号码或 UUID 脱敏规则改写。
    return 'R' + ''.join(chr(65 + nibble) for byte in digest for nibble in (byte >> 4, byte & 15))


def _person_role(detail, name):
    explicit = re.search(r'身份(?:是|为)?\s*[:：]?\s*([^，。；;\n]{1,30})', detail)
    if explicit:
        return explicit.group(1).strip()
    after_name = re.search(re.escape(name) + r'(?:是我(?:的)?|是)([^，。；;\n]{1,30})', detail)
    if after_name:
        return after_name.group(1).strip()
    before_name = re.search(r'(?:^|[：:，。；;\s])([^，。；;：:\s]{2,20})' + re.escape(name), detail)
    return before_name.group(1).strip() if before_name else ''


async def store_memory(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    memory_type: str,
    subject: str,
    content: dict[str, Any],
    importance: int = 3,
    source_session_id: uuid.UUID | str | None = None,
) -> RelationshipMemory:
    """写入或更新一条长期记忆。

    如果同一 pair_id + user_id + subject 已存在同类记忆，合并更新。
    """
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        raise ValueError("pair_id 和 user_id 不能为空")

    subject = str(subject or "").strip()[:100]
    if not subject:
        raise ValueError("记忆主题不能为空")

    memory_type = str(memory_type or "event").strip().lower()
    if memory_type not in ("person", "event", "strategy", "pattern", "taboo"):
        memory_type = "event"

    importance = max(1, min(5, int(importance or 3)))

    # 查找是否已有同 subject 的同类记忆
    existing = await db.execute(
        select(RelationshipMemory).where(
            RelationshipMemory.pair_id == pid,
            RelationshipMemory.user_id == uid,
            RelationshipMemory.memory_type == memory_type,
            RelationshipMemory.subject == subject,
        ).limit(1)
    )
    record = existing.scalar_one_or_none()

    if record:
        # 合并更新：保留旧内容，追加新信息
        old_content = record.content or {}
        merged = {**old_content, **content}
        if memory_type == 'person' and content.get('source_user_message_id'):
            evidence = list(old_content.get('person_evidence') or [])
            for source in (old_content, content):
                message_id = source.get('source_user_message_id')
                detail = source.get('detail')
                if message_id and detail and not any(item.get('source_user_message_id') == message_id for item in evidence):
                    entry = {'source_user_message_id': message_id, 'detail': detail}
                    if source.get('evidence_text'):
                        entry['evidence_text'] = source['evidence_text']
                    evidence.append(entry)
                elif not message_id and detail and not any(item.get('detail') == detail for item in evidence):
                    evidence.append({'detail': detail, 'evidence_status': 'legacy_unverified'})
            merged['person_evidence'] = evidence
        elif memory_type != 'person':
            evidence = fact_evidence(old_content)
            for entry in fact_evidence(content):
                if entry not in evidence:
                    evidence.append(entry)
            merged['fact_evidence'] = evidence
            merged['detail'] = '；'.join(dict.fromkeys(str(item.get('detail') or '') for item in evidence if item.get('detail')))
        record.content = merged
        record.importance = max(record.importance, importance)
        record.updated_at = _utcnow()
        if source_session_id:
            record.source_session_id = _normalize_uuid(source_session_id)
    else:
        if memory_type == 'person' and content.get('source_user_message_id'):
            entry = {'source_user_message_id': content['source_user_message_id'], 'detail': content.get('detail', '')}
            if content.get('evidence_text'):
                entry['evidence_text'] = content['evidence_text']
            content = {**content, 'person_evidence': [entry]}
        record = RelationshipMemory(
            pair_id=pid,
            user_id=uid,
            memory_type=memory_type,
            subject=subject,
            content=content,
            importance=importance,
            source_session_id=_normalize_uuid(source_session_id),
        )
        db.add(record)

    await db.flush()
    return record


async def recall_memories(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    query: str = "",
    memory_types: list[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """检索相关的长期记忆。

    根据关键词模糊匹配 subject 和 content，按重要度 + 最近引用排序。
    """
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        return []

    stmt = select(RelationshipMemory).where(
        RelationshipMemory.pair_id == pid,
        RelationshipMemory.user_id == uid,
    )

    if memory_types:
        stmt = stmt.where(RelationshipMemory.memory_type.in_(memory_types))

    # 关键词匹配（支持完整匹配及中文长句核心词抽取匹配）
    keyword = str(query or "").strip()
    if keyword:
        pattern = f"%{keyword}%"
        conditions = [
            RelationshipMemory.subject.ilike(pattern),
            cast(RelationshipMemory.content, String).ilike(pattern),
        ]

        # 若 query 较长，提取其中的非停用核心词段，提升自然长句的召回率
        import re
        tokens = [t for t in re.split(r"[\s,，。？！!?、~—]+", keyword) if len(t) >= 2]
        for t in tokens:
            if t != keyword:
                conditions.append(RelationshipMemory.subject.ilike(f"%{t}%"))
                conditions.append(cast(RelationshipMemory.content, String).ilike(f"%{t}%"))

        stop_words = set("的一了是在有我你他她它我们他们这个那个怎么怎么办什么如果因为所以而且但是")
        clean_kw = "".join(c for c in keyword if c not in stop_words)
        for i in range(len(clean_kw) - 1):
            sub = clean_kw[i : i + 2]
            if len(sub) == 2:
                conditions.append(RelationshipMemory.subject.ilike(f"%{sub}%"))
                conditions.append(cast(RelationshipMemory.content, String).ilike(f"%{sub}%"))

        stmt = stmt.where(or_(*conditions))

    stmt = stmt.order_by(
        desc(RelationshipMemory.importance),
        desc(RelationshipMemory.last_referenced_at),
        desc(RelationshipMemory.updated_at),
    ).limit(max(1, min(limit, 20)))

    result = await db.execute(stmt)
    records = result.scalars().all()

    # 更新 last_referenced_at
    now = _utcnow()
    for r in records:
        r.last_referenced_at = now

    return [
        {
            "id": str(r.id),
            "type": r.memory_type,
            "subject": r.subject,
            "content": _content_with_evidence_ids(r),
            "importance": r.importance,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in records
    ]


async def batch_store_from_skill(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    memories: list[dict[str, Any]],
    source_session_id: uuid.UUID | str | None = None,
) -> int:
    """批量写入 Skill 提取的记忆。

    memories 格式：[{"type": "person", "subject": "小林", "content": "...", "importance": 3}]
    返回成功写入的条数。
    """
    count = 0
    for item in memories:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject", "")).strip()
        if not subject:
            continue
        try:
            await store_memory(
                db,
                pair_id=pair_id,
                user_id=user_id,
                memory_type=str(item.get("type", "event")),
                subject=subject,
                content={"detail": str(item.get("content", ""))},
                importance=int(item.get("importance", 3)),
                source_session_id=source_session_id,
            )
            count += 1
        except Exception as exc:
            logger.warning("Failed to store memory '%s': %s", subject, exc)
    return count


async def list_all_memories(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """列出所有长期记忆（管理用）。"""
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        return []

    result = await db.execute(
        select(RelationshipMemory).where(
            RelationshipMemory.pair_id == pid,
            RelationshipMemory.user_id == uid,
        ).order_by(
            desc(RelationshipMemory.importance),
            desc(RelationshipMemory.updated_at),
        ).limit(max(1, min(limit, 100)))
    )
    return [
        {
            "id": str(r.id),
            "type": r.memory_type,
            "subject": r.subject,
            "content": _content_with_evidence_ids(r),
            "importance": r.importance,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in result.scalars().all()
    ]


async def get_active_taboos(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str | None,
    user_id: uuid.UUID | str | None,
    limit: int = 5,
) -> list[str]:
    """获取用户当前生效的雷区、反感点和绝对底线记忆，供静默注入提示词。"""
    if not user_id or not pair_id:
        return []
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        return []

    result = await db.execute(
        select(RelationshipMemory).where(
            RelationshipMemory.pair_id == pid,
            RelationshipMemory.user_id == uid,
            RelationshipMemory.memory_type == "taboo",
        ).order_by(
            desc(RelationshipMemory.importance),
            desc(RelationshipMemory.updated_at),
        ).limit(max(1, min(limit, 10)))
    )
    taboos = []
    for r in result.scalars().all():
        detail = ""
        if isinstance(r.content, dict):
            detail = str(r.content.get("detail") or r.content.get("content") or "").strip()
        elif r.content:
            detail = str(r.content).strip()
        item_text = f"{r.subject}"
        if detail and detail != r.subject:
            item_text += f"（{detail}）"
        taboos.append(item_text)
    return taboos


async def plan_memory_removal(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    user_id: uuid.UUID | str,
    memory_id: uuid.UUID | str | None = None,
    subject: str | None = None,
    memory_type: str | None = None,
    evidence_ids: list[str] | None = None,
    person_selector: str | None = None,
    delete_all: bool = False,
    refs: list[str] | None = None,
    request_text: str | None = None,
    all_scope_requested: bool = False,
) -> list[dict]:
    """只计算停用范围；这里不改记录，确认后由单独的服务执行。"""
    def planned(record, remaining=None):
        label=record.subject + ("（"+str(person_selector)+"）" if person_selector else "")
        if record.memory_type=='person':
            evidence=_content_with_evidence_ids(record).get('person_evidence') or []
            kept={item['evidence_id'] for item in (remaining or {}).get('person_evidence',[])}
            removed=[item for item in evidence if item['evidence_id'] not in kept]
            if removed:
                label+='，'+str(len(removed))+' 份原文：'+'；'.join(str(item.get('detail') or '') for item in removed)
        elif (record.content or {}).get('fact_evidence'):
            label += '，原文：' + '；'.join(str(item.get('detail') or '') for item in fact_evidence(record.content))
        return {"record_id":str(record.id),"version":_record_ref(record),"remaining":remaining,"label":label}
    pid = _normalize_uuid(pair_id)
    uid = _normalize_uuid(user_id)
    if not pid or not uid:
        return []

    if all_scope_requested:
        records = await _ordered_records(db,pid,uid)
        return [planned(record) for record in records]

    clean_subject = str(subject or "").strip()

    # 引用绑定记录内容，不随检索排序换对象；删除前仍逐条核对用户原话。
    if refs:
        table = await _records_by_ref(db, pair_id=pid, user_id=uid)
        # 人物子引用由父记录的内容版本和原文位置组成；不能把查询发出的引用拒之门外。
        if len(refs)==1:
            key=str(refs[0] or '').strip().upper()
            child=re.fullmatch(r'(R[A-P]{16})-([1-9][0-9]*)',key)
            parent=child.group(1) if child else key
            record=table.get(parent)
            if record is not None and record.memory_type=='person' and (child or person_selector):
                if clean_subject and clean_subject!=record.subject:
                    raise ValueError('记录和主题对不上，未停用。')
                evidence=_content_with_evidence_ids(record).get('person_evidence') or []
                selected_ids=evidence_ids
                if child:
                    index=int(child.group(2))-1
                    if index>=len(evidence):
                        raise ValueError('没有找到这份人物原文，未停用。')
                    selected_ids=[evidence[index]['evidence_id']]
                plan=await plan_memory_removal(db,pair_id=pid,user_id=uid,memory_id=record.id,subject=record.subject,
                    memory_type=memory_type,evidence_ids=selected_ids,person_selector=person_selector,delete_all=delete_all,
                    request_text=None if key in str(request_text or '').upper() else request_text)
                if any(item['version']!=parent for item in plan):
                    raise ValueError('这份原文已经变化，请重新查询并确认。')
                return plan
        selected_records: list[RelationshipMemory] = []
        seen: set[uuid.UUID] = set()
        for ref in refs:
            key = str(ref or '').strip().upper()
            record = table.get(key)
            if record is None:
                raise ValueError('没有找到这个记录编号，未删除任何记录。')
            if record.id in seen:
                continue
            seen.add(record.id)
            if clean_subject and record.subject != clean_subject:
                raise ValueError('记录和主题对不上，未删除。')
            detail = (record.content or {}).get('detail', '')
            if request_text and key not in str(request_text).upper() and not identifies_record(record, request_text):
                raise ValueError('这条记录和用户本轮说的话对不上，未删除。')
            if record.memory_type == 'person' and len((record.content or {}).get('person_evidence') or []) > 1:
                raise ValueError('这条人物资料下有多份原文，请说明是哪一位，未删除。')
            selected_records.append(record)
        return [planned(record) for record in selected_records]

    conditions = [
        RelationshipMemory.pair_id == pid,
        RelationshipMemory.user_id == uid,
    ]
    has_target = False

    # 若提供了 memory_id，必须是有效的 UUID 格式；无效 UUID 绝不能退化为全局匹配
    if memory_id is not None and str(memory_id).strip():
        mid = _normalize_uuid(memory_id)
        if not mid:
            return []
        conditions.append(RelationshipMemory.id == mid)
        has_target = True

    # 若提供了 subject，必须非空
    if clean_subject:
        conditions.append(RelationshipMemory.subject == clean_subject)
        has_target = True

    # 必须至少具备有效 memory_id 或非空 subject 之一作为具体定位标识
    if not has_target:
        return []

    if memory_type is not None and str(memory_type).strip():
        conditions.append(RelationshipMemory.memory_type == str(memory_type).strip())

    result = await db.execute(select(RelationshipMemory).where(*conditions))
    target = result.scalars().first()
    if target is None and clean_subject:
        # 用户说的是“搬家”，存的是“搬家（下周三）”：按去掉时间后缀的主题再找一次。
        strip_time = lambda value: re.sub(r'（[^）]*）|\([^)]*\)', '', str(value or '')).strip()
        base = strip_time(clean_subject)
        if base:
            loose = [cond for cond in conditions if getattr(cond, 'right', None) is not None and getattr(getattr(cond, 'left', None), 'key', '') != 'subject']
            rows = (await db.execute(select(RelationshipMemory).where(*loose))).scalars().all()
            matches = [row for row in rows if strip_time(row.subject) == base]
            if len(matches) > 1:
                raise ValueError('这个主题下有多条记录，请说明是哪一条，未删除任何记录。')
            target = matches[0] if matches else None
    if target:
        if request_text and not identifies_record(target, request_text):
            raise ValueError('这条记录和用户本轮指定的对象对不上，未删除。')
        content = _content_with_evidence_ids(target)
        evidence = content.get('person_evidence') or []
        if target.memory_type == 'person' and evidence:
            selector = str(person_selector or '').strip()
            requested_ids = set(evidence_ids or [])
            known_ids = {row['evidence_id'] for row in evidence}
            if requested_ids - known_ids:
                raise ValueError('没有找到指定的人物原文，未删除。')
            if selector:
                if len(selector) < 2 or selector == target.subject:
                    raise ValueError('同名人物需要补充身份，未删除。')
                selected = [row for row in evidence if selector in _person_role(row.get('detail', ''), target.subject) and (not requested_ids or row['evidence_id'] in requested_ids)]
                if len({_person_role(row.get('detail', ''), target.subject) for row in selected}) > 1:
                    raise ValueError('这个身份仍对应多个人，请选择更具体的身份或原文，未删除。')
            elif requested_ids:
                selected = [row for row in evidence if row['evidence_id'] in requested_ids]
            elif delete_all or len(evidence) == 1:
                selected = evidence
            else:
                raise ValueError('这个名字下有多份人物资料，请说明身份或选择具体原文，未删除。')
            if not selected:
                return []
            removed_ids = {row['evidence_id'] for row in selected}
            remaining = [row for row in evidence if row['evidence_id'] not in removed_ids]
            if remaining:
                latest = remaining[-1]
                content['person_evidence'] = remaining
                content['detail'] = latest.get('detail', '')
                content.pop('evidence_text', None)
                content.pop('authorization_user_message_id', None)
                if latest.get('evidence_text'):
                    content['evidence_text'] = latest['evidence_text']
                content.pop('source_user_message_id', None)
                if latest.get('source_user_message_id'):
                    content['source_user_message_id'] = latest['source_user_message_id']
                return [planned(target,content)]
        return [planned(target)]
    return []


async def remove_memory(db, **selection):
    """旧入口只检查目标，不再执行；明确拒绝绕过二次确认的调用。"""
    if await plan_memory_removal(db, **selection):
        raise ValueError('记忆停用需要用户二次确认，请先建立停用请求。')
    return False


async def decay_memories(
    db: AsyncSession,
    *,
    pair_id: uuid.UUID | str,
    older_than_days: int = 90,
) -> int:
    """衰减长期未引用的低重要度记忆。

    将超过 older_than_days 未引用且重要度 <= 2 的记忆降低重要度。
    """
    pid = _normalize_uuid(pair_id)
    if not pid:
        return 0

    cutoff = _utcnow() - timedelta(days=older_than_days)
    result = await db.execute(
        update(RelationshipMemory).where(
            RelationshipMemory.pair_id == pid,
            RelationshipMemory.importance <= 2,
            or_(
                RelationshipMemory.last_referenced_at.is_(None),
                RelationshipMemory.last_referenced_at < cutoff,
            ),
            RelationshipMemory.updated_at < cutoff,
        ).values(importance=1)
    )
    return result.rowcount or 0
