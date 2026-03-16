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

# ── CHANGED: Conversational system prompt with explicit handoffs ───────────────
ROUTER_SYSTEM_PROMPT = """You are the Router, a sharp and warm team coordinator for Helix.
Your job is to understand what the user is building, then introduce ONE specialist agent
at a time, with explicit user consent before each handoff.

## Your Personality
- Conversational, calm, and confident — like a brilliant colleague
- You never dump multiple questions at once. ONE question per message
- You're concise. No filler phrases. No corporate speak
- You speak in plain sentences, not bullet points

## Your Team (introduce ONE at a time)
- **ARIA** (CTO): Technical feasibility and architecture
- **FELIX** (CFO): Financial projections, burn rate, runway
- **NOVA** (CMO): Marketing strategy and positioning
- **JUDGE** (Investor): Critical evaluation and fundability

## CRITICAL: One Agent at a Time with User Consent
- You NEVER run all agents automatically
- Each agent has their own conversation with the user
- After each agent finishes, YOU come back and ask if user wants the next agent
- The user controls the pace and can skip agents

## Phase 1: Initial Intake (2-3 questions max)
Have a brief conversation to understand the idea:
  User: "I want to build an AI scheduling tool for dentists"
  You: "Interesting — dentists are underserved by software. Solo practices or bigger groups?"
  User: "Solo practices"
  You: "Got it. Are you at the idea stage or do you have something built already?"

## Phase 2: First Handoff (to ARIA)
Once you have basic context, introduce ARIA:
  "Okay, I have a good picture. Let me bring in Aria, our CTO — she'll look at the
   technical side and suggest an architecture. Aria, over to you!"

Then ARIA speaks and has her own conversation with the user.

## Phase 3: Handoff Checkpoints (CRITICAL)
After ARIA finishes, YOU come back and ask:
  "Aria's covered the technical angle. Want to hear from Felix next? He's our CFO —
   he'll break down the costs and funding needs. Or we can skip to Nova for marketing."

Wait for user response. If they say yes, introduce Felix:
  "Great, Felix — take it away!"

After FELIX finishes:
  "Felix has laid out the financials. Nova's our CMO — she can work on your value
   proposition and go-to-market. Want her perspective?"

After NOVA finishes:
  "Last up is Judge — he plays the skeptical investor and will stress-test the idea.
   Ready for the tough love?"

## Example Handoff Phrases
- "Want me to bring in [Agent] next?"
- "Should I pass the baton to [Agent]?"
- "Ready to hear from [Agent], or would you prefer to skip ahead?"
- "[Agent] can cover [topic] — interested?"

## Rules
- ONE question per message, maximum
- ALWAYS ask before bringing in the next agent
- Never auto-run multiple agents in sequence
- Each agent should have a real back-and-forth, not just dump information
- You're the host — you introduce, you check in, you facilitate"""


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
    
    def _detect_agent_request(self, user_input: str) -> Optional[str]:
        """
        Detect if user is requesting a specific agent or wants to move forward.
        Returns the agent name or 'next' if detected, None otherwise.
        """
        text = user_input.lower().strip()
        
        # FIRST: Check for specific agent mentions with "move to" pattern
        # This must come before generic "move to" detection
        if 'move to' in text:
            if 'aria' in text:
                return 'aria'
            if 'felix' in text:
                return 'felix'
            if 'nova' in text:
                return 'nova'
            if 'judge' in text:
                return 'judge'
        
        # Check for "go back to" or "connect me to" patterns
        go_back_patterns = ['go back to', 'connect me to', 'switch to', 'talk to', 'ask']
        for pattern in go_back_patterns:
            if pattern in text:
                if 'aria' in text:
                    return 'aria'
                if 'felix' in text:
                    return 'felix'
                if 'nova' in text:
                    return 'nova'
                if 'judge' in text:
                    return 'judge'
        
        # Direct agent mentions (only if they're asking for that agent specifically)
        if any(x in text for x in ['bring in aria', 'hear from aria', 'yes, aria', "let's hear from aria"]):
            return 'aria'
        if any(x in text for x in ['bring in felix', 'hear from felix', 'yes, felix', "let's hear from felix", 'yes, bring in felix']):
            return 'felix'
        if any(x in text for x in ['bring in nova', 'hear from nova', 'yes, nova', "let's hear from nova"]):
            return 'nova'
        if any(x in text for x in ['bring in judge', 'hear from judge', 'yes, judge', "let's hear from judge", 'tough love', 'ready for feedback']):
            return 'judge'
        
        # Skip to specific agent
        if 'skip to' in text:
            if 'felix' in text:
                return 'felix'
            if 'nova' in text:
                return 'nova'
            if 'judge' in text:
                return 'judge'
        
        # Move forward phrases (generic - no specific agent mentioned)
        move_phrases = [
            'next agent', 'move on', 'continue', 'proceed', 'go ahead', 'yes', 'sure',
            'let\'s go', 'bring', 'pass the baton', 'ready',
            'ok', 'okay', 'yep', 'yeah', 'sounds good', 'let\'s hear', 'go for it',
            'let\'s continue', 'next'
        ]
        if any(phrase in text for phrase in move_phrases):
            return 'next'
        
        return None

    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute Pillar 1 workflow with conversational agent handoffs.
        
        State machine:
        - intake: Gathering initial info from user
        - aria_pending: Asking if user wants to hear from Aria
        - aria_active: Aria is speaking
        - felix_pending: Asking if user wants to hear from Felix
        - felix_active: Felix is speaking
        - nova_pending: Asking if user wants to hear from Nova
        - nova_active: Nova is speaking
        - judge_pending: Asking if user wants to hear from Judge
        - judge_active: Judge is speaking
        - complete: All done
        """
        logger.info(f"ROUTER executing, stage: {context.metadata.get('workflow_stage', 'intake')}")
        
        stage = context.metadata.get("workflow_stage", "intake")
        user_response = context.metadata.get("last_user_response", "").lower()
        
        # Check if user is requesting to move to a specific agent or next
        agent_request = self._detect_agent_request(user_response)
        
        # Handle direct agent requests at ANY stage (not just intake)
        # This allows users to say "go back to Aria" or "connect me to Felix" at any point
        if agent_request and agent_request != 'next':
            if agent_request == 'aria':
                context.metadata["workflow_stage"] = "aria_pending"
                stage = "aria_pending"
                logger.info("User requested to switch to ARIA")
            elif agent_request == 'felix':
                context.metadata["workflow_stage"] = "felix_pending"
                stage = "felix_pending"
                logger.info("User requested to switch to FELIX")
            elif agent_request == 'nova':
                context.metadata["workflow_stage"] = "nova_pending"
                stage = "nova_pending"
                logger.info("User requested to switch to NOVA")
            elif agent_request == 'judge':
                context.metadata["workflow_stage"] = "judge_pending"
                stage = "judge_pending"
                logger.info("User requested to switch to JUDGE")
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: INTAKE - Gather initial info
        # ═══════════════════════════════════════════════════════════════════════
        if stage == "intake":
            clarification_checkpoint = await self._intake_clarification(context)
            if clarification_checkpoint and not clarification_checkpoint.is_resolved:
                return self.format_response(
                    content=clarification_checkpoint.prompt,
                    hitl_checkpoint=clarification_checkpoint,
                    metadata={"stage": "intake", "workflow_stage": "intake"},
                )
            
            # Intake complete - offer to bring in Aria
            context.metadata["workflow_stage"] = "aria_pending"
            handoff_prompt = """Great, I have a good picture of your idea!

Let me bring in Aria, our CTO — she'll assess the technical feasibility and suggest an architecture.

Ready to hear from Aria?"""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.IDEA_CLARIFICATION,
                prompt=handoff_prompt,
                options=[HITLDecision.APPROVE],
                metadata={"next_agent": "aria"},
            )
            return self.format_response(
                content=handoff_prompt,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "aria_pending"},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: ARIA
        # ═══════════════════════════════════════════════════════════════════════
        elif stage == "aria_pending":
            # User approved - run Aria
            context.metadata["workflow_stage"] = "aria_active"
            logger.info("Running ARIA (CTO) analysis...")
            
            aria_response = await self.call_agent(self.aria, context)
            context.metadata["aria_analysis"] = aria_response.content
            
            # After Aria, offer Felix
            context.metadata["workflow_stage"] = "felix_pending"
            handoff_prompt = f"""{aria_response.content}

---

That's my technical take. Want me to pass the baton to Felix? He's our CFO — he'll break down the costs, burn rate, and funding strategy."""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.IDEA_CLARIFICATION,
                prompt=handoff_prompt,
                options=[HITLDecision.APPROVE],
                metadata={"next_agent": "felix"},
            )
            return self.format_response(
                content=handoff_prompt,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "felix_pending"},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: FELIX
        # ═══════════════════════════════════════════════════════════════════════
        elif stage == "felix_pending":
            context.metadata["workflow_stage"] = "felix_active"
            logger.info("Running FELIX (CFO) analysis...")
            
            felix_response = await self.call_agent(self.felix, context)
            context.metadata["felix_analysis"] = felix_response.content
            
            # After Felix, offer Nova
            context.metadata["workflow_stage"] = "nova_pending"
            handoff_prompt = f"""{felix_response.content}

---

That's the financial picture. Want me to bring in Nova? She's our CMO — she'll work on your value proposition and go-to-market strategy."""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.IDEA_CLARIFICATION,
                prompt=handoff_prompt,
                options=[HITLDecision.APPROVE],
                metadata={"next_agent": "nova"},
            )
            return self.format_response(
                content=handoff_prompt,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "nova_pending"},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: NOVA
        # ═══════════════════════════════════════════════════════════════════════
        elif stage == "nova_pending":
            context.metadata["workflow_stage"] = "nova_active"
            logger.info("Running NOVA (CMO) analysis...")
            
            nova_response = await self.call_agent(self.nova, context)
            context.metadata["nova_analysis"] = nova_response.content
            
            # After Nova, offer Judge
            context.metadata["workflow_stage"] = "judge_pending"
            handoff_prompt = f"""{nova_response.content}

---

That's the marketing angle. Last up is Judge — he plays the skeptical investor and will stress-test the whole idea. Ready for the tough love?"""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.IDEA_CLARIFICATION,
                prompt=handoff_prompt,
                options=[HITLDecision.APPROVE],
                metadata={"next_agent": "judge"},
            )
            return self.format_response(
                content=handoff_prompt,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "judge_pending"},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: JUDGE
        # ═══════════════════════════════════════════════════════════════════════
        elif stage == "judge_pending":
            context.metadata["workflow_stage"] = "judge_active"
            logger.info("Running JUDGE (Investor) evaluation...")
            
            judge_response = await self.call_agent(self.judge, context)
            context.metadata["judge_analysis"] = judge_response.content
            
            # After Judge, wrap up
            context.metadata["workflow_stage"] = "complete"
            wrap_up = f"""{judge_response.content}

---

**That's the full team's perspective!**

You've heard from:
- **Aria** (CTO) on technical feasibility
- **Felix** (CFO) on financials and runway
- **Nova** (CMO) on marketing and positioning
- **Judge** (Investor) on fundability

What would you like to do next? You can:
- Ask follow-up questions to any of us
- Move to **Pillar 2** to start building
- Save this analysis for later"""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.BRIEF_APPROVAL,
                prompt=wrap_up,
                options=[HITLDecision.APPROVE, HITLDecision.EDIT],
                metadata={"stage": "complete"},
            )
            return self.format_response(
                content=wrap_up,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "complete", "workflow_complete": True},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: COMPLETE
        # ═══════════════════════════════════════════════════════════════════════
        else:
            return self.format_response(
                content="The analysis is complete. Let me know if you have any questions!",
                metadata={"workflow_stage": "complete", "workflow_complete": True},
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