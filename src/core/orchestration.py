"""
Intelligent Orchestration System

Provides smart baton passing between agents with:
- Context-aware handoffs
- Dynamic routing based on conversation state
- Intelligent follow-up question generation
- Bidirectional conversation support
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from src.core.models import (
    AgentRole,
    HITLCheckpoint,
    HITLDecision,
    HITLGateType,
    SessionState,
)

logger = logging.getLogger(__name__)


class HandoffReason(Enum):
    """Reasons for agent handoff."""
    TASK_COMPLETE = "task_complete"
    NEEDS_EXPERTISE = "needs_expertise"
    USER_REQUESTED = "user_requested"
    CLARIFICATION_NEEDED = "clarification_needed"
    DEPENDENCY_REQUIRED = "dependency_required"
    REVIEW_REQUESTED = "review_requested"
    ERROR_ESCALATION = "error_escalation"


class ConversationIntent(Enum):
    """User's intent in the conversation."""
    PROVIDE_INFO = "provide_info"
    ASK_QUESTION = "ask_question"
    REQUEST_CHANGE = "request_change"
    APPROVE = "approve"
    REJECT = "reject"
    CLARIFY = "clarify"
    ELABORATE = "elaborate"
    REDIRECT = "redirect"


@dataclass
class AgentHandoff:
    """Represents a handoff between agents."""
    from_agent: AgentRole
    to_agent: AgentRole
    reason: HandoffReason
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: UUID = field(default_factory=uuid4)


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    speaker: str  # 'user' or agent role
    content: str
    intent: Optional[ConversationIntent] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    requires_response: bool = False
    follow_up_questions: List[str] = field(default_factory=list)


@dataclass
class SmartCheckpoint:
    """
    Enhanced HITL checkpoint with intelligent features.
    
    Supports:
    - Dynamic follow-up questions based on context
    - Conversation history awareness
    - Smart suggestions based on previous responses
    - Ability to request specific information
    """
    id: UUID = field(default_factory=uuid4)
    gate_type: HITLGateType = HITLGateType.IDEA_CLARIFICATION
    pillar: int = 1
    agent: AgentRole = AgentRole.ROUTER
    
    # Core content
    prompt: str = ""
    options: List[HITLDecision] = field(default_factory=list)
    
    # Smart features
    questions: List[Dict[str, Any]] = field(default_factory=list)  # Structured questions
    suggestions: List[str] = field(default_factory=list)  # Smart suggestions
    context_summary: str = ""  # Summary of conversation so far
    required_fields: List[str] = field(default_factory=list)  # Required info
    optional_fields: List[str] = field(default_factory=list)  # Optional info
    
    # Conversation state
    conversation_history: List[ConversationTurn] = field(default_factory=list)
    pending_clarifications: List[str] = field(default_factory=list)
    
    # Resolution
    is_resolved: bool = False
    decision: Optional[HITLDecision] = None
    user_responses: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    def to_hitl_checkpoint(self) -> HITLCheckpoint:
        """Convert to standard HITLCheckpoint for compatibility."""
        return HITLCheckpoint(
            id=self.id,
            gate_type=self.gate_type,
            pillar=self.pillar,
            agent=self.agent,
            prompt=self.prompt,
            options=self.options,
            metadata={
                "questions": self.questions,
                "suggestions": self.suggestions,
                "context_summary": self.context_summary,
                "required_fields": self.required_fields,
                "conversation_history": [
                    {"speaker": t.speaker, "content": t.content}
                    for t in self.conversation_history[-5:]  # Last 5 turns
                ],
            },
            is_resolved=self.is_resolved,
            decision=self.decision,
        )


class IntelligentOrchestrator:
    """
    Intelligent orchestration system for smart agent coordination.
    
    Features:
    - Context-aware agent routing
    - Dynamic handoff decisions
    - Intelligent follow-up generation
    - Conversation state management
    - Smart checkpoint creation
    """
    
    def __init__(self, session_state: SessionState):
        self.session_state = session_state
        self.conversation_history: List[ConversationTurn] = []
        self.handoff_history: List[AgentHandoff] = []
        self.active_agent: Optional[AgentRole] = None
        self.pending_handoffs: List[AgentHandoff] = []
        
        # Agent capabilities and dependencies
        self._agent_capabilities = self._define_agent_capabilities()
        self._agent_dependencies = self._define_agent_dependencies()
        
        # Callbacks
        self._on_handoff_callbacks: List[Callable[[AgentHandoff], None]] = []
        self._on_checkpoint_callbacks: List[Callable[[SmartCheckpoint], None]] = []
    
    def _define_agent_capabilities(self) -> Dict[AgentRole, Set[str]]:
        """Define what each agent can do."""
        return {
            # Pillar 1
            AgentRole.ROUTER: {"orchestrate", "clarify", "synthesize", "delegate"},
            AgentRole.ARIA: {"technical_analysis", "architecture", "stack_recommendation", "risk_assessment"},
            AgentRole.FELIX: {"financial_analysis", "cost_estimation", "runway_projection", "pricing_research"},
            AgentRole.NOVA: {"marketing_strategy", "positioning", "copywriting", "audience_analysis"},
            AgentRole.JUDGE: {"investment_evaluation", "critical_analysis", "fundability_assessment"},
            
            # Pillar 2
            AgentRole.ORCHESTRATOR: {"orchestrate", "coordinate", "pipeline_management"},
            AgentRole.PLANNER: {"spec_creation", "task_decomposition", "dependency_analysis"},
            AgentRole.CODER: {"code_generation", "implementation", "refactoring"},
            AgentRole.TESTER: {"test_generation", "test_execution", "coverage_analysis"},
            AgentRole.DOCS: {"documentation", "comments", "readme_generation"},
            AgentRole.REVIEWER: {"code_review", "security_analysis", "quality_assessment"},
            
            # Pillar 3
            AgentRole.SAGE: {"codebase_analysis", "question_answering", "context_retrieval"},
        }
    
    def _define_agent_dependencies(self) -> Dict[AgentRole, List[AgentRole]]:
        """Define agent dependencies (who needs output from whom)."""
        return {
            # Pillar 1 - FELIX needs ARIA's tech analysis for cost estimation
            AgentRole.FELIX: [AgentRole.ARIA],
            AgentRole.NOVA: [AgentRole.ARIA, AgentRole.FELIX],
            AgentRole.JUDGE: [AgentRole.ARIA, AgentRole.FELIX, AgentRole.NOVA],
            
            # Pillar 2 - Sequential dependencies
            AgentRole.CODER: [AgentRole.PLANNER],
            AgentRole.TESTER: [AgentRole.CODER],
            AgentRole.DOCS: [AgentRole.CODER, AgentRole.TESTER],
            AgentRole.REVIEWER: [AgentRole.CODER, AgentRole.TESTER, AgentRole.DOCS],
        }
    
    def add_conversation_turn(
        self,
        speaker: str,
        content: str,
        intent: Optional[ConversationIntent] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationTurn:
        """Add a turn to the conversation history."""
        # Auto-detect intent if not provided
        if intent is None and speaker == "user":
            intent = self._detect_intent(content)
        
        turn = ConversationTurn(
            speaker=speaker,
            content=content,
            intent=intent,
            metadata=metadata or {},
            requires_response=speaker == "user",
        )
        
        self.conversation_history.append(turn)
        logger.debug(f"Conversation turn added: {speaker} - {intent}")
        
        return turn
    
    def _detect_intent(self, content: str) -> ConversationIntent:
        """Detect user intent from their message."""
        content_lower = content.lower()
        
        # Question detection
        if any(q in content_lower for q in ["?", "what", "how", "why", "when", "where", "who", "can you"]):
            return ConversationIntent.ASK_QUESTION
        
        # Approval/rejection
        if any(w in content_lower for w in ["approve", "yes", "looks good", "proceed", "go ahead", "lgtm"]):
            return ConversationIntent.APPROVE
        if any(w in content_lower for w in ["reject", "no", "don't", "stop", "cancel"]):
            return ConversationIntent.REJECT
        
        # Change request
        if any(w in content_lower for w in ["change", "modify", "update", "instead", "rather", "different"]):
            return ConversationIntent.REQUEST_CHANGE
        
        # Clarification
        if any(w in content_lower for w in ["clarify", "explain", "mean", "understand"]):
            return ConversationIntent.CLARIFY
        
        # Elaboration
        if any(w in content_lower for w in ["more", "detail", "elaborate", "expand"]):
            return ConversationIntent.ELABORATE
        
        # Default to providing info
        return ConversationIntent.PROVIDE_INFO
    
    def should_handoff(
        self,
        current_agent: AgentRole,
        task_context: Dict[str, Any],
    ) -> Tuple[bool, Optional[AgentRole], Optional[HandoffReason]]:
        """
        Determine if the current agent should hand off to another.
        
        Returns:
            Tuple of (should_handoff, target_agent, reason)
        """
        # Check if task is complete
        if task_context.get("task_complete"):
            next_agent = self._get_next_agent_in_pipeline(current_agent)
            if next_agent:
                return True, next_agent, HandoffReason.TASK_COMPLETE
        
        # Check if expertise is needed
        required_capability = task_context.get("required_capability")
        if required_capability:
            expert = self._find_agent_with_capability(required_capability)
            if expert and expert != current_agent:
                return True, expert, HandoffReason.NEEDS_EXPERTISE
        
        # Check for user-requested redirect
        last_turn = self.conversation_history[-1] if self.conversation_history else None
        if last_turn and last_turn.intent == ConversationIntent.REDIRECT:
            target = self._parse_redirect_target(last_turn.content)
            if target:
                return True, target, HandoffReason.USER_REQUESTED
        
        # Check for clarification needs
        if task_context.get("needs_clarification"):
            return True, None, HandoffReason.CLARIFICATION_NEEDED
        
        return False, None, None
    
    def _get_next_agent_in_pipeline(self, current: AgentRole) -> Optional[AgentRole]:
        """Get the next agent in the standard pipeline."""
        pillar1_order = [AgentRole.ROUTER, AgentRole.ARIA, AgentRole.FELIX, AgentRole.NOVA, AgentRole.JUDGE]
        pillar2_order = [AgentRole.ORCHESTRATOR, AgentRole.PLANNER, AgentRole.CODER, AgentRole.TESTER, AgentRole.DOCS, AgentRole.REVIEWER]
        
        for pipeline in [pillar1_order, pillar2_order]:
            if current in pipeline:
                idx = pipeline.index(current)
                if idx < len(pipeline) - 1:
                    return pipeline[idx + 1]
        
        return None
    
    def _find_agent_with_capability(self, capability: str) -> Optional[AgentRole]:
        """Find an agent that has the required capability."""
        for agent, capabilities in self._agent_capabilities.items():
            if capability in capabilities:
                return agent
        return None
    
    def _parse_redirect_target(self, content: str) -> Optional[AgentRole]:
        """Parse user content to find redirect target."""
        content_lower = content.lower()
        
        agent_keywords = {
            AgentRole.ARIA: ["aria", "cto", "technical", "tech"],
            AgentRole.FELIX: ["felix", "cfo", "financial", "money", "cost"],
            AgentRole.NOVA: ["nova", "cmo", "marketing", "market"],
            AgentRole.JUDGE: ["judge", "investor", "funding"],
            AgentRole.PLANNER: ["planner", "plan", "spec"],
            AgentRole.CODER: ["coder", "code", "implement"],
            AgentRole.TESTER: ["tester", "test"],
            AgentRole.DOCS: ["docs", "document"],
            AgentRole.REVIEWER: ["reviewer", "review"],
            AgentRole.SAGE: ["sage", "codebase"],
        }
        
        for agent, keywords in agent_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return agent
        
        return None
    
    def create_smart_checkpoint(
        self,
        gate_type: HITLGateType,
        agent: AgentRole,
        pillar: int,
        base_prompt: str,
        questions: Optional[List[Dict[str, Any]]] = None,
        required_fields: Optional[List[str]] = None,
        generate_suggestions: bool = True,
    ) -> SmartCheckpoint:
        """
        Create an intelligent checkpoint with context awareness.
        
        Args:
            gate_type: Type of HITL gate
            agent: Agent creating the checkpoint
            pillar: Pillar number
            base_prompt: Base prompt text
            questions: Structured questions to ask
            required_fields: Required information fields
            generate_suggestions: Whether to generate smart suggestions
        """
        checkpoint = SmartCheckpoint(
            gate_type=gate_type,
            pillar=pillar,
            agent=agent,
            prompt=base_prompt,
            options=self._get_options_for_gate(gate_type),
            questions=questions or [],
            required_fields=required_fields or [],
            conversation_history=self.conversation_history[-10:],  # Last 10 turns
        )
        
        # Generate context summary
        checkpoint.context_summary = self._generate_context_summary()
        
        # Generate smart suggestions if enabled
        if generate_suggestions:
            checkpoint.suggestions = self._generate_suggestions(gate_type, agent)
        
        # Notify callbacks
        for callback in self._on_checkpoint_callbacks:
            try:
                callback(checkpoint)
            except Exception as e:
                logger.error(f"Checkpoint callback error: {e}")
        
        return checkpoint
    
    def _get_options_for_gate(self, gate_type: HITLGateType) -> List[HITLDecision]:
        """Get appropriate options for a gate type."""
        gate_options = {
            HITLGateType.IDEA_CLARIFICATION: [HITLDecision.APPROVE],
            HITLGateType.AGENT_DRAFT_REVIEW: [HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
            HITLGateType.BRIEF_APPROVAL: [HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
            HITLGateType.TASK_INTAKE: [HITLDecision.APPROVE],
            HITLGateType.SPEC_APPROVAL: [HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
            HITLGateType.MID_TASK_INTERRUPT: [HITLDecision.APPROVE, HITLDecision.EDIT],
            HITLGateType.REVIEWER_FLAG: [HITLDecision.FIX, HITLDecision.IGNORE, HITLDecision.EXPLAIN],
            HITLGateType.FINAL_PACKAGE: [HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
            HITLGateType.INDEXING_CONFIRM: [HITLDecision.APPROVE, HITLDecision.REJECT],
            HITLGateType.REINDEX_APPROVAL: [HITLDecision.APPROVE, HITLDecision.REJECT],
            HITLGateType.UNCERTAINTY_ESCALATION: [HITLDecision.APPROVE],
            HITLGateType.CONTEXT_CONFIRMATION: [HITLDecision.APPROVE, HITLDecision.EDIT],
        }
        return gate_options.get(gate_type, [HITLDecision.APPROVE, HITLDecision.REJECT])
    
    def _generate_context_summary(self) -> str:
        """Generate a summary of the conversation so far."""
        if not self.conversation_history:
            return "No previous conversation."
        
        # Get key points from conversation
        user_inputs = [t for t in self.conversation_history if t.speaker == "user"]
        agent_outputs = [t for t in self.conversation_history if t.speaker != "user"]
        
        summary_parts = []
        
        if user_inputs:
            summary_parts.append(f"User has provided {len(user_inputs)} inputs.")
            # Get the main topic from first user input
            if user_inputs[0].content:
                topic = user_inputs[0].content[:100]
                summary_parts.append(f"Main topic: {topic}...")
        
        if agent_outputs:
            agents_involved = set(t.speaker for t in agent_outputs)
            summary_parts.append(f"Agents involved: {', '.join(agents_involved)}")
        
        return " ".join(summary_parts)
    
    def _generate_suggestions(self, gate_type: HITLGateType, agent: AgentRole) -> List[str]:
        """Generate smart suggestions based on context."""
        suggestions = []
        
        # Gate-specific suggestions
        if gate_type == HITLGateType.IDEA_CLARIFICATION:
            suggestions = [
                "Provide more details about your target market",
                "Describe your unique value proposition",
                "Share any existing traction or validation",
            ]
        elif gate_type == HITLGateType.SPEC_APPROVAL:
            suggestions = [
                "Request more detailed acceptance criteria",
                "Ask for complexity estimates",
                "Request dependency analysis",
            ]
        elif gate_type == HITLGateType.REVIEWER_FLAG:
            suggestions = [
                "Request automated fix",
                "Ask for alternative approaches",
                "Request security impact analysis",
            ]
        
        return suggestions
    
    def process_user_response(
        self,
        checkpoint: SmartCheckpoint,
        decision: HITLDecision,
        user_input: str,
        field_responses: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[SmartCheckpoint]]:
        """
        Process user response to a checkpoint.
        
        Returns:
            Tuple of (is_complete, follow_up_checkpoint)
            - is_complete: True if no more input needed
            - follow_up_checkpoint: New checkpoint if follow-up needed
        """
        # Add to conversation history
        self.add_conversation_turn(
            speaker="user",
            content=user_input,
            intent=self._decision_to_intent(decision),
            metadata={"decision": decision.value, "field_responses": field_responses},
        )
        
        # Store responses
        checkpoint.user_responses = field_responses or {}
        checkpoint.decision = decision
        
        # Check if we need follow-up
        if decision == HITLDecision.EDIT:
            # User wants changes - need to understand what
            if not user_input.strip():
                # No details provided, ask for specifics
                follow_up = self._create_follow_up_checkpoint(
                    checkpoint,
                    "What specific changes would you like to make?",
                    [
                        {"id": "changes", "question": "Describe the changes you'd like", "required": True},
                    ],
                )
                return False, follow_up
        
        # Check for missing required fields
        missing_fields = self._check_required_fields(checkpoint, field_responses)
        if missing_fields:
            follow_up = self._create_follow_up_checkpoint(
                checkpoint,
                f"Please provide the following required information: {', '.join(missing_fields)}",
                [{"id": f, "question": f"Please provide: {f}", "required": True} for f in missing_fields],
            )
            return False, follow_up
        
        # Check if response needs clarification
        if self._needs_clarification(user_input):
            follow_up = self._create_follow_up_checkpoint(
                checkpoint,
                "Could you please clarify your response?",
                [{"id": "clarification", "question": "Please elaborate on your previous response", "required": True}],
            )
            return False, follow_up
        
        # Mark as resolved
        checkpoint.is_resolved = True
        checkpoint.resolved_at = datetime.utcnow()
        
        return True, None
    
    def _decision_to_intent(self, decision: HITLDecision) -> ConversationIntent:
        """Convert HITL decision to conversation intent."""
        mapping = {
            HITLDecision.APPROVE: ConversationIntent.APPROVE,
            HITLDecision.REJECT: ConversationIntent.REJECT,
            HITLDecision.EDIT: ConversationIntent.REQUEST_CHANGE,
            HITLDecision.FIX: ConversationIntent.REQUEST_CHANGE,
            HITLDecision.IGNORE: ConversationIntent.APPROVE,
            HITLDecision.EXPLAIN: ConversationIntent.CLARIFY,
        }
        return mapping.get(decision, ConversationIntent.PROVIDE_INFO)
    
    def _check_required_fields(
        self,
        checkpoint: SmartCheckpoint,
        responses: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Check for missing required fields."""
        if not checkpoint.required_fields or not responses:
            return []
        
        missing = []
        for field in checkpoint.required_fields:
            if field not in responses or not responses[field]:
                missing.append(field)
        
        return missing
    
    def _needs_clarification(self, user_input: str) -> bool:
        """Check if user input needs clarification."""
        # Very short responses might need clarification
        if len(user_input.strip()) < 10:
            return False  # Short is okay for simple approvals
        
        # Check for ambiguous language
        ambiguous_phrases = ["maybe", "not sure", "i think", "possibly", "might"]
        if any(phrase in user_input.lower() for phrase in ambiguous_phrases):
            return True
        
        return False
    
    def _create_follow_up_checkpoint(
        self,
        original: SmartCheckpoint,
        prompt: str,
        questions: List[Dict[str, Any]],
    ) -> SmartCheckpoint:
        """Create a follow-up checkpoint."""
        return SmartCheckpoint(
            gate_type=original.gate_type,
            pillar=original.pillar,
            agent=original.agent,
            prompt=prompt,
            options=[HITLDecision.APPROVE],  # Just need confirmation
            questions=questions,
            conversation_history=self.conversation_history[-10:],
            context_summary=f"Follow-up to: {original.prompt[:100]}...",
        )
    
    def record_handoff(self, handoff: AgentHandoff) -> None:
        """Record an agent handoff."""
        self.handoff_history.append(handoff)
        self.active_agent = handoff.to_agent
        
        # Add to conversation
        self.add_conversation_turn(
            speaker=handoff.from_agent.value,
            content=f"Handing off to {handoff.to_agent.value}: {handoff.reason.value}",
            metadata={"handoff_id": str(handoff.id)},
        )
        
        # Notify callbacks
        for callback in self._on_handoff_callbacks:
            try:
                callback(handoff)
            except Exception as e:
                logger.error(f"Handoff callback error: {e}")
    
    def on_handoff(self, callback: Callable[[AgentHandoff], None]) -> None:
        """Register a callback for handoffs."""
        self._on_handoff_callbacks.append(callback)
    
    def on_checkpoint(self, callback: Callable[[SmartCheckpoint], None]) -> None:
        """Register a callback for checkpoints."""
        self._on_checkpoint_callbacks.append(callback)
    
    def get_conversation_context(self, max_turns: int = 10) -> str:
        """Get formatted conversation context for agents."""
        recent = self.conversation_history[-max_turns:]
        
        lines = []
        for turn in recent:
            speaker = turn.speaker.upper() if turn.speaker != "user" else "USER"
            lines.append(f"[{speaker}]: {turn.content}")
        
        return "\n".join(lines)
    
    def get_agent_context(self, agent: AgentRole) -> Dict[str, Any]:
        """Get context relevant to a specific agent."""
        # Get outputs from dependency agents
        dependencies = self._agent_dependencies.get(agent, [])
        dependency_outputs = {}
        
        for dep in dependencies:
            # Find the most recent output from this agent
            for turn in reversed(self.conversation_history):
                if turn.speaker == dep.value:
                    dependency_outputs[dep.value] = turn.content
                    break
        
        return {
            "conversation_context": self.get_conversation_context(),
            "dependency_outputs": dependency_outputs,
            "handoff_history": [
                {"from": h.from_agent.value, "to": h.to_agent.value, "reason": h.reason.value}
                for h in self.handoff_history[-5:]
            ],
            "active_agent": self.active_agent.value if self.active_agent else None,
        }
