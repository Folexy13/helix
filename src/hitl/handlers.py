"""
HITL Handlers

Different handlers for presenting checkpoints and collecting user decisions.
Supports console, voice, and API-based interactions.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from src.core.models import HITLCheckpoint, HITLDecision
from src.hitl.checkpoint_manager import CheckpointManager, format_checkpoint_prompt

logger = logging.getLogger(__name__)


class HITLHandler(ABC):
    """
    Abstract base class for HITL handlers.
    
    Handlers are responsible for presenting checkpoints to users
    and collecting their decisions.
    """
    
    @abstractmethod
    async def present_checkpoint(self, checkpoint: HITLCheckpoint) -> HITLDecision:
        """
        Present a checkpoint to the user and get their decision.
        
        Args:
            checkpoint: The checkpoint to present
            
        Returns:
            User's decision
        """
        pass
    
    @abstractmethod
    async def get_user_input(self, prompt: str) -> str:
        """
        Get free-form input from the user.
        
        Args:
            prompt: Prompt to show the user
            
        Returns:
            User's input
        """
        pass


class ConsoleHITLHandler(HITLHandler):
    """
    Console-based HITL handler.
    
    Presents checkpoints in the terminal and collects input via stdin.
    """
    
    def __init__(self, checkpoint_manager: Optional[CheckpointManager] = None):
        """
        Initialize the console handler.
        
        Args:
            checkpoint_manager: Optional checkpoint manager to register with
        """
        self.checkpoint_manager = checkpoint_manager
        
        if checkpoint_manager:
            checkpoint_manager.on_checkpoint_created(self._on_checkpoint)
    
    def _on_checkpoint(self, checkpoint: HITLCheckpoint) -> None:
        """Handle new checkpoint creation."""
        # In async context, this would trigger the presentation
        logger.info(f"New checkpoint: {checkpoint.gate_type.value}")
    
    async def present_checkpoint(self, checkpoint: HITLCheckpoint) -> HITLDecision:
        """Present checkpoint in console and get decision."""
        # Format and print the checkpoint
        formatted = format_checkpoint_prompt(checkpoint)
        print(formatted)
        
        # Build options prompt
        options = checkpoint.options
        options_str = ", ".join(f"{i+1}. {opt.value}" for i, opt in enumerate(options))
        
        while True:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: input(f"\nYour choice ({options_str}): ").strip().lower()
                )
                
                # Parse input
                if user_input.isdigit():
                    idx = int(user_input) - 1
                    if 0 <= idx < len(options):
                        return options[idx]
                else:
                    # Try to match by name
                    for opt in options:
                        if opt.value.lower() == user_input:
                            return opt
                
                print(f"Invalid choice. Please enter one of: {options_str}")
                
            except (EOFError, KeyboardInterrupt):
                print("\nOperation cancelled.")
                return HITLDecision.REJECT
    
    async def get_user_input(self, prompt: str) -> str:
        """Get free-form input from console."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: input(f"{prompt}: ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            return ""


class VoiceHITLHandler(HITLHandler):
    """
    Voice-based HITL handler using Nova 2 Sonic.
    
    Speaks checkpoints and listens for voice responses.
    """
    
    def __init__(
        self,
        voice_session,  # HelixVoiceSession
        checkpoint_manager: Optional[CheckpointManager] = None,
    ):
        """
        Initialize the voice handler.
        
        Args:
            voice_session: Active voice session
            checkpoint_manager: Optional checkpoint manager
        """
        self.voice_session = voice_session
        self.checkpoint_manager = checkpoint_manager
        
        if checkpoint_manager:
            checkpoint_manager.on_checkpoint_created(self._on_checkpoint)
    
    def _on_checkpoint(self, checkpoint: HITLCheckpoint) -> None:
        """Handle new checkpoint creation."""
        logger.info(f"Voice checkpoint: {checkpoint.gate_type.value}")
    
    async def present_checkpoint(self, checkpoint: HITLCheckpoint) -> HITLDecision:
        """Present checkpoint via voice and get decision."""
        # Build voice prompt
        options_str = ", ".join(opt.value for opt in checkpoint.options)
        voice_prompt = f"{checkpoint.prompt}\n\nPlease say one of: {options_str}"
        
        # Use voice session to handle the checkpoint
        response = await self.voice_session.handle_hitl_checkpoint(
            voice_prompt,
            [opt.value for opt in checkpoint.options],
        )
        
        # Parse response to decision
        for opt in checkpoint.options:
            if opt.value.lower() in response.lower():
                return opt
        
        # Default to first option if unclear
        return checkpoint.options[0]
    
    async def get_user_input(self, prompt: str) -> str:
        """Get voice input from user."""
        # Speak the prompt
        response = await self.voice_session.process_text_input(prompt)
        
        # Return the transcribed response
        if response:
            return response.content
        return ""


class APIHITLHandler(HITLHandler):
    """
    API-based HITL handler for web/mobile interfaces.
    
    Queues checkpoints for external handling and waits for responses.
    This handler properly blocks execution until the user makes a decision,
    enabling true Human-in-the-Loop control between agent stages.
    """
    
    def __init__(
        self,
        checkpoint_manager: Optional[CheckpointManager] = None,
        timeout: float = 600.0,  # 10 minute timeout (increased for complex decisions)
    ):
        """
        Initialize the API handler.
        
        Args:
            checkpoint_manager: Optional checkpoint manager
            timeout: Timeout for waiting for responses
        """
        self.checkpoint_manager = checkpoint_manager
        self.timeout = timeout
        
        # Pending checkpoints waiting for external resolution
        # Key: checkpoint_id (str), Value: dict with event, decision, input
        self._pending: dict = {}
        
        if checkpoint_manager:
            checkpoint_manager.on_checkpoint_created(self._on_checkpoint)
    
    def _on_checkpoint(self, checkpoint: HITLCheckpoint) -> None:
        """Handle new checkpoint creation - register it for external resolution."""
        checkpoint_id = str(checkpoint.id)
        if checkpoint_id not in self._pending:
            logger.info(f"APIHITLHandler: Registering checkpoint {checkpoint_id} for external resolution")
            self._pending[checkpoint_id] = {
                "checkpoint": checkpoint,
                "event": asyncio.Event(),
                "decision": None,
                "input": None,
            }
    
    def register_checkpoint(self, checkpoint_id: str, checkpoint: Optional[HITLCheckpoint] = None) -> None:
        """
        Explicitly register a checkpoint for external resolution.
        
        This is useful when checkpoints are created outside the CheckpointManager
        (e.g., SmartCheckpoint objects created directly in workflows).
        
        Args:
            checkpoint_id: The checkpoint ID to register
            checkpoint: Optional checkpoint object for reference
        """
        if checkpoint_id not in self._pending:
            logger.info(f"APIHITLHandler: Explicitly registering checkpoint {checkpoint_id}")
            self._pending[checkpoint_id] = {
                "checkpoint": checkpoint,
                "event": asyncio.Event(),
                "decision": None,
                "input": None,
            }
    
    async def present_checkpoint(self, checkpoint) -> HITLDecision:
        """
        Wait for external resolution of checkpoint.
        
        This method BLOCKS until the user makes a decision via the frontend.
        The frontend sends a 'hitl_decision' event which triggers resolve_external().
        
        Args:
            checkpoint: HITLCheckpoint or SmartCheckpoint to present
            
        Returns:
            The user's decision
        """
        # Handle both HITLCheckpoint and SmartCheckpoint (which has .id attribute)
        checkpoint_id = str(checkpoint.id)
        
        # Always ensure the checkpoint is registered
        if checkpoint_id not in self._pending:
            logger.info(f"APIHITLHandler: Auto-registering checkpoint {checkpoint_id} in present_checkpoint")
            self._pending[checkpoint_id] = {
                "checkpoint": checkpoint,
                "event": asyncio.Event(),
                "decision": None,
                "input": None,
            }
        
        pending = self._pending[checkpoint_id]
        
        logger.info(f"APIHITLHandler: Waiting for user decision on checkpoint {checkpoint_id}...")
        
        try:
            # BLOCK here until the user makes a decision
            # The event is set by resolve_external() when hitl_decision comes from frontend
            await asyncio.wait_for(
                pending["event"].wait(),
                timeout=self.timeout,
            )
            
            decision = pending["decision"] or HITLDecision.APPROVE
            user_input = pending.get("input", "")
            
            # Store the last resolved input for retrieval
            self._last_resolved_input = user_input
            self._last_resolved_checkpoint_id = checkpoint_id
            
            logger.info(f"APIHITLHandler: Checkpoint {checkpoint_id} resolved with decision: {decision}")
            return decision
            
        except asyncio.TimeoutError:
            logger.warning(f"APIHITLHandler: Checkpoint {checkpoint_id} timed out after {self.timeout}s")
            self._last_resolved_input = ""
            self._last_resolved_checkpoint_id = checkpoint_id
            return HITLDecision.REJECT
        finally:
            # Clean up after resolution
            self._pending.pop(checkpoint_id, None)
    
    def get_last_user_input(self) -> str:
        """Get the user input from the last resolved checkpoint."""
        return getattr(self, '_last_resolved_input', '')
    
    async def get_user_input(self, prompt: str) -> str:
        """Get input via API (not implemented for simple prompts)."""
        return ""
    
    def resolve_external(
        self,
        checkpoint_id: str,
        decision: HITLDecision,
        user_input: Optional[str] = None,
    ) -> bool:
        """
        Resolve a checkpoint from external source (API call / WebSocket event).
        
        This is called when the frontend sends a 'hitl_decision' event.
        It sets the decision and triggers the asyncio.Event to unblock
        the waiting present_checkpoint() call.
        
        Args:
            checkpoint_id: ID of the checkpoint
            decision: User's decision
            user_input: Optional additional input
            
        Returns:
            True if resolved, False if not found
        """
        logger.info(f"APIHITLHandler: resolve_external called for {checkpoint_id} with decision {decision}")
        logger.info(f"APIHITLHandler: Current pending checkpoints: {list(self._pending.keys())}")
        
        if checkpoint_id not in self._pending:
            logger.warning(f"APIHITLHandler: Checkpoint {checkpoint_id} not found in pending!")
            return False
        
        pending = self._pending[checkpoint_id]
        pending["decision"] = decision
        pending["input"] = user_input
        pending["event"].set()  # This unblocks the waiting present_checkpoint()
        
        logger.info(f"APIHITLHandler: Successfully resolved checkpoint {checkpoint_id}")
        return True
    
    def get_pending_checkpoints(self) -> list:
        """Get list of pending checkpoints for API response."""
        return [
            {
                "id": str(p["checkpoint"].id),
                "gate_type": p["checkpoint"].gate_type.value,
                "pillar": p["checkpoint"].pillar,
                "agent": p["checkpoint"].agent.value,
                "prompt": p["checkpoint"].prompt,
                "options": [opt.value for opt in p["checkpoint"].options],
            }
            for p in self._pending.values()
        ]
