"""
ORCHESTRATOR Agent

The Strands Agents master coordinator for Pillar 2. Manages the full pipeline,
handles agent hand-offs with user consent (like Pillar 1), tracks state, and 
assembles the final output package. Also integrates with Nova Act for GitHub PR creation.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.agents.pillar2.planner import PlannerAgent
from src.agents.pillar2.coder import CoderAgent
from src.agents.pillar2.tester import TesterAgent
from src.agents.pillar2.docs import DocsAgent
from src.agents.pillar2.reviewer import ReviewerAgent
from src.core.models import (
    AgentRole,
    CodeOutput,
    Conversation,
    EngineeringSpec,
    GitHubPRInfo,
    HITLCheckpoint,
    HITLDecision,
    HITLGateType,
    MessageRole,
    ReasoningEffort,
    SessionState,
)

logger = logging.getLogger(__name__)

# ── CHANGED: Conversational system prompt with explicit handoffs (like Pillar 1) ───────────────
ORCHESTRATOR_SYSTEM_PROMPT = """You are the ORCHESTRATOR, a sharp and efficient team coordinator for Helix's Engineering Workforce.
Your job is to understand what the user wants to build, then introduce ONE specialist agent
at a time, with explicit user consent before each handoff.

## Your Personality
- Conversational, efficient, and confident — like a senior tech lead
- You never dump multiple questions at once. ONE question per message
- You're concise. No filler phrases. No corporate speak
- You speak in plain sentences, not bullet points

## Your Team (introduce ONE at a time)
- **PLANNER**: Creates ERD diagrams, UML, architecture diagrams, and engineering specs
- **CODER**: Writes production-ready code, installs dependencies, creates project structure
- **TESTER**: Creates and runs test suites automatically
- **DOCS**: Generates comprehensive documentation
- **REVIEWER**: Reviews for quality, security, and best practices

## CRITICAL: One Agent at a Time with User Consent
- You NEVER run all agents automatically
- Each agent has their own conversation with the user
- After each agent finishes, YOU come back and ask if user wants the next agent
- The user controls the pace and can skip agents

## Phase 1: Initial Intake (1-2 questions max)
Have a brief conversation to deeply understand the requirements by asking smart, technical, yet accessible questions:
  User: "Build a todo app with React"
  You: "Got it — a React todo app. Would you prefer a minimalist design or something more robust with a video background and glassmorphism?"
  User: "A highly sophisticated design."
  You: "Perfect. Let me bring in the Planner to design the architecture."

IMPORTANT FOR INTAKE:
Whenever you ask a question to the user, you MUST also provide exactly 2-4 actionable, distinct suggestions they could choose from as answers.
You provide these suggestions as a bulleted list at the very end of your message, prefaced exactly with "SUGGESTIONS:".

Example:
Got it — a real estate platform. What primary aesthetic are you aiming for?
SUGGESTIONS:
- Modern glassmorphism with video backgrounds
- Clean, minimalist aesthetic with lots of white space
- High-contrast dark mode with neon accents

## Phase 2: First Handoff (to PLANNER)
Once you have basic context, introduce PLANNER:
  "Okay, I have a good picture. Let me bring in the Planner — they'll design the
   architecture and create the technical spec. Planner, over to you!"

Then PLANNER speaks and has their own conversation with the user.

## Phase 3: Handoff Checkpoints (CRITICAL)
After PLANNER finishes, YOU come back and ask:
  "Planner's covered the architecture. Want to hear from Coder next? They'll
   implement everything based on this spec. Or we can skip to Tester."

Wait for user response. If they say yes, introduce Coder:
  "Great, Coder — take it away!"

After CODER finishes:
  "Coder has built the project. Tester can run automated tests next.
   Want their perspective?"

After TESTER finishes:
  "Tests are done. Docs can generate documentation, or we can skip to Reviewer
   for a final quality check. What would you prefer?"

After DOCS finishes:
  "Documentation is ready. Last up is Reviewer — they'll do a final quality
   and security review. Ready for the review?"

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


class OrchestratorAgent(BaseAgent):
    """
    ORCHESTRATOR - Master coordinator for Pillar 2.
    
    Manages the full engineering pipeline with conversational handoffs.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.ORCHESTRATOR,
            name="ORCHESTRATOR",
            description="Pillar 2 Coordinator - Manages the engineering pipeline",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            reasoning_effort=None,  # Orchestrator doesn't need extended thinking
        )
        
        # Initialize specialist agents
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.docs = DocsAgent()
        self.reviewer = ReviewerAgent()
        
        # Pipeline state
        self._pipeline_state = {
            "stage": "idle",
            "spec": None,
            "code": None,
            "tests": None,
            "docs": None,
            "review": None,
        }
    
    def _detect_agent_request(self, user_input: str) -> Optional[str]:
        """
        Detect if user is requesting a specific agent or wants to move forward.
        Returns the agent name or 'next' if detected, None otherwise.
        """
        text = user_input.lower().strip()
        
        # FIRST: Check for specific agent mentions with "move to" pattern
        if 'move to' in text:
            if 'planner' in text:
                return 'planner'
            if 'coder' in text:
                return 'coder'
            if 'tester' in text:
                return 'tester'
            if 'docs' in text or 'documentation' in text:
                return 'docs'
            if 'reviewer' in text:
                return 'reviewer'
        
        # Check for "go back to" or "connect me to" patterns
        go_back_patterns = ['go back to', 'connect me to', 'switch to', 'talk to', 'ask']
        for pattern in go_back_patterns:
            if pattern in text:
                if 'planner' in text:
                    return 'planner'
                if 'coder' in text:
                    return 'coder'
                if 'tester' in text:
                    return 'tester'
                if 'docs' in text or 'documentation' in text:
                    return 'docs'
                if 'reviewer' in text:
                    return 'reviewer'
        
        # Direct agent mentions
        if any(x in text for x in ['bring in planner', 'hear from planner', 'yes, planner', "let's hear from planner"]):
            return 'planner'
        if any(x in text for x in ['bring in coder', 'hear from coder', 'yes, coder', "let's hear from coder", 'yes, bring in coder', 'start coding', 'build it']):
            return 'coder'
        if any(x in text for x in ['bring in tester', 'hear from tester', 'yes, tester', "let's hear from tester", 'run tests']):
            return 'tester'
        if any(x in text for x in ['bring in docs', 'hear from docs', 'yes, docs', "let's hear from docs", 'generate docs', 'documentation']):
            return 'docs'
        if any(x in text for x in ['bring in reviewer', 'hear from reviewer', 'yes, reviewer', "let's hear from reviewer", 'review', 'quality check']):
            return 'reviewer'
        
        # Skip to specific agent
        if 'skip to' in text:
            if 'coder' in text:
                return 'coder'
            if 'tester' in text:
                return 'tester'
            if 'docs' in text:
                return 'docs'
            if 'reviewer' in text:
                return 'reviewer'
        
        # Move forward phrases (generic - no specific agent mentioned)
        move_phrases = [
            'next agent', 'move on', 'continue', 'proceed', 'go ahead', 'yes', 'sure',
            'let\'s go', 'bring', 'pass the baton', 'ready',
            'ok', 'okay', 'yep', 'yeah', 'sounds good', 'let\'s hear', 'go for it',
            'let\'s continue', 'next', 'approve'
        ]
        if any(phrase in text for phrase in move_phrases):
            return 'next'
        
        # Regenerate/retry patterns
        if any(x in text for x in ['regenerate', 'try again', 'redo', 'retry']):
            return 'regenerate'
        
        return None

    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute Pillar 2 workflow with conversational agent handoffs.
        
        State machine:
        - intake: Gathering initial info from user
        - planner_pending: Asking if user wants to hear from Planner
        - planner_active: Planner is speaking
        - coder_pending: Asking if user wants to hear from Coder
        - coder_active: Coder is speaking
        - tester_pending: Asking if user wants to hear from Tester
        - tester_active: Tester is speaking
        - docs_pending: Asking if user wants to hear from Docs
        - docs_active: Docs is speaking
        - reviewer_pending: Asking if user wants to hear from Reviewer
        - reviewer_active: Reviewer is speaking
        - complete: All done
        """
        logger.info(f"ORCHESTRATOR executing, stage: {context.metadata.get('workflow_stage', 'intake')}")
        
        stage = context.metadata.get("workflow_stage", "intake")
        user_response = context.metadata.get("last_user_response", "").lower()
        
        # Check if user is requesting to move to a specific agent or next
        agent_request = self._detect_agent_request(user_response)
        
        # Handle regenerate request - go back to previous agent
        if agent_request == 'regenerate':
            previous_stage = context.metadata.get("previous_stage", stage)
            if previous_stage.endswith("_pending"):
                # Re-run the agent
                stage = previous_stage
                context.metadata["workflow_stage"] = stage
                logger.info(f"Regenerating: going back to {stage}")
        
        # Handle direct agent requests at ANY stage
        if agent_request and agent_request not in ['next', 'regenerate']:
            if agent_request == 'planner':
                context.metadata["workflow_stage"] = "planner_pending"
                stage = "planner_pending"
                logger.info("User requested to switch to PLANNER")
            elif agent_request == 'coder':
                context.metadata["workflow_stage"] = "coder_pending"
                stage = "coder_pending"
                logger.info("User requested to switch to CODER")
            elif agent_request == 'tester':
                context.metadata["workflow_stage"] = "tester_pending"
                stage = "tester_pending"
                logger.info("User requested to switch to TESTER")
            elif agent_request == 'docs':
                context.metadata["workflow_stage"] = "docs_pending"
                stage = "docs_pending"
                logger.info("User requested to switch to DOCS")
            elif agent_request == 'reviewer':
                context.metadata["workflow_stage"] = "reviewer_pending"
                stage = "reviewer_pending"
                logger.info("User requested to switch to REVIEWER")
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: INTAKE - Simple confirmation, no technical questions
        # ═══════════════════════════════════════════════════════════════════════
        if stage == "intake":
            # Check if user asked a question or wants clarification
            user_response = context.metadata.get("last_user_response", "").lower()
            
            # Detect if user is asking a question or wants more info
            question_patterns = [
                "what will you build", "what exactly", "how long", "how much",
                "explain", "tell me more", "what do you mean", "clarify",
                "i have a question", "question", "?"
            ]
            is_question = any(pattern in user_response for pattern in question_patterns)
            
            # Detect if user is approving/ready to proceed
            approval_patterns = [
                "yes", "let's start", "start", "ready", "go ahead", "proceed",
                "ok", "okay", "sure", "sounds good", "let's go", "build it"
            ]
            is_approval = any(pattern in user_response for pattern in approval_patterns)
            
            # If user asked a question, answer it and stay in intake
            if is_question and not is_approval:
                original_request = context.user_input
                answer_prompt = f"""The user wants to build something for: "{original_request}"
They asked: "{user_response}"
IMPORTANT: Answer their question briefly but smartly in 1-2 sentences. Then ask a follow-up technical question to narrow down the architecture (e.g., preferred design system, authentication type, database choice, or visual aesthetic like "video background vs minimalist").
Provide EXACTLY 2-4 suggestions at the end, formatted like:
SUGGESTIONS:
- Suggestion 1
- Suggestion 2"""

                response = await self.invoke_model(
                    prompt=answer_prompt,
                    context=context,
                    use_tools=False,
                )
                answer_text = response.get("text", "").strip()
                
                # Extract suggestions
                suggestions = []
                if "SUGGESTIONS:" in answer_text:
                    parts = answer_text.split("SUGGESTIONS:")
                    answer_text = parts[0].strip()
                    lines = parts[1].strip().split("\n")
                    for line in lines:
                        clean_line = line.strip().lstrip("-").lstrip("•").strip()
                        if clean_line:
                            suggestions.append(clean_line)

                checkpoint = self.create_hitl_checkpoint(
                    gate_type=HITLGateType.TASK_INTAKE,
                    prompt=answer_text,
                    options=[HITLDecision.APPROVE],
                    metadata={"next_agent": "planner", "answered_question": True},
                    suggestions=suggestions,
                )
                return self.format_response(
                    content=answer_text,
                    hitl_checkpoint=checkpoint,
                    metadata={"workflow_stage": "intake"},
                )
            
            # Store the original request if not already stored
            if not context.metadata.get("original_request"):
                context.metadata["original_request"] = context.user_input
            original_request = context.metadata.get("original_request", context.user_input)
            
            if is_approval:
                context.metadata["workflow_stage"] = "planner_pending"
                stage = "planner_pending"
            elif not user_response:
                handoff_prompt = f"""Got it! I understand you want to build: **{original_request[:200]}**
Before we hand off to the Planner, could you clarify your preferred design aesthetic? Do you want a robust modern UI with a background video and glassmorphism, or a clean minimalist approach?
SUGGESTIONS:
- Highly sophisticated with a background video and glassmorphism
- Clean, minimalist aesthetic with lots of white space
- High-contrast dark mode with neon accents"""

                suggestions = [
                    "Highly sophisticated with a background video and glassmorphism",
                    "Clean, minimalist aesthetic with lots of white space",
                    "High-contrast dark mode with neon accents"
                ]

                # remove the SUGGESTIONS block from the prompt shown to user
                prompt_to_show = handoff_prompt.split("SUGGESTIONS:")[0].strip()

                checkpoint = self.create_hitl_checkpoint(
                    gate_type=HITLGateType.TASK_INTAKE,
                    prompt=prompt_to_show,
                    options=[HITLDecision.APPROVE],
                    metadata={"next_agent": "planner"},
                    suggestions=suggestions,
                )
                return self.format_response(
                    content=prompt_to_show,
                    hitl_checkpoint=checkpoint,
                    metadata={"workflow_stage": "intake"},
                )
            else:
                # General conversation in intake before moving to planner
                original_request = context.user_input
                answer_prompt = f"""The user wants to build something for: "{original_request}"
They just said: "{user_response}"
Respond briefly, incorporating their preference, and ask if they are ready to hand off to the Planner to design the architecture.
Provide EXACTLY 2-4 suggestions at the end, formatted like:
SUGGESTIONS:
- Suggestion 1
- Suggestion 2"""

                response = await self.invoke_model(
                    prompt=answer_prompt,
                    context=context,
                    use_tools=False,
                )
                answer_text = response.get("text", "").strip()
                
                # Extract suggestions
                suggestions = []
                if "SUGGESTIONS:" in answer_text:
                    parts = answer_text.split("SUGGESTIONS:")
                    answer_text = parts[0].strip()
                    lines = parts[1].strip().split("\n")
                    for line in lines:
                        clean_line = line.strip().lstrip("-").lstrip("•").strip()
                        if clean_line:
                            suggestions.append(clean_line)

                checkpoint = self.create_hitl_checkpoint(
                    gate_type=HITLGateType.TASK_INTAKE,
                    prompt=answer_text,
                    options=[HITLDecision.APPROVE],
                    metadata={"next_agent": "planner"},
                    suggestions=suggestions,
                )
                return self.format_response(
                    content=answer_text,
                    hitl_checkpoint=checkpoint,
                    metadata={"workflow_stage": "intake"},
                )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: PLANNER
        # ═══════════════════════════════════════════════════════════════════════
        elif stage == "planner_pending":
            context.metadata["previous_stage"] = "planner_pending"
            context.metadata["workflow_stage"] = "planner_active"
            logger.info("Running PLANNER analysis...")
            
            planner_response = await self.call_agent(self.planner, context)
            context.metadata["planner_analysis"] = planner_response.content
            context.metadata["engineering_spec"] = planner_response.metadata
            
            # After Planner, offer Coder
            context.metadata["workflow_stage"] = "coder_pending"
            handoff_prompt = f"""{planner_response.content}

---

That's the architecture and spec. Want me to pass the baton to the Coder? They'll implement everything based on this design."""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.SPEC_APPROVAL,
                prompt=handoff_prompt,
                options=[HITLDecision.APPROVE, HITLDecision.EDIT],
                metadata={"next_agent": "coder"},
            )
            return self.format_response(
                content=handoff_prompt,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "coder_pending"},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: CODER
        # ═══════════════════════════════════════════════════════════════════════
        elif stage == "coder_pending":
            context.metadata["previous_stage"] = "coder_pending"
            context.metadata["workflow_stage"] = "coder_active"
            logger.info("Running CODER implementation...")
            
            coder_response = await self.call_agent(self.coder, context)
            context.metadata["coder_analysis"] = coder_response.content
            context.metadata["code_output"] = coder_response.metadata.get("code_output", {})
            
            # After Coder, offer Tester
            context.metadata["workflow_stage"] = "tester_pending"
            
            code_output = coder_response.metadata.get("code_output", {})
            files_created = list(code_output.get("files", {}).keys())
            
            handoff_prompt = f"""{coder_response.content}

---

**Files Created:** {len(files_created)}
{chr(10).join(f'  - `{f}`' for f in files_created[:5])}
{f'  - ... and {len(files_created) - 5} more' if len(files_created) > 5 else ''}

That's the implementation. Want me to bring in the Tester? They'll create and run automated tests."""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.REVIEWER_FLAG,
                prompt=handoff_prompt,
                options=[HITLDecision.APPROVE, HITLDecision.EDIT],
                metadata={"next_agent": "tester", "files_created": files_created},
            )
            return self.format_response(
                content=handoff_prompt,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "tester_pending", "code_output": code_output},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: TESTER
        # ═══════════════════════════════════════════════════════════════════════
        elif stage == "tester_pending":
            context.metadata["previous_stage"] = "tester_pending"
            context.metadata["workflow_stage"] = "tester_active"
            logger.info("Running TESTER analysis...")
            
            tester_response = await self.call_agent(self.tester, context)
            context.metadata["tester_analysis"] = tester_response.content
            context.metadata["test_output"] = tester_response.metadata
            
            # After Tester, offer Docs
            context.metadata["workflow_stage"] = "docs_pending"
            handoff_prompt = f"""{tester_response.content}

---

Tests are done. Want me to bring in Docs? They'll generate comprehensive documentation for the project. Or we can skip to Reviewer for a final quality check."""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.MID_TASK_INTERRUPT,
                prompt=handoff_prompt,
                options=[HITLDecision.APPROVE, HITLDecision.EDIT],
                metadata={"next_agent": "docs"},
            )
            return self.format_response(
                content=handoff_prompt,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "docs_pending"},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: DOCS
        # ═══════════════════════════════════════════════════════════════════════
        elif stage == "docs_pending":
            context.metadata["previous_stage"] = "docs_pending"
            context.metadata["workflow_stage"] = "docs_active"
            logger.info("Running DOCS generation...")
            
            docs_response = await self.call_agent(self.docs, context)
            context.metadata["docs_analysis"] = docs_response.content
            context.metadata["docs_output"] = docs_response.metadata
            
            # After Docs, offer Reviewer
            context.metadata["workflow_stage"] = "reviewer_pending"
            handoff_prompt = f"""{docs_response.content}

---

Documentation is ready. Last up is the Reviewer — they'll do a final quality and security review. Ready for the review?"""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.MID_TASK_INTERRUPT,
                prompt=handoff_prompt,
                options=[HITLDecision.APPROVE],
                metadata={"next_agent": "reviewer"},
            )
            return self.format_response(
                content=handoff_prompt,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "reviewer_pending"},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: REVIEWER
        # ═══════════════════════════════════════════════════════════════════════
        elif stage == "reviewer_pending":
            context.metadata["previous_stage"] = "reviewer_pending"
            context.metadata["workflow_stage"] = "reviewer_active"
            logger.info("Running REVIEWER evaluation...")
            
            reviewer_response = await self.call_agent(self.reviewer, context)
            context.metadata["reviewer_analysis"] = reviewer_response.content
            
            # After Reviewer, wrap up
            context.metadata["workflow_stage"] = "complete"
            
            # Assemble final package
            final_package = await self._assemble_final_package(context)
            
            wrap_up = f"""{reviewer_response.content}

---

**🎉 Engineering Complete!**

You've heard from:
- **Planner** on architecture and specs
- **Coder** on implementation
- **Tester** on automated tests
- **Docs** on documentation
- **Reviewer** on quality and security

What would you like to do next? You can:
- Ask follow-up questions to any agent
- Move to **Pillar 3** for codebase intelligence
- Deploy to GitHub (create PR)
- Download the project as ZIP
- Save this for later"""
            
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.FINAL_PACKAGE,
                prompt=wrap_up,
                options=[HITLDecision.APPROVE, HITLDecision.EDIT],
                metadata={
                    "stage": "complete",
                    "final_package": final_package,
                    "deployment_options": [
                        {
                            "id": "github_pr",
                            "label": "🔀 Create GitHub PR",
                            "description": "Push to branch and create pull request",
                        },
                        {
                            "id": "download",
                            "label": "📦 Download ZIP",
                            "description": "Download all files as a ZIP archive",
                        },
                        {
                            "id": "pillar3",
                            "label": "🧠 Move to Pillar 3",
                            "description": "Get codebase intelligence and insights",
                        },
                    ],
                },
            )
            return self.format_response(
                content=wrap_up,
                hitl_checkpoint=checkpoint,
                metadata={"workflow_stage": "complete", "workflow_complete": True, "final_package": final_package},
            )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STAGE: COMPLETE
        # ═══════════════════════════════════════════════════════════════════════
        else:
            return self.format_response(
                content="The engineering is complete. Let me know if you have any questions or want to revisit any agent!",
                metadata={"workflow_stage": "complete", "workflow_complete": True},
            )
    
    async def _intake_clarification(self, context: AgentContext) -> Optional[HITLCheckpoint]:
        """
        Drive a one-question-at-a-time intake conversation (HITL Gate 2.1).
        """
        # If intake is already complete, skip
        if context.metadata.get("clarification_complete"):
            return None

        # Build conversation history so far
        conversation_so_far = context.metadata.get("intake_conversation", [])
        answers_collected = context.metadata.get("intake_answers", {})

        # The things we need to know
        required_topics = [
            "tech_stack",    # what technologies to use
            "features",      # key features to implement
        ]

        # Check which topics are still missing
        missing = [t for t in required_topics if t not in answers_collected]

        # If we have everything, mark intake complete
        if not missing:
            context.metadata["clarification_complete"] = True
            return None

        # Ask the model to generate ONE natural follow-up question
        history_text = "\n".join(
            f"{turn['role'].upper()}: {turn['content']}"
            for turn in conversation_so_far
        ) if conversation_so_far else "No conversation yet."

        next_topic = missing[0]
        topic_hints = {
            "tech_stack": "what technologies or frameworks they want to use (React, Vue, Python, etc.)",
            "features": "the key features or functionality they need",
        }

        single_question_prompt = f"""You are the Orchestrator, a conversational AI coordinator for an engineering platform.

The user wants to build something. You're gathering context one question at a time.

User's request: {context.user_input}

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
        conversation_so_far.append({"role": "orchestrator", "content": question_text})
        context.metadata["intake_conversation"] = conversation_so_far
        context.metadata["current_intake_topic"] = next_topic

        return self.create_hitl_checkpoint(
            gate_type=HITLGateType.TASK_INTAKE,
            prompt=question_text,
            options=[HITLDecision.APPROVE],
            metadata={"topic": next_topic},
        )
    
    def record_intake_answer(self, context: AgentContext, user_response: str) -> None:
        """Record user's answer to an intake question."""
        topic = context.metadata.get("current_intake_topic")
        if topic:
            answers = context.metadata.get("intake_answers", {})
            answers[topic] = user_response
            context.metadata["intake_answers"] = answers
            
            # Also add to conversation history
            conversation = context.metadata.get("intake_conversation", [])
            conversation.append({"role": "user", "content": user_response})
            context.metadata["intake_conversation"] = conversation
    
    async def _assemble_final_package(self, context: AgentContext) -> Dict[str, Any]:
        """Assemble the final output package."""
        code_output = context.metadata.get("code_output", {})
        
        return {
            "feature_description": context.user_input,
            "spec": context.metadata.get("planner_analysis", ""),
            "files": code_output.get("files", {}),
            "tests": context.metadata.get("test_output", {}),
            "docs": context.metadata.get("docs_output", {}),
            "review": {
                "status": context.metadata.get("reviewer_analysis", ""),
            },
        }
    
    def _format_final_package(self, package: Dict[str, Any]) -> str:
        """Format the final package for display."""
        files = package.get("files", {})
        tests = package.get("tests", {})
        docs = package.get("docs", {})
        review = package.get("review", {})
        
        return f"""
# 🚀 ENGINEERING WORKFORCE OUTPUT: {package.get('feature_description', 'Feature')[:50]}...

> **Status:** The Engineering Workforce has completed the implementation and quality verification.

---

### 📁 SOURCE ARTIFACTS
* **Files Created/Modified:** `{len(files)}`
{chr(10).join(f'  - `{f}`' for f in list(files.keys())[:5])}
{f'  - ... and {len(files) - 5} more' if len(files) > 5 else ''}

---

### 🧪 TEST SUITE
* **Tests Generated:** `{len(tests)}`

---

### 📚 DOCUMENTATION
* **Docs Generated:** `{len(docs)}`

---

### 🔍 QUALITY ASSURANCE (REVIEWER)
* **Review Status:** Completed

---

**Ready for deployment.**
"""
    
    async def create_pr(self, context: AgentContext, package: Dict[str, Any]) -> GitHubPRInfo:
        """
        Create a GitHub PR using Nova Act.
        
        This is called after final approval (HITL Gate 2.5).
        """
        import re
        feature_slug = re.sub(r'[^a-z0-9]+', '-', context.user_input.lower())[:30]
        branch_name = f"feature/{feature_slug}"
        
        # Combine all files
        all_files = {}
        all_files.update(package.get("files", {}))
        all_files.update(package.get("tests", {}))
        all_files.update(package.get("docs", {}))
        
        # Generate PR description
        description = f"""## Summary
{context.user_input}

## Changes
- Added {len(package.get('files', {}))} source files
- Added {len(package.get('tests', {}))} test files
- Added {len(package.get('docs', {}))} documentation files

## Review Notes
{package.get('review', {}).get('status', 'Pending review')}

---
*Generated by Helix Engineering Workforce*
*Powered by Amazon Nova*
"""
        
        # Simulated PR creation (would use Nova Act in production)
        pr_number = 42
        
        return GitHubPRInfo(
            pr_number=pr_number,
            pr_url=f"https://github.com/owner/repo/pull/{pr_number}",
            branch_name=branch_name,
            title=f"feat: {context.user_input[:50]}",
            description=description,
        )
    
    def get_voice_config(self) -> Dict[str, Any]:
        """Get Nova 2 Sonic voice configuration for ORCHESTRATOR."""
        return {
            "voice_id": "orchestrator",
            "style": "efficient",
            "pace": "clear",
            "tone": "professional",
            "language": "en-US",
        }
