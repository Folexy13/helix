"""
Nova 2 Sonic Client

Handles bidirectional streaming voice interactions with Amazon Nova 2 Sonic.
Supports real-time speech-to-speech with natural turn-taking.
"""

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from uuid import UUID, uuid4

import boto3
from botocore.config import Config

from src.core.config import settings
from src.voice.voice_config import AgentVoice, VoiceConfig

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """A chunk of audio data."""
    data: bytes
    timestamp: datetime = field(default_factory=datetime.utcnow)
    is_final: bool = False


@dataclass
class TranscriptEvent:
    """A transcription event from Nova 2 Sonic."""
    text: str
    is_final: bool
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SpeechEvent:
    """A speech synthesis event from Nova 2 Sonic."""
    audio_data: bytes
    text: str
    is_final: bool
    agent_voice: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class NovaSonicClient:
    """
    Client for Amazon Nova 2 Sonic speech-to-speech model.
    
    Features:
    - Bidirectional full-duplex streaming
    - Natural turn-taking with configurable VAD
    - Crossmodal interaction (voice + text)
    - Asynchronous tool use during conversation
    - Multiple voice personas for different agents
    """
    
    def __init__(
        self,
        region: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        """
        Initialize the Nova 2 Sonic client.
        
        Args:
            region: AWS region
            model_id: Nova 2 Sonic model ID
        """
        self.region = region or settings.aws_region
        self.model_id = model_id or settings.nova_sonic_model_id
        
        # Configure boto3 client
        config = Config(
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        
        self._client = boto3.client("bedrock-runtime", config=config)
        
        # Active sessions
        self._sessions: Dict[UUID, "VoiceSession"] = {}
        
        # Audio settings
        self.sample_rate = settings.voice_sample_rate
        self.channels = settings.voice_channels
        
        logger.info(f"NovaSonicClient initialized for region: {self.region}")
    
    async def start_session(
        self,
        voice: AgentVoice,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        on_transcript: Optional[Callable[[TranscriptEvent], None]] = None,
        on_speech: Optional[Callable[[SpeechEvent], None]] = None,
    ) -> "VoiceSession":
        """
        Start a new voice session.
        
        Args:
            voice: Voice configuration for the agent
            system_prompt: System prompt for the conversation
            tools: Tools available during the conversation
            on_transcript: Callback for transcription events
            on_speech: Callback for speech synthesis events
            
        Returns:
            VoiceSession object for managing the session
        """
        session = VoiceSession(
            client=self,
            voice=voice,
            system_prompt=system_prompt,
            tools=tools,
            on_transcript=on_transcript,
            on_speech=on_speech,
        )
        
        self._sessions[session.id] = session
        
        logger.info(f"Started voice session: {session.id}")
        
        return session
    
    async def invoke_streaming(
        self,
        audio_stream: AsyncIterator[bytes],
        voice: AgentVoice,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[SpeechEvent]:
        """
        Invoke Nova 2 Sonic with streaming audio.
        
        This is the core streaming interface for speech-to-speech.
        
        Args:
            audio_stream: Async iterator of audio chunks
            voice: Voice configuration
            system_prompt: System prompt
            conversation_history: Previous conversation turns
            
        Yields:
            SpeechEvent objects with synthesized audio
        """
        # Build the request
        request_body = {
            "modelId": self.model_id,
            "voiceConfig": voice.to_dict(),
            "audioConfig": {
                "sampleRate": self.sample_rate,
                "channels": self.channels,
                "encoding": "pcm",
            },
        }
        
        if system_prompt:
            request_body["systemPrompt"] = system_prompt
        
        if conversation_history:
            request_body["conversationHistory"] = conversation_history
        
        try:
            # In production, this would use the actual streaming API
            # For now, we simulate the streaming behavior
            
            # Collect audio input
            audio_chunks = []
            async for chunk in audio_stream:
                audio_chunks.append(chunk)
            
            # Combine audio
            full_audio = b"".join(audio_chunks)
            
            # Simulate transcription and response
            # In production, this uses the actual Nova 2 Sonic API
            
            yield SpeechEvent(
                audio_data=b"",  # Would be actual audio
                text="I understand. Let me help you with that.",
                is_final=True,
                agent_voice=voice.voice_id,
            )
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise
    
    async def text_to_speech(
        self,
        text: str,
        voice: AgentVoice,
    ) -> bytes:
        """
        Convert text to speech using Nova 2 Sonic.
        
        Args:
            text: Text to synthesize
            voice: Voice configuration
            
        Returns:
            Audio bytes
        """
        try:
            # Build request
            request_body = {
                "text": text,
                "voiceConfig": voice.to_dict(),
                "audioConfig": {
                    "sampleRate": self.sample_rate,
                    "channels": self.channels,
                    "encoding": "pcm",
                },
            }
            
            # In production, this calls the actual API
            # response = self._client.invoke_model(...)
            
            # Simulated response
            return b""  # Would be actual audio bytes
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise
    
    async def speech_to_text(
        self,
        audio_data: bytes,
        language: str = "en-US",
    ) -> str:
        """
        Convert speech to text using Nova 2 Sonic.
        
        Args:
            audio_data: Audio bytes
            language: Language code
            
        Returns:
            Transcribed text
        """
        try:
            # Build request
            request_body = {
                "audio": base64.b64encode(audio_data).decode(),
                "language": language,
                "audioConfig": {
                    "sampleRate": self.sample_rate,
                    "channels": self.channels,
                    "encoding": "pcm",
                },
            }
            
            # In production, this calls the actual API
            # response = self._client.invoke_model(...)
            
            # Simulated response
            return "Transcribed text would appear here"
            
        except Exception as e:
            logger.error(f"STT error: {e}")
            raise
    
    def get_session(self, session_id: UUID) -> Optional["VoiceSession"]:
        """Get an active session by ID."""
        return self._sessions.get(session_id)
    
    def close_session(self, session_id: UUID) -> None:
        """Close and remove a session."""
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            session.close()
            logger.info(f"Closed voice session: {session_id}")


class VoiceSession:
    """
    A voice conversation session with Nova 2 Sonic.
    
    Manages the bidirectional streaming connection and handles:
    - Audio input/output
    - Turn-taking
    - Interruptions
    - Tool calls during conversation
    - Crossmodal switching (voice <-> text)
    """
    
    def __init__(
        self,
        client: NovaSonicClient,
        voice: AgentVoice,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        on_transcript: Optional[Callable[[TranscriptEvent], None]] = None,
        on_speech: Optional[Callable[[SpeechEvent], None]] = None,
    ):
        """
        Initialize a voice session.
        
        Args:
            client: Nova Sonic client
            voice: Voice configuration
            system_prompt: System prompt
            tools: Available tools
            on_transcript: Transcript callback
            on_speech: Speech callback
        """
        self.id = uuid4()
        self.client = client
        self.voice = voice
        self.system_prompt = system_prompt
        self.tools = tools or []
        
        # Callbacks
        self.on_transcript = on_transcript
        self.on_speech = on_speech
        
        # Session state
        self._active = True
        self._conversation_history: List[Dict[str, str]] = []
        self._pending_tool_calls: List[Dict[str, Any]] = []
        
        # Audio buffers
        self._input_buffer: List[bytes] = []
        self._output_buffer: List[bytes] = []
        
        # Turn-taking state
        self._user_speaking = False
        self._agent_speaking = False
        self._interrupted = False
        
        # Connection timeout (8 minutes as per Nova 2 Sonic spec)
        self._timeout = settings.voice_connection_timeout
        self._started_at = datetime.utcnow()
        
        logger.info(f"VoiceSession created: {self.id}")
    
    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        if not self._active:
            return False
        
        # Check timeout
        elapsed = (datetime.utcnow() - self._started_at).total_seconds()
        if elapsed > self._timeout:
            self._active = False
            return False
        
        return True
    
    async def send_audio(self, audio_data: bytes) -> None:
        """
        Send audio data to the session.
        
        Args:
            audio_data: PCM audio bytes
        """
        if not self.is_active:
            raise RuntimeError("Session is not active")
        
        self._input_buffer.append(audio_data)
        self._user_speaking = True
        
        # If agent is speaking and user starts, handle interruption
        if self._agent_speaking and self.voice.interruptible:
            self._interrupted = True
            self._agent_speaking = False
            logger.debug("User interrupted agent")
    
    async def send_text(self, text: str) -> None:
        """
        Send text input to the session (crossmodal).
        
        This allows switching from voice to text mid-conversation.
        
        Args:
            text: Text input
        """
        if not self.is_active:
            raise RuntimeError("Session is not active")
        
        # Add to conversation history
        self._conversation_history.append({
            "role": "user",
            "content": text,
        })
        
        # Process and generate response
        await self._process_input(text)
    
    async def _process_input(self, text: str) -> None:
        """Process user input and generate response."""
        # This would invoke the model and generate a response
        # For now, we simulate the behavior
        
        response_text = f"I heard: {text}"
        
        # Add to history
        self._conversation_history.append({
            "role": "assistant",
            "content": response_text,
        })
        
        # Generate speech
        if self.on_speech:
            event = SpeechEvent(
                audio_data=b"",
                text=response_text,
                is_final=True,
                agent_voice=self.voice.voice_id,
            )
            self.on_speech(event)
    
    async def receive_audio(self) -> AsyncIterator[bytes]:
        """
        Receive audio output from the session.
        
        Yields:
            Audio chunks as they become available
        """
        while self.is_active:
            if self._output_buffer:
                yield self._output_buffer.pop(0)
            else:
                await asyncio.sleep(0.01)
    
    def switch_voice(self, new_voice: AgentVoice) -> None:
        """
        Switch to a different agent voice.
        
        This allows different agents to speak in the same session.
        
        Args:
            new_voice: New voice configuration
        """
        self.voice = new_voice
        logger.debug(f"Switched voice to: {new_voice.voice_id}")
    
    def add_tool_result(self, tool_id: str, result: Any) -> None:
        """
        Add a tool result for asynchronous tool use.
        
        Nova 2 Sonic supports async tool use - the conversation
        continues while tools process in the background.
        
        Args:
            tool_id: Tool call ID
            result: Tool result
        """
        # Find and update the pending tool call
        for tool_call in self._pending_tool_calls:
            if tool_call.get("id") == tool_id:
                tool_call["result"] = result
                tool_call["completed"] = True
                break
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the conversation history."""
        return self._conversation_history.copy()
    
    def get_remaining_time(self) -> float:
        """Get remaining session time in seconds."""
        elapsed = (datetime.utcnow() - self._started_at).total_seconds()
        return max(0, self._timeout - elapsed)
    
    def close(self) -> None:
        """Close the session."""
        self._active = False
        self._input_buffer.clear()
        self._output_buffer.clear()
        logger.info(f"VoiceSession closed: {self.id}")
    
    async def renew(self) -> "VoiceSession":
        """
        Renew the session before timeout.
        
        Creates a new session with the same configuration
        and conversation history.
        
        Returns:
            New VoiceSession
        """
        # Create new session
        new_session = await self.client.start_session(
            voice=self.voice,
            system_prompt=self.system_prompt,
            tools=self.tools,
            on_transcript=self.on_transcript,
            on_speech=self.on_speech,
        )
        
        # Transfer conversation history
        new_session._conversation_history = self._conversation_history.copy()
        
        # Close old session
        self.close()
        
        logger.info(f"Session renewed: {self.id} -> {new_session.id}")
        
        return new_session
