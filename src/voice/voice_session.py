"""
Voice Session Manager

High-level interface for managing voice interactions across all Helix pillars.
Integrates Nova 2 Sonic with the agent system.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.core.models import AgentRole, Conversation, MessageRole, SessionState
from src.voice.sonic_client import NovaSonicClient, SpeechEvent, TranscriptEvent, VoiceSession as SonicSession
from src.voice.voice_config import AgentVoice, VoiceConfig

logger = logging.getLogger(__name__)


@dataclass
class VoiceInteraction:
    """A single voice interaction (user input + agent response)."""
    id: UUID = field(default_factory=uuid4)
    user_text: str = ""
    user_audio: Optional[bytes] = None
    agent_text: str = ""
    agent_audio: Optional[bytes] = None
    agent_role: Optional[AgentRole] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0


class VoiceSessionManager:
    """
    Manages voice sessions for Helix.
    
    Provides a high-level interface that:
    - Routes voice input to appropriate agents
    - Manages voice personas for different agents
    - Handles crossmodal switching (voice <-> text)
    - Coordinates with HITL checkpoints
    - Maintains conversation context
    """
    
    def __init__(
        self,
        sonic_client: Optional[NovaSonicClient] = None,
    ):
        """
        Initialize the voice session manager.
        
        Args:
            sonic_client: Nova Sonic client instance
        """
        self.sonic_client = sonic_client or NovaSonicClient()
        
        # Active voice sessions
        self._sessions: Dict[UUID, "HelixVoiceSession"] = {}
        
        # Agent voice mappings
        self._voice_config = VoiceConfig()
        
        logger.info("VoiceSessionManager initialized")
    
    async def create_session(
        self,
        session_state: SessionState,
        initial_agent: AgentRole = AgentRole.ROUTER,
        on_agent_speak: Optional[Callable[[AgentRole, str, bytes], None]] = None,
        on_user_speak: Optional[Callable[[str], None]] = None,
    ) -> "HelixVoiceSession":
        """
        Create a new Helix voice session.
        
        Args:
            session_state: The Helix session state
            initial_agent: Initial agent to handle conversation
            on_agent_speak: Callback when agent speaks
            on_user_speak: Callback when user speaks
            
        Returns:
            HelixVoiceSession for managing the voice interaction
        """
        # Get voice for initial agent
        voice = self._voice_config.get_voice_for_agent(initial_agent.value)
        if not voice:
            voice = VoiceConfig.ROUTER  # Default to router voice
        
        # Create underlying Sonic session
        sonic_session = await self.sonic_client.start_session(
            voice=voice,
            system_prompt=self._get_system_prompt(initial_agent),
        )
        
        # Create Helix voice session
        helix_session = HelixVoiceSession(
            manager=self,
            sonic_session=sonic_session,
            session_state=session_state,
            current_agent=initial_agent,
            on_agent_speak=on_agent_speak,
            on_user_speak=on_user_speak,
        )
        
        self._sessions[helix_session.id] = helix_session
        
        logger.info(f"Created Helix voice session: {helix_session.id}")
        
        return helix_session
    
    def _get_system_prompt(self, agent_role: AgentRole) -> str:
        """Get system prompt for an agent's voice interaction."""
        prompts = {
            AgentRole.ROUTER: "You are coordinating a startup analysis. Speak naturally and guide the conversation.",
            AgentRole.ARIA: "You are ARIA, the CTO. Speak with technical precision and confidence.",
            AgentRole.FELIX: "You are FELIX, the CFO. Speak with measured confidence about financial matters.",
            AgentRole.NOVA: "You are NOVA, the CMO. Speak with warmth and energy about marketing.",
            AgentRole.JUDGE: "You are JUDGE, the investor. Speak with skeptical but fair evaluation.",
            AgentRole.ORCHESTRATOR: "You are coordinating software development. Speak clearly and efficiently.",
            AgentRole.SAGE: "You are SAGE, the codebase expert. Speak patiently and thoughtfully.",
        }
        return prompts.get(agent_role, "You are a helpful AI assistant.")
    
    def get_session(self, session_id: UUID) -> Optional["HelixVoiceSession"]:
        """Get an active session by ID."""
        return self._sessions.get(session_id)
    
    async def close_session(self, session_id: UUID) -> None:
        """Close a voice session."""
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            await session.close()
            logger.info(f"Closed Helix voice session: {session_id}")
    
    async def close_all_sessions(self) -> None:
        """Close all active sessions."""
        for session_id in list(self._sessions.keys()):
            await self.close_session(session_id)


class HelixVoiceSession:
    """
    A Helix voice session that integrates Nova 2 Sonic with agents.
    
    Features:
    - Multi-agent voice conversations
    - Automatic voice switching between agents
    - HITL checkpoint handling via voice
    - Crossmodal interaction support
    - Conversation history tracking
    """
    
    def __init__(
        self,
        manager: VoiceSessionManager,
        sonic_session: SonicSession,
        session_state: SessionState,
        current_agent: AgentRole,
        on_agent_speak: Optional[Callable[[AgentRole, str, bytes], None]] = None,
        on_user_speak: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize a Helix voice session.
        
        Args:
            manager: Voice session manager
            sonic_session: Underlying Sonic session
            session_state: Helix session state
            current_agent: Current active agent
            on_agent_speak: Callback when agent speaks
            on_user_speak: Callback when user speaks
        """
        self.id = uuid4()
        self.manager = manager
        self.sonic_session = sonic_session
        self.session_state = session_state
        self.current_agent = current_agent
        
        # Callbacks
        self.on_agent_speak = on_agent_speak
        self.on_user_speak = on_user_speak
        
        # Interaction history
        self._interactions: List[VoiceInteraction] = []
        
        # State
        self._active = True
        self._processing = False
        self._pending_hitl = None
        
        logger.info(f"HelixVoiceSession created: {self.id}")
    
    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return self._active and self.sonic_session.is_active
    
    async def process_voice_input(self, audio_data: bytes) -> Optional[AgentResponse]:
        """
        Process voice input from the user.
        
        Args:
            audio_data: PCM audio bytes
            
        Returns:
            Agent response if processing completed
        """
        if not self.is_active:
            raise RuntimeError("Session is not active")
        
        if self._processing:
            # Queue the audio for later
            await self.sonic_session.send_audio(audio_data)
            return None
        
        self._processing = True
        
        try:
            # Send audio to Sonic
            await self.sonic_session.send_audio(audio_data)
            
            # Get transcription
            transcript = await self.manager.sonic_client.speech_to_text(audio_data)
            
            if self.on_user_speak:
                self.on_user_speak(transcript)
            
            # Process with current agent
            response = await self._process_with_agent(transcript)
            
            # Generate speech response
            if response and response.content:
                voice = VoiceConfig.get_voice_for_agent(self.current_agent.value)
                audio = await self.manager.sonic_client.text_to_speech(
                    response.content,
                    voice or VoiceConfig.ROUTER,
                )
                
                if self.on_agent_speak:
                    self.on_agent_speak(self.current_agent, response.content, audio)
                
                # Record interaction
                self._interactions.append(VoiceInteraction(
                    user_text=transcript,
                    user_audio=audio_data,
                    agent_text=response.content,
                    agent_audio=audio,
                    agent_role=self.current_agent,
                ))
            
            return response
            
        finally:
            self._processing = False
    
    async def process_text_input(self, text: str) -> Optional[AgentResponse]:
        """
        Process text input (crossmodal).
        
        Args:
            text: Text input from user
            
        Returns:
            Agent response
        """
        if not self.is_active:
            raise RuntimeError("Session is not active")
        
        if self.on_user_speak:
            self.on_user_speak(text)
        
        # Process with current agent
        response = await self._process_with_agent(text)
        
        # Generate speech response
        if response and response.content:
            voice = VoiceConfig.get_voice_for_agent(self.current_agent.value)
            audio = await self.manager.sonic_client.text_to_speech(
                response.content,
                voice or VoiceConfig.ROUTER,
            )
            
            if self.on_agent_speak:
                self.on_agent_speak(self.current_agent, response.content, audio)
            
            # Record interaction
            self._interactions.append(VoiceInteraction(
                user_text=text,
                agent_text=response.content,
                agent_audio=audio,
                agent_role=self.current_agent,
            ))
        
        return response
    
    async def _process_with_agent(self, user_input: str) -> Optional[AgentResponse]:
        """Process input with the current agent."""
        # This would be implemented to route to the appropriate agent
        # For now, return a placeholder
        
        from src.agents.base import AgentResponse
        
        return AgentResponse(
            agent=self.current_agent,
            content=f"I heard: {user_input}",
        )
    
    async def switch_agent(self, new_agent: AgentRole) -> None:
        """
        Switch to a different agent.
        
        This changes the voice persona and routing.
        
        Args:
            new_agent: New agent to switch to
        """
        old_agent = self.current_agent
        self.current_agent = new_agent
        
        # Switch voice
        voice = VoiceConfig.get_voice_for_agent(new_agent.value)
        if voice:
            self.sonic_session.switch_voice(voice)
        
        logger.info(f"Switched agent: {old_agent.value} -> {new_agent.value}")
    
    async def handle_hitl_checkpoint(
        self,
        checkpoint_prompt: str,
        options: List[str],
    ) -> str:
        """
        Handle a HITL checkpoint via voice.
        
        Speaks the checkpoint prompt and waits for user response.
        
        Args:
            checkpoint_prompt: Prompt to speak to user
            options: Available options
            
        Returns:
            User's decision
        """
        # Speak the checkpoint prompt
        voice = VoiceConfig.get_voice_for_agent(self.current_agent.value)
        audio = await self.manager.sonic_client.text_to_speech(
            checkpoint_prompt,
            voice or VoiceConfig.ROUTER,
        )
        
        if self.on_agent_speak:
            self.on_agent_speak(self.current_agent, checkpoint_prompt, audio)
        
        # Wait for user response
        # In production, this would wait for actual voice input
        self._pending_hitl = {
            "prompt": checkpoint_prompt,
            "options": options,
        }
        
        # Return placeholder - actual implementation would wait
        return options[0] if options else "approve"
    
    def get_interaction_history(self) -> List[VoiceInteraction]:
        """Get the interaction history."""
        return self._interactions.copy()
    
    def get_remaining_time(self) -> float:
        """Get remaining session time."""
        return self.sonic_session.get_remaining_time()
    
    async def renew(self) -> "HelixVoiceSession":
        """
        Renew the session before timeout.
        
        Returns:
            New session with preserved state
        """
        # Renew underlying Sonic session
        new_sonic = await self.sonic_session.renew()
        
        # Create new Helix session
        new_session = HelixVoiceSession(
            manager=self.manager,
            sonic_session=new_sonic,
            session_state=self.session_state,
            current_agent=self.current_agent,
            on_agent_speak=self.on_agent_speak,
            on_user_speak=self.on_user_speak,
        )
        
        # Transfer history
        new_session._interactions = self._interactions.copy()
        
        # Update manager
        self.manager._sessions.pop(self.id, None)
        self.manager._sessions[new_session.id] = new_session
        
        # Close old session
        self._active = False
        
        logger.info(f"Session renewed: {self.id} -> {new_session.id}")
        
        return new_session
    
    async def close(self) -> None:
        """Close the session."""
        self._active = False
        self.sonic_session.close()
        logger.info(f"HelixVoiceSession closed: {self.id}")
