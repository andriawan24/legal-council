"""
Agent Orchestrator - Coordinates AI agents in deliberation.

Determines which agents should respond based on context,
manages agent interactions, and handles response generation.
"""

import asyncio
import logging
from typing import Any

from agents.base import AgentResponse, AgentContext, BaseAgent
from agents.strict import StrictConstructionistAgent
from agents.humanist import HumanistAgent
from agents.historian import HistorianAgent
from schemas import (
    AgentId,
    ParsedCaseInput,
    SimilarCase,
    DeliberationMessage,
    MessageIntent,
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates AI agent responses during deliberation.

    Responsibilities:
    - Determine which agents should respond
    - Generate coordinated responses
    - Handle agent reactions to each other
    - Manage conversation flow
    """

    def __init__(self):
        """Initialize the orchestrator with all agents."""
        self.agents: dict[AgentId, BaseAgent] = {
            AgentId.STRICT: StrictConstructionistAgent(),
            AgentId.HUMANIST: HumanistAgent(),
            AgentId.HISTORIAN: HistorianAgent(),
        }

        # Track which agent spoke last for rotation
        self._last_speaker: AgentId | None = None
        self._speaker_counts: dict[AgentId, int] = {
            AgentId.STRICT: 0,
            AgentId.HUMANIST: 0,
            AgentId.HISTORIAN: 0,
        }

    def determine_responding_agents(
        self,
        user_message: str,
        target_agent: AgentId | str | None,
        conversation_history: list[DeliberationMessage],
    ) -> list[AgentId]:
        """
        Determine which agent(s) should respond to the user's message.

        Args:
            user_message: The user's input
            target_agent: Explicit agent target (or "all")
            conversation_history: Previous messages

        Returns:
            List of agent IDs that should respond
        """
        message_lower = user_message.lower()

        # If user explicitly targets "all" agents
        if target_agent == "all" or any(
            phrase in message_lower
            for phrase in [
                "semua hakim",
                "all judges",
                "everyone",
                "pendapat semua",
                "bagaimana menurut kalian",
            ]
        ):
            return list(self.agents.keys())

        # If user targets a specific agent
        if target_agent and target_agent in AgentId.__members__.values():
            return [AgentId(target_agent)]

        # Check for direct agent mentions in message
        responding_agents: list[AgentId] = []

        for agent_id, agent in self.agents.items():
            if agent.should_respond_to(user_message):
                responding_agents.append(agent_id)

        # If no specific trigger, use rotation based on who spoke least
        if not responding_agents:
            responding_agents = [self._select_next_speaker(conversation_history)]

        return responding_agents

    def _select_next_speaker(
        self, conversation_history: list[DeliberationMessage]
    ) -> AgentId:
        """Select the next speaker based on rotation and recency."""
        # Count recent agent messages
        recent_speakers: dict[AgentId, int] = {
            AgentId.STRICT: 0,
            AgentId.HUMANIST: 0,
            AgentId.HISTORIAN: 0,
        }

        for msg in conversation_history[-6:]:  # Last 6 messages
            if hasattr(msg.sender, "agent_id"):
                agent_id = msg.sender.agent_id
                if agent_id in recent_speakers:
                    recent_speakers[agent_id] += 1

        # Return the agent who has spoken least recently
        min_count = min(recent_speakers.values())
        candidates = [
            agent_id
            for agent_id, count in recent_speakers.items()
            if count == min_count
        ]

        # Prefer historian for general questions (provides facts)
        if AgentId.HISTORIAN in candidates:
            return AgentId.HISTORIAN

        return candidates[0]

    def check_for_reactions(
        self,
        last_response: AgentResponse,
        conversation_history: list[DeliberationMessage],
    ) -> list[AgentId]:
        """
        Check if any agents want to react to the last response.

        Args:
            last_response: The most recent agent response
            conversation_history: Full conversation history

        Returns:
            List of agent IDs that want to react
        """
        reacting_agents: list[AgentId] = []

        # Create a mock message from the last response
        mock_message = DeliberationMessage(
            id="temp",
            session_id="temp",
            sender={"type": "agent", "agent_id": last_response.agent_id},
            content=last_response.content,
            timestamp=None,
        )

        for agent_id, agent in self.agents.items():
            # Don't react to yourself
            if agent_id == last_response.agent_id:
                continue

            if agent.should_react_to(mock_message):
                reacting_agents.append(agent_id)

        return reacting_agents

    async def generate_responses(
        self,
        user_message: str,
        target_agent: AgentId | str | None,
        parsed_case: ParsedCaseInput | None,
        similar_cases: list[SimilarCase],
        case_statistics: dict[str, Any] | None,
        conversation_history: list[DeliberationMessage],
    ) -> list[AgentResponse]:
        """
        Generate responses from appropriate agents.

        Args:
            user_message: The user's input
            target_agent: Optional specific agent target
            parsed_case: Parsed case information
            similar_cases: Similar cases from database
            case_statistics: Case statistics
            conversation_history: Previous messages

        Returns:
            List of agent responses
        """
        # Build case summary from parsed case
        case_summary = self._build_case_summary(parsed_case, similar_cases)

        # Create context for agents
        context = AgentContext(
            case_summary=case_summary,
            parsed_case=parsed_case,
            similar_cases=similar_cases,
            case_statistics=case_statistics,
            conversation_history=conversation_history,
            user_message=user_message,
        )

        # Determine which agents should respond
        responding_agent_ids = self.determine_responding_agents(
            user_message, target_agent, conversation_history
        )

        logger.info(f"Agents responding: {responding_agent_ids}")

        # Generate responses (in parallel if multiple agents)
        responses: list[AgentResponse] = []

        if len(responding_agent_ids) == 1:
            # Single agent - straightforward response
            agent = self.agents[responding_agent_ids[0]]
            response = await agent.generate_response(context)
            responses.append(response)
        else:
            # Multiple agents - parallel generation
            tasks = []
            for agent_id in responding_agent_ids:
                agent = self.agents[agent_id]
                tasks.append(agent.generate_response(context))

            responses = await asyncio.gather(*tasks)

        # Check for reactive responses (limit to avoid infinite loops)
        if len(responses) == 1 and len(conversation_history) > 2:
            reacting_ids = self.check_for_reactions(
                responses[0], conversation_history
            )
            if reacting_ids:
                # Allow one reaction
                reacting_agent = self.agents[reacting_ids[0]]
                # Update context with the new response
                context.user_message = (
                    f"[Responding to {responses[0].agent_id.value}] "
                    f"{responses[0].content[:200]}..."
                )
                reaction = await reacting_agent.generate_response(context)
                responses.append(reaction)

        return responses

    def _build_case_summary(
        self,
        parsed_case: ParsedCaseInput | None,
        similar_cases: list[SimilarCase],
    ) -> str:
        """Build a textual summary of the case for agents."""
        if not parsed_case:
            return "No case details provided yet."

        summary_parts = [
            f"Case Type: {parsed_case.case_type.value}",
            f"Summary: {parsed_case.summary}",
        ]

        if parsed_case.defendant_profile:
            profile = parsed_case.defendant_profile
            summary_parts.append(
                f"Defendant: {'First offender' if profile.is_first_offender else 'Repeat offender'}"
            )
            if profile.age:
                summary_parts.append(f"Age: {profile.age}")

        if parsed_case.key_facts:
            summary_parts.append(f"Key Facts: {', '.join(parsed_case.key_facts[:5])}")

        if parsed_case.charges:
            summary_parts.append(f"Charges: {', '.join(parsed_case.charges[:3])}")

        if parsed_case.narcotics:
            n = parsed_case.narcotics
            summary_parts.append(
                f"Narcotics Details: {n.substance}, {n.weight_grams}g, Intent: {n.intent.value}"
            )

        if parsed_case.corruption:
            c = parsed_case.corruption
            summary_parts.append(
                f"Corruption Details: State loss IDR {c.state_loss_idr:,.0f}"
            )
            if c.position:
                summary_parts.append(f"Position: {c.position}")

        return "\n".join(summary_parts)

    def get_initial_message_content(
        self,
        parsed_case: ParsedCaseInput,
        similar_cases: list[SimilarCase],
    ) -> str:
        """Generate the initial system message for a new session."""
        case_type_names = {
            "narcotics": "Narkotika",
            "corruption": "Korupsi",
            "general_criminal": "Pidana Umum",
            "other": "Lainnya",
        }

        case_type_display = case_type_names.get(
            parsed_case.case_type.value, parsed_case.case_type.value
        )

        msg = f"""Selamat datang di Ruang Musyawarah Hakim (Virtual Deliberation Room).

**Perkara yang akan dibahas:**
- Jenis: {case_type_display}
- Ringkasan: {parsed_case.summary[:200]}{'...' if len(parsed_case.summary) > 200 else ''}

**Panel Hakim:**
1. **Hakim Penafsir Ketat** - Menekankan penafsiran hukum secara tekstual
2. **Hakim Rehabilitatif** - Mempertimbangkan aspek kemanusiaan dan pemulihan
3. **Hakim Ahli Yurisprudensi** - Membandingkan dengan preseden dan statistik

**Kasus Serupa Ditemukan:** {len(similar_cases)} kasus

Anda dapat:
- Bertanya kepada semua hakim atau hakim tertentu
- Meminta pendapat tentang aspek tertentu dari kasus
- Meminta perbandingan dengan kasus serupa
- Mengajukan argumen untuk dibahas

Silakan mulai musyawarah dengan pertanyaan atau pernyataan Anda."""

        return msg
