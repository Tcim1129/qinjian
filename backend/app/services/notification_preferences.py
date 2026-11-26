"""站内提醒偏好。创建时生效，不删除已有消息，不代表系统推送授权。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

NOTIFICATION_CATEGORIES = (
    "task_reminder", "relationship_activity", "milestone", "safety_support", "product_update",
)
NOTIFICATION_PREFS_KEY = "mobile_notification_preferences"
TYPE_CATEGORIES = {
    "task_plan_reminder": "task_reminder",
    "report_ready": "relationship_activity",
    "pair_change": "relationship_activity",
    "crisis": "safety_support",
    "milestone": "milestone",
    "system": "product_update",
    "product_update": "product_update",
}


def default_notification_preference(category: str) -> dict:
    return {
        "category": category, "enabled": True, "in_app_enabled": True,
        "wechat_subscription_enabled": False, "app_push_enabled": False,
        "quiet_hours": {"enabled": False, "start": None, "end": None},
        "daily_limit": 5, "subscription_state": "unsubscribed",
    }


def notification_prefs(user: User) -> dict:
    return _preferences_from_product_prefs(user.product_prefs)


def _preferences_from_product_prefs(product_prefs) -> dict:
    prefs = product_prefs if isinstance(product_prefs, dict) else {}
    stored = prefs.get(NOTIFICATION_PREFS_KEY)
    result = {}
    for category in NOTIFICATION_CATEGORIES:
        base = default_notification_preference(category)
        if isinstance(stored, dict) and isinstance(stored.get(category), dict):
            base.update(stored[category])
            base["category"] = category
        result[category] = base
    return result


async def in_app_notification_enabled(db: AsyncSession, user_id, notification_type: str) -> bool:
    # 未分类的新类型保持既有行为；新增消息类型时应在上面的映射中明确归属。
    category = TYPE_CATEGORIES.get(notification_type)
    if category is None:
        return True
    # 任务生成可能持有较早加载的 User；直接读列，避免沿用身份映射里的旧开关。
    row = (await db.execute(select(User.product_prefs).where(User.id == user_id))).first()
    if row is None:
        return False
    entry = _preferences_from_product_prefs(row[0])[category]
    return bool(entry.get("enabled", True) and entry.get("in_app_enabled", True))
