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

Your role is to create clear, well-structured engineering documentation.

**OUTPUT FORMAT - USE MARKDOWN WITH CLEAR SECTIONS:**

## 🏗️ Architecture Overview
Describe the system components and how they interact. Use bullet points.

## 📊 Database Schema
For each entity, use this format:
### EntityName
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| name | String | User's name |

## 📁 Project Structure
```
project-name/
├── src/
│   ├── components/
│   ├── pages/
│   └── utils/
├── package.json
└── README.md
```

## 📦 Dependencies
### Frontend
- react: ^18.2.0
- tailwindcss: ^3.4.0

### Backend
- express: ^4.18.0
- prisma: ^5.0.0

## ⚙️ Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| DATABASE_URL | Database connection | postgresql://... |
| JWT_SECRET | Auth secret key | your-secret-key |

## 📋 Implementation Tasks
1. **Setup Project** (Priority: High)
   - Initialize React with Vite
   - Configure Tailwind CSS
   - Files: package.json, vite.config.ts, tailwind.config.js

2. **Create Components** (Priority: High)
   - Build reusable UI components
   - Files: src/components/*.tsx

CRITICAL RULES:
- Use clear markdown formatting with headers and tables
- NO "TBD" or placeholder text - provide real, specific content
- Include actual package versions
- Be specific about file paths
- NO questions - just design and plan"""


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
            reasoning_effort=ReasoningEffort.HIGH,  # Deep thinking for planning
        )
        
        # NOTE: Tools disabled to avoid "Model produced invalid sequence" errors
        # Specialist agents will now operate autonomously without tool-calling overhead.
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute PLANNER's task decomposition.
        
        Args:
            context: Agent execution context with user input
            
        Returns:
            AgentResponse with engineering specification
        """
        logger.info(f"PLANNER analyzing: {context.user_input[:100]}...")
        
        # Get codebase context if available
        codebase_context = context.codebase_context or ""
        
        # Build the planning prompt
        planning_prompt = f"""Create a detailed engineering specification for the following request:

## Feature Request:
{context.user_input}

## Codebase Context:
{codebase_context if codebase_context else "No codebase context available. Assume a new project."}

## Additional Context:
{context.metadata.get('additional_context', 'No additional context provided.')}

Please create a comprehensive engineering specification following your standard output format.

Think carefully about:
1. What exactly needs to be built
2. How to break this into discrete, testable tasks
3. What dependencies exist between tasks
4. What could go wrong and how to handle it
5. How to test each component

Use extended thinking to reason through the problem thoroughly before providing your specification."""

        try:
            # Invoke model with HIGH extended thinking
            # NOTE: use_tools=False to avoid "Model produced invalid sequence" errors
            response = await self.invoke_model(
                prompt=planning_prompt,
                context=context,
                use_tools=False,
            )
            
            # Extract the specification
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
                content="I encountered an error while creating the engineering specification.",
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
        
        # Simple parsing - extract tasks
        import re
        
        # Find task patterns
        task_pattern = r'\*\*Task \d+:\s*([^*]+)\*\*'
        task_matches = re.findall(task_pattern, spec_text)
        
        for i, task_name in enumerate(task_matches):
            tasks.append({
                "id": i + 1,
                "name": task_name.strip(),
                "status": "pending",
                "complexity": "medium",
            })
        
        # Find acceptance criteria
        criteria_pattern = r'- \[ \] (.+)'
        criteria_matches = re.findall(criteria_pattern, spec_text)
        acceptance_criteria = [c.strip() for c in criteria_matches]
        
        # Estimate overall complexity
        if len(tasks) <= 3:
            complexity = "low"
        elif len(tasks) <= 6:
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
