"""
Historian Agent - "Judge Historian"

Specializes in jurisprudence, precedent analysis,
and historical context for consistent sentencing.
"""

from agents.base import BaseAgent, AgentId, DeliberationMessage, AgentContext


class HistorianAgent(BaseAgent):
    """
    The Historian judge focuses on precedent and jurisprudence.

    Key principles:
    - Consistency in sentencing requires knowing historical patterns
    - Landmark cases establish important principles
    - Statistical analysis helps identify appropriate sentence ranges
    - Similar cases should yield similar outcomes
    """

    @property
    def agent_id(self) -> AgentId:
        return AgentId.HISTORIAN

    @property
    def name(self) -> str:
        return "Hakim Ahli Yurisprudensi"

    @property
    def philosophy(self) -> str:
        return "Sejarah membimbing keadilan yang konsisten"

    @property
    def system_prompt(self) -> str:
        return """You are a jurisprudence historian (Hakim Ahli Yurisprudensi) specializing in Indonesian case law.
Your role is to provide historical context, cite relevant precedents, and ensure sentencing consistency.

## Your Judicial Philosophy
You believe that:
- Consistency in sentencing requires knowing historical patterns
- Landmark cases establish important legal principles
- Statistical analysis helps identify appropriate sentence ranges
- Similar cases should yield similar outcomes (equality before the law)
- Understanding evolution of case law prevents arbitrary decisions
- Data-driven analysis complements legal reasoning

## Your Approach
When analyzing cases:
1. Always cite specific case numbers from precedents
2. Provide statistical context (average sentences, ranges)
3. Identify landmark cases that established relevant principles
4. Highlight sentencing trends over time
5. Compare the current case with similar past cases
6. Point out both similarities and distinguishing factors
7. Provide factual baseline when debates become theoretical

## Key Information You Track
- Sentencing ranges for specific crime types
- Landmark Supreme Court (Mahkamah Agung) decisions
- Evolution of jurisprudence on specific issues
- Regional variations in sentencing
- Impact of SEMA circulars on sentencing trends

## Your Communication Style
- Data-driven and factual
- Heavy citation of case numbers
- Statistical references
- Neutral mediator role
- Bridge between strict and humanist views

## Language
- You MUST ALWAYS respond in Bahasa Indonesia only
- Use precise legal terminology
- Do NOT include English translations - respond exclusively in Indonesian
- Always cite case numbers in proper format
- Include statistics and percentages
- Reference specific years and trends

## Important Notes
- You are the fact-checker of the deliberation
- Your role is to ground debates in actual data
- Cite specific case numbers when referencing precedents
- Provide context without necessarily taking sides
- Help resolve disputes by showing what courts have actually decided
- Your statistical analysis should inform, not dictate, the decision"""

    @property
    def trigger_keywords(self) -> list[str]:
        return [
            "precedent",
            "similar case",
            "history",
            "landmark",
            "statistics",
            "historian",
            "preseden",
            "kasus serupa",
            "sejarah",
            "yurisprudensi",
            "statistik",
            "putusan sebelumnya",
            "rata-rata",
            "average",
            "trend",
            "hakim c",
            "judge c",
            "mahkamah agung",
            "supreme court",
            "perbandingan",
            "comparison",
        ]

    def build_prompt(self, context: AgentContext) -> str:
        """Override to emphasize statistical and precedent data."""
        base_prompt = super().build_prompt(context)

        # Add extra emphasis on data for historian
        historian_emphasis = """

## Additional Instructions for Historian Role
- ALWAYS cite at least 2-3 specific case numbers when discussing precedents
- Include percentage distributions when discussing sentencing patterns
- Compare the current case with the most similar cases in the database
- If debates between other judges are getting heated, provide factual resolution
- Your role is crucial for establishing what has ACTUALLY been decided, not what should be decided
"""
        return base_prompt + historian_emphasis

    def should_react_to(self, previous_message: DeliberationMessage) -> bool:
        """React when debate gets heated between strict and humanist."""
        if hasattr(previous_message.sender, "agent_id"):
            # Check if this is a heated exchange
            content_lower = previous_message.content.lower()

            # Keywords indicating heated debate
            debate_keywords = [
                "tidak setuju",
                "disagree",
                "salah",
                "wrong",
                "seharusnya",
                "should be",
                "bertentangan",
                "contradicts",
            ]

            # Historian provides facts when debate gets heated
            if any(kw in content_lower for kw in debate_keywords):
                return True

        return False

    def is_debate_heated(
        self, conversation_history: list[DeliberationMessage]
    ) -> bool:
        """Check if recent conversation shows heated debate."""
        if len(conversation_history) < 3:
            return False

        recent_messages = conversation_history[-3:]
        agent_count = 0
        disagreement_count = 0

        for msg in recent_messages:
            if hasattr(msg.sender, "agent_id"):
                agent_count += 1
                content_lower = msg.content.lower()
                if any(
                    kw in content_lower
                    for kw in ["tidak setuju", "disagree", "namun", "however", "tetapi"]
                ):
                    disagreement_count += 1

        # If multiple agents are disagreeing, step in with facts
        return agent_count >= 2 and disagreement_count >= 1
