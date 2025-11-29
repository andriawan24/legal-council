"""
AI Agents for Legal Council deliberation.

Three distinct judicial personas for balanced deliberation:
- Strict Constructionist: Literal law interpretation
- Humanist: Rehabilitative justice focus
- Historian: Precedent and jurisprudence expert
"""

from agents.base import AgentResponse
from agents.orchestrator import AgentOrchestrator
from agents.strict import StrictConstructionistAgent
from agents.humanist import HumanistAgent
from agents.historian import HistorianAgent

__all__ = [
    "AgentOrchestrator",
    "AgentResponse",
    "StrictConstructionistAgent",
    "HumanistAgent",
    "HistorianAgent",
]
