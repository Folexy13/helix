"""
FELIX - CFO Agent

Estimates costs, monthly burn rate, expected revenue milestones, and runway.
Uses web grounding for live pricing data. Gives realistic numbers grounded
in real market data, not optimistic founder projections.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort
from src.tools.advanced_tools import WebGroundingTool

logger = logging.getLogger(__name__)

FELIX_SYSTEM_PROMPT = """You are FELIX, the Chief Financial Officer (CFO) for Helix.

## Who You Are
You've seen enough startup financials to know that founders almost always underestimate
burn and overestimate early revenue. You're not a pessimist — you're a realist who
wants companies to survive. You use actual numbers, not vague ranges. You explain
your assumptions so founders can push back if they're wrong.

## How You Communicate
- Open with one sentence reacting to the financial shape of this specific idea —
  is this capital-intensive or lean? Does the revenue model make sense immediately?
- Write in paragraphs with numbers woven in naturally. Avoid bullet-only responses.
- Always state your assumptions explicitly: "I'm assuming a 3-person team at $8k/month
  average..." — so the founder can correct you
- Give ranges only when genuinely uncertain, and explain why
- When you use live pricing data from web search, cite the source inline

## What You Must Cover (weave in naturally)
1. Initial build cost — what does it cost to get to launch?
2. Monthly burn breakdown — people, infrastructure, tools, other
3. Revenue model reality check — when could this realistically make money?
4. Runway at $250k, $500k, and $1M seed rounds
5. The single biggest financial risk (not a list of five)
6. What fundraising stage this idea is suited for right now

## What You Never Do
- Never present fantasy hockey-stick revenue projections without caveats
- Never give burn rates without stating the team size assumption
- Never say "it depends" without following with your best estimate
- Never ignore ARIA's technical complexity when estimating build costs"""


class FelixAgent(BaseAgent):
    """FELIX - CFO Agent for financial analysis with live web pricing data."""

    def __init__(self):
        super().__init__(
            role=AgentRole.FELIX,
            name="FELIX",
            description="CFO Agent - Financial projections and cost analysis with live web data",
            system_prompt=FELIX_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        self._web_grounding = WebGroundingTool()
        self._register_felix_tools()

    def _register_felix_tools(self) -> None:
        self.register_tool(Tool(
            name="web_search_pricing",
            description="Search the web for current pricing of cloud services, APIs, and SaaS tools",
            parameters={
                "query": {"type": "string", "description": "Search query for pricing"},
                "category": {
                    "type": "string",
                    "enum": ["cloud", "api", "saas", "infrastructure", "general"],
                },
            },
            handler=self._web_search_pricing,
        ))

        self.register_tool(Tool(
            name="calculate_burn_rate",
            description="Calculate monthly burn rate from team and infrastructure inputs",
            parameters={
                "team_size": {"type": "integer"},
                "avg_salary": {"type": "number", "description": "Monthly salary per person (USD)"},
                "infrastructure_cost": {"type": "number"},
                "other_costs": {"type": "number"},
            },
            handler=self._calculate_burn_rate,
        ))

        self.register_tool(Tool(
            name="calculate_runway",
            description="Calculate runway in months given funding and burn",
            parameters={
                "funding": {"type": "number"},
                "monthly_burn": {"type": "number"},
                "revenue": {"type": "number", "default": 0},
            },
            handler=self._calculate_runway,
        ))

    async def _web_search_pricing(self, query: str, category: str) -> Dict[str, Any]:
        try:
            if category == "cloud":
                result = await self._web_grounding.get_aws_pricing(query)
            elif category == "api":
                result = await self._web_grounding.get_api_pricing(query)
            elif category == "saas":
                result = await self._web_grounding.get_saas_pricing(query)
            else:
                result = await self._web_grounding.execute(
                    query=f"{query} pricing cost", category="pricing", recency="month"
                )

            if result.success:
                return {
                    "query": query,
                    "results": result.output.get("results", ""),
                    "sources": result.output.get("sources", []),
                    "live_data": True,
                }
            return await self._fallback_pricing(query, category)

        except Exception as e:
            logger.warning(f"Web grounding failed: {e}")
            return await self._fallback_pricing(query, category)

    async def _fallback_pricing(self, query: str, category: str) -> Dict[str, Any]:
        """Cached pricing data used when web grounding is unavailable."""
        data = {
            "cloud": {
                "aws_ec2_t3_medium": "$0.0416/hr",
                "aws_rds_postgres_t3_medium": "$0.095/hr",
                "aws_s3": "$0.023/GB/month",
                "aws_lambda": "$0.0000166667/GB-second",
                "aws_bedrock_nova_lite": "$0.00006/1K input tokens",
                "vercel_pro": "$20/month",
                "railway_starter": "$5/month",
            },
            "api": {
                "openai_gpt4o": "$0.0025/1K input tokens",
                "anthropic_claude_sonnet": "$0.003/1K input tokens",
                "stripe": "2.9% + $0.30/transaction",
                "twilio_sms": "$0.0079/message",
                "sendgrid_essentials": "$19.95/month (50K emails)",
                "resend": "$20/month (50K emails)",
            },
            "saas": {
                "github_team": "$4/user/month",
                "linear": "$8/user/month",
                "figma_professional": "$15/editor/month",
                "notion_team": "$10/user/month",
                "vercel_pro": "$20/month",
                "supabase_pro": "$25/month",
            },
        }
        return {
            "query": query,
            "results": data.get(category, {}),
            "live_data": False,
            "note": "Cached pricing — web grounding unavailable. Verify current rates.",
        }

    async def _calculate_burn_rate(
        self,
        team_size: int,
        avg_salary: float,
        infrastructure_cost: float,
        other_costs: float,
    ) -> Dict[str, Any]:
        personnel = team_size * avg_salary
        overhead = personnel * 0.30  # benefits, taxes, etc.
        total = personnel + overhead + infrastructure_cost + other_costs

        return {
            "personnel": personnel,
            "overhead_30pct": overhead,
            "infrastructure": infrastructure_cost,
            "other": other_costs,
            "total_monthly_burn": round(total, 2),
            "note": "30% overhead applied to personnel for benefits/taxes/payroll",
        }

    async def _calculate_runway(
        self, funding: float, monthly_burn: float, revenue: float = 0
    ) -> Dict[str, Any]:
        net_burn = monthly_burn - revenue
        if net_burn <= 0:
            return {"status": "profitable", "runway_months": "∞", "net_burn": net_burn}

        runway = funding / net_burn
        status = (
            "healthy" if runway > 24
            else "adequate" if runway > 12
            else "concerning" if runway > 6
            else "critical"
        )

        return {
            "funding": funding,
            "monthly_burn": monthly_burn,
            "monthly_revenue": revenue,
            "net_burn": net_burn,
            "runway_months": round(runway, 1),
            "status": status,
        }

    async def execute(self, context: AgentContext) -> AgentResponse:
        logger.info(f"FELIX analyzing: {context.user_input[:100]}...")

        # ── Pull cross-agent context ──────────────────────────────────────────
        aria_analysis = context.metadata.get("aria_analysis", "")
        intake_answers = context.metadata.get("intake_answers", {})

        intake_summary = (
            "\n".join(f"- {k.replace('_', ' ').title()}: {v}"
                      for k, v in intake_answers.items())
            if intake_answers else "No structured intake data."
        )

        # Derive complexity signal from ARIA for smarter cost estimates
        complexity_hint = ""
        if aria_analysis:
            if "high complexity" in aria_analysis.lower() or "complex" in aria_analysis.lower():
                complexity_hint = "ARIA flagged HIGH complexity — factor in longer build time and higher dev costs."
            elif "low complexity" in aria_analysis.lower() or "simple" in aria_analysis.lower():
                complexity_hint = "ARIA flagged LOW complexity — lean toward tighter cost estimates."

        analysis_prompt = f"""You're the CFO for Helix. Analyze this startup's financial picture:

IDEA: {context.user_input}

FOUNDER CONTEXT:
{intake_summary}

TECHNICAL ANALYSIS FROM ARIA (CTO):
{aria_analysis if aria_analysis else "Not yet available."}

COMPLEXITY SIGNAL: {complexity_hint if complexity_hint else "Not assessed."}

Use the web_search_pricing tool to look up actual costs for the infrastructure and
APIs this product will likely need. Then use calculate_burn_rate and calculate_runway
to ground your projections in real numbers.

State your assumptions clearly. Cover:
- What it costs to build to launch (one-time)
- Monthly burn (with team size assumption stated)
- Revenue reality check — when could this break even?
- Runway at $250k, $500k, $1M
- The single biggest financial risk

Write in paragraphs. Be specific. Cite your sources when using live pricing data."""

        try:
            response = await self.invoke_model(
                prompt=analysis_prompt,
                context=context,
                use_tools=True,
            )

            analysis = response.get("text", "")
            reasoning = response.get("reasoning", "")

            # ── Structured extraction ─────────────────────────────────────────
            financial_metadata = await self.structured_extract(
                text=analysis,
                schema={
                    "monthly_burn_rate": "number in USD, extract the primary burn rate estimate",
                    "runway_months": "integer, extract runway at the most prominent funding level",
                    "initial_build_cost": "number in USD, one-time cost to reach launch",
                    "revenue_milestones": "list of strings describing revenue milestones",
                    "funding_stage": "string: pre-seed, seed, series-a, or bootstrapped",
                },
                context=context,
            )

            return self.format_response(
                content=analysis,
                reasoning=reasoning,
                hitl_checkpoint=None,  # Don't interrupt flow mid-analysis
                metadata={
                    "monthly_burn_rate": financial_metadata.get("monthly_burn_rate"),
                    "runway_months": financial_metadata.get("runway_months"),
                    "initial_build_cost": financial_metadata.get("initial_build_cost"),
                    "revenue_milestones": financial_metadata.get("revenue_milestones", []),
                    "funding_stage": financial_metadata.get("funding_stage", "seed"),
                },
            )

        except Exception as e:
            logger.error(f"FELIX execution error: {e}")
            return self.format_response(
                content="I ran into an error during financial analysis.",
                success=False,
                error=str(e),
            )

    def get_voice_config(self) -> Dict[str, Any]:
        return {
            "voice_id": "felix",
            "style": "professional",
            "pace": "measured",
            "tone": "confident",
            "language": "en-US",
        }