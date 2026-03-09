"""
Automation Module

Provides browser automation using Amazon Nova Act for:
- GitHub PR creation
- Repository browsing
- UI automation workflows
"""

from src.automation.nova_act import (
    NovaActClient,
    GitHubAutomation,
    ActionType,
    BrowserAction,
    ActionResult,
    WorkflowResult,
    get_github_automation,
)

__all__ = [
    "NovaActClient",
    "GitHubAutomation",
    "ActionType",
    "BrowserAction",
    "ActionResult",
    "WorkflowResult",
    "get_github_automation",
]
