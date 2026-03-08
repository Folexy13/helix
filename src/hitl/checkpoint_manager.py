"""
Checkpoint Manager

Manages HITL checkpoints across all three pillars.
Tracks pending decisions, handles resolution, and maintains audit trail.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from src.core.models import (
    HITLCheckpoint,
    HITLDecision,
    HITLGateType,
    SessionState,
)

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages Human-in-the-Loop checkpoints.
    
    Responsibilities:
    - Track pending checkpoints
    - Handle checkpoint resolution
    - Maintain audit trail
    - Coordinate with voice/UI handlers
    """
    
    def __init__(self, session_state: SessionState):
        """
        Initialize the checkpoint manager.
        
        Args:
            session_state: The session state to manage
        """
        self.session_state = session_state
        
        # Callbacks for checkpoint events
        self._on_checkpoint_created: List[Callable[[HITLCheckpoint], None]] = []
        self._on_checkpoint_resolved: List[Callable[[HITLCheckpoint], None]] = []
        
        logger.info("CheckpointManager initialized")
    
    def add_checkpoint(self, checkpoint: HITLCheckpoint) -> None:
        """
        Add a new checkpoint.
        
        Args:
            checkpoint: The checkpoint to add
        """
        self.session_state.add_checkpoint(checkpoint)
        
        # Notify listeners
        for callback in self._on_checkpoint_created:
            try:
                callback(checkpoint)
            except Exception as e:
                logger.error(f"Checkpoint callback error: {e}")
        
        logger.info(f"Checkpoint added: {checkpoint.gate_type.value}")
    
    def resolve_checkpoint(
        self,
        checkpoint_id: UUID,
        decision: HITLDecision,
        user_input: Optional[str] = None,
    ) -> bool:
        """
        Resolve a pending checkpoint.
        
        Args:
            checkpoint_id: ID of the checkpoint to resolve
            decision: User's decision
            user_input: Optional additional input from user
            
        Returns:
            True if checkpoint was resolved, False if not found
        """
        # Find the checkpoint
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            logger.warning(f"Checkpoint not found: {checkpoint_id}")
            return False
        
        # Validate decision
        if decision not in checkpoint.options:
            logger.warning(f"Invalid decision {decision} for checkpoint {checkpoint_id}")
            return False
        
        # Resolve
        self.session_state.resolve_checkpoint(checkpoint_id, decision, user_input)
        
        # Notify listeners
        for callback in self._on_checkpoint_resolved:
            try:
                callback(checkpoint)
            except Exception as e:
                logger.error(f"Checkpoint resolved callback error: {e}")
        
        logger.info(f"Checkpoint resolved: {checkpoint.gate_type.value} -> {decision.value}")
        
        return True
    
    def get_checkpoint(self, checkpoint_id: UUID) -> Optional[HITLCheckpoint]:
        """Get a checkpoint by ID."""
        for checkpoint in self.session_state.checkpoints:
            if checkpoint.id == checkpoint_id:
                return checkpoint
        return None
    
    def get_pending_checkpoints(self) -> List[HITLCheckpoint]:
        """Get all pending (unresolved) checkpoints."""
        return [
            cp for cp in self.session_state.checkpoints
            if not cp.is_resolved
        ]
    
    def get_pending_for_pillar(self, pillar: int) -> List[HITLCheckpoint]:
        """Get pending checkpoints for a specific pillar."""
        return [
            cp for cp in self.get_pending_checkpoints()
            if cp.pillar == pillar
        ]
    
    def get_next_pending(self) -> Optional[HITLCheckpoint]:
        """Get the next pending checkpoint (oldest first)."""
        pending = self.get_pending_checkpoints()
        if pending:
            return min(pending, key=lambda cp: cp.timestamp)
        return None
    
    def has_pending(self) -> bool:
        """Check if there are any pending checkpoints."""
        return len(self.session_state.pending_checkpoints) > 0
    
    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Get the complete audit trail of all decisions."""
        return self.session_state.get_audit_trail()
    
    def get_checkpoint_summary(self) -> Dict[str, Any]:
        """Get a summary of checkpoint status."""
        all_checkpoints = self.session_state.checkpoints
        pending = self.get_pending_checkpoints()
        resolved = [cp for cp in all_checkpoints if cp.is_resolved]
        
        # Count by pillar
        by_pillar = {1: 0, 2: 0, 3: 0}
        for cp in all_checkpoints:
            by_pillar[cp.pillar] = by_pillar.get(cp.pillar, 0) + 1
        
        # Count by decision
        by_decision = {}
        for cp in resolved:
            if cp.decision:
                by_decision[cp.decision.value] = by_decision.get(cp.decision.value, 0) + 1
        
        return {
            "total": len(all_checkpoints),
            "pending": len(pending),
            "resolved": len(resolved),
            "by_pillar": by_pillar,
            "by_decision": by_decision,
        }
    
    def on_checkpoint_created(self, callback: Callable[[HITLCheckpoint], None]) -> None:
        """Register a callback for when checkpoints are created."""
        self._on_checkpoint_created.append(callback)
    
    def on_checkpoint_resolved(self, callback: Callable[[HITLCheckpoint], None]) -> None:
        """Register a callback for when checkpoints are resolved."""
        self._on_checkpoint_resolved.append(callback)
    
    def clear_callbacks(self) -> None:
        """Clear all registered callbacks."""
        self._on_checkpoint_created.clear()
        self._on_checkpoint_resolved.clear()


def format_checkpoint_prompt(checkpoint: HITLCheckpoint) -> str:
    """
    Format a checkpoint for display.
    
    Args:
        checkpoint: The checkpoint to format
        
    Returns:
        Formatted string for display
    """
    gate_names = {
        HITLGateType.IDEA_CLARIFICATION: "Idea Clarification",
        HITLGateType.AGENT_DRAFT_REVIEW: "Agent Draft Review",
        HITLGateType.BRIEF_APPROVAL: "Startup Brief Approval",
        HITLGateType.TASK_INTAKE: "Task Intake",
        HITLGateType.SPEC_APPROVAL: "Engineering Spec Approval",
        HITLGateType.MID_TASK_INTERRUPT: "Mid-Task Review",
        HITLGateType.REVIEWER_FLAG: "Reviewer Flag",
        HITLGateType.FINAL_PACKAGE: "Final Package Approval",
        HITLGateType.INDEXING_CONFIRM: "Indexing Confirmation",
        HITLGateType.REINDEX_APPROVAL: "Re-indexing Approval",
        HITLGateType.UNCERTAINTY_ESCALATION: "Clarification Needed",
        HITLGateType.CONTEXT_CONFIRMATION: "Context Confirmation",
    }
    
    gate_name = gate_names.get(checkpoint.gate_type, checkpoint.gate_type.value)
    
    options_str = " | ".join(
        f"[{opt.value.upper()}]" for opt in checkpoint.options
    )
    
    return f"""
╔══════════════════════════════════════════════════════════════════╗
║  🛑 HITL CHECKPOINT: {gate_name:<42} ║
╠══════════════════════════════════════════════════════════════════╣
║  Pillar: {checkpoint.pillar}  |  Agent: {checkpoint.agent.value:<10}                          ║
╠══════════════════════════════════════════════════════════════════╣

{checkpoint.prompt}

╠══════════════════════════════════════════════════════════════════╣
║  Options: {options_str:<54} ║
╚══════════════════════════════════════════════════════════════════╝
"""
