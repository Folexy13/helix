"""
FELIX - CFO Agent

Estimates costs, monthly burn rate, expected revenue milestones, and runway.
Uses Nova 2 Lite's built-in web grounding tool to pull live pricing data
(cloud costs, API costs, SaaS tool costs).

Gives a realistic financial picture grounded in real numbers.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

FELIX_SYSTEM_PROMPT = """You are FELIX, the Chief Financial Officer (CFO) agent for Helix.

Your role is to provide comprehensive financial analysis and projections for startup ideas.

## Your Responsibilities:
1. **Cost Estimation**: Calculate development costs, infrastructure costs, and operational expenses
2. **Burn Rate Analysis**: Estimate monthly burn rate based on team size and operations
3. **Revenue Projections**: Model potential revenue streams and milestones
4. **Runway Calculation**: Determine how long funding will last
5. **Pricing Research**: Use web grounding to find current market prices for services
6. **Financial Risk Assessment**: Identify financial risks and mitigation strategies
7. **Funding Requirements**: Estimate how much funding is needed for different stages

## Your Personality:
- Measured, confident, and data-driven
- You speak with authority but acknowledge market uncertainties
- You prioritize realistic projections over optimistic ones
- You always cite sources when using market data

## Output Format:
Structure your analysis with clear sections:
1. Initial Development Costs
2. Monthly Operating Costs Breakdown
3. Estimated Monthly Burn Rate
4. Revenue Model & Projections
5. Break-even Analysis
6. Runway Calculation (at different funding levels)
7. Key Financial Risks
8. Recommended Funding Strategy

Always provide specific numbers with clear assumptions stated."""


class FelixAgent(BaseAgent):
    """
    FELIX - CFO Agent for financial analysis.
    
    Uses web grounding for live pricing data.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.FELIX,
            name="FELIX",
            description="CFO Agent - Financial projections and cost analysis expert",
            system_prompt=FELIX_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        
        # Register FELIX-specific tools
        self._register_felix_tools()
    
    def _register_felix_tools(self) -> None:
        """Register tools specific to FELIX."""
        
        # Web grounding tool for live pricing
        self.register_tool(Tool(
            name="web_search_pricing",
            description="Search the web for current pricing information for cloud services, APIs, and SaaS tools",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query for pricing information",
                },
                "category": {
                    "type": "string",
                    "enum": ["cloud", "api", "saas", "infrastructure", "general"],
                    "description": "Category of pricing to search for",
                },
            },
            handler=self._web_search_pricing,
        ))
        
        # Cost calculator tool
        self.register_tool(Tool(
            name="calculate_burn_rate",
            description="Calculate monthly burn rate based on team and infrastructure",
            parameters={
                "team_size": {
                    "type": "integer",
                    "description": "Number of team members",
                },
                "avg_salary": {
                    "type": "number",
                    "description": "Average monthly salary per team member",
                },
                "infrastructure_cost": {
                    "type": "number",
                    "description": "Monthly infrastructure cost",
                },
                "other_costs": {
                    "type": "number",
                    "description": "Other monthly operational costs",
                },
            },
            handler=self._calculate_burn_rate,
        ))
        
        # Runway calculator
        self.register_tool(Tool(
            name="calculate_runway",
            description="Calculate runway based on funding and burn rate",
            parameters={
                "funding": {
                    "type": "number",
                    "description": "Total funding available",
                },
                "monthly_burn": {
                    "type": "number",
                    "description": "Monthly burn rate",
                },
                "revenue": {
                    "type": "number",
                    "description": "Expected monthly revenue (optional)",
                    "default": 0,
                },
            },
            handler=self._calculate_runway,
        ))
    
    async def _web_search_pricing(
        self,
        query: str,
        category: str,
    ) -> Dict[str, Any]:
        """
        Search for pricing information using web grounding.
        
        In production, this would use Nova 2 Lite's built-in web grounding.
        For now, we return realistic pricing data.
        """
        # Simulated pricing data (in production, this uses web grounding)
        pricing_data = {
            "cloud": {
                "aws_ec2_t3_medium": {"price": 0.0416, "unit": "per hour", "source": "AWS Pricing"},
                "aws_rds_postgres": {"price": 0.095, "unit": "per hour", "source": "AWS Pricing"},
                "aws_s3": {"price": 0.023, "unit": "per GB/month", "source": "AWS Pricing"},
                "vercel_pro": {"price": 20, "unit": "per month", "source": "Vercel Pricing"},
            },
            "api": {
                "openai_gpt4": {"price": 0.03, "unit": "per 1K tokens", "source": "OpenAI Pricing"},
                "stripe": {"price": 2.9, "unit": "% + $0.30 per transaction", "source": "Stripe Pricing"},
                "twilio_sms": {"price": 0.0079, "unit": "per message", "source": "Twilio Pricing"},
                "sendgrid": {"price": 19.95, "unit": "per month (40K emails)", "source": "SendGrid Pricing"},
            },
            "saas": {
                "slack_business": {"price": 12.50, "unit": "per user/month", "source": "Slack Pricing"},
                "github_team": {"price": 4, "unit": "per user/month", "source": "GitHub Pricing"},
                "notion_team": {"price": 10, "unit": "per user/month", "source": "Notion Pricing"},
                "linear": {"price": 8, "unit": "per user/month", "source": "Linear Pricing"},
            },
            "infrastructure": {
                "domain": {"price": 12, "unit": "per year", "source": "Average"},
                "ssl_certificate": {"price": 0, "unit": "free with Let's Encrypt", "source": "Let's Encrypt"},
                "monitoring_datadog": {"price": 15, "unit": "per host/month", "source": "Datadog Pricing"},
            },
        }
        
        category_data = pricing_data.get(category, pricing_data["general"] if "general" in pricing_data else {})
        
        return {
            "query": query,
            "category": category,
            "results": category_data,
            "note": "Prices are approximate and may vary. Always verify with official sources.",
            "last_updated": "2026-03",
        }
    
    async def _calculate_burn_rate(
        self,
        team_size: int,
        avg_salary: float,
        infrastructure_cost: float,
        other_costs: float,
    ) -> Dict[str, Any]:
        """Calculate monthly burn rate."""
        personnel_cost = team_size * avg_salary
        total_burn = personnel_cost + infrastructure_cost + other_costs
        
        # Add typical overhead (benefits, taxes, etc.) - roughly 30%
        overhead = personnel_cost * 0.30
        total_with_overhead = total_burn + overhead
        
        return {
            "personnel_cost": personnel_cost,
            "overhead": overhead,
            "infrastructure_cost": infrastructure_cost,
            "other_costs": other_costs,
            "total_monthly_burn": total_with_overhead,
            "breakdown": {
                "personnel_percentage": (personnel_cost + overhead) / total_with_overhead * 100,
                "infrastructure_percentage": infrastructure_cost / total_with_overhead * 100,
                "other_percentage": other_costs / total_with_overhead * 100,
            },
        }
    
    async def _calculate_runway(
        self,
        funding: float,
        monthly_burn: float,
        revenue: float = 0,
    ) -> Dict[str, Any]:
        """Calculate runway in months."""
        net_burn = monthly_burn - revenue
        
        if net_burn <= 0:
            runway_months = float('inf')
            status = "profitable"
        else:
            runway_months = funding / net_burn
            if runway_months > 24:
                status = "healthy"
            elif runway_months > 12:
                status = "adequate"
            elif runway_months > 6:
                status = "concerning"
            else:
                status = "critical"
        
        return {
            "funding": funding,
            "monthly_burn": monthly_burn,
            "monthly_revenue": revenue,
            "net_monthly_burn": net_burn,
            "runway_months": runway_months if runway_months != float('inf') else "Infinite (profitable)",
            "status": status,
            "recommendation": self._get_runway_recommendation(runway_months, status),
        }
    
    def _get_runway_recommendation(self, months: float, status: str) -> str:
        """Get recommendation based on runway status."""
        recommendations = {
            "profitable": "Focus on growth and reinvestment.",
            "healthy": "Good position. Consider strategic investments.",
            "adequate": "Start planning next funding round in 6 months.",
            "concerning": "Prioritize fundraising or cost reduction immediately.",
            "critical": "Emergency measures needed. Cut costs or seek bridge funding.",
        }
        return recommendations.get(status, "Review financial strategy.")
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute FELIX's financial analysis.
        
        Args:
            context: Agent execution context with user input
            
        Returns:
            AgentResponse with financial analysis
        """
        logger.info(f"FELIX analyzing: {context.user_input[:100]}...")
        
        # Get technical context from ARIA if available
        tech_context = context.metadata.get("aria_analysis", "")
        
        # Build the analysis prompt
        analysis_prompt = f"""Analyze the following startup idea from a financial perspective:

## Startup Idea:
{context.user_input}

## Technical Context (from CTO):
{tech_context if tech_context else "No technical analysis available yet."}

## Additional Context:
{context.metadata.get('additional_context', 'No additional context provided.')}

Please provide a comprehensive financial analysis following your standard output format.

Use the available tools to:
1. Search for current pricing of relevant cloud services and APIs
2. Calculate realistic burn rates based on team size
3. Project runway at different funding levels

Be specific with numbers and always state your assumptions clearly.
Consider both bootstrapped and funded scenarios."""

        try:
            # Invoke model with tools for web grounding
            response = await self.invoke_model(
                prompt=analysis_prompt,
                context=context,
                use_tools=True,
            )
            
            # Extract the analysis
            analysis = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse key financial metrics
            financial_metrics = self._parse_financial_metrics(analysis)
            
            # Create HITL checkpoint for review
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.AGENT_DRAFT_REVIEW,
                prompt=f"FELIX (CFO) has completed the financial analysis. Please review:\n\n{analysis[:500]}...",
                options=[HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
                metadata={"full_analysis": analysis, "financial_metrics": financial_metrics},
            )
            
            return self.format_response(
                content=analysis,
                reasoning=reasoning,
                hitl_checkpoint=checkpoint,
                metadata={
                    "monthly_burn_rate": financial_metrics.get("burn_rate"),
                    "runway_months": financial_metrics.get("runway"),
                    "initial_funding_needed": financial_metrics.get("funding_needed"),
                    "revenue_milestones": financial_metrics.get("milestones", []),
                },
            )
            
        except Exception as e:
            logger.error(f"FELIX execution error: {e}")
            return self.format_response(
                content="I encountered an error while analyzing the financial aspects.",
                success=False,
                error=str(e),
            )
    
    def _parse_financial_metrics(self, analysis: str) -> Dict[str, Any]:
        """
        Parse the analysis text to extract financial metrics.
        """
        result = {
            "burn_rate": None,
            "runway": None,
            "funding_needed": None,
            "milestones": [],
        }
        
        # Simple parsing - in production, use structured output
        import re
        
        # Try to find burn rate mentions
        burn_match = re.search(r'\$?([\d,]+)\s*(?:per month|/month|monthly burn)', analysis, re.IGNORECASE)
        if burn_match:
            result["burn_rate"] = float(burn_match.group(1).replace(",", ""))
        
        # Try to find runway mentions
        runway_match = re.search(r'(\d+)\s*months?\s*(?:runway|of runway)', analysis, re.IGNORECASE)
        if runway_match:
            result["runway"] = int(runway_match.group(1))
        
        return result
    
    def get_voice_config(self) -> Dict[str, Any]:
        """
        Get Nova 2 Sonic voice configuration for FELIX.
        
        FELIX has a measured, confident male voice.
        """
        return {
            "voice_id": "felix",
            "style": "professional",
            "pace": "measured",
            "tone": "confident",
            "language": "en-US",
        }
