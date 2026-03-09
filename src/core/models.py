"""
Data models and enums for Helix.

Defines the core data structures used throughout the application.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class NovaModel(str, Enum):
    """Available Amazon Nova models."""
    # Nova 2 models (latest)
    NOVA_LITE = "amazon.nova-lite-v1:0"  # Nova Lite for text generation
    NOVA_PRO = "amazon.nova-pro-v1:0"    # Nova Pro for advanced reasoning
    NOVA_SONIC = "amazon.nova-sonic-v1:0"  # Nova Sonic for voice
    NOVA_EMBEDDINGS = "amazon.titan-embed-text-v2:0"  # Titan for embeddings


class ReasoningEffort(str, Enum):
    """
    Extended thinking reasoning effort levels for Nova 2 Lite.
    
    - LOW: Tasks with added complexity requiring structured thinking
    - MEDIUM: Multi-step tasks and coding workflows
    - HIGH: STEM reasoning and advanced problem-solving
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentRole(str, Enum):
    """Agent roles in Helix."""
    # Pillar 1 - Founding Team
    ARIA = "aria"      # CTO Agent
    FELIX = "felix"    # CFO Agent
    NOVA = "nova"      # CMO Agent
    JUDGE = "judge"    # Investor Agent
    ROUTER = "router"  # Orchestrator for Pillar 1
    
    # Pillar 2 - Engineering Workforce
    PLANNER = "planner"
    CODER = "coder"
    TESTER = "tester"
    DOCS = "docs"
    REVIEWER = "reviewer"
    ORCHESTRATOR = "orchestrator"
    
    # Pillar 3 - Codebase Intelligence
    SAGE = "sage"


class MessageRole(str, Enum):
    """Message roles in conversations."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class HITLGateType(str, Enum):
    """Types of Human-in-the-Loop gates."""
    # Pillar 1 Gates
    IDEA_CLARIFICATION = "gate_1_1"
    AGENT_DRAFT_REVIEW = "gate_1_2"
    BRIEF_APPROVAL = "gate_1_3"
    
    # Pillar 2 Gates
    TASK_INTAKE = "gate_2_1"
    SPEC_APPROVAL = "gate_2_2"
    MID_TASK_INTERRUPT = "gate_2_3"
    REVIEWER_FLAG = "gate_2_4"
    FINAL_PACKAGE = "gate_2_5"
    
    # Pillar 3 Gates
    INDEXING_CONFIRM = "gate_3_1"
    REINDEX_APPROVAL = "gate_3_2"
    UNCERTAINTY_ESCALATION = "gate_3_3"
    CONTEXT_CONFIRMATION = "gate_3_4"


class HITLDecision(str, Enum):
    """Possible decisions at HITL gates."""
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    REORDER = "reorder"
    FIX = "fix"
    IGNORE = "ignore"
    EXPLAIN = "explain"
    # Next steps decisions (for smart navigation)
    BUILD = "build"
    REFINE = "refine"
    SAVE = "save"
    CREATE_PR = "create_pr"
    REVIEW = "review"
    MODIFY = "modify"
    DOCKER = "docker"
    GITHUB_PR = "github_pr"
    LOCAL = "local"
    DOWNLOAD = "download"


class Message(BaseModel):
    """A single message in a conversation."""
    id: UUID = Field(default_factory=uuid4)
    role: MessageRole
    content: str
    agent: Optional[AgentRole] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """A conversation thread."""
    id: UUID = Field(default_factory=uuid4)
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_message(self, role: MessageRole, content: str, agent: Optional[AgentRole] = None) -> Message:
        """Add a message to the conversation."""
        message = Message(role=role, content=content, agent=agent)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message
    
    def get_context(self, max_messages: int = 50) -> List[Dict[str, str]]:
        """Get conversation context for model input."""
        recent_messages = self.messages[-max_messages:]
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in recent_messages
        ]


class HITLCheckpoint(BaseModel):
    """A Human-in-the-Loop checkpoint."""
    id: UUID = Field(default_factory=uuid4)
    gate_type: HITLGateType
    pillar: int
    agent: AgentRole
    prompt: str
    options: List[HITLDecision]
    decision: Optional[HITLDecision] = None
    user_input: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def is_resolved(self) -> bool:
        """Check if checkpoint has been resolved."""
        return self.decision is not None


class StartupBrief(BaseModel):
    """Output from Pillar 1 - The Founding Team."""
    id: UUID = Field(default_factory=uuid4)
    idea: str
    
    # ARIA (CTO) output
    technical_architecture: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    technical_risks: Optional[List[str]] = None
    development_complexity: Optional[str] = None
    
    # FELIX (CFO) output
    financial_projection: Optional[str] = None
    monthly_burn_rate: Optional[float] = None
    runway_months: Optional[int] = None
    revenue_milestones: Optional[List[str]] = None
    
    # NOVA (CMO) output
    landing_page_copy: Optional[str] = None
    value_proposition: Optional[str] = None
    tagline: Optional[str] = None
    target_audience: Optional[str] = None
    go_to_market: Optional[str] = None
    
    # JUDGE (Investor) output
    investor_questions: Optional[List[str]] = None
    fundability_score: Optional[int] = None  # 1-10
    investor_feedback: Optional[str] = None
    
    # Overall
    feasibility_score: Optional[int] = None  # 1-10
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved: bool = False


class EngineeringSpec(BaseModel):
    """Engineering specification from PLANNER agent."""
    id: UUID = Field(default_factory=uuid4)
    feature_description: str
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    estimated_complexity: str = "medium"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved: bool = False


class CodeOutput(BaseModel):
    """Output from CODER agent."""
    id: UUID = Field(default_factory=uuid4)
    files: Dict[str, str] = Field(default_factory=dict)  # filename -> content
    tests: Dict[str, str] = Field(default_factory=dict)  # test filename -> content
    documentation: Dict[str, str] = Field(default_factory=dict)
    review_flags: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GitHubPRInfo(BaseModel):
    """Information about a created GitHub Pull Request."""
    pr_number: int
    pr_url: str
    branch_name: str
    title: str
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CodebaseIndex(BaseModel):
    """Index information for a codebase (Pillar 3)."""
    id: UUID = Field(default_factory=uuid4)
    repository_url: str
    indexed_files: List[str] = Field(default_factory=list)
    excluded_files: List[str] = Field(default_factory=list)
    total_chunks: int = 0
    last_indexed_at: Optional[datetime] = None
    last_commit_sha: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
    """
    Complete session state for Helix.
    
    Tracks all completed checkpoints, decisions, and active pipelines.
    """
    id: UUID = Field(default_factory=uuid4)
    
    # Conversations per pillar
    pillar1_conversation: Conversation = Field(default_factory=Conversation)
    pillar2_conversation: Conversation = Field(default_factory=Conversation)
    pillar3_conversation: Conversation = Field(default_factory=Conversation)
    
    # HITL tracking
    checkpoints: List[HITLCheckpoint] = Field(default_factory=list)
    pending_checkpoints: List[UUID] = Field(default_factory=list)
    
    # Pillar outputs
    startup_brief: Optional[StartupBrief] = None
    engineering_spec: Optional[EngineeringSpec] = None
    code_output: Optional[CodeOutput] = None
    github_pr: Optional[GitHubPRInfo] = None
    codebase_index: Optional[CodebaseIndex] = None
    
    # Session metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    active_pillar: Optional[int] = None
    
    def add_checkpoint(self, checkpoint: HITLCheckpoint) -> None:
        """Add a new HITL checkpoint."""
        self.checkpoints.append(checkpoint)
        self.pending_checkpoints.append(checkpoint.id)
        self.updated_at = datetime.utcnow()
    
    def resolve_checkpoint(
        self, 
        checkpoint_id: UUID, 
        decision: HITLDecision, 
        user_input: Optional[str] = None
    ) -> None:
        """Resolve a pending checkpoint."""
        for checkpoint in self.checkpoints:
            if checkpoint.id == checkpoint_id:
                checkpoint.decision = decision
                checkpoint.user_input = user_input
                checkpoint.resolved_at = datetime.utcnow()
                if checkpoint_id in self.pending_checkpoints:
                    self.pending_checkpoints.remove(checkpoint_id)
                break
        self.updated_at = datetime.utcnow()
    
    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Get complete audit trail of all decisions."""
        return [
            {
                "checkpoint_id": str(cp.id),
                "gate": cp.gate_type.value,
                "agent": cp.agent.value,
                "decision": cp.decision.value if cp.decision else None,
                "user_input": cp.user_input,
                "timestamp": cp.timestamp.isoformat(),
                "resolved_at": cp.resolved_at.isoformat() if cp.resolved_at else None,
            }
            for cp in self.checkpoints
        ]
