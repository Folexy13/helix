"""
ARIA - CTO Agent

Evaluates technical feasibility, recommends tech stack, architecture approach,
infrastructure needs, and third-party integrations. Flags technical risks
and estimates development complexity.

Uses Nova 2 Lite with extended thinking set to `medium` for deeper analysis.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

ARIA_SYSTEM_PROMPT = """You are ARIA, the Chief Technology Officer (CTO) agent for Helix.

Your role is to evaluate the technical feasibility of startup ideas and provide comprehensive technical guidance.

## Your Responsibilities:
1. **Technical Feasibility Assessment**: Evaluate if the idea can be built with current technology
2. **Tech Stack Recommendation**: Suggest the most appropriate technologies, frameworks, and tools
3. **Architecture Design**: Propose a high-level system architecture
4. **Infrastructure Planning**: Recommend cloud services, hosting, and scaling strategies
5. **Third-Party Integrations**: Identify necessary APIs, services, and integrations
6. **Risk Assessment**: Flag potential technical challenges and risks
7. **Complexity Estimation**: Estimate development effort and timeline

## Your Personality:
- Calm, precise, and technical
- You speak with confidence but acknowledge uncertainties
- You prioritize practical, scalable solutions over cutting-edge but risky technologies
- You consider both short-term MVP needs and long-term scalability

## Output Format:
Structure your analysis with clear sections:
1. Technical Feasibility Score (1-10)
2. Recommended Tech Stack
3. Architecture Overview
4. Infrastructure Requirements
5. Key Integrations Needed
6. Technical Risks & Mitigations
7. Development Complexity (Low/Medium/High)
8. Estimated Timeline

Always be specific and actionable in your recommendations."""


class AriaAgent(BaseAgent):
    """
    ARIA - CTO Agent for technical feasibility analysis.
    
    Uses extended thinking (medium) for deep technical analysis.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.ARIA,
            name="ARIA",
            description="CTO Agent - Technical feasibility and architecture expert",
            system_prompt=ARIA_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        
        # Register ARIA-specific tools
        self._register_aria_tools()
    
    def _register_aria_tools(self) -> None:
        """Register tools specific to ARIA."""
        
        # Tool for analyzing tech stack compatibility
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
        
        # Tool for estimating infrastructure costs
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
        self,
        technologies: List[str],
        use_case: str,
    ) -> Dict[str, Any]:
        """Analyze tech stack compatibility."""
        # This would integrate with external APIs or databases
        # For now, return a structured analysis
        return {
            "technologies": technologies,
            "use_case": use_case,
            "compatibility_score": 8,
            "recommendations": [
                "Consider using TypeScript for better type safety",
                "PostgreSQL is a solid choice for relational data",
            ],
            "concerns": [
                "Ensure team has experience with chosen stack",
            ],
        }
    
    async def _estimate_infrastructure(
        self,
        scale: str,
        features: List[str],
    ) -> Dict[str, Any]:
        """Estimate infrastructure requirements."""
        # Scale-based estimates
        scale_multipliers = {
            "small": 1,
            "medium": 3,
            "large": 10,
            "enterprise": 50,
        }
        
        base_cost = 100  # Base monthly cost in USD
        multiplier = scale_multipliers.get(scale, 1)
        
        return {
            "scale": scale,
            "features": features,
            "estimated_monthly_cost": base_cost * multiplier,
            "recommended_services": [
                "AWS EC2 or ECS for compute",
                "RDS for database",
                "S3 for storage",
                "CloudFront for CDN",
            ],
            "scaling_strategy": "Horizontal auto-scaling with load balancer",
        }
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute ARIA's technical analysis.
        
        Args:
            context: Agent execution context with user input
            
        Returns:
            AgentResponse with technical analysis
        """
        logger.info(f"ARIA analyzing: {context.user_input[:100]}...")
        
        # Build the analysis prompt
        analysis_prompt = f"""Analyze the following startup idea from a technical perspective:

## Startup Idea:
{context.user_input}

## Additional Context:
{context.metadata.get('additional_context', 'No additional context provided.')}

Please provide a comprehensive technical analysis following your standard output format.
Consider:
- What technologies would be best suited for this?
- What are the main technical challenges?
- How complex would this be to build?
- What infrastructure would be needed?
- What third-party services would be required?

Be specific and actionable in your recommendations."""

        try:
            # Invoke model with extended thinking
            response = await self.invoke_model(
                prompt=analysis_prompt,
                context=context,
                use_tools=True,
            )
            
            # Extract the analysis
            analysis = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse key information from the analysis
            tech_analysis = self._parse_analysis(analysis)
            
            # Create HITL checkpoint for review
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.AGENT_DRAFT_REVIEW,
                prompt=f"ARIA (CTO) has completed the technical analysis. Please review:\n\n{analysis[:500]}...",
                options=[HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
                metadata={"full_analysis": analysis, "tech_analysis": tech_analysis},
            )
            
            return self.format_response(
                content=analysis,
                reasoning=reasoning,
                hitl_checkpoint=checkpoint,
                metadata={
                    "tech_stack": tech_analysis.get("tech_stack", []),
                    "complexity": tech_analysis.get("complexity", "medium"),
                    "feasibility_score": tech_analysis.get("feasibility_score", 7),
                    "risks": tech_analysis.get("risks", []),
                },
            )
            
        except Exception as e:
            logger.error(f"ARIA execution error: {e}")
            return self.format_response(
                content="I encountered an error while analyzing the technical aspects.",
                success=False,
                error=str(e),
            )
    
    def _parse_analysis(self, analysis: str) -> Dict[str, Any]:
        """
        Parse the analysis text to extract structured information.
        """
        result = {
            "tech_stack": [],
            "complexity": "medium",
            "feasibility_score": 7,
            "risks": [],
            "timeline": "3-6 months",
        }
        
        analysis_lower = analysis.lower()
        
        # Detect complexity
        if any(word in analysis_lower for word in ["high complexity", "complex", "difficult", "challenging"]):
            result["complexity"] = "high"
        elif any(word in analysis_lower for word in ["low complexity", "simple", "easy", "straightforward"]):
            result["complexity"] = "low"
        
        # Improved tech stack detection
        tech_keywords = [
            "python", "javascript", "typescript", "react", "vue", "angular", "next.js",
            "node.js", "django", "fastapi", "flask", "postgresql", "mongodb", "sqlite",
            "redis", "aws", "gcp", "azure", "docker", "kubernetes", "tailwind", "shadcn",
            "supabase", "firebase", "bedrock", "nova", "lambda", "s3", "rds"
        ]
        
        for tech in tech_keywords:
            # Use regex to match whole words/phrases only to avoid false positives
            if re.search(rf'\b{re.escape(tech)}\b', analysis_lower):
                result["tech_stack"].append(tech.upper())
        
        # Detect feasibility score if mentioned like "Score: 8/10"
        score_match = re.search(r'(?:score|feasibility):\s*(\d+)(?:/10)?', analysis_lower)
        if score_match:
            result["feasibility_score"] = int(score_match.group(1))
            
        return result
    
    def get_voice_config(self) -> Dict[str, Any]:
        """
        Get Nova 2 Sonic voice configuration for ARIA.
        
        ARIA has a calm, precise, technical female voice.
        """
        return {
            "voice_id": "aria",
            "style": "technical",
            "pace": "measured",
            "tone": "confident",
            "language": "en-US",
        }
