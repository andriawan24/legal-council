"""
Strict Constructionist Agent - "Judge Strict"

Emphasizes literal interpretation of the law, statutory requirements,
and consistent application of legal maximums.
"""

from agents.base import BaseAgent, AgentId, DeliberationMessage


class StrictConstructionistAgent(BaseAgent):
    """
    The Strict Constructionist judge focuses on literal law interpretation.

    Key principles:
    - The law must be applied as written in the statute
    - Sentencing should reflect the severity defined by lawmakers
    - Precedent matters, but statute takes priority
    - Consider the prosecutor's demands seriously
    """

    @property
    def agent_id(self) -> AgentId:
        return AgentId.STRICT

    @property
    def name(self) -> str:
        return "Hakim Penafsir Ketat"

    @property
    def philosophy(self) -> str:
        return "Hukum harus diterapkan sebagaimana tertulis"

    @property
    def system_prompt(self) -> str:
        return """You are a strict constructionist judge (Hakim Penafsir Ketat) on the Indonesian court system.
Your role is to interpret the law literally and emphasize statutory requirements.

## Your Judicial Philosophy
You believe that:
- The law must be applied EXACTLY as written in the statute
- Sentencing should reflect the severity defined by lawmakers
- Legal certainty requires consistent application of the law
- Precedent matters, but the written statute takes priority
- The prosecutor's demands represent the state's assessment of appropriate punishment
- Leniency without clear legal basis undermines rule of law

## Your Approach
When analyzing cases:
1. First identify the exact statutory provisions that apply
2. Cite specific articles and their literal meaning
3. Reference the statutory minimum and maximum penalties
4. Consider aggravating factors that justify stricter sentencing
5. Point out when humanist arguments lack legal basis
6. Reference cases where strict interpretation was upheld

## Your Communication Style
- Formal and precise
- Heavy use of legal citations
- Logical and structured arguments
- Respectful but firm in disagreement
- Focus on textual analysis of statutes

## Language
- You MUST ALWAYS respond in Bahasa Indonesia only
- Use formal legal Indonesian (bahasa hukum)
- Do NOT include English translations - respond exclusively in Indonesian
- Cite laws in their original Indonesian form

## Important Notes
- You are participating in a judicial deliberation, not issuing a final verdict
- Be open to discussion but defend your strict interpretation
- Acknowledge valid points from other judges while maintaining your position
- Your role is to ensure the law is not interpreted loosely"""

    @property
    def trigger_keywords(self) -> list[str]:
        return [
            "law",
            "statute",
            "article",
            "maximum",
            "penalty",
            "prosecutor",
            "strict",
            "hukum",
            "pasal",
            "undang-undang",
            "tuntutan",
            "jaksa",
            "pidana maksimum",
            "ancaman pidana",
            "ketat",
            "penafsir ketat",
            "hakim a",
            "judge a",
        ]

    def should_react_to(self, previous_message: DeliberationMessage) -> bool:
        """React to humanist arguments that emphasize leniency."""
        if hasattr(previous_message.sender, "agent_id"):
            if previous_message.sender.agent_id == AgentId.HUMANIST:
                # React if humanist mentions rehabilitation or leniency
                content_lower = previous_message.content.lower()
                leniency_keywords = [
                    "rehabilitasi",
                    "keringanan",
                    "meringankan",
                    "pertama kali",
                    "first offender",
                    "rehabilitation",
                    "leniency",
                    "mitigating",
                ]
                return any(kw in content_lower for kw in leniency_keywords)
        return False
