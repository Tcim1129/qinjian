"""D2 历史报告只读影响面审计脚本。

目标：统计有多少已完成的历史报告 (Report.status == 'completed')，其对应的来源打卡 (Checkin)
当前被设置为 private。
原则：纯只读查询，绝不修改、删除任何生产数据。
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# 确保 backend 在 sys.path 中
repo_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_backend not in sys.path:
    sys.path.insert(0, repo_backend)

from app.core.config import settings
from app.models import Checkin, Report, ReportStatus, ReportType
from app.services.checkin_visibility import PRIVATE, PARTNER_VISIBLE_SCOPES


async def audit_impact(db_url_or_engine: str | Any) -> dict[str, Any]:
    """只读统计受 private 来源打卡影响的历史报告。"""
    if hasattr(db_url_or_engine, "connect"):
        engine = db_url_or_engine
        should_dispose = False
    else:
        engine = create_async_engine(db_url_or_engine)
        should_dispose = True
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    impact_summary = {
        "total_completed_reports": 0,
        "affected_reports_total": 0,
        "affected_by_type": {
            "daily": 0,
            "weekly": 0,
            "monthly": 0,
            "solo": 0,
        },
        "affected_pairs": set(),
        "affected_details": [],
    }

    async with session_factory() as db:
        # 1. 查询所有已完成的报告
        reports_stmt = (
            select(Report)
            .where(Report.status == ReportStatus.COMPLETED)
            .order_by(Report.report_date.desc(), Report.id.desc())
        )
        reports_result = await db.execute(reports_stmt)
        reports = reports_result.scalars().all()
        impact_summary["total_completed_reports"] = len(reports)

        for report in reports:
            rep_type_val = report.type.value if hasattr(report.type, "value") else str(report.type)
            if not report.pair_id or not report.report_date:
                continue

            # 计算此报告关联的打卡日期窗口
            if rep_type_val == "daily":
                start_date = report.report_date
                end_date = report.report_date
            elif rep_type_val == "weekly":
                start_date = report.report_date - timedelta(days=6)
                end_date = report.report_date
            elif rep_type_val == "monthly":
                start_date = report.report_date - timedelta(days=29)
                end_date = report.report_date
            else:
                continue

            # 查询此日期范围内属于该 pair 的 private 打卡
            private_checkins_stmt = select(Checkin).where(
                Checkin.pair_id == report.pair_id,
                Checkin.checkin_date >= start_date,
                Checkin.checkin_date <= end_date,
                Checkin.visibility_scope == PRIVATE,
            )
            res = await db.execute(private_checkins_stmt)
            private_checkins = res.scalars().all()

            if private_checkins:
                impact_summary["affected_reports_total"] += 1
                impact_summary["affected_by_type"][rep_type_val] = (
                    impact_summary["affected_by_type"].get(rep_type_val, 0) + 1
                )
                impact_summary["affected_pairs"].add(str(report.pair_id))
                impact_summary["affected_details"].append(
                    {
                        "report_id": str(report.id),
                        "report_type": rep_type_val,
                        "report_date": str(report.report_date),
                        "pair_id": str(report.pair_id),
                        "private_checkin_count": len(private_checkins),
                        "private_checkin_ids": [str(c.id) for c in private_checkins],
                    }
                )

    if should_dispose:
        await engine.dispose()
    impact_summary["affected_pair_count"] = len(impact_summary["affected_pairs"])
    impact_summary["affected_pairs"] = sorted(list(impact_summary["affected_pairs"]))
    return impact_summary


def print_report(summary: dict[str, Any]) -> None:
    print("=" * 60)
    print("   D2 历史报告受 Private 来源记录影响面审计结果（只读）")
    print("=" * 60)
    print(f"已完成的历史报告总数: {summary['total_completed_reports']}")
    print(f"包含 Private 记录的历史报告数: {summary['affected_reports_total']}")
    print(f"受影响配对空间数 (pair_count): {summary['affected_pair_count']}")
    print("按报告类型细分:")
    for rep_type, count in summary["affected_by_type"].items():
        print(f"  - {rep_type:10s}: {count}")
    print("=" * 60)
    if summary["affected_details"]:
        print(f"样例受影响报告（最多展示 5 条）:")
        for detail in summary["affected_details"][:5]:
            print(
                f"  * [{detail['report_type']}] 日期:{detail['report_date']} "
                f"报告ID:{detail['report_id'][:8]}... "
                f"含 {detail['private_checkin_count']} 条 private 打卡"
            )
        print("=" * 60)
    else:
        print("当前未发现含有 private 打卡历史的已完成报告，或数据库暂无此类数据。")


async def run_self_test():
    """使用内存 SQLite 进行自测，确保审计脚本算法完全正确。"""
    from sqlalchemy.pool import StaticPool
    from app.core.database import Base
    from app.models import Pair, PairStatus, PairType, User

    test_db_url = "sqlite+aiosqlite://"
    engine = create_async_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    pair_id = uuid.uuid4()
    u1_id = uuid.uuid4()
    u2_id = uuid.uuid4()
    d1 = date(2026, 9, 20)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as db:
        pair = Pair(
            id=pair_id,
            user_a_id=u1_id,
            user_b_id=u2_id,
            type=PairType.COUPLE,
            status=PairStatus.ACTIVE,
            invite_code="audit-test",
        )
        db.add(pair)
        # 添加一条 private 打卡
        c_priv = Checkin(
            id=uuid.uuid4(),
            user_id=u1_id,
            pair_id=pair_id,
            checkin_date=d1,
            content="机密内容",
            visibility_scope=PRIVATE,
        )
        # 添加一份已完成报告（命中此 private 打卡）
        r_comp = Report(
            id=uuid.uuid4(),
            pair_id=pair_id,
            type=ReportType.DAILY,
            status=ReportStatus.COMPLETED,
            report_date=d1,
            content={"summary": "包含了机密"},
        )
        db.add_all([c_priv, r_comp])
        await db.commit()

    summary = await audit_impact(engine)
    assert summary["total_completed_reports"] == 1
    assert summary["affected_reports_total"] == 1
    assert summary["affected_pair_count"] == 1
    print(">>> 审计脚本自测试通过 (Self-test passed)！")
    print_report(summary)
    await engine.dispose()


def main():
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="只读统计含 private 来源打卡的历史报告数量")
    parser.add_argument("--db-url", default=None, help="数据库连接 URL（默认取 settings.DATABASE_URL）")
    parser.add_argument("--self-test", action="store_true", help="使用内存数据库执行自测试")
    args = parser.parse_args()

    if args.self_test:
        asyncio.run(run_self_test())
        return

    db_url = args.db_url or settings.DATABASE_URL
    try:
        summary = asyncio.run(audit_impact(db_url))
        print_report(summary)
    except Exception as e:
        print(f"连接数据库执行审计失败（如数据库未启动）: {e}")
        print("提示：可使用 --self-test 验证脚本逻辑，或通过 --db-url 传入目标数据库 URL。")


if __name__ == "__main__":
    main()
