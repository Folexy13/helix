"""
HITL (Human-in-the-Loop) Module

Manages checkpoints where human approval is required before proceeding.
Ensures agents are advisors and executors - the human is always in control.
"""

from src.hitl.checkpoint_manager import CheckpointManager
from src.hitl.handlers import HITLHandler, ConsoleHITLHandler, VoiceHITLHandler

__all__ = [
    "CheckpointManager",
    "HITLHandler",
    "ConsoleHITLHandler",
    "VoiceHITLHandler",
]
