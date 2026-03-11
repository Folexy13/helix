"""
ARIA - CTO Agent

Evaluates technical feasibility, recommends tech stack, architecture approach,
infrastructure needs, and third-party integrations. Flags technical risks
and estimates development complexity.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

ARIA_SYSTEM_PROMPT = """You are ARIA, the Chief Technology Officer (CTO) for Helix.

## Who You Are
You're the kind of CTO who has actually shipped products — not just architected them.
You've made the wrong tech call before and learned from it. You give real opinions,
not safe answers. When something is a bad idea technically, you say so clearly.
When something is exciting to build, that shows too.

## How You Communicate
- Open with one sentence that reacts to what's interesting (or concerning) about
  this specific idea — never a generic intro
- Write in paragraphs, like a smart colleague talking. Not bullet lists.
- Be specific. Don't say "use a modern stack" — say why you'd pick FastAPI over
  Django for this use case, or why React Native beats Flutter here
- Flag risks early, frame them as solvable unless they genuinely aren't
- One technical opinion per paragraph — don't cram everything into walls of text

## What You Must Cover (weave in naturally, don't use these as headers)
1. What's technically interesting or tricky about this idea
2. Your recommended stack with reasoning for each choice
3. High-level architecture (how does data flow? what are the core services?)
4. The single biggest technical risk and how to mitigate it
5. Rough complexity: MVP timeline and what "done" looks like for v1
6. Feasibility score 1-10 — state it clearly with one sentence of reasoning

## What You Never Do
- Never say "Certainly!" or "Great question!" or "As an AI..."
- Never hedge everything — pick a stack and defend it
- Never list technologies without explaining why you chose them over alternatives
- Never ignore the context from other agents when it's provided"""


class AriaAgent(BaseAgent):
    """ARIA - CTO Agent for technical feasibility analysis."""

    def __init__(self):
        super().__init__(
            role=AgentRole.ARIA,
            name="ARIA",
            description="CTO Agent - Technical feasibility and architecture expert",
            system_prompt=ARIA_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        self._register_aria_tools()

    def _register_aria_tools(self) -> None:
        self.register_tool(Tool(
            name="analyze_tech_stack",
            description="Analyze compatibility and trade-offs of a proposed tech stack",
            parameters={
                "technologies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of technologies to analyze",
                },
                "use_case": {
                    "type": "string",
                    "description": "The use case or project type",
                },
            },
            handler=self._analyze_tech_stack,
        ))

        self.register_tool(Tool(
            name="estimate_infrastructure",
            description="Estimate infrastructure requirements and costs",
            parameters={
                "scale": {
                    "type": "string",
                    "enum": ["small", "medium", "large", "enterprise"],
                    "description": "Expected scale of the application",
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key features requiring infrastructure",
                },
            },
            handler=self._estimate_infrastructure,
        ))

    async def _analyze_tech_stack(
        self, technologies: List[str], use_case: str
    ) -> Dict[str, Any]:
        return {
            "technologies": technologies,
            "use_case": use_case,
            "compatibility_score": 8,
            "recommendations": [
                "Consider TypeScript for better type safety and long-term maintainability",
                "PostgreSQL is the right default for relational data — avoid premature NoSQL",
            ],
            "concerns": ["Validate team familiarity with chosen stack before committing"],
        }

    async def _estimate_infrastructure(
        self, scale: str, features: List[str]
    ) -> Dict[str, Any]:
        scale_costs = {"small": 100, "medium": 300, "large": 1000, "enterprise": 5000}
        monthly_cost = scale_costs.get(scale, 100)

        return {
            "scale": scale,
            "estimated_monthly_cost_usd": monthly_cost,
            "recommended_services": [
                "AWS ECS or Railway for compute (simpler than raw EC2 for early stage)",
                "RDS PostgreSQL for database",
                "S3 + CloudFront for assets",
                "Upstash Redis for caching/queues",
            ],
            "scaling_strategy": "Start on managed services, containerize early for portability",
        }

    async def execute(self, context: AgentContext) -> AgentResponse:
        logger.info(f"ARIA analyzing: {context.user_input[:100]}...")

        # ── Pull cross-agent context if available ─────────────────────────────
        intake_answers = context.metadata.get("intake_answers", {})
        intake_summary = (
            "\n".join(f"- {k.replace('_', ' ').title()}: {v}"
                      for k, v in intake_answers.items())
            if intake_answers else "No structured intake data."
        )

        analysis_prompt = f"""You're the CTO for Helix. Analyze this startup idea:

IDEA: {context.user_input}

WHAT WE KNOW FROM THE FOUNDER:
{intake_summary}

ADDITIONAL CONTEXT: {context.metadata.get('additional_context', 'None.')}

Give a thorough technical analysis. Be specific about stack choices and reasoning.
State your feasibility score (1-10) clearly near the end.
Write in paragraphs — no bullet dumps."""

        try:
            response = await self.invoke_model(
                prompt=analysis_prompt,
                context=context,
                use_tools=True,
            )

            analysis = response.get("text", "")
            reasoning = response.get("reasoning", "")

            # ── Structured extraction replaces brittle regex ──────────────────
            tech_metadata = await self.structured_extract(
                text=analysis,
                schema={
                    "tech_stack": "list of technology names mentioned as recommendations",
                    "complexity": "one of: low, medium, high",
                    "feasibility_score": "integer 1-10",
                    "risks": "list of up to 4 key technical risks as short strings",
                    "mvp_timeline": "string estimate like '2-3 months'",
                },
                context=context,
            )

            # ── Skip noisy mid-flow HITL — only surface if analysis is weak ──
            checkpoint = None
            if tech_metadata.get("feasibility_score", 10) <= 3:
                checkpoint = self.create_hitl_checkpoint(
                    gate_type=HITLGateType.AGENT_DRAFT_REVIEW,
                    prompt=(
                        f"ARIA flagged low technical feasibility "
                        f"(score: {tech_metadata.get('feasibility_score')}/10). "
                        f"Review before proceeding:\n\n{analysis[:800]}"
                    ),
                    options=[HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
                    metadata={"full_analysis": analysis},
                )

            return self.format_response(
                content=analysis,
                reasoning=reasoning,
                hitl_checkpoint=checkpoint,
                metadata={
                    "tech_stack": tech_metadata.get("tech_stack", []),
                    "complexity": tech_metadata.get("complexity", "medium"),
                    "feasibility_score": tech_metadata.get("feasibility_score", 7),
                    "risks": tech_metadata.get("risks", []),
                    "mvp_timeline": tech_metadata.get("mvp_timeline", ""),
                },
            )

        except Exception as e:
            logger.error(f"ARIA execution error: {e}")
            return self.format_response(
                content="I ran into an error during technical analysis.",
                success=False,
                error=str(e),
            )

    def get_voice_config(self) -> Dict[str, Any]:
        return {
            "voice_id": "aria",
            "style": "technical",
            "pace": "measured",
            "tone": "confident",
            "language": "en-US",
        }