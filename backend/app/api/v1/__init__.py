from fastapi import APIRouter
from importlib import import_module

from .auth import router as auth_router
from .pairs import router as pairs_router
from .checkins import router as checkins_router
from .reports import router as reports_router
from .upload import router as upload_router
from .tree import router as tree_router
from .crisis import router as crisis_router
from .longdistance import router as longdistance_router
from .milestones import router as milestones_router
from .community import router as community_router
from .agent import router as agent_router


def _load_optional_router(module_name: str):
    try:
        return import_module(f"{__package__}.{module_name}").router
    except ModuleNotFoundError as exc:
        expected_names = {module_name, f"{__package__}.{module_name}"}
        if exc.name in expected_names:
            return None
        raise


tasks_router = _load_optional_router("tasks")
insights_router = _load_optional_router("insights")
admin_router = _load_optional_router("admin")
privacy_router = _load_optional_router("privacy")

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(pairs_router)
api_router.include_router(checkins_router)
api_router.include_router(reports_router)
api_router.include_router(upload_router)
api_router.include_router(tree_router)
api_router.include_router(crisis_router)
api_router.include_router(longdistance_router)
api_router.include_router(milestones_router)
api_router.include_router(community_router)
api_router.include_router(agent_router)
if tasks_router is not None:
    api_router.include_router(tasks_router)
if insights_router is not None:
    api_router.include_router(insights_router)
if admin_router is not None:
    api_router.include_router(admin_router)
if privacy_router is not None:
    api_router.include_router(privacy_router)
