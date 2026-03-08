"""
Pillar 1: The Founding Team

AI Startup Co-Founder agents that analyze business ideas and deliver
comprehensive business breakdowns.

Agents:
- ARIA (CTO): Technical feasibility and architecture
- FELIX (CFO): Financial projections and costs
- NOVA (CMO): Marketing and go-to-market strategy
- JUDGE (Investor): Investment readiness evaluation
- ROUTER: Orchestrator that coordinates all agents
"""

from src.agents.pillar1.aria import AriaAgent
from src.agents.pillar1.felix import FelixAgent
from src.agents.pillar1.nova_cmo import NovaCMOAgent
from src.agents.pillar1.judge import JudgeAgent
from src.agents.pillar1.router import RouterAgent

__all__ = [
    "AriaAgent",
    "FelixAgent",
    "NovaCMOAgent",
    "JudgeAgent",
    "RouterAgent",
]
