"""
PLANNER Agent

Uses Nova 2 Lite with extended thinking (`high` budget) to decompose
plain English requests into structured engineering specs: tasks, subtasks,
dependencies, acceptance criteria, and estimated complexity.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, EngineeringSpec, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are the PLANNER agent for Helix's Engineering Workforce.

Your role is to create COMPREHENSIVE engineering documentation including:
- ERD (Entity Relationship Diagrams) in Mermaid format
- UML diagrams (Class, Sequence, Component) in Mermaid format
- Architecture diagrams in Mermaid format
- Detailed engineering specifications

## Your Responsibilities:
1. **Architecture Design**: Design the system architecture
2. **Database Design**: Create ERD with all entities and relationships
3. **Class Design**: Create UML class diagrams
4. **Flow Design**: Create sequence diagrams for key flows
5. **Task Decomposition**: Break down into implementable tasks
6. **Dependency Mapping**: Identify dependencies between tasks

## Your Output Format:
ALWAYS include these sections:

```markdown
## 🏗️ Architecture Overview

### System Architecture
\`\`\`mermaid
graph TB
    subgraph Frontend
        UI[React/Next.js UI]
        State[State Management]
    end
    subgraph Backend
        API[REST API]
        Auth[Authentication]
        BL[Business Logic]
    end
    subgraph Database
        DB[(PostgreSQL/MongoDB)]
    end
    UI --> API
    API --> Auth
    API --> BL
    BL --> DB
\`\`\`

### Component Diagram
\`\`\`mermaid
graph LR
    [Component relationships]
\`\`\`

## 📊 Database Design (ERD)

\`\`\`mermaid
erDiagram
    USER ||--o{ ORDER : places
    USER {
        int id PK
        string email
        string password_hash
        datetime created_at
    }
    ORDER ||--|{ ORDER_ITEM : contains
    ORDER {
        int id PK
        int user_id FK
        decimal total
        string status
    }
    [... all entities ...]
\`\`\`

## 📐 UML Class Diagram

\`\`\`mermaid
classDiagram
    class User {
        +int id
        +string email
        +create()
        +authenticate()
    }
    [... all classes ...]
\`\`\`

## 🔄 Sequence Diagrams

### User Registration Flow
\`\`\`mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant D as Database
    U->>F: Fill registration form
    F->>A: POST /api/register
    A->>D: Insert user
    D-->>A: User created
    A-->>F: Success + JWT
    F-->>U: Redirect to dashboard
\`\`\`

## 📋 Implementation Tasks

### Task 1: [Name]
- **Files**: [List of files to create]
- **Dependencies**: [What this depends on]
- **Acceptance Criteria**: [Clear criteria]
- **Complexity**: [Low/Medium/High]

[... more tasks ...]

## 🗂️ Project Structure

\`\`\`
project/
├── src/
│   ├── components/
│   ├── pages/
│   ├── api/
│   ├── models/
│   └── utils/
├── tests/
├── docs/
├── package.json
└── README.md
\`\`\`

## 📦 Dependencies

- [List all npm/pip packages needed]

## 🔧 Environment Variables

- [List all env vars needed]
```

## CRITICAL RULES:
- ALWAYS include Mermaid diagrams - they are essential
- ALWAYS include ERD for any project with data
- ALWAYS include project structure
- ALWAYS list dependencies
- Be specific and actionable
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
        
        # Register PLANNER-specific tools
        self._register_planner_tools()
    
    def _register_planner_tools(self) -> None:
        """Register tools specific to PLANNER."""
        
        # Task decomposition tool
        self.register_tool(Tool(
            name="decompose_task",
            description="Break down a high-level task into subtasks",
            parameters={
                "task_description": {
                    "type": "string",
                    "description": "The high-level task to decompose",
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about the codebase or requirements",
                },
            },
            handler=self._decompose_task,
        ))
        
        # Complexity estimation tool
        self.register_tool(Tool(
            name="estimate_complexity",
            description="Estimate the complexity of a task",
            parameters={
                "task": {
                    "type": "string",
                    "description": "Task description",
                },
                "factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Factors affecting complexity",
                },
            },
            handler=self._estimate_complexity,
        ))
        
        # Dependency analysis tool
        self.register_tool(Tool(
            name="analyze_dependencies",
            description="Analyze dependencies between tasks",
            parameters={
                "tasks": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of tasks to analyze",
                },
            },
            handler=self._analyze_dependencies,
        ))
    
    async def _decompose_task(
        self,
        task_description: str,
        context: str,
    ) -> Dict[str, Any]:
        """Decompose a high-level task into subtasks."""
        return {
            "original_task": task_description,
            "subtasks": [
                {"name": "Setup", "description": "Initial setup and configuration"},
                {"name": "Core Implementation", "description": "Main functionality"},
                {"name": "Error Handling", "description": "Handle edge cases"},
                {"name": "Testing", "description": "Write tests"},
                {"name": "Documentation", "description": "Document the implementation"},
            ],
            "estimated_total_hours": 8,
        }
    
    async def _estimate_complexity(
        self,
        task: str,
        factors: List[str],
    ) -> Dict[str, Any]:
        """Estimate task complexity."""
        # Simple heuristic based on factors
        complexity_score = len(factors) * 2
        
        if complexity_score <= 4:
            complexity = "low"
            hours = "1-2"
        elif complexity_score <= 8:
            complexity = "medium"
            hours = "2-4"
        else:
            complexity = "high"
            hours = "4-8"
        
        return {
            "task": task,
            "factors": factors,
            "complexity": complexity,
            "estimated_hours": hours,
            "confidence": "medium",
        }
    
    async def _analyze_dependencies(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Analyze task dependencies."""
        # Build dependency graph
        dependency_order = []
        for i, task in enumerate(tasks):
            dependency_order.append({
                "task": task.get("name", f"Task {i+1}"),
                "order": i + 1,
                "depends_on": task.get("dependencies", []),
                "blocks": [],
            })
        
        return {
            "tasks_analyzed": len(tasks),
            "dependency_order": dependency_order,
            "critical_path": [t["task"] for t in dependency_order],
            "parallelizable": [],
        }
    
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
            response = await self.invoke_model(
                prompt=planning_prompt,
                context=context,
                use_tools=True,
            )
            
            # Extract the specification
            spec_text = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse into structured spec
            engineering_spec = self._parse_engineering_spec(context.user_input, spec_text)
            
            # Create HITL checkpoint for spec approval (Gate 2.2)
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.SPEC_APPROVAL,
                prompt=f"""PLANNER has created the engineering specification. Please review:

{spec_text[:1000]}...

You can:
- **Approve**: Proceed with implementation
- **Edit**: Modify tasks or requirements
- **Reorder**: Change the implementation order
- **Reject**: Start over with different requirements""",
                options=[HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REORDER, HITLDecision.REJECT],
                metadata={"spec": engineering_spec.model_dump(), "full_spec": spec_text},
            )
            
            return self.format_response(
                content=spec_text,
                reasoning=reasoning,
                hitl_checkpoint=checkpoint,
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
