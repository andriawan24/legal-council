"""
Base agent class for Legal Council AI agents.

Provides common functionality and interface for all judicial agents.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

from config import get_settings
from schemas import AgentId, ParsedCaseInput, SimilarCase, DeliberationMessage

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from an AI agent."""

    agent_id: AgentId
    content: str
    cited_cases: list[str] = field(default_factory=list)
    cited_laws: list[str] = field(default_factory=list)
    intent: str | None = None


@dataclass
class AgentContext:
    """Context provided to agents for generating responses."""

    case_summary: str
    parsed_case: ParsedCaseInput | None
    similar_cases: list[SimilarCase]
    case_statistics: dict[str, Any] | None
    conversation_history: list[DeliberationMessage]
    user_message: str


class BaseAgent(ABC):
    """Abstract base class for judicial AI agents."""

    def __init__(self):
        """Initialize the agent with Vertex AI."""
        settings = get_settings()
        vertexai.init(project=settings.gcp_project, location=settings.gcp_region)
        self.model = GenerativeModel(settings.vertex_ai_model)
        self.generation_config = GenerationConfig(
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=2048,
        )

    @property
    @abstractmethod
    def agent_id(self) -> AgentId:
        """Return the agent's identifier."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the agent's display name."""
        pass

    @property
    @abstractmethod
    def philosophy(self) -> str:
        """Return the agent's legal philosophy."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the agent's system prompt."""
        pass

    def build_prompt(self, context: AgentContext) -> str:
        """Build the full prompt for the agent."""
        # Format conversation history
        history_text = ""
        if context.conversation_history:
            history_lines = []
            for msg in context.conversation_history[-10:]:  # Last 10 messages
                sender_name = self._get_sender_name(msg.sender)
                history_lines.append(f"{sender_name}: {msg.content}")
            history_text = "\n".join(history_lines)

        # Format similar cases
        similar_cases_text = ""
        if context.similar_cases:
            cases_lines = []
            for case in context.similar_cases[:5]:  # Top 5 similar cases
                cases_lines.append(
                    f"- Case {case.case_number}: {case.verdict_summary} "
                    f"(Sentence: {case.sentence_months} months, "
                    f"Similarity: {case.similarity_score:.0%})"
                )
            similar_cases_text = "\n".join(cases_lines)

        # Format case statistics
        stats_text = ""
        if context.case_statistics:
            dist = context.case_statistics.get("sentence_distribution", {})
            stats_text = (
                f"Based on {context.case_statistics.get('total_cases', 0)} similar cases:\n"
                f"- Average sentence: {dist.get('average_months', 0)} months\n"
                f"- Median sentence: {dist.get('median_months', 0)} months\n"
                f"- Range: {dist.get('min_months', 0)} - {dist.get('max_months', 0)} months"
            )

        prompt = f"""{self.system_prompt}

## Current Case Context
{context.case_summary}

## Similar Cases from Database
{similar_cases_text or "No similar cases found."}

## Case Statistics
{stats_text or "No statistics available."}

## Conversation History
{history_text or "This is the start of the deliberation."}

## User Message
{context.user_message}

Please respond to the user's message from your judicial perspective.
Be specific, cite relevant laws or precedents when applicable, and maintain your philosophical stance.
Respond in a conversational but professional manner, as if speaking in a judicial chamber.
If you cite specific cases or laws, mention them clearly.

IMPORTANT: You MUST respond in Bahasa Indonesia. All your responses must be in Indonesian language.
"""
        return prompt

    def _get_sender_name(self, sender: Any) -> str:
        """Get display name for a message sender."""
        if hasattr(sender, "type"):
            if sender.type == "user":
                return "Presiding Judge"
            elif sender.type == "agent":
                agent_names = {
                    AgentId.STRICT: "Judge Strict",
                    AgentId.HUMANIST: "Judge Humanist",
                    AgentId.HISTORIAN: "Judge Historian",
                }
                return agent_names.get(sender.agent_id, "Judge")
            elif sender.type == "system":
                return "System"
        return "Unknown"

    async def generate_response(self, context: AgentContext) -> AgentResponse:
        """Generate a response to the user's message."""
        prompt = self.build_prompt(context)

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.generation_config,
            )

            content = response.text

            # Extract cited cases and laws from response
            cited_cases = self._extract_cited_cases(content)
            cited_laws = self._extract_cited_laws(content)

            return AgentResponse(
                agent_id=self.agent_id,
                content=content,
                cited_cases=cited_cases,
                cited_laws=cited_laws,
                intent="provide_analysis",
            )

        except Exception as e:
            logger.error(f"Error generating response from {self.name}: {e}")
            return AgentResponse(
                agent_id=self.agent_id,
                content=f"I apologize, but I encountered an issue while formulating my response. Please try again.",
                cited_cases=[],
                cited_laws=[],
                intent=None,
            )

    async def generate_response_stream(
        self, context: AgentContext
    ) -> AsyncIterator[str]:
        """Generate a streaming response to the user's message."""
        prompt = self.build_prompt(context)

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.generation_config,
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Error streaming response from {self.name}: {e}")
            yield f"I apologize, but I encountered an issue while formulating my response."

    def _extract_cited_cases(self, content: str) -> list[str]:
        """Extract cited case numbers from response content."""
        import re

        # Match Indonesian case number patterns
        patterns = [
            r"\d+/Pid\.Sus/\d{4}/PN\s*[\w\.]+",  # Criminal cases
            r"\d+/Pid\.B/\d{4}/PN\s*[\w\.]+",
            r"\d+/Pdt\.G/\d{4}/PN\s*[\w\.]+",  # Civil cases
            r"Putusan\s+(?:MA\s+)?No\.?\s*\d+[A-Z]*/[A-Z\.]+/\d{4}",  # Supreme Court
        ]

        cited = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            cited.extend(matches)

        return list(set(cited))  # Remove duplicates

    def _extract_cited_laws(self, content: str) -> list[str]:
        """Extract cited law references from response content."""
        import re

        # Match Indonesian law patterns
        patterns = [
            r"UU\s+No\.?\s*\d+\s+Tahun\s+\d{4}",  # Undang-Undang
            r"Pasal\s+\d+(?:\s+[Aa]yat\s*\(\d+\))?",  # Pasal
            r"SEMA\s+No\.?\s*\d+(?:/\d{4})?",  # Surat Edaran MA
            r"PERMA\s+No\.?\s*\d+(?:/\d{4})?",  # Peraturan MA
            r"PP\s+No\.?\s*\d+\s+Tahun\s+\d{4}",  # Peraturan Pemerintah
        ]

        cited = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            cited.extend(matches)

        return list(set(cited))  # Remove duplicates

    def should_respond_to(self, user_message: str) -> bool:
        """Determine if this agent should respond to the user's message."""
        message_lower = user_message.lower()

        # Check for direct mentions
        if self.agent_id.value in message_lower:
            return True

        # Check for philosophical keywords
        return any(keyword in message_lower for keyword in self.trigger_keywords)

    @property
    @abstractmethod
    def trigger_keywords(self) -> list[str]:
        """Keywords that trigger this agent to respond."""
        pass

    def should_react_to(self, previous_message: DeliberationMessage) -> bool:
        """Determine if this agent should react to another agent's message."""
        # Default: don't react unless overridden
        return False
