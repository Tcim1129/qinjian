"""测试 Agent Skill 路由 (/api/v1/agent/skill/*)。"""

import uuid
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.agent import skill_analyze, skill_select_proposal, skill_review, skill_memories
from app.core.database import Base
from app.models import User, Pair, PairType, PairStatus, SkillAnalysisRecord
from app.ai.skill_delivery import DeliveryPackage, ProblemSummary, ActionProposal, StanceCard


@pytest.mark.asyncio
async def test_agent_skill_routes_flow(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as db:
        user = User(email="skill_routes@qinjian.com", nickname="测试者", password_hash="hash")
        partner = User(email="partner_skill@qinjian.com", nickname="伴侣", password_hash="hash")
        db.add_all([user, partner])
        await db.flush()

        pair = Pair(
            user_a_id=user.id,
            user_b_id=partner.id,
            type=PairType.COUPLE,
            status=PairStatus.ACTIVE,
            invite_code="SKILLTESTCODE",
        )
        db.add(pair)
        await db.commit()

        # Mock orchestrate
        async def mock_orchestrate(content, **kwargs):
            pkg = DeliveryPackage(
                primary_intent="resolve",
                is_complex=True,
                summary=ProblemSummary(user_emotion="纠结", core_need="达成共识"),
                stances=[StanceCard(person="我", position="想早点定"), StanceCard(person="对方", position="等等看")],
                proposals=[ActionProposal(id="A", title="方案A：折中计划", description="先定机票后定酒店")],
                memories_to_save=[{"type": "event", "subject": "假期行程讨论", "content": "关于出行节奏的分歧", "importance": 3}],
            )
            return pkg

        async def mock_generate_draft(content, proposal_id, **kwargs):
            return {
                "drafts": [{"style": "温和版", "content": "亲爱的，关于假期我们这么定如何？"}],
                "opening_line": "在忙吗？想跟你聊两句假期的事情",
            }

        from app.ai.skill_registry import SkillOutput

        async def mock_execute_skill(skill, context, previous_results):
            if skill.name == "review":
                return SkillOutput(
                    skill_name="review",
                    success=True,
                    data={"lesson": "多倾听，不预设立场", "what_worked": ["及时沟通"]},
                )
            if skill.name == "memory_write":
                return SkillOutput(
                    skill_name="memory_write",
                    success=True,
                    data={"memories": [{"type": "strategy", "subject": "旅行预先规划", "content": "提前两周对齐预算与行程", "importance": 4}]},
                )
            return SkillOutput(skill_name=skill.name, success=True, data={})

        monkeypatch.setattr("app.ai.skill_orchestrator.orchestrate", mock_orchestrate)
        monkeypatch.setattr("app.ai.skill_orchestrator.generate_draft_for_proposal", mock_generate_draft)
        monkeypatch.setattr("app.ai.skill_registry.execute_skill", mock_execute_skill)

        # 1. 调用 skill_analyze
        analyze_resp = await skill_analyze(
            pair_id=pair.id,
            content="我们因为下个月的旅行安排又产生分歧了，我特别焦虑",
            user=user,
            db=db,
        )
        assert "record_id" in analyze_resp
        assert "delivery" in analyze_resp
        assert analyze_resp["delivery"]["primary_intent"] == "resolve"
        assert len(analyze_resp["delivery"]["proposals"]) == 1

        record_id = uuid.UUID(analyze_resp["record_id"])

        # 2. 调用 skill_select_proposal
        proposal_resp = await skill_select_proposal(
            pair_id=pair.id,
            record_id=record_id,
            proposal_id="A",
            user=user,
            db=db,
        )
        assert proposal_resp["proposal_id"] == "A"
        assert "draft" in proposal_resp
        assert len(proposal_resp["draft"]["drafts"]) >= 1

        # 验证数据库中记录被更新
        rec = await db.get(SkillAnalysisRecord, record_id)
        assert rec.selected_proposal_id == "A"
        assert rec.delivery_json.get("draft") is not None

        # 3. 调用 skill_review
        review_resp = await skill_review(
            pair_id=pair.id,
            content="后来我们按照方案A沟通了，虽然还是有点波折但最终订好了",
            record_id=record_id,
            user=user,
            db=db,
        )
        assert "review" in review_resp

        # 4. 调用 skill_memories
        memories_resp = await skill_memories(
            pair_id=pair.id,
            query="假期",
            user=user,
            db=db,
        )
        assert "memories" in memories_resp
        assert len(memories_resp["memories"]) >= 1
        assert any(m["subject"] == "假期行程讨论" for m in memories_resp["memories"])
