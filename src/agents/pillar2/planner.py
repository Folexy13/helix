"""
PLANNER Agent

Uses Nova 2 Lite with extended thinking (`high` budget) to decompose
plain English requests into structured engineering specs.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.core.models import AgentRole, EngineeringSpec, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are the PLANNER agent for Helix's Engineering Workforce.

Your role is to create a BRIEF, CLEAR plan for the application. Keep it SHORT and PROCEDURAL.

## CRITICAL: KEEP OUTPUT SHORT
- Maximum 150 words total
- Use bullet points, not paragraphs
- No lengthy descriptions
- Be direct and actionable

## OUTPUT FORMAT (EXACTLY THIS):

**What I'll Build:**
[1-2 sentences describing the app in simple terms]

**Key Features:**
• [Feature 1 - simple description]
• [Feature 2 - simple description]
• [Feature 3 - simple description]
• [Feature 4 - simple description]

**Pages I'll Create:**
1. Home Page - [what it shows]
2. Dashboard - [what it shows]
3. [Other pages as needed]

**Ready to start coding?**

## RULES:
- Keep it under 150 words
- No technical jargon - explain like talking to a friend
- Focus on WHAT the user will get, not HOW it's built
- Make it sound exciting but brief
- End with "Ready to start coding?" to hand off to CODER
"""


class PlannerAgent(BaseAgent):
    """
    PLANNER - Engineering specification agent.
    
    Uses extended thinking (high) for thorough task decomposition.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.PLANNER,
            name="PLANNER",
            description="Engineering Spec Agent - Decomposes requests into implementable tasks",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            reasoning_effort=None,  # Disabled - not supported
        )
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute PLANNER's task decomposition.
        
        Args:
            context: Agent execution context with user input
            
        Returns:
            AgentResponse with engineering specification
        """
        logger.info(f"PLANNER analyzing: {context.user_input[:100]}...")
        
        # Build a simple planning prompt
        planning_prompt = f"""Create a brief plan for this project:

**User's Request:** {context.user_input}

Remember:
- Keep it under 150 words
- Use simple language (no tech jargon)
- Focus on what the user will GET
- List 4-5 key features
- List 3-5 pages you'll create
- End with "Ready to start coding?"

Now create the plan:"""

        try:
            response = await self.invoke_model(
                prompt=planning_prompt,
                context=context,
                use_tools=False,
            )
            
            spec_text = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse into structured spec
            engineering_spec = self._parse_engineering_spec(context.user_input, spec_text)
            
            return self.format_response(
                content=spec_text,
                reasoning=reasoning,
                metadata={
                    "spec_id": str(engineering_spec.id),
                    "task_count": len(engineering_spec.tasks),
                    "complexity": engineering_spec.estimated_complexity,
                    "tasks": engineering_spec.tasks,
                },
            )
            
        except Exception as e:
            logger.error(f"PLANNER execution error: {e}")
            return self.format_response(
                content="I encountered an error while creating the plan.",
                success=False,
                error=str(e),
            )
    
    def _parse_engineering_spec(self, feature_description: str, spec_text: str) -> EngineeringSpec:
        """
        Parse the specification text into a structured EngineeringSpec.
        """
        tasks = []
        dependencies = []
        acceptance_criteria = []
        
        import re
        
        # Find feature patterns
        feature_pattern = r'[•\-]\s*(.+)'
        feature_matches = re.findall(feature_pattern, spec_text)
        
        for i, feature in enumerate(feature_matches[:5]):  # Max 5 tasks
            tasks.append({
                "id": i + 1,
                "name": feature.strip(),
                "status": "pending",
                "complexity": "medium",
            })
        
        # Simple complexity estimate
        if len(tasks) <= 3:
            complexity = "low"
        elif len(tasks) <= 5:
            complexity = "medium"
        else:
            complexity = "high"
        
        return EngineeringSpec(
            feature_description=feature_description,
            tasks=tasks,
            dependencies=dependencies,
            acceptance_criteria=acceptance_criteria,
            estimated_complexity=complexity,
        )
    
    def get_voice_config(self) -> Dict[str, Any]:
        """Get Nova 2 Sonic voice configuration for PLANNER."""
        return {
            "voice_id": "planner",
            "style": "analytical",
            "pace": "thoughtful",
            "tone": "precise",
            "language": "en-US",
        }
