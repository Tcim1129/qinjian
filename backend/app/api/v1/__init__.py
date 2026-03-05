from fastapi import APIRouter

from .auth import router as auth_router
from .pairs import router as pairs_router
from .checkins import router as checkins_router
from .reports import router as reports_router
from .upload import router as upload_router
from .tree import router as tree_router
from .crisis import router as crisis_router
from .tasks import router as tasks_router
from .longdistance import router as longdistance_router
from .milestones import router as milestones_router
from .community import router as community_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(pairs_router)
api_router.include_router(checkins_router)
api_router.include_router(reports_router)
api_router.include_router(upload_router)
api_router.include_router(tree_router)
api_router.include_router(crisis_router)
api_router.include_router(tasks_router)
api_router.include_router(longdistance_router)
api_router.include_router(milestones_router)
api_router.include_router(community_router)
