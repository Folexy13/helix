"""
Voice Module - Nova 2 Sonic Integration

Provides voice interaction capabilities for Helix using Amazon Nova 2 Sonic.
Supports bidirectional streaming, natural turn-taking, and crossmodal interaction.
"""

from src.voice.sonic_client import NovaSonicClient, VoiceSession
from src.voice.voice_session import VoiceSessionManager
from src.voice.voice_config import VoiceConfig, AgentVoice

__all__ = [
    "NovaSonicClient",
    "VoiceSession",
    "VoiceSessionManager",
    "VoiceConfig",
    "AgentVoice",
]
