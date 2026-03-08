"""
JUDGE - Investor Agent

Plays the role of a skeptical but fair seed investor. Asks hard questions,
pokes holes in the idea, and gives an honest fundability score with reasoning.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are JUDGE, the Investor Agent for Helix.

Your role is to evaluate startup ideas from an investor's perspective - skeptical but fair.

## Your Responsibilities:
1. **Critical Analysis**: Identify weaknesses and potential failure points
2. **Market Validation**: Question market size and demand assumptions
3. **Team Assessment**: Evaluate if the team can execute
4. **Competitive Analysis**: Challenge competitive positioning claims
5. **Business Model Scrutiny**: Question revenue and growth assumptions
6. **Risk Identification**: Highlight key risks investors would see
7. **Fundability Assessment**: Provide an honest fundability score

## Your Personality:
- Firm, skeptical, but ultimately fair
- You ask the hard questions that founders need to answer
- You've seen hundreds of pitches and know what works
- You're direct but not cruel - you want founders to succeed

## Your Approach:
1. First, acknowledge what's compelling about the idea
2. Then, systematically challenge key assumptions
3. Ask 5-7 tough questions a real investor would ask
4. Provide constructive feedback on how to strengthen the pitch
5. Give an honest fundability score with clear reasoning

## Output Format:
Structure your analysis with clear sections:
1. Initial Impression (What's compelling)
2. Key Concerns (What worries me)
3. Hard Questions (5-7 questions you'd ask in a pitch meeting)
4. Competitive Threats (What could kill this)
5. What Would Make This Fundable
6. Fundability Score (1-10) with detailed reasoning
7. Recommended Next Steps

Be direct and honest. Founders need truth, not false encouragement."""


class JudgeAgent(BaseAgent):
    """
    JUDGE - Investor Agent for fundability assessment.
    
    Provides critical but fair evaluation of startup ideas.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.JUDGE,
            name="JUDGE",
            description="Investor Agent - Critical evaluation and fundability assessment",
            system_prompt=JUDGE_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        
        # Register JUDGE-specific tools
        self._register_judge_tools()
    
    def _register_judge_tools(self) -> None:
        """Register tools specific to JUDGE."""
        
        # Market size validation tool
        self.register_tool(Tool(
            name="validate_market_size",
            description="Validate market size claims and assumptions",
            parameters={
                "market_claim": {
                    "type": "string",
                    "description": "The market size claim to validate",
                },
                "industry": {
                    "type": "string",
                    "description": "Industry or market segment",
                },
            },
            handler=self._validate_market_size,
        ))
        
        # Competitor threat analysis
        self.register_tool(Tool(
            name="analyze_competitive_threats",
            description="Analyze competitive threats and barriers to entry",
            parameters={
                "product_description": {
                    "type": "string",
                    "description": "Description of the product",
                },
                "market": {
                    "type": "string",
                    "description": "Target market",
                },
            },
            handler=self._analyze_competitive_threats,
        ))
        
        # Fundability scoring tool
        self.register_tool(Tool(
            name="calculate_fundability_score",
            description="Calculate a fundability score based on multiple factors",
            parameters={
                "market_size": {
                    "type": "string",
                    "enum": ["small", "medium", "large", "massive"],
                    "description": "Market size assessment",
                },
                "team_strength": {
                    "type": "string",
                    "enum": ["weak", "average", "strong", "exceptional"],
                    "description": "Team strength assessment",
                },
                "differentiation": {
                    "type": "string",
                    "enum": ["none", "weak", "moderate", "strong"],
                    "description": "Product differentiation level",
                },
                "traction": {
                    "type": "string",
                    "enum": ["none", "early", "growing", "strong"],
                    "description": "Current traction level",
                },
                "timing": {
                    "type": "string",
                    "enum": ["too_early", "early", "right", "late"],
                    "description": "Market timing assessment",
                },
            },
            handler=self._calculate_fundability_score,
        ))
    
    async def _validate_market_size(
        self,
        market_claim: str,
        industry: str,
    ) -> Dict[str, Any]:
        """Validate market size claims."""
        return {
            "market_claim": market_claim,
            "industry": industry,
            "validation_status": "requires_verification",
            "concerns": [
                "TAM vs SAM vs SOM distinction needed",
                "Growth rate assumptions should be cited",
                "Geographic scope should be clarified",
            ],
            "questions": [
                "What's your serviceable addressable market (SAM)?",
                "What market share can you realistically capture in 5 years?",
                "What's driving the market growth you're projecting?",
            ],
            "recommendation": "Provide bottom-up market sizing based on customer segments",
        }
    
    async def _analyze_competitive_threats(
        self,
        product_description: str,
        market: str,
    ) -> Dict[str, Any]:
        """Analyze competitive threats."""
        return {
            "product": product_description,
            "market": market,
            "threat_categories": [
                {
                    "category": "Direct Competitors",
                    "threat_level": "high",
                    "description": "Existing solutions solving the same problem",
                },
                {
                    "category": "Big Tech Entry",
                    "threat_level": "medium",
                    "description": "Risk of large companies entering the space",
                },
                {
                    "category": "Substitute Solutions",
                    "threat_level": "medium",
                    "description": "Alternative ways customers solve this problem",
                },
                {
                    "category": "New Entrants",
                    "threat_level": "medium",
                    "description": "Other startups that could emerge",
                },
            ],
            "key_questions": [
                "What's your moat against well-funded competitors?",
                "Why can't Google/Microsoft/Amazon build this?",
                "What happens if a competitor raises 10x your funding?",
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
        """Calculate fundability score."""
        # Scoring weights
        scores = {
            "market_size": {"small": 1, "medium": 2, "large": 3, "massive": 4},
            "team_strength": {"weak": 1, "average": 2, "strong": 3, "exceptional": 4},
            "differentiation": {"none": 0, "weak": 1, "moderate": 2, "strong": 3},
            "traction": {"none": 0, "early": 1, "growing": 2, "strong": 3},
            "timing": {"too_early": 1, "early": 2, "right": 3, "late": 1},
        }
        
        # Calculate weighted score
        market_score = scores["market_size"].get(market_size, 2) * 2.5
        team_score = scores["team_strength"].get(team_strength, 2) * 2.0
        diff_score = scores["differentiation"].get(differentiation, 1) * 1.5
        traction_score = scores["traction"].get(traction, 0) * 2.0
        timing_score = scores["timing"].get(timing, 2) * 1.0
        
        total_score = market_score + team_score + diff_score + traction_score + timing_score
        max_score = 4 * 2.5 + 4 * 2.0 + 3 * 1.5 + 3 * 2.0 + 3 * 1.0  # 31.5
        
        fundability_score = round((total_score / max_score) * 10, 1)
        
        # Determine verdict
        if fundability_score >= 8:
            verdict = "Highly Fundable"
            recommendation = "Strong candidate for seed funding"
        elif fundability_score >= 6:
            verdict = "Fundable with Work"
            recommendation = "Address key concerns before pitching"
        elif fundability_score >= 4:
            verdict = "Needs Significant Improvement"
            recommendation = "Focus on traction and differentiation"
        else:
            verdict = "Not Currently Fundable"
            recommendation = "Pivot or validate core assumptions"
        
        return {
            "fundability_score": fundability_score,
            "verdict": verdict,
            "recommendation": recommendation,
            "breakdown": {
                "market_size": {"value": market_size, "score": market_score},
                "team_strength": {"value": team_strength, "score": team_score},
                "differentiation": {"value": differentiation, "score": diff_score},
                "traction": {"value": traction, "score": traction_score},
                "timing": {"value": timing, "score": timing_score},
            },
            "total_score": total_score,
            "max_possible": max_score,
        }
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute JUDGE's investor evaluation.
        
        Args:
            context: Agent execution context with user input
            
        Returns:
            AgentResponse with investor evaluation
        """
        logger.info(f"JUDGE evaluating: {context.user_input[:100]}...")
        
        # Get context from other agents
        tech_context = context.metadata.get("aria_analysis", "")
        financial_context = context.metadata.get("felix_analysis", "")
        marketing_context = context.metadata.get("nova_analysis", "")
        
        # Build the evaluation prompt
        evaluation_prompt = f"""Evaluate the following startup idea from an investor's perspective:

## Startup Idea:
{context.user_input}

## Technical Analysis (from CTO):
{tech_context if tech_context else "No technical analysis available."}

## Financial Analysis (from CFO):
{financial_context if financial_context else "No financial analysis available."}

## Marketing Strategy (from CMO):
{marketing_context if marketing_context else "No marketing analysis available."}

## Additional Context:
{context.metadata.get('additional_context', 'No additional context provided.')}

As a seasoned seed investor who has seen hundreds of pitches, provide your honest evaluation.

Remember:
1. Start with what's compelling - every idea has something
2. Then be direct about concerns and weaknesses
3. Ask the hard questions founders need to answer
4. Provide a fundability score (1-10) with clear reasoning
5. Give actionable advice on how to improve

Be skeptical but fair. Your job is to help founders see their blind spots."""

        try:
            # Invoke model with extended thinking for thorough analysis
            response = await self.invoke_model(
                prompt=evaluation_prompt,
                context=context,
                use_tools=True,
            )
            
            # Extract the evaluation
            evaluation = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse investor feedback
            investor_feedback = self._parse_investor_feedback(evaluation)
            
            # Create HITL checkpoint for review
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.AGENT_DRAFT_REVIEW,
                prompt=f"JUDGE (Investor) has completed the evaluation. Please review:\n\n{evaluation[:500]}...",
                options=[HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
                metadata={"full_evaluation": evaluation, "investor_feedback": investor_feedback},
            )
            
            return self.format_response(
                content=evaluation,
                reasoning=reasoning,
                hitl_checkpoint=checkpoint,
                metadata={
                    "fundability_score": investor_feedback.get("fundability_score"),
                    "hard_questions": investor_feedback.get("hard_questions", []),
                    "key_concerns": investor_feedback.get("key_concerns", []),
                    "verdict": investor_feedback.get("verdict"),
                },
            )
            
        except Exception as e:
            logger.error(f"JUDGE execution error: {e}")
            return self.format_response(
                content="I encountered an error while evaluating the idea.",
                success=False,
                error=str(e),
            )
    
    def _parse_investor_feedback(self, evaluation: str) -> Dict[str, Any]:
        """
        Parse the evaluation text to extract investor feedback.
        """
        result = {
            "fundability_score": None,
            "hard_questions": [],
            "key_concerns": [],
            "verdict": None,
        }
        
        import re
        
        # Try to find fundability score
        score_match = re.search(r'(?:fundability|score)[:\s]*(\d+)(?:/10)?', evaluation, re.IGNORECASE)
        if score_match:
            result["fundability_score"] = int(score_match.group(1))
        
        # Extract questions (lines ending with ?)
        questions = re.findall(r'[^\n]*\?', evaluation)
        result["hard_questions"] = [q.strip() for q in questions[:7]]  # Top 7 questions
        
        # Determine verdict based on score
        if result["fundability_score"]:
            score = result["fundability_score"]
            if score >= 8:
                result["verdict"] = "Highly Fundable"
            elif score >= 6:
                result["verdict"] = "Fundable with Work"
            elif score >= 4:
                result["verdict"] = "Needs Improvement"
            else:
                result["verdict"] = "Not Currently Fundable"
        
        return result
    
    def get_voice_config(self) -> Dict[str, Any]:
        """
        Get Nova 2 Sonic voice configuration for JUDGE.
        
        JUDGE has a firm, skeptical, slightly formal male voice.
        """
        return {
            "voice_id": "judge",
            "style": "formal",
            "pace": "deliberate",
            "tone": "skeptical",
            "language": "en-US",
        }
