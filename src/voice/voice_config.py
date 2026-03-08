"""
Voice Configuration for Nova 2 Sonic

Defines voice configurations for each Helix agent with distinct personas.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class VoiceStyle(str, Enum):
    """Voice style options."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"
    ENERGETIC = "energetic"
    FORMAL = "formal"
    THOUGHTFUL = "thoughtful"
    NEUTRAL = "neutral"


class VoicePace(str, Enum):
    """Voice pace options."""
    SLOW = "slow"
    MEASURED = "measured"
    NORMAL = "normal"
    DYNAMIC = "dynamic"
    FAST = "fast"


class VoiceTone(str, Enum):
    """Voice tone options."""
    WARM = "warm"
    CONFIDENT = "confident"
    SKEPTICAL = "skeptical"
    HELPFUL = "helpful"
    PRECISE = "precise"
    PROFESSIONAL = "professional"


class SupportedLanguage(str, Enum):
    """Languages supported by Nova 2 Sonic."""
    ENGLISH_US = "en-US"
    ENGLISH_UK = "en-GB"
    ENGLISH_IN = "en-IN"
    ENGLISH_AU = "en-AU"
    FRENCH = "fr-FR"
    ITALIAN = "it-IT"
    GERMAN = "de-DE"
    SPANISH = "es-ES"
    PORTUGUESE = "pt-BR"
    HINDI = "hi-IN"


@dataclass
class AgentVoice:
    """Voice configuration for a specific agent."""
    voice_id: str
    style: VoiceStyle
    pace: VoicePace
    tone: VoiceTone
    language: SupportedLanguage = SupportedLanguage.ENGLISH_US
    
    # Voice activity detection sensitivity
    # low = more thoughtful conversations, high = quick responses
    vad_sensitivity: str = "low"
    
    # Whether this voice can be interrupted
    interruptible: bool = True
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for API calls."""
        return {
            "voiceId": self.voice_id,
            "style": self.style.value,
            "pace": self.pace.value,
            "tone": self.tone.value,
            "language": self.language.value,
            "vadSensitivity": self.vad_sensitivity,
            "interruptible": str(self.interruptible).lower(),
        }


class VoiceConfig:
    """
    Voice configurations for all Helix agents.
    
    Each agent has a distinct voice persona configured for Nova 2 Sonic.
    """
    
    # Pillar 1 - Founding Team voices
    ARIA = AgentVoice(
        voice_id="aria",
        style=VoiceStyle.TECHNICAL,
        pace=VoicePace.MEASURED,
        tone=VoiceTone.CONFIDENT,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="low",
    )
    
    FELIX = AgentVoice(
        voice_id="felix",
        style=VoiceStyle.PROFESSIONAL,
        pace=VoicePace.MEASURED,
        tone=VoiceTone.CONFIDENT,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="low",
    )
    
    NOVA_CMO = AgentVoice(
        voice_id="nova_cmo",
        style=VoiceStyle.ENERGETIC,
        pace=VoicePace.DYNAMIC,
        tone=VoiceTone.WARM,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="medium",
    )
    
    JUDGE = AgentVoice(
        voice_id="judge",
        style=VoiceStyle.FORMAL,
        pace=VoicePace.MEASURED,
        tone=VoiceTone.SKEPTICAL,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="low",
    )
    
    ROUTER = AgentVoice(
        voice_id="router",
        style=VoiceStyle.NEUTRAL,
        pace=VoicePace.NORMAL,
        tone=VoiceTone.PROFESSIONAL,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="medium",
    )
    
    # Pillar 2 - Engineering Workforce voices
    PLANNER = AgentVoice(
        voice_id="planner",
        style=VoiceStyle.TECHNICAL,
        pace=VoicePace.MEASURED,
        tone=VoiceTone.PRECISE,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="low",
    )
    
    CODER = AgentVoice(
        voice_id="coder",
        style=VoiceStyle.TECHNICAL,
        pace=VoicePace.NORMAL,
        tone=VoiceTone.PRECISE,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="low",
    )
    
    TESTER = AgentVoice(
        voice_id="tester",
        style=VoiceStyle.TECHNICAL,
        pace=VoicePace.NORMAL,
        tone=VoiceTone.PRECISE,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="low",
    )
    
    DOCS = AgentVoice(
        voice_id="docs",
        style=VoiceStyle.PROFESSIONAL,
        pace=VoicePace.MEASURED,
        tone=VoiceTone.HELPFUL,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="low",
    )
    
    REVIEWER = AgentVoice(
        voice_id="reviewer",
        style=VoiceStyle.FORMAL,
        pace=VoicePace.MEASURED,
        tone=VoiceTone.PRECISE,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="low",
    )
    
    ORCHESTRATOR = AgentVoice(
        voice_id="orchestrator",
        style=VoiceStyle.PROFESSIONAL,
        pace=VoicePace.NORMAL,
        tone=VoiceTone.PROFESSIONAL,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="medium",
    )
    
    # Pillar 3 - Codebase Intelligence voice
    SAGE = AgentVoice(
        voice_id="sage",
        style=VoiceStyle.THOUGHTFUL,
        pace=VoicePace.MEASURED,
        tone=VoiceTone.HELPFUL,
        language=SupportedLanguage.ENGLISH_US,
        vad_sensitivity="low",
    )
    
    @classmethod
    def get_voice_for_agent(cls, agent_name: str) -> Optional[AgentVoice]:
        """Get voice configuration for an agent by name."""
        voice_map = {
            "aria": cls.ARIA,
            "felix": cls.FELIX,
            "nova": cls.NOVA_CMO,
            "nova_cmo": cls.NOVA_CMO,
            "judge": cls.JUDGE,
            "router": cls.ROUTER,
            "planner": cls.PLANNER,
            "coder": cls.CODER,
            "tester": cls.TESTER,
            "docs": cls.DOCS,
            "reviewer": cls.REVIEWER,
            "orchestrator": cls.ORCHESTRATOR,
            "sage": cls.SAGE,
        }
        return voice_map.get(agent_name.lower())
    
    @classmethod
    def get_all_voices(cls) -> Dict[str, AgentVoice]:
        """Get all voice configurations."""
        return {
            "aria": cls.ARIA,
            "felix": cls.FELIX,
            "nova_cmo": cls.NOVA_CMO,
            "judge": cls.JUDGE,
            "router": cls.ROUTER,
            "planner": cls.PLANNER,
            "coder": cls.CODER,
            "tester": cls.TESTER,
            "docs": cls.DOCS,
            "reviewer": cls.REVIEWER,
            "orchestrator": cls.ORCHESTRATOR,
            "sage": cls.SAGE,
        }
