"""
API Module

Provides REST and WebSocket endpoints for Helix:
- Voice endpoints for real-time speech-to-speech
- GitHub OAuth for repository connection
- Pillar endpoints for each module
- HITL interaction endpoints
"""

from src.api.voice_endpoints import router as voice_router
from src.api.github_oauth import router as github_router

__all__ = [
    "voice_router",
    "github_router",
]
