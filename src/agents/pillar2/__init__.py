"""
Pillar 2: The Engineering Workforce

Autonomous coding agents that plan, code, test, document, and review
software tasks - producing ready-to-merge output packages.

Agents:
- PLANNER: Decomposes requests into engineering specs
- CODER: Writes code based on approved plans
- TESTER: Writes and validates tests
- DOCS: Creates documentation
- REVIEWER: Reviews for security and quality
- ORCHESTRATOR: Coordinates the full pipeline
"""

from src.agents.pillar2.planner import PlannerAgent
from src.agents.pillar2.coder import CoderAgent
from src.agents.pillar2.tester import TesterAgent
from src.agents.pillar2.docs import DocsAgent
from src.agents.pillar2.reviewer import ReviewerAgent
from src.agents.pillar2.orchestrator import OrchestratorAgent

__all__ = [
    "PlannerAgent",
    "CoderAgent",
    "TesterAgent",
    "DocsAgent",
    "ReviewerAgent",
    "OrchestratorAgent",
]
