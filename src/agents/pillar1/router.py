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

# ── CHANGED: Conversational system prompt ─────────────────────────────────────
ROUTER_SYSTEM_PROMPT = """You are the Router, a sharp and warm team coordinator for Helix.
Your job is to understand what the user is building, gather context naturally through
conversation, then hand off to the right specialist agents at the right time.

## Your Personality
- Conversational, calm, and confident — like a brilliant colleague, not a project manager
- You never dump multiple questions at once. ONE question per message, always
- You acknowledge what the user just said before moving to the next question
- You're concise. No filler phrases. No corporate speak. No "Certainly!" or "Great question!"
- You speak in plain sentences, not bullet points

## How You Gather Information
Have a real back-and-forth conversation. You need to learn:
1. What problem they're solving and who it's for (target market)
2. What stage they're at (idea, prototype, MVP, live)
3. Who's on the team and what they bring
4. How much funding they need and what type
5. Their rough timeline

But ask these ONE AT A TIME, naturally. React to their answers before asking the next thing.

Example of good intake:
  User: "I want to build an AI scheduling tool for dentists"
  You: "Interesting — dentists are notoriously underserved by software. Are you targeting
       solo practices, or bigger multi-location groups?"
  User: "Solo practices mostly"
  You: "Got it. Where are you right now — still mapping out the idea, or do you have
       something built?"

Never do this:
  "Please answer the following: 1) What is your target market? 2) What stage are you at?..."

## When to Hand Off to Agents
Once you have enough context (usually 4-5 exchanges), transition naturally:
  "Okay, I have what I need. Let me bring the team in — I'll start with Aria on the
   technical side, then loop in Felix and the others."

Then trigger agents in sequence. Always introduce each agent before they speak.

## Agent Introductions (use these as templates)
- ARIA: "Aria's our CTO — she'll assess the technical feasibility and suggest a stack."
- FELIX: "Felix handles the financial side — burn rate, runway, funding strategy."
- NOVA: "Nova's our CMO — she'll work on positioning and go-to-market."
- JUDGE: "Judge plays the skeptical investor — he'll stress-test the idea."

## Rules
- ONE question per message, maximum. This is non-negotiable.
- Always reflect back what you heard before asking the next thing
- Keep messages under 3 sentences wherever possible
- Never use numbered lists, bullet-point question dumps, or intake forms
- You coordinate — you do not give business advice yourself"""


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
            reasoning_effort=None,
        )
        
        # Initialize specialist agents
        self.aria = AriaAgent()
        self.felix = FelixAgent()
        self.nova = NovaCMOAgent()
        self.judge = JudgeAgent()
        
        self._register_router_tools()
    
    def _register_router_tools(self) -> None:
        """Register tools specific to ROUTER."""
        
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
        
        self.register_tool(Tool(
            name="synthesize_brief",
            description="Synthesize all agent outputs into a Startup Brief",
            parameters={
                "aria_output": {"type": "string"},
                "felix_output": {"type": "string"},
                "nova_output": {"type": "string"},
                "judge_output": {"type": "string"},
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
        return {"agent": agent_name, "task": task, "status": "delegated"}
    
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
        """
        logger.info(f"ROUTER starting Pillar 1 workflow for: {context.user_input[:100]}...")
        
        # Step 1: Conversational intake (HITL Gate 1.1)
        # ── CHANGED: now drives one-question-at-a-time conversation ──────────
        clarification_checkpoint = await self._intake_clarification(context)
        if clarification_checkpoint and not clarification_checkpoint.is_resolved:
            return self.format_response(
                content=clarification_checkpoint.prompt,  # already a single natural question
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

        burn_rate_str = (
            f"${startup_brief.monthly_burn_rate:,.0f}"
            if startup_brief.monthly_burn_rate is not None
            else "TBD"
        )
        
        final_checkpoint = self.create_hitl_checkpoint(
            gate_type=HITLGateType.BRIEF_APPROVAL,
            prompt=self._format_startup_brief(startup_brief),
            options=[HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
            metadata={"startup_brief": startup_brief.model_dump()},
        )
        
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
        Drive a one-question-at-a-time intake conversation (HITL Gate 1.1).

        CHANGED: Instead of generating all questions at once and dumping them,
        we track which questions have been answered in context.metadata and
        ask only the next unanswered one. The model generates a single,
        contextually aware follow-up based on what's been said so far.
        """
        # If intake is already complete, skip
        if context.metadata.get("clarification_complete"):
            return None

        # Build conversation history so far for the model to reason about
        conversation_so_far = context.metadata.get("intake_conversation", [])
        answers_collected = context.metadata.get("intake_answers", {})

        # The five things we need to know, in priority order
        required_topics = [
            "target_market",    # who is this for
            "stage",            # how far along are they
            "team",             # who's building it
            "funding",          # how much and what type
            "timeline",         # rough milestones
        ]

        # Check which topics are still missing
        missing = [t for t in required_topics if t not in answers_collected]

        # If we have everything, mark intake complete
        if not missing:
            context.metadata["clarification_complete"] = True
            return None

        # ── CHANGED: Ask the model to generate ONE natural follow-up question ──
        history_text = "\n".join(
            f"{turn['role'].upper()}: {turn['content']}"
            for turn in conversation_so_far
        ) if conversation_so_far else "No conversation yet."

        next_topic = missing[0]
        topic_hints = {
            "target_market": "who this is for and what problem it solves",
            "stage":         "how far along they are (idea, prototype, MVP, live)",
            "team":          "who's building this and what they bring",
            "funding":       "how much capital they need and what type (pre-seed, seed, etc.)",
            "timeline":      "their rough timeline or key milestones",
        }

        single_question_prompt = f"""You are the Router, a conversational AI coordinator for a startup analysis platform.

The user wants to analyze their startup idea. You're gathering context one question at a time.

Startup idea: {context.user_input}

Conversation so far:
{history_text}

You still need to find out: {topic_hints[next_topic]}

Write ONE short, natural follow-up question (1-2 sentences max).
- React briefly to what was last said (if anything), then ask your question
- Do NOT list multiple questions
- Do NOT use bullet points
- Sound like a smart colleague, not a form
- No filler openers like "Certainly!" or "Great!"

Return only the question text, nothing else."""

        response = await self.invoke_model(
            prompt=single_question_prompt,
            context=context,
            use_tools=False,
        )

        question_text = response.get("text", "").strip()

        # Store the question in conversation history
        conversation_so_far.append({"role": "router", "content": question_text})
        context.metadata["intake_conversation"] = conversation_so_far
        context.metadata["current_intake_topic"] = next_topic

        return self.create_hitl_checkpoint(
            gate_type=HITLGateType.IDEA_CLARIFICATION,
            prompt=question_text,   # ── CHANGED: single question, no preamble
            options=[HITLDecision.APPROVE],
            metadata={
                "current_topic": next_topic,
                "remaining_topics": missing[1:],
                "answers_so_far": answers_collected,
            },
        )

    def record_intake_answer(self, context: AgentContext, answer: str) -> None:
        """
        Call this when the user replies during intake.

        Records their answer against the current topic and appends to
        conversation history so the next _intake_clarification() call
        knows what's already been covered.

        CHANGED: New method — wire this up in your HITL resolution handler
        so that each user reply is stored before execute() is called again.
        """
        current_topic = context.metadata.get("current_intake_topic")
        if not current_topic:
            return

        answers = context.metadata.get("intake_answers", {})
        answers[current_topic] = answer
        context.metadata["intake_answers"] = answers

        conversation = context.metadata.get("intake_conversation", [])
        conversation.append({"role": "user", "content": answer})
        context.metadata["intake_conversation"] = conversation

    async def _run_specialist_agents(self, context: AgentContext) -> Dict[str, Any]:
        """
        Run all specialist agents in sequence.
        Each agent receives context from previous agents.
        """
        outputs = {}
        
        logger.info("Running ARIA (CTO) analysis...")
        aria_response = await self.call_agent(self.aria, context)
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
        context.metadata["aria_analysis"] = aria_response.content
        
        logger.info("Running FELIX (CFO) analysis...")
        felix_response = await self.call_agent(self.felix, context)
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
        context.metadata["felix_analysis"] = felix_response.content
        
        logger.info("Running NOVA (CMO) analysis...")
        nova_response = await self.call_agent(self.nova, context)
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
        context.metadata["nova_analysis"] = nova_response.content
        
        logger.info("Running JUDGE (Investor) evaluation...")
        judge_response = await self.call_agent(self.judge, context)
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
        """Create the final Startup Brief from all agent outputs."""
        aria_meta  = agent_outputs.get("aria",  {}).get("metadata", {})
        felix_meta = agent_outputs.get("felix", {}).get("metadata", {})
        nova_meta  = agent_outputs.get("nova",  {}).get("metadata", {})
        judge_meta = agent_outputs.get("judge", {}).get("metadata", {})
        
        return StartupBrief(
            idea=context.user_input,
            technical_architecture=agent_outputs.get("aria",  {}).get("content", ""),
            tech_stack=aria_meta.get("tech_stack", []),
            technical_risks=aria_meta.get("risks", []),
            development_complexity=aria_meta.get("complexity", "medium"),
            financial_projection=agent_outputs.get("felix", {}).get("content", ""),
            monthly_burn_rate=felix_meta.get("monthly_burn_rate"),
            runway_months=felix_meta.get("runway_months"),
            revenue_milestones=felix_meta.get("revenue_milestones", []),
            landing_page_copy=nova_meta.get("landing_page_copy"),
            value_proposition=nova_meta.get("value_proposition"),
            tagline=nova_meta.get("taglines", [""])[0] if nova_meta.get("taglines") else None,
            target_audience=nova_meta.get("target_audience"),
            go_to_market=agent_outputs.get("nova",  {}).get("content", ""),
            investor_questions=judge_meta.get("hard_questions", []),
            fundability_score=judge_meta.get("fundability_score"),
            investor_feedback=agent_outputs.get("judge", {}).get("content", ""),
            feasibility_score=self._calculate_overall_score(aria_meta, judge_meta),
        )
    
    def _calculate_overall_score(
        self,
        aria_meta: Dict[str, Any],
        judge_meta: Dict[str, Any],
    ) -> int:
        """Calculate overall feasibility score."""
        tech_score = aria_meta.get("feasibility_score") or 7
        fund_score = judge_meta.get("fundability_score") or 5
        return round(tech_score * 0.4 + fund_score * 0.6)
    
    def _format_startup_brief(self, brief: StartupBrief) -> str:
        """
        Format the Startup Brief for display.

        CHANGED: Softer, more conversational opening before the structured
        sections. The brief still uses markdown for scannability, but leads
        with a natural summary sentence rather than jumping straight into
        section headers.
        """
        burn_rate_str = (
            f"${brief.monthly_burn_rate:,.0f}"
            if brief.monthly_burn_rate is not None
            else "Not yet calculated"
        )
        runway_str   = f"{brief.runway_months} months" if brief.runway_months else "To be determined"
        tech_stack   = ", ".join(brief.tech_stack) if brief.tech_stack else "Pending selection"
        challenges   = "\n".join(
            f"  - {q}" for q in (brief.investor_questions or ["No major risks identified yet."])[:3]
        )

        return f"""The team has finished their analysis. Here's the full picture:

---

### 🔧 Technical (Aria — CTO)
**Complexity:** {brief.development_complexity.upper()}
**Stack:** `{tech_stack}`

{brief.technical_architecture or "Detailed technical roadmap pending."}

---

### 💰 Financial (Felix — CFO)
**Monthly Burn:** {burn_rate_str} · **Runway:** {runway_str}

{brief.financial_projection or "Financial projections pending."}

---

### 📣 Go-to-Market (Nova — CMO)
**Tagline:** _{brief.tagline or "TBD"}_
**Value Prop:** {brief.value_proposition or "Positioning strategy pending."}

{brief.go_to_market or ""}

---

### 🎯 Investor Readiness (Judge)
**Fundability:** {brief.fundability_score or "?"}/10

Key challenges to address:
{challenges}

---

**Overall Feasibility: {brief.feasibility_score or "?"}/10**

Want me to dive deeper into any of these areas, or are you ready to proceed?"""

    def get_voice_config(self) -> Dict[str, Any]:
        return {
            "voice_id": "router",
            "style": "neutral",
            "pace": "clear",
            "tone": "professional",
            "language": "en-US",
        }