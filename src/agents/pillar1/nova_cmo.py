"""
NOVA - CMO Agent

Writes the value proposition, taglines, target audience breakdown,
and go-to-market strategy. Understands positioning and messaging.
Grounds creative work in the financial and technical realities from
ARIA and FELIX.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

NOVA_CMO_SYSTEM_PROMPT = """You are NOVA, the Chief Marketing Officer (CMO) for Helix.

## Who You Are
Hey! I'm Nova, the CMO. I've launched products and I know what actually drives growth —
it's rarely what founders think. I'm excited about ideas, but I'm not a cheerleader.
My job is to find the sharpest way to position your product so the right people
immediately get why they need it.

## How You Communicate
- Start with what's genuinely marketable about THIS idea — or the positioning challenge
- Write in paragraphs — marketing thinking is narrative, not bullet points
- When giving tagline options, explain the strategic bet behind each
- Ground go-to-market in Felix's budget reality
- Push back gently if there's a positioning problem

## What You Cover (naturally, not as a checklist)
1. Core value proposition — one crisp sentence that makes customers nod
2. Who this is really for — a vivid description of the actual person
3. Tagline options with strategic reasoning
4. The most effective launch channel for this product
5. Go-to-market phases: pre-launch, launch week, first 90 days
6. What "good traction" looks like

## CRITICAL: Handoff at the End
After sharing your marketing perspective, offer to hand off:
"That's the marketing angle. Last up is Judge — he plays the skeptical investor and
will stress-test the whole idea. Ready for the tough love, or any questions for me first?"

Or if user has questions, answer them first, THEN offer the handoff.

## What You Never Do
- Never write generic taglines that could apply to anything
- Never ignore the competitive landscape
- Never recommend channels that don't match budget
- Never end without offering to hand off to Judge"""


class NovaCMOAgent(BaseAgent):
    """NOVA - CMO Agent for marketing strategy and positioning."""

    def __init__(self):
        super().__init__(
            role=AgentRole.NOVA,
            name="NOVA",
            description="CMO Agent - Marketing strategy, positioning, and messaging expert",
            system_prompt=NOVA_CMO_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.LOW,
        )
        self._register_nova_tools()

    def _register_nova_tools(self) -> None:
        self.register_tool(Tool(
            name="analyze_audience",
            description="Analyze and segment target audience for a product",
            parameters={
                "product_description": {"type": "string"},
                "industry": {"type": "string"},
            },
            handler=self._analyze_audience,
        ))

        self.register_tool(Tool(
            name="analyze_positioning",
            description="Analyze competitive positioning opportunities",
            parameters={
                "product": {"type": "string"},
                "competitors": {"type": "array", "items": {"type": "string"}},
            },
            handler=self._analyze_positioning,
        ))

        self.register_tool(Tool(
            name="generate_copy_variations",
            description="Generate multiple tagline or headline variations with strategic rationale",
            parameters={
                "copy_type": {
                    "type": "string",
                    "enum": ["headline", "tagline", "cta", "description"],
                },
                "key_message": {"type": "string"},
                "tone": {
                    "type": "string",
                    "enum": ["professional", "casual", "bold", "friendly", "urgent"],
                },
            },
            handler=self._generate_copy_variations,
        ))

    async def _analyze_audience(
        self, product_description: str, industry: str
    ) -> Dict[str, Any]:
        return {
            "primary_persona": {
                "description": "The person who feels this problem most acutely",
                "pain_points": ["Inefficiency slowing down their core work",
                                "Existing tools built for a different use case",
                                "Manual processes that don't scale"],
                "buying_trigger": "When the pain costs more than the solution",
                "where_they_hang_out": ["Industry Slack groups", "LinkedIn", "niche forums"],
            },
            "secondary_persona": {
                "description": "Adjacent buyer who benefits but isn't the primary champion",
                "note": "Don't build messaging for this group first — dilutes the core pitch",
            },
            "anti_persona": "Who this is NOT for — being clear about this sharpens positioning",
        }

    async def _analyze_positioning(
        self, product: str, competitors: List[str]
    ) -> Dict[str, Any]:
        return {
            "positioning_angles": [
                {
                    "angle": "Category creation",
                    "bet": "If no clear competitor, own the category name",
                    "risk": "Requires educating the market — expensive and slow",
                },
                {
                    "angle": "Direct comparison",
                    "bet": "Name the leader and say why you're better for a specific use case",
                    "risk": "Validates the incumbent — only works if differentiation is clear",
                },
                {
                    "angle": "Audience-first positioning",
                    "bet": "Lead with the identity of the customer, not the product",
                    "risk": "Can feel narrow — but sharpness wins early traction",
                },
            ],
            "recommendation": "Pick one angle and commit. Trying all three dilutes the message.",
        }

    async def _generate_copy_variations(
        self, copy_type: str, key_message: str, tone: str
    ) -> Dict[str, Any]:
        # Placeholder — in production the LLM generates these dynamically
        return {
            "note": "Taglines are generated by the model based on full context — "
                    "this tool structures the request, not the output.",
            "copy_type": copy_type,
            "tone": tone,
            "key_message": key_message,
        }

    async def execute(self, context: AgentContext) -> AgentResponse:
        logger.info(f"NOVA analyzing: {context.user_input[:100]}...")

        # ── Pull cross-agent context ──────────────────────────────────────────
        aria_analysis = context.metadata.get("aria_analysis", "")
        felix_analysis = context.metadata.get("felix_analysis", "")
        intake_answers = context.metadata.get("intake_answers", {})

        intake_summary = (
            "\n".join(f"- {k.replace('_', ' ').title()}: {v}"
                      for k, v in intake_answers.items())
            if intake_answers else "No structured intake data."
        )

        # Extract budget signal from FELIX for channel recommendations
        budget_signal = ""
        if felix_analysis:
            if "bootstrapped" in felix_analysis.lower() or "pre-seed" in felix_analysis.lower():
                budget_signal = "This is likely bootstrapped or pre-seed — recommend zero/low-cost channels."
            elif "seed" in felix_analysis.lower() or "series" in felix_analysis.lower():
                budget_signal = "Seed-stage budget available — can mix paid and organic channels."

        analysis_prompt = f"""You're the CMO for Helix. Build the marketing strategy for this startup:

IDEA: {context.user_input}

FOUNDER CONTEXT:
{intake_summary}

TECHNICAL CONTEXT FROM ARIA:
{aria_analysis if aria_analysis else "Not yet available."}

FINANCIAL CONTEXT FROM FELIX:
{felix_analysis if felix_analysis else "Not yet available."}

BUDGET SIGNAL: {budget_signal if budget_signal else "Unknown — assume lean."}

Your job is to find the sharpest positioning and most practical path to first customers.

Write three taglines — but explain the strategic bet behind each one, not just the words.
Describe the target customer vividly — a real person, not a demographic category.
Make the go-to-market concrete: what do they do on day 1, week 1, month 1?

Write in paragraphs. Be specific. Good marketing thinking is narrative, not a checklist."""

        try:
            response = await self.invoke_model(
                prompt=analysis_prompt,
                context=context,
                use_tools=True,
            )

            analysis = response.get("text", "")
            reasoning = response.get("reasoning", "")

            # ── Structured extraction ─────────────────────────────────────────
            marketing_metadata = await self.structured_extract(
                text=analysis,
                schema={
                    "value_proposition": "string — the core one-sentence value prop",
                    "taglines": "list of exactly 3 tagline strings",
                    "target_audience": "string — vivid description of primary customer",
                    "primary_launch_channel": "string — single best channel to start",
                    "landing_page_copy": "string — hero section copy if present",
                },
                context=context,
            )

            return self.format_response(
                content=analysis,
                reasoning=reasoning,
                hitl_checkpoint=None,
                metadata={
                    "value_proposition": marketing_metadata.get("value_proposition"),
                    "taglines": marketing_metadata.get("taglines", []),
                    "target_audience": marketing_metadata.get("target_audience"),
                    "primary_launch_channel": marketing_metadata.get("primary_launch_channel"),
                    "landing_page_copy": marketing_metadata.get("landing_page_copy"),
                },
            )

        except Exception as e:
            logger.error(f"NOVA execution error: {e}")
            return self.format_response(
                content="I ran into an error while building the marketing strategy.",
                success=False,
                error=str(e),
            )

    def get_voice_config(self) -> Dict[str, Any]:
        return {
            "voice_id": "nova_cmo",
            "style": "energetic",
            "pace": "dynamic",
            "tone": "warm",
            "language": "en-US",
        }