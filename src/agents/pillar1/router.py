"""
ROUTER - Pillar 1 Orchestrator Agent

The Strands Agents orchestrator for Pillar 1. Takes the user's input,
breaks it into domain tasks, dispatches to each specialist agent using
the `use_agent` pattern, collects outputs, and synthesizes a unified
Helix Startup Brief.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.agents.pillar1.aria import AriaAgent
from src.agents.pillar1.felix import FelixAgent
from src.agents.pillar1.nova_cmo import NovaCMOAgent
from src.agents.pillar1.judge import JudgeAgent
from src.core.models import (
    AgentRole,
    Conversation,
    HITLCheckpoint,
    HITLDecision,
    HITLGateType,
    MessageRole,
    ReasoningEffort,
    SessionState,
    StartupBrief,
)

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are the ROUTER, the orchestrator for Helix's Founding Team (Pillar 1).

Your role is to coordinate the analysis of startup ideas by delegating to specialist agents
and synthesizing their outputs into a comprehensive Startup Brief.

## Your Team:
- **ARIA (CTO)**: Technical feasibility and architecture
- **FELIX (CFO)**: Financial projections and costs
- **NOVA (CMO)**: Marketing strategy and positioning
- **JUDGE (Investor)**: Critical evaluation and fundability

## Your Responsibilities:
1. **Intake**: Gather necessary information about the startup idea
2. **Clarification**: Ask clarifying questions before analysis begins
3. **Delegation**: Route tasks to appropriate specialist agents
4. **Coordination**: Ensure agents have context from each other
5. **Synthesis**: Combine all analyses into a unified Startup Brief
6. **Quality Control**: Ensure all sections are complete and coherent

## Your Workflow:
1. Receive the startup idea from the user
2. Ask 3-5 clarifying questions (HITL Gate 1.1)
3. Dispatch to ARIA for technical analysis
4. Dispatch to FELIX for financial analysis (with ARIA's context)
5. Dispatch to NOVA for marketing strategy (with ARIA and FELIX context)
6. Dispatch to JUDGE for investor evaluation (with all context)
7. Synthesize the final Startup Brief
8. Present for user approval (HITL Gate 1.3)

## Your Personality:
- Clear, neutral, and efficient
- You keep the process moving smoothly
- You ensure nothing falls through the cracks
- You're the glue that holds the team together"""


class RouterAgent(BaseAgent):
    """
    ROUTER - Orchestrator for Pillar 1 (Founding Team).
    
    Coordinates all specialist agents and synthesizes the Startup Brief.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.ROUTER,
            name="ROUTER",
            description="Pillar 1 Orchestrator - Coordinates the Founding Team",
            system_prompt=ROUTER_SYSTEM_PROMPT,
            reasoning_effort=None,  # Router doesn't need extended thinking
        )
        
        # Initialize specialist agents
        self.aria = AriaAgent()
        self.felix = FelixAgent()
        self.nova = NovaCMOAgent()
        self.judge = JudgeAgent()
        
        # Register ROUTER-specific tools
        self._register_router_tools()
    
    def _register_router_tools(self) -> None:
        """Register tools specific to ROUTER."""
        
        # Tool to call specialist agents
        self.register_tool(Tool(
            name="use_agent",
            description="Delegate a task to a specialist agent",
            parameters={
                "agent_name": {
                    "type": "string",
                    "enum": ["aria", "felix", "nova", "judge"],
                    "description": "Name of the agent to call",
                },
                "task": {
                    "type": "string",
                    "description": "The task to delegate",
                },
                "context": {
                    "type": "object",
                    "description": "Additional context for the agent",
                },
            },
            handler=self._use_agent,
        ))
        
        # Tool to synthesize the brief
        self.register_tool(Tool(
            name="synthesize_brief",
            description="Synthesize all agent outputs into a Startup Brief",
            parameters={
                "aria_output": {
                    "type": "string",
                    "description": "ARIA's technical analysis",
                },
                "felix_output": {
                    "type": "string",
                    "description": "FELIX's financial analysis",
                },
                "nova_output": {
                    "type": "string",
                    "description": "NOVA's marketing strategy",
                },
                "judge_output": {
                    "type": "string",
                    "description": "JUDGE's investor evaluation",
                },
            },
            handler=self._synthesize_brief,
        ))
    
    async def _use_agent(
        self,
        agent_name: str,
        task: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Delegate to a specialist agent."""
        agents = {
            "aria": self.aria,
            "felix": self.felix,
            "nova": self.nova,
            "judge": self.judge,
        }
        
        agent = agents.get(agent_name)
        if not agent:
            return {"error": f"Unknown agent: {agent_name}"}
        
        # This is a placeholder - actual execution happens in execute()
        return {
            "agent": agent_name,
            "task": task,
            "status": "delegated",
        }
    
    async def _synthesize_brief(
        self,
        aria_output: str,
        felix_output: str,
        nova_output: str,
        judge_output: str,
    ) -> Dict[str, Any]:
        """Synthesize outputs into a Startup Brief."""
        return {
            "status": "synthesized",
            "sections": ["technical", "financial", "marketing", "investor"],
        }
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute the full Pillar 1 workflow.
        
        This orchestrates all specialist agents and produces the Startup Brief.
        
        Args:
            context: Agent execution context with user input
            
        Returns:
            AgentResponse with the complete Startup Brief
        """
        logger.info(f"ROUTER starting Pillar 1 workflow for: {context.user_input[:100]}...")
        
        # Step 1: Intake clarification (HITL Gate 1.1)
        clarification_checkpoint = await self._intake_clarification(context)
        if clarification_checkpoint and not clarification_checkpoint.is_resolved:
            return self.format_response(
                content="I need some clarifying information before we begin the analysis.",
                hitl_checkpoint=clarification_checkpoint,
                metadata={"stage": "intake"},
            )
        
        # Step 2: Run all specialist agents
        agent_outputs = await self._run_specialist_agents(context)
        
        # Step 3: Synthesize the Startup Brief
        startup_brief = await self._create_startup_brief(context, agent_outputs)
        
        # Step 4: Final approval (HITL Gate 1.3)
        if context.metadata.get("resolved_gate_1_3"):
            return self.format_response(
                content=self._format_startup_brief(startup_brief),
                metadata={"stage": "complete", "approved": True}
            )

        burn_rate_str = f"${startup_brief.monthly_burn_rate:,.0f}" if startup_brief.monthly_burn_rate is not None else "TBD"
        
        final_checkpoint = self.create_hitl_checkpoint(
            gate_type=HITLGateType.BRIEF_APPROVAL,
            prompt=f"""The Founding Team has completed the analysis. Here's your Helix Startup Brief:

## Summary
{startup_brief.idea}

## Technical Feasibility (ARIA)
Complexity: {startup_brief.development_complexity}
Tech Stack: {', '.join(startup_brief.tech_stack or [])}

## Financial Projection (FELIX)
Monthly Burn: {burn_rate_str}
Runway: {startup_brief.runway_months or 'TBD'} months

## Marketing (NOVA)
Tagline: {startup_brief.tagline or 'TBD'}
Value Prop: {startup_brief.value_proposition or 'TBD'}

## Investor Evaluation (JUDGE)
Fundability Score: {startup_brief.fundability_score or 'TBD'}/10

Please review and approve this brief to proceed.""",
            options=[HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
            metadata={"startup_brief": startup_brief.model_dump()},
        )
        
        # Store the brief in session state
        context.session_state.startup_brief = startup_brief
        
        return self.format_response(
            content=self._format_startup_brief(startup_brief),
            hitl_checkpoint=final_checkpoint,
            metadata={
                "stage": "complete",
                "startup_brief_id": str(startup_brief.id),
                "agent_outputs": {
                    "aria": agent_outputs.get("aria", {}).get("content", ""),
                    "felix": agent_outputs.get("felix", {}).get("content", ""),
                    "nova": agent_outputs.get("nova", {}).get("content", ""),
                    "judge": agent_outputs.get("judge", {}).get("content", ""),
                },
            },
        )
    
    async def _intake_clarification(self, context: AgentContext) -> Optional[HITLCheckpoint]:
        """
        Generate clarifying questions for the user (HITL Gate 1.1).
        """
        # Generate clarifying questions based on the input
        clarification_prompt = f"""Based on this startup idea, what clarifying questions should I ask?

Idea: {context.user_input}

Generate exactly 3-5 concise bullet points (starting with '-') that will help the team provide better analysis.

RULES:
1. Return ONLY the bullet points.
2. Do not include any introductory text like "Certainly" or "Here are".
3. Do not include any concluding text.
4. Focus on target market, stage, team, funding, and timeline."""

        response = await self.invoke_model(
            prompt=clarification_prompt,
            context=context,
            use_tools=False,
        )
        
        questions = response.get("text", "")
        
        # Check if we already have answers in metadata
        if context.metadata.get("clarification_complete"):
            return None
        
        return self.create_hitl_checkpoint(
            gate_type=HITLGateType.IDEA_CLARIFICATION,
            prompt=f"""Before the Founding Team begins their analysis, I have a few questions:

{questions}

Please provide your answers to help us give you the most relevant analysis.""",
            options=[HITLDecision.APPROVE],  # User just needs to provide answers
            metadata={"questions": questions},
        )
    
    async def _run_specialist_agents(self, context: AgentContext) -> Dict[str, Any]:
        """
        Run all specialist agents in sequence.
        
        Each agent receives context from previous agents.
        """
        outputs = {}
        
        # Run ARIA (CTO)
        logger.info("Running ARIA (CTO) analysis...")
        aria_response = await self.call_agent(self.aria, context)
        
        # Robustly extract technical metadata
        aria_meta = await self.structured_extract(
            text=aria_response.content,
            schema={
                "tech_stack": "list of strings",
                "complexity": "low/medium/high",
                "feasibility_score": "integer 1-10",
                "risks": "list of strings"
            },
            context=context
        )
        
        outputs["aria"] = {
            "content": aria_response.content,
            "metadata": aria_meta,
            "checkpoint": aria_response.hitl_checkpoint,
        }
        
        # Add ARIA's output to context for FELIX
        context.metadata["aria_analysis"] = aria_response.content
        
        # Run FELIX (CFO)
        logger.info("Running FELIX (CFO) analysis...")
        felix_response = await self.call_agent(self.felix, context)
        
        # Robustly extract financial metadata
        felix_meta = await self.structured_extract(
            text=felix_response.content,
            schema={
                "monthly_burn_rate": "number",
                "runway_months": "integer",
                "milestones": "list of strings"
            },
            context=context
        )
        
        outputs["felix"] = {
            "content": felix_response.content,
            "metadata": felix_meta,
            "checkpoint": felix_response.hitl_checkpoint,
        }
        
        # Add FELIX's output to context for NOVA
        context.metadata["felix_analysis"] = felix_response.content
        
        # Run NOVA (CMO)
        logger.info("Running NOVA (CMO) analysis...")
        nova_response = await self.call_agent(self.nova, context)
        
        # Robustly extract marketing metadata
        nova_meta = await self.structured_extract(
            text=nova_response.content,
            schema={
                "value_proposition": "string",
                "tagline": "string (the best one)",
                "target_audience": "string",
                "landing_page_copy": "string"
            },
            context=context
        )
        
        outputs["nova"] = {
            "content": nova_response.content,
            "metadata": nova_meta,
            "checkpoint": nova_response.hitl_checkpoint,
        }
        
        # Add NOVA's output to context for JUDGE
        context.metadata["nova_analysis"] = nova_response.content
        
        # Run JUDGE (Investor)
        logger.info("Running JUDGE (Investor) evaluation...")
        judge_response = await self.call_agent(self.judge, context)
        
        # Robustly extract investor metadata
        judge_meta = await self.structured_extract(
            text=judge_response.content,
            schema={
                "fundability_score": "integer 1-10",
                "hard_questions": "list of strings"
            },
            context=context
        )
        
        outputs["judge"] = {
            "content": judge_response.content,
            "metadata": judge_meta,
            "checkpoint": judge_response.hitl_checkpoint,
        }
        
        return outputs
    
    async def _create_startup_brief(
        self,
        context: AgentContext,
        agent_outputs: Dict[str, Any],
    ) -> StartupBrief:
        """
        Create the final Startup Brief from all agent outputs.
        """
        # Extract metadata from each agent
        aria_meta = agent_outputs.get("aria", {}).get("metadata", {})
        felix_meta = agent_outputs.get("felix", {}).get("metadata", {})
        nova_meta = agent_outputs.get("nova", {}).get("metadata", {})
        judge_meta = agent_outputs.get("judge", {}).get("metadata", {})
        
        brief = StartupBrief(
            idea=context.user_input,
            
            # ARIA (CTO) outputs
            technical_architecture=agent_outputs.get("aria", {}).get("content", ""),
            tech_stack=aria_meta.get("tech_stack", []),
            technical_risks=aria_meta.get("risks", []),
            development_complexity=aria_meta.get("complexity", "medium"),
            
            # FELIX (CFO) outputs
            financial_projection=agent_outputs.get("felix", {}).get("content", ""),
            monthly_burn_rate=felix_meta.get("monthly_burn_rate"),
            runway_months=felix_meta.get("runway_months"),
            revenue_milestones=felix_meta.get("revenue_milestones", []),
            
            # NOVA (CMO) outputs
            landing_page_copy=nova_meta.get("landing_page_copy"),
            value_proposition=nova_meta.get("value_proposition"),
            tagline=nova_meta.get("taglines", [""])[0] if nova_meta.get("taglines") else None,
            target_audience=nova_meta.get("target_audience"),
            go_to_market=agent_outputs.get("nova", {}).get("content", ""),
            
            # JUDGE (Investor) outputs
            investor_questions=judge_meta.get("hard_questions", []),
            fundability_score=judge_meta.get("fundability_score"),
            investor_feedback=agent_outputs.get("judge", {}).get("content", ""),
            
            # Overall
            feasibility_score=self._calculate_overall_score(aria_meta, judge_meta),
        )
        
        return brief
    
    def _calculate_overall_score(
        self,
        aria_meta: Dict[str, Any],
        judge_meta: Dict[str, Any],
    ) -> int:
        """Calculate overall feasibility score."""
        tech_score = aria_meta.get("feasibility_score")
        if tech_score is None:
            tech_score = 7
            
        fund_score = judge_meta.get("fundability_score")
        if fund_score is None:
            fund_score = 5
        
        # Weighted average
        return round((tech_score * 0.4 + fund_score * 0.6))
    
    def _format_startup_brief(self, brief: StartupBrief) -> str:
        """Format the Startup Brief for display."""
        burn_rate_str = f"${brief.monthly_burn_rate:,.0f}" if brief.monthly_burn_rate is not None else "Not yet calculated"
        runway_str = f"{brief.runway_months} months" if brief.runway_months else "To be determined"
        tech_stack = ", ".join(brief.tech_stack) if brief.tech_stack else "Pending selection"
        
        return f"""
# 🚀 HELIX STARTUP BRIEF: {brief.idea[:50]}...

> **Executive Summary:** A comprehensive analysis of the proposed startup venture by the Helix Founding Team.

---

### 🔧 TECHNICAL ARCHITECTURE (ARIA)
* **Complexity:** {brief.development_complexity.upper()}
* **Recommended Stack:** `{tech_stack}`
* **Analysis:** {brief.technical_architecture or 'Detailed technical roadmap pending.'}

---

### 💰 FINANCIAL STRATEGY (FELIX)
* **Est. Monthly Burn:** `{burn_rate_str}`
* **Est. Runway:** `{runway_str}`
* **Milestones:** {', '.join(brief.revenue_milestones) if brief.revenue_milestones else 'Revenue targets pending.'}

---

### 📣 GO-TO-MARKET (NOVA)
* **Tagline:** "_{brief.tagline or 'TBD'}_"
* **Value Prop:** {brief.value_proposition or 'Market positioning strategy pending.'}
* **Target:** {brief.target_audience or 'Audience segmentation pending.'}

---

### 🎯 INVESTOR READINESS (JUDGE)
* **Fundability Score:** **{brief.fundability_score or '?'}/10**
* **Key Challenges:**
{chr(10).join(f'  - {q}' for q in (brief.investor_questions or ['No major risks identified yet.'])[:3])}

---

**Overall Feasibility:** {brief.feasibility_score or '?'}/10
"""
    
    def get_voice_config(self) -> Dict[str, Any]:
        """
        Get Nova 2 Sonic voice configuration for ROUTER.
        
        ROUTER has a clear, neutral coordination voice.
        """
        return {
            "voice_id": "router",
            "style": "neutral",
            "pace": "clear",
            "tone": "professional",
            "language": "en-US",
        }
