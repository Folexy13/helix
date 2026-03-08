"""
Voice Module - Nova 2 Sonic Integration

Provides voice interaction capabilities for Helix using Amazon Nova 2 Sonic.
Supports bidirectional streaming, natural turn-taking, and crossmodal interaction.
"""

from src.voice.sonic_client import NovaSonicClient
from src.voice.voice_session import VoiceSession
from src.voice.voice_config import VoiceConfig, AgentVoice

__all__ = [
    "NovaSonicClient",
    "VoiceSession",
    "VoiceConfig",
    "AgentVoice",
]
