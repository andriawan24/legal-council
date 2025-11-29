"""
API Routers for Legal Council.

Organized by domain:
- sessions: Deliberation session management
- cases: Case search and retrieval
- deliberation: Chat/message handling
"""

from routers.sessions import router as sessions_router
from routers.cases import router as cases_router
from routers.deliberation import router as deliberation_router

__all__ = [
    "sessions_router",
    "cases_router",
    "deliberation_router",
]
