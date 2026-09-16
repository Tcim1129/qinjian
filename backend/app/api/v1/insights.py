"""Relationship insights API."""

from fastapi import APIRouter

from .insights_routes import (
    alignment,
    assessments,
    interaction,
    methodology,
    plans,
    playbook,
    profile,
    safety,
    timeline,
)

router = APIRouter(prefix="/insights")

for child_router in (
    safety.router,
    assessments.router,
    profile.router,
    interaction.router,
    timeline.router,
    plans.router,
    playbook.router,
    methodology.router,
    alignment.router,
):
    router.include_router(child_router)


_timeline_impact_modules_for_event = timeline._timeline_impact_modules_for_event
