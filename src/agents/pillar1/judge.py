"""
JUDGE - Investor Agent

Plays the role of a skeptical but fair seed investor. Asks hard questions,
identifies real risks, and gives an honest fundability score grounded in
context from all other agents.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are JUDGE, the Investor Agent for Helix.

## Who You Are
Alright, I'm Judge — the investor perspective. I've been on both sides of the table —
founded companies and written checks. I give the feedback most investors won't say
out loud. I'm tough because I've seen what happens when founders don't hear the hard
truth early. But I'm fair — even a weak pitch has a path forward.

## How You Communicate
- Open with what genuinely caught your attention — one honest sentence
- Name the single biggest concern before anything else. Don't bury it.
- Ask 2-3 hard questions an investor would actually ask
- Give a fundability score (1-10) with clear reasoning
- End with the one thing that would move the needle most

## What You Cover (naturally, not as a checklist)
1. What's genuinely compelling — investors get excited too
2. The single biggest risk you'd lose sleep over
3. 2-3 hard questions with context for why they matter
4. What this is competing with (including "do nothing")
5. Fundability score 1-10 with honest reasoning
6. One concrete action to make this more fundable

## How to Use Cross-Agent Context
- If ARIA flagged high complexity, factor into fundability (execution risk)
- If FELIX's burn is high relative to traction, flag it
- If NOVA's positioning is weak, challenge the go-to-market thesis
- Connect the dots — that's what good investors do

## CRITICAL: Wrap-Up at the End
Since you're the last agent, wrap up the whole session:
"That's my investor take. You've now heard from the whole team — Aria on tech, Felix
on finances, Nova on marketing, and me on fundability. Any questions for any of us,
or would you like to move forward with building this?"

Offer next steps like:
- "Ready to take this to Pillar 2 and start building?"
- "Want to refine anything based on what you've heard?"
- "Any questions before we wrap up?"

## What You Never Do
- Never give a score without reasoning
- Never list every possible risk — pick the real ones
- Never end on pure negativity
- Never forget to wrap up and offer next steps"""


class JudgeAgent(BaseAgent):
    """JUDGE - Investor Agent for fundability assessment."""

    def __init__(self):
        super().__init__(
            role=AgentRole.JUDGE,
            name="JUDGE",
            description="Investor Agent - Critical evaluation and fundability assessment",
            system_prompt=JUDGE_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        self._register_judge_tools()

    def _register_judge_tools(self) -> None:
        self.register_tool(Tool(
            name="validate_market_size",
            description="Validate market size claims and surface key assumptions to challenge",
            parameters={
                "market_claim": {"type": "string"},
                "industry": {"type": "string"},
            },
            handler=self._validate_market_size,
        ))

        self.register_tool(Tool(
            name="analyze_competitive_threats",
            description="Analyze competitive threats and barriers to entry",
            parameters={
                "product_description": {"type": "string"},
                "market": {"type": "string"},
            },
            handler=self._analyze_competitive_threats,
        ))

        self.register_tool(Tool(
            name="calculate_fundability_score",
            description="Calculate a structured fundability score based on key dimensions",
            parameters={
                "market_size": {
                    "type": "string",
                    "enum": ["small", "medium", "large", "massive"],
                },
                "team_strength": {
                    "type": "string",
                    "enum": ["weak", "average", "strong", "exceptional"],
                },
                "differentiation": {
                    "type": "string",
                    "enum": ["none", "weak", "moderate", "strong"],
                },
                "traction": {
                    "type": "string",
                    "enum": ["none", "early", "growing", "strong"],
                },
                "timing": {
                    "type": "string",
                    "enum": ["too_early", "early", "right", "late"],
                },
            },
            handler=self._calculate_fundability_score,
        ))

    async def _validate_market_size(
        self, market_claim: str, industry: str
    ) -> Dict[str, Any]:
        return {
            "market_claim": market_claim,
            "investor_questions": [
                "What's the SAM (serviceable addressable market), not the TAM?",
                "What share of SAM can you realistically win in year 3?",
                "Is this market growing, flat, or declining — and why?",
            ],
            "red_flags": [
                "Top-down TAM without bottom-up validation",
                "Growth rate projections without cited source",
                "Global TAM when product only works in one geography",
            ],
            "recommendation": "Bottom-up: count the customers, multiply by price, that's your real market.",
        }

    async def _analyze_competitive_threats(
        self, product_description: str, market: str
    ) -> Dict[str, Any]:
        return {
            "threat_categories": [
                {
                    "category": "Existing incumbents",
                    "question": "Why haven't they already built this feature?",
                },
                {
                    "category": "Well-funded startups",
                    "question": "Who else is raising money to solve this right now?",
                },
                {
                    "category": "The 'do nothing' option",
                    "question": "Why do customers switch at all? What's the trigger?",
                },
                {
                    "category": "Big tech",
                    "question": "If this works, why can't Google/Microsoft ship it in 6 months?",
                },
            ],
            "moat_checklist": [
                "Network effects (does it get better as more people use it?)",
                "Data advantage (does usage create defensible training data?)",
                "Switching costs (how painful is it to leave?)",
                "Brand/trust (is trust a competitive barrier in this market?)",
            ],
        }

    async def _calculate_fundability_score(
        self,
        market_size: str,
        team_strength: str,
        differentiation: str,
        traction: str,
        timing: str,
    ) -> Dict[str, Any]:
        weights = {
            "market_size":    {"small": 1, "medium": 2, "large": 3, "massive": 4},
            "team_strength":  {"weak": 1, "average": 2, "strong": 3, "exceptional": 4},
            "differentiation":{"none": 0, "weak": 1, "moderate": 2, "strong": 3},
            "traction":       {"none": 0, "early": 1, "growing": 2, "strong": 3},
            "timing":         {"too_early": 1, "early": 2, "right": 3, "late": 1},
        }

        scores = {
            "market":  weights["market_size"][market_size] * 2.5,
            "team":    weights["team_strength"][team_strength] * 2.0,
            "diff":    weights["differentiation"][differentiation] * 1.5,
            "traction":weights["traction"][traction] * 2.0,
            "timing":  weights["timing"][timing] * 1.0,
        }

        total = sum(scores.values())
        max_score = 4*2.5 + 4*2.0 + 3*1.5 + 3*2.0 + 3*1.0  # 31.5
        fundability = round((total / max_score) * 10, 1)

        verdict = (
            "Highly Fundable" if fundability >= 8
            else "Fundable with work" if fundability >= 6
            else "Needs significant improvement" if fundability >= 4
            else "Not currently fundable"
        )

        return {
            "fundability_score": fundability,
            "verdict": verdict,
            "breakdown": scores,
            "lowest_scoring_dimension": min(scores, key=scores.get),
            "highest_scoring_dimension": max(scores, key=scores.get),
        }

    async def execute(self, context: AgentContext) -> AgentResponse:
        logger.info(f"JUDGE evaluating: {context.user_input[:100]}...")

        # ── Pull full cross-agent context ─────────────────────────────────────
        aria_analysis = context.metadata.get("aria_analysis", "")
        felix_analysis = context.metadata.get("felix_analysis", "")
        nova_analysis = context.metadata.get("nova_analysis", "")
        intake_answers = context.metadata.get("intake_answers", {})

        intake_summary = (
            "\n".join(f"- {k.replace('_', ' ').title()}: {v}"
                      for k, v in intake_answers.items())
            if intake_answers else "No structured intake data."
        )

        # ── Build cross-agent signal summary for smarter evaluation ──────────
        signal_notes = []
        if aria_analysis and ("high complexity" in aria_analysis.lower() or "complex" in aria_analysis.lower()):
            signal_notes.append("ARIA flagged HIGH technical complexity — this is an execution risk.")
        if felix_analysis and "burn" in felix_analysis.lower():
            signal_notes.append("FELIX provided burn/runway projections — factor these into fundability.")
        if nova_analysis and ("broad" in nova_analysis.lower() or "crowded" in nova_analysis.lower()):
            signal_notes.append("NOVA flagged positioning challenges — question the go-to-market thesis.")

        cross_agent_signals = (
            "\n".join(f"- {s}" for s in signal_notes)
            if signal_notes else "No specific risk signals from other agents."
        )

        evaluation_prompt = f"""You're the investor evaluator for Helix. Give an honest assessment:

IDEA: {context.user_input}

FOUNDER CONTEXT:
{intake_summary}

TECHNICAL ANALYSIS (ARIA - CTO):
{aria_analysis if aria_analysis else "Not available."}

FINANCIAL ANALYSIS (FELIX - CFO):
{felix_analysis if felix_analysis else "Not available."}

MARKETING STRATEGY (NOVA - CMO):
{nova_analysis if nova_analysis else "Not available."}

CROSS-AGENT RISK SIGNALS:
{cross_agent_signals}

You have the full picture now. Give the honest investor take.

Start with what's genuinely compelling — name it. Then hit the single biggest risk.
Ask 2-3 hard questions a real investor would ask in a first meeting.
Use calculate_fundability_score to ground your score in structured criteria.
Explain your score in a paragraph — not just a number.
End with the one thing that would most move the needle if they addressed it.

Don't soften the hard parts. Don't be cruel about them either. Be the investor
they'll be glad they talked to before their first pitch meeting."""

        try:
            response = await self.invoke_model(
                prompt=evaluation_prompt,
                context=context,
                use_tools=True,
            )

            evaluation = response.get("text", "")
            reasoning = response.get("reasoning", "")

            # ── Structured extraction ─────────────────────────────────────────
            investor_metadata = await self.structured_extract(
                text=evaluation,
                schema={
                    "fundability_score": "integer 1-10",
                    "verdict": "string: one of Highly Fundable / Fundable with work / Needs improvement / Not currently fundable",
                    "hard_questions": "list of 2-3 hard questions as strings",
                    "biggest_risk": "string — the single biggest risk in one sentence",
                    "one_thing_to_fix": "string — the highest-leverage improvement",
                },
                context=context,
            )

            return self.format_response(
                content=evaluation,
                reasoning=reasoning,
                hitl_checkpoint=None,
                metadata={
                    "fundability_score": investor_metadata.get("fundability_score"),
                    "verdict": investor_metadata.get("verdict"),
                    "hard_questions": investor_metadata.get("hard_questions", []),
                    "biggest_risk": investor_metadata.get("biggest_risk"),
                    "one_thing_to_fix": investor_metadata.get("one_thing_to_fix"),
                },
            )

        except Exception as e:
            logger.error(f"JUDGE execution error: {e}")
            return self.format_response(
                content="I ran into an error during investor evaluation.",
                success=False,
                error=str(e),
            )

    def get_voice_config(self) -> Dict[str, Any]:
        return {
            "voice_id": "judge",
            "style": "formal",
            "pace": "deliberate",
            "tone": "skeptical",
            "language": "en-US",
        }