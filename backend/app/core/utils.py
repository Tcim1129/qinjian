import uuid
from datetime import datetime, timezone
from typing import Optional, Union

def normalize_uuid(val: Union[str, uuid.UUID, None]) -> Optional[uuid.UUID]:
    """将字符串规范化为 UUID。"""
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return None

def utcnow() -> datetime:
    """获取无时区信息的 UTC 当前时间（与数据库存储格式一致）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
