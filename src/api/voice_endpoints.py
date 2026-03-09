"""
Voice WebSocket Endpoints

Real-time voice interaction endpoints using Nova 2 Sonic.
Provides bidirectional streaming for speech-to-speech conversations.

Features:
- WebSocket-based audio streaming
- Real-time transcription
- Agent voice responses
- Crossmodal switching (voice <-> text)
- Multi-agent voice handoffs
"""

import asyncio
import base64
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from src.voice.nova_sonic import (
    NovaSonicStream,
    NovaSonicManager,
    VoiceConfig,
    VoicePersona,
    TurnTakingSensitivity,
    AGENT_VOICES,
    TranscriptChunk,
    SpeechChunk,
    ToolCallEvent,
    AudioFrame,
    get_sonic_manager,
)
from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


# =============================================================================
# Models
# =============================================================================

class VoiceSessionRequest(BaseModel):
    """Request to create a voice session."""
    agent_name: str
    system_prompt: Optional[str] = None
    pillar: int = 1  # 1, 2, or 3
    session_id: Optional[str] = None


class VoiceSessionResponse(BaseModel):
    """Response with voice session details."""
    session_id: str
    agent_name: str
    voice_id: str
    websocket_url: str
    expires_at: str


class TextInputRequest(BaseModel):
    """Request to send text input (crossmodal)."""
    session_id: str
    text: str


class VoiceSwitchRequest(BaseModel):
    """Request to switch agent voice."""
    session_id: str
    new_agent: str


# =============================================================================
# Session Management
# =============================================================================

# Active voice sessions
_voice_sessions: Dict[str, Dict[str, Any]] = {}


def get_agent_system_prompt(agent_name: str, pillar: int) -> str:
    """Get the system prompt for an agent."""
    
    prompts = {
        # Pillar 1 - Founding Team
        "ROUTER": """You are the ROUTER agent, the team coordinator for Helix's Founding Team.
Your role is to orchestrate the analysis of startup ideas by coordinating with specialist agents.
Speak clearly and professionally. Guide the user through the idea evaluation process.
Ask clarifying questions before dispatching to specialist agents.""",
        
        "ARIA": """You are ARIA, the Chief Technology Officer agent.
Your role is to evaluate technical feasibility, recommend tech stacks, and identify technical risks.
Speak with calm precision. Be thorough but accessible in your technical explanations.
Consider scalability, security, and development complexity in your analysis.""",
        
        "FELIX": """You are FELIX, the Chief Financial Officer agent.
Your role is to estimate costs, project revenue, and provide financial analysis.
Speak with measured confidence. Use real data when available.
Consider cloud costs, API costs, team costs, and runway in your projections.""",
        
        "NOVA": """You are NOVA, the Chief Marketing Officer agent.
Your role is to craft positioning, messaging, and go-to-market strategy.
Speak with warmth and energy. Be creative but grounded in market realities.
Consider target audience, value proposition, and competitive positioning.""",
        
        "JUDGE": """You are JUDGE, the Investor Advisor agent.
Your role is to evaluate fundability and ask hard questions about the business.
Speak with firm skepticism but fairness. Challenge assumptions constructively.
Consider market size, team capability, and competitive moats.""",
        
        # Pillar 2 - Engineering Workforce
        "ORCHESTRATOR": """You are the ORCHESTRATOR agent, the engineering lead for Helix.
Your role is to coordinate the engineering workflow from planning to deployment.
Speak clearly and efficiently. Guide the user through the development process.
Manage handoffs between PLANNER, CODER, TESTER, DOCS, and REVIEWER.""",
        
        "PLANNER": """You are the PLANNER agent, the technical architect.
Your role is to decompose tasks into engineering specifications.
Speak methodically. Break down complex requirements into clear, actionable tasks.
Consider dependencies, acceptance criteria, and estimated complexity.""",
        
        "CODER": """You are the CODER agent, the senior developer.
Your role is to implement features based on approved specifications.
Speak technically but clearly. Explain your implementation decisions.
Write clean, maintainable code that follows project conventions.""",
        
        # Pillar 3 - Codebase Intelligence
        "SAGE": """You are SAGE, the codebase intelligence agent.
Your role is to answer questions about the codebase with patience and precision.
Speak thoughtfully. Ground all answers in the actual indexed codebase.
When uncertain, ask for clarification rather than guessing.""",
    }
    
    return prompts.get(agent_name.upper(), prompts["ORCHESTRATOR"])


# =============================================================================
# REST Endpoints
# =============================================================================

@router.post("/sessions", response_model=VoiceSessionResponse)
async def create_voice_session(request: VoiceSessionRequest):
    """
    Create a new voice session.
    
    Returns WebSocket URL for audio streaming.
    """
    session_id = request.session_id or str(uuid4())
    agent_name = request.agent_name.upper()
    
    # Get voice config
    voice_config = AGENT_VOICES.get(agent_name, AGENT_VOICES["ORCHESTRATOR"])
    
    # Get system prompt
    system_prompt = request.system_prompt or get_agent_system_prompt(
        agent_name, request.pillar
    )
    
    # Store session info
    _voice_sessions[session_id] = {
        "agent_name": agent_name,
        "voice_config": voice_config,
        "system_prompt": system_prompt,
        "pillar": request.pillar,
        "created_at": datetime.utcnow().isoformat(),
        "stream": None,
    }
    
    # Calculate expiration (8 minutes from now)
    expires_at = datetime.utcnow().timestamp() + settings.voice_connection_timeout
    
    return VoiceSessionResponse(
        session_id=session_id,
        agent_name=agent_name,
        voice_id=voice_config.voice_id.value,
        websocket_url=f"/voice/ws/{session_id}",
        expires_at=datetime.fromtimestamp(expires_at).isoformat(),
    )


@router.post("/sessions/{session_id}/text")
async def send_text_input(session_id: str, request: TextInputRequest):
    """
    Send text input to a voice session (crossmodal switching).
    
    Allows switching from voice to text mid-conversation.
    """
    if session_id not in _voice_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _voice_sessions[session_id]
    stream = session.get("stream")
    
    if not stream or not stream.is_active:
        raise HTTPException(status_code=400, detail="Session not active")
    
    await stream.send_text(request.text)
    
    return {"status": "sent", "text": request.text}


@router.post("/sessions/{session_id}/switch-voice")
async def switch_voice(session_id: str, request: VoiceSwitchRequest):
    """
    Switch to a different agent voice mid-session.
    
    Used for multi-agent conversations.
    """
    if session_id not in _voice_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _voice_sessions[session_id]
    stream = session.get("stream")
    
    if not stream or not stream.is_active:
        raise HTTPException(status_code=400, detail="Session not active")
    
    new_agent = request.new_agent.upper()
    new_voice = AGENT_VOICES.get(new_agent, AGENT_VOICES["ORCHESTRATOR"])
    
    stream.switch_voice(new_voice)
    session["agent_name"] = new_agent
    session["voice_config"] = new_voice
    
    return {
        "status": "switched",
        "new_agent": new_agent,
        "new_voice_id": new_voice.voice_id.value,
    }


@router.delete("/sessions/{session_id}")
async def close_voice_session(session_id: str):
    """Close a voice session."""
    if session_id not in _voice_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _voice_sessions.pop(session_id)
    stream = session.get("stream")
    
    if stream:
        await stream.stop()
    
    return {"status": "closed", "session_id": session_id}


@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a voice session."""
    if session_id not in _voice_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _voice_sessions[session_id]
    stream = session.get("stream")
    
    return {
        "session_id": session_id,
        "agent_name": session["agent_name"],
        "voice_id": session["voice_config"].voice_id.value,
        "pillar": session["pillar"],
        "created_at": session["created_at"],
        "is_active": stream.is_active if stream else False,
        "remaining_time": stream.get_remaining_time() if stream else 0,
    }


@router.get("/agents")
async def list_available_agents():
    """List available agents with their voice configurations."""
    agents = []
    
    for agent_name, voice_config in AGENT_VOICES.items():
        agents.append({
            "name": agent_name,
            "voice_id": voice_config.voice_id.value,
            "speaking_rate": voice_config.speaking_rate,
            "interruptible": voice_config.interruptible,
        })
    
    return {"agents": agents}


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@router.websocket("/ws/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time voice streaming.
    
    Protocol:
    - Client sends: {"type": "audio", "data": "<base64 audio>"}
    - Client sends: {"type": "text", "data": "<text input>"}
    - Server sends: {"type": "transcript", "text": "...", "is_final": bool}
    - Server sends: {"type": "speech", "audio": "<base64>", "text": "..."}
    - Server sends: {"type": "turn_change", "speaker": "user"|"agent"}
    - Server sends: {"type": "tool_call", "tool": "...", "args": {...}}
    """
    await websocket.accept()
    
    if session_id not in _voice_sessions:
        await websocket.send_json({
            "type": "error",
            "message": "Session not found",
        })
        await websocket.close()
        return
    
    session = _voice_sessions[session_id]
    
    # Create callbacks for stream events
    async def on_transcript(chunk: TranscriptChunk):
        try:
            await websocket.send_json({
                "type": "transcript",
                "text": chunk.text,
                "is_final": chunk.is_final,
                "confidence": chunk.confidence,
                "speaker": chunk.speaker,
            })
        except Exception as e:
            logger.error(f"Failed to send transcript: {e}")
    
    async def on_speech(chunk: SpeechChunk):
        try:
            audio_b64 = base64.b64encode(chunk.audio_data).decode() if chunk.audio_data else ""
            await websocket.send_json({
                "type": "speech",
                "audio": audio_b64,
                "text": chunk.text,
                "is_final": chunk.is_final,
                "voice_id": chunk.voice_id,
            })
        except Exception as e:
            logger.error(f"Failed to send speech: {e}")
    
    async def on_tool_call(event: ToolCallEvent):
        try:
            await websocket.send_json({
                "type": "tool_call",
                "tool_id": event.tool_id,
                "tool": event.tool_name,
                "args": event.arguments,
            })
        except Exception as e:
            logger.error(f"Failed to send tool call: {e}")
    
    async def on_turn_change(speaker: str):
        try:
            await websocket.send_json({
                "type": "turn_change",
                "speaker": speaker,
            })
        except Exception as e:
            logger.error(f"Failed to send turn change: {e}")
    
    # Create Nova Sonic stream
    stream = NovaSonicStream(
        session_id=uuid4(),
        voice_config=session["voice_config"],
        system_prompt=session["system_prompt"],
        on_transcript=lambda c: asyncio.create_task(on_transcript(c)),
        on_speech=lambda c: asyncio.create_task(on_speech(c)),
        on_tool_call=lambda e: asyncio.create_task(on_tool_call(e)),
        on_turn_change=lambda s: asyncio.create_task(on_turn_change(s)),
    )
    
    session["stream"] = stream
    
    # Start the stream
    await stream.start()
    
    # Send session started message
    await websocket.send_json({
        "type": "session_started",
        "session_id": session_id,
        "agent_name": session["agent_name"],
        "voice_id": session["voice_config"].voice_id.value,
    })
    
    try:
        # Main message loop
        while stream.is_active:
            try:
                # Receive message with timeout
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=1.0,
                )
                
                msg_type = message.get("type")
                
                if msg_type == "audio":
                    # Decode and send audio
                    audio_b64 = message.get("data", "")
                    audio_data = base64.b64decode(audio_b64)
                    
                    frame = AudioFrame(
                        data=audio_data,
                        sample_rate=16000,
                        channels=1,
                    )
                    await stream.send_audio(frame)
                
                elif msg_type == "text":
                    # Crossmodal text input
                    text = message.get("data", "")
                    await stream.send_text(text)
                
                elif msg_type == "switch_voice":
                    # Switch agent voice
                    new_agent = message.get("agent", "").upper()
                    new_voice = AGENT_VOICES.get(new_agent)
                    if new_voice:
                        stream.switch_voice(new_voice)
                        await websocket.send_json({
                            "type": "voice_switched",
                            "agent": new_agent,
                            "voice_id": new_voice.voice_id.value,
                        })
                
                elif msg_type == "tool_result":
                    # Provide tool result
                    from src.voice.nova_sonic import ToolResultEvent
                    result = ToolResultEvent(
                        tool_id=message.get("tool_id", ""),
                        result=message.get("result"),
                        success=message.get("success", True),
                    )
                    await stream.provide_tool_result(result)
                
                elif msg_type == "ping":
                    # Keep-alive ping
                    await websocket.send_json({"type": "pong"})
                
                elif msg_type == "close":
                    # Client requested close
                    break
                    
            except asyncio.TimeoutError:
                # No message received, continue loop
                continue
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received")
                continue
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })
    finally:
        # Clean up
        await stream.stop()
        
        await websocket.send_json({
            "type": "session_ended",
            "session_id": session_id,
            "conversation_history": stream.get_conversation_history(),
        })


# =============================================================================
# Multi-Agent Voice Orchestration
# =============================================================================

class VoiceOrchestrator:
    """
    Orchestrates multi-agent voice conversations.
    
    Handles agent handoffs with voice switching,
    maintaining conversation context across agents.
    """
    
    def __init__(self):
        self._active_conversations: Dict[str, Dict[str, Any]] = {}
    
    async def start_conversation(
        self,
        conversation_id: str,
        initial_agent: str,
        pillar: int,
    ) -> NovaSonicStream:
        """Start a new multi-agent conversation."""
        voice_config = AGENT_VOICES.get(
            initial_agent.upper(),
            AGENT_VOICES["ORCHESTRATOR"]
        )
        
        system_prompt = get_agent_system_prompt(initial_agent, pillar)
        
        stream = NovaSonicStream(
            session_id=uuid4(),
            voice_config=voice_config,
            system_prompt=system_prompt,
        )
        
        self._active_conversations[conversation_id] = {
            "stream": stream,
            "current_agent": initial_agent,
            "pillar": pillar,
            "agent_history": [initial_agent],
        }
        
        await stream.start()
        
        return stream
    
    async def handoff_to_agent(
        self,
        conversation_id: str,
        new_agent: str,
        context: Optional[str] = None,
    ) -> bool:
        """
        Hand off conversation to a different agent.
        
        Switches voice and updates system prompt while
        maintaining conversation history.
        """
        if conversation_id not in self._active_conversations:
            return False
        
        conv = self._active_conversations[conversation_id]
        stream = conv["stream"]
        
        # Get new voice config
        new_voice = AGENT_VOICES.get(
            new_agent.upper(),
            AGENT_VOICES["ORCHESTRATOR"]
        )
        
        # Switch voice
        stream.switch_voice(new_voice)
        
        # Update conversation state
        conv["current_agent"] = new_agent
        conv["agent_history"].append(new_agent)
        
        # If context provided, add to conversation
        if context:
            await stream.send_text(f"[Handoff context: {context}]")
        
        return True
    
    async def end_conversation(self, conversation_id: str) -> Optional[List[Dict]]:
        """End a conversation and return history."""
        if conversation_id not in self._active_conversations:
            return None
        
        conv = self._active_conversations.pop(conversation_id)
        stream = conv["stream"]
        
        history = stream.get_conversation_history()
        await stream.stop()
        
        return history
    
    def get_current_agent(self, conversation_id: str) -> Optional[str]:
        """Get the current speaking agent."""
        conv = self._active_conversations.get(conversation_id)
        return conv["current_agent"] if conv else None
    
    def get_agent_history(self, conversation_id: str) -> List[str]:
        """Get the history of agents in the conversation."""
        conv = self._active_conversations.get(conversation_id)
        return conv["agent_history"] if conv else []


# Global orchestrator
_voice_orchestrator: Optional[VoiceOrchestrator] = None


def get_voice_orchestrator() -> VoiceOrchestrator:
    """Get or create the global voice orchestrator."""
    global _voice_orchestrator
    if _voice_orchestrator is None:
        _voice_orchestrator = VoiceOrchestrator()
    return _voice_orchestrator
