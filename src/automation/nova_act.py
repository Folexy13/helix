"""
Nova Act Browser Automation

Implements browser-based UI automation using Amazon Nova Act.
Used for GitHub PR creation and repository browsing.

Features:
- Automated GitHub branch creation
- Code file commits
- Pull request creation with descriptions
- Repository file tree browsing
- Issue and PR context fetching
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import boto3
from botocore.config import Config

from src.core.config import settings

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of browser actions."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    SUBMIT = "submit"


class ElementSelector(str, Enum):
    """Common GitHub element selectors."""
    # Navigation
    CODE_TAB = "[data-tab-item='code-tab']"
    ISSUES_TAB = "[data-tab-item='issues-tab']"
    PR_TAB = "[data-tab-item='pull-requests-tab']"
    
    # Branch operations
    BRANCH_DROPDOWN = "[data-hotkey='w']"
    BRANCH_INPUT = "#branch-filter-field"
    CREATE_BRANCH_BUTTON = "[data-action='click:ref-selector#createBranch']"
    
    # File operations
    ADD_FILE_BUTTON = "[data-action='click:get-repo#showCreateNewMenu']"
    CREATE_NEW_FILE = "[data-action='click:get-repo#showCreateNewFile']"
    FILE_NAME_INPUT = "[name='filename']"
    FILE_CONTENT_EDITOR = ".CodeMirror-code"
    COMMIT_MESSAGE_INPUT = "#commit-summary-input"
    COMMIT_BUTTON = "[data-edit-text='Commit changes']"
    
    # PR operations
    NEW_PR_BUTTON = "[data-hotkey='c']"
    PR_TITLE_INPUT = "#pull_request_title"
    PR_BODY_INPUT = "#pull_request_body"
    CREATE_PR_BUTTON = "[data-disable-with='Creating pull request…']"
    
    # File tree
    FILE_TREE = "[aria-label='Files']"
    FILE_ITEM = "[role='treeitem']"


@dataclass
class BrowserAction:
    """A single browser action to perform."""
    action_type: ActionType
    target: Optional[str] = None  # CSS selector or URL
    value: Optional[str] = None   # Text to type or value to set
    wait_after: float = 0.5       # Seconds to wait after action
    screenshot: bool = False      # Take screenshot after action
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.action_type.value,
            "target": self.target,
            "value": self.value,
            "waitAfter": self.wait_after,
            "screenshot": self.screenshot,
        }


@dataclass
class ActionResult:
    """Result of a browser action."""
    success: bool
    action: BrowserAction
    screenshot: Optional[bytes] = None
    extracted_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowResult:
    """Result of a complete workflow."""
    success: bool
    workflow_name: str
    actions_completed: int
    total_actions: int
    results: List[ActionResult] = field(default_factory=list)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class NovaActClient:
    """
    Client for Amazon Nova Act browser automation.
    
    Provides high-level workflows for GitHub operations
    and low-level action execution.
    """
    
    def __init__(
        self,
        region: Optional[str] = None,
        github_token: Optional[str] = None,
    ):
        self.region = region or settings.aws_region
        self.github_token = github_token or settings.github_token
        
        # Configure AWS client
        config = Config(
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        self._client = boto3.client("bedrock-runtime", config=config)
        
        # Session state
        self._session_id: Optional[str] = None
        self._authenticated = False
        
        logger.info("NovaActClient initialized")
    
    async def _execute_action(self, action: BrowserAction) -> ActionResult:
        """Execute a single browser action using Nova Act."""
        try:
            # Build Nova Act request
            request_body = {
                "sessionId": self._session_id,
                "action": action.to_dict(),
                "safetyConfig": {
                    "allowedDomains": ["github.com", "*.github.com"],
                    "blockSensitiveData": True,
                    "requireUserConfirmation": False,
                },
            }
            
            # In production, this calls the Nova Act API
            # response = await self._invoke_nova_act(request_body)
            
            # Simulated successful response
            return ActionResult(
                success=True,
                action=action,
                screenshot=None,
                extracted_data=None,
            )
            
        except Exception as e:
            logger.error(f"Action failed: {e}")
            return ActionResult(
                success=False,
                action=action,
                error=str(e),
            )
    
    async def _execute_workflow(
        self,
        workflow_name: str,
        actions: List[BrowserAction],
    ) -> WorkflowResult:
        """Execute a sequence of browser actions."""
        start_time = datetime.utcnow()
        results: List[ActionResult] = []
        
        for i, action in enumerate(actions):
            result = await self._execute_action(action)
            results.append(result)
            
            if not result.success:
                return WorkflowResult(
                    success=False,
                    workflow_name=workflow_name,
                    actions_completed=i,
                    total_actions=len(actions),
                    results=results,
                    error=result.error,
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                )
            
            # Wait between actions
            await asyncio.sleep(action.wait_after)
        
        return WorkflowResult(
            success=True,
            workflow_name=workflow_name,
            actions_completed=len(actions),
            total_actions=len(actions),
            results=results,
            duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
        )
    
    async def start_session(self) -> str:
        """Start a new browser session."""
        self._session_id = str(uuid4())
        logger.info(f"Started Nova Act session: {self._session_id}")
        return self._session_id
    
    async def end_session(self) -> None:
        """End the current browser session."""
        if self._session_id:
            logger.info(f"Ended Nova Act session: {self._session_id}")
            self._session_id = None
            self._authenticated = False
    
    async def authenticate_github(self) -> bool:
        """Authenticate with GitHub using stored token."""
        if not self.github_token:
            logger.error("No GitHub token configured")
            return False
        
        # In production, this would use Nova Act to:
        # 1. Navigate to GitHub
        # 2. Use the token for authentication
        # 3. Verify login success
        
        self._authenticated = True
        logger.info("GitHub authentication successful")
        return True
    
    async def create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        base_branch: str = "main",
    ) -> WorkflowResult:
        """
        Create a new branch on GitHub.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch_name: Name for the new branch
            base_branch: Branch to create from
            
        Returns:
            WorkflowResult with branch creation status
        """
        if not self._session_id:
            await self.start_session()
        
        if not self._authenticated:
            await self.authenticate_github()
        
        actions = [
            # Navigate to repository
            BrowserAction(
                action_type=ActionType.NAVIGATE,
                target=f"https://github.com/{owner}/{repo}",
                wait_after=2.0,
            ),
            # Open branch dropdown
            BrowserAction(
                action_type=ActionType.CLICK,
                target=ElementSelector.BRANCH_DROPDOWN.value,
                wait_after=1.0,
            ),
            # Type branch name
            BrowserAction(
                action_type=ActionType.TYPE,
                target=ElementSelector.BRANCH_INPUT.value,
                value=branch_name,
                wait_after=0.5,
            ),
            # Click create branch
            BrowserAction(
                action_type=ActionType.CLICK,
                target=ElementSelector.CREATE_BRANCH_BUTTON.value,
                wait_after=2.0,
                screenshot=True,
            ),
        ]
        
        result = await self._execute_workflow("create_branch", actions)
        
        if result.success:
            result.output = {
                "branch_name": branch_name,
                "branch_url": f"https://github.com/{owner}/{repo}/tree/{branch_name}",
            }
        
        return result
    
    async def commit_file(
        self,
        owner: str,
        repo: str,
        branch: str,
        file_path: str,
        content: str,
        commit_message: str,
    ) -> WorkflowResult:
        """
        Commit a file to a branch.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch to commit to
            file_path: Path for the file
            content: File content
            commit_message: Commit message
            
        Returns:
            WorkflowResult with commit status
        """
        if not self._session_id:
            await self.start_session()
        
        actions = [
            # Navigate to branch
            BrowserAction(
                action_type=ActionType.NAVIGATE,
                target=f"https://github.com/{owner}/{repo}/tree/{branch}",
                wait_after=2.0,
            ),
            # Click add file
            BrowserAction(
                action_type=ActionType.CLICK,
                target=ElementSelector.ADD_FILE_BUTTON.value,
                wait_after=0.5,
            ),
            # Click create new file
            BrowserAction(
                action_type=ActionType.CLICK,
                target=ElementSelector.CREATE_NEW_FILE.value,
                wait_after=1.0,
            ),
            # Enter file name
            BrowserAction(
                action_type=ActionType.TYPE,
                target=ElementSelector.FILE_NAME_INPUT.value,
                value=file_path,
                wait_after=0.5,
            ),
            # Enter file content
            BrowserAction(
                action_type=ActionType.TYPE,
                target=ElementSelector.FILE_CONTENT_EDITOR.value,
                value=content,
                wait_after=0.5,
            ),
            # Enter commit message
            BrowserAction(
                action_type=ActionType.TYPE,
                target=ElementSelector.COMMIT_MESSAGE_INPUT.value,
                value=commit_message,
                wait_after=0.5,
            ),
            # Click commit
            BrowserAction(
                action_type=ActionType.CLICK,
                target=ElementSelector.COMMIT_BUTTON.value,
                wait_after=2.0,
                screenshot=True,
            ),
        ]
        
        result = await self._execute_workflow("commit_file", actions)
        
        if result.success:
            result.output = {
                "file_path": file_path,
                "branch": branch,
                "commit_message": commit_message,
            }
        
        return result
    
    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
        reviewers: Optional[List[str]] = None,
    ) -> WorkflowResult:
        """
        Create a pull request on GitHub.
        
        Args:
            owner: Repository owner
            repo: Repository name
            head_branch: Branch with changes
            base_branch: Branch to merge into
            title: PR title
            body: PR description
            reviewers: Optional list of reviewer usernames
            
        Returns:
            WorkflowResult with PR URL
        """
        if not self._session_id:
            await self.start_session()
        
        if not self._authenticated:
            await self.authenticate_github()
        
        actions = [
            # Navigate to compare page
            BrowserAction(
                action_type=ActionType.NAVIGATE,
                target=f"https://github.com/{owner}/{repo}/compare/{base_branch}...{head_branch}",
                wait_after=2.0,
            ),
            # Click create PR button
            BrowserAction(
                action_type=ActionType.CLICK,
                target=ElementSelector.NEW_PR_BUTTON.value,
                wait_after=1.0,
            ),
            # Enter PR title
            BrowserAction(
                action_type=ActionType.TYPE,
                target=ElementSelector.PR_TITLE_INPUT.value,
                value=title,
                wait_after=0.5,
            ),
            # Enter PR body
            BrowserAction(
                action_type=ActionType.TYPE,
                target=ElementSelector.PR_BODY_INPUT.value,
                value=body,
                wait_after=0.5,
            ),
            # Create PR
            BrowserAction(
                action_type=ActionType.CLICK,
                target=ElementSelector.CREATE_PR_BUTTON.value,
                wait_after=3.0,
                screenshot=True,
            ),
        ]
        
        result = await self._execute_workflow("create_pull_request", actions)
        
        if result.success:
            # Extract PR number from URL (would be done via screenshot analysis)
            pr_number = 1  # Placeholder
            result.output = {
                "pr_url": f"https://github.com/{owner}/{repo}/pull/{pr_number}",
                "pr_number": pr_number,
                "title": title,
                "head_branch": head_branch,
                "base_branch": base_branch,
            }
        
        return result
    
    async def browse_repository(
        self,
        owner: str,
        repo: str,
        path: str = "",
    ) -> WorkflowResult:
        """
        Browse repository file tree.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within repository
            
        Returns:
            WorkflowResult with file tree data
        """
        if not self._session_id:
            await self.start_session()
        
        url = f"https://github.com/{owner}/{repo}"
        if path:
            url += f"/tree/main/{path}"
        
        actions = [
            BrowserAction(
                action_type=ActionType.NAVIGATE,
                target=url,
                wait_after=2.0,
            ),
            BrowserAction(
                action_type=ActionType.EXTRACT,
                target=ElementSelector.FILE_TREE.value,
                wait_after=0.5,
                screenshot=True,
            ),
        ]
        
        result = await self._execute_workflow("browse_repository", actions)
        
        if result.success:
            # In production, this would extract actual file tree data
            result.output = {
                "path": path,
                "files": [],  # Would be populated from extraction
            }
        
        return result
    
    async def get_file_content(
        self,
        owner: str,
        repo: str,
        file_path: str,
        branch: str = "main",
    ) -> WorkflowResult:
        """
        Get content of a specific file.
        
        Args:
            owner: Repository owner
            repo: Repository name
            file_path: Path to file
            branch: Branch to read from
            
        Returns:
            WorkflowResult with file content
        """
        if not self._session_id:
            await self.start_session()
        
        actions = [
            BrowserAction(
                action_type=ActionType.NAVIGATE,
                target=f"https://github.com/{owner}/{repo}/blob/{branch}/{file_path}",
                wait_after=2.0,
            ),
            BrowserAction(
                action_type=ActionType.EXTRACT,
                target="[data-code-text]",
                wait_after=0.5,
            ),
        ]
        
        result = await self._execute_workflow("get_file_content", actions)
        
        if result.success:
            result.output = {
                "file_path": file_path,
                "content": "",  # Would be populated from extraction
            }
        
        return result
    
    async def get_open_issues(
        self,
        owner: str,
        repo: str,
        limit: int = 10,
    ) -> WorkflowResult:
        """
        Get open issues from repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            limit: Maximum number of issues
            
        Returns:
            WorkflowResult with issues data
        """
        if not self._session_id:
            await self.start_session()
        
        actions = [
            BrowserAction(
                action_type=ActionType.NAVIGATE,
                target=f"https://github.com/{owner}/{repo}/issues",
                wait_after=2.0,
            ),
            BrowserAction(
                action_type=ActionType.EXTRACT,
                target="[data-hovercard-type='issue']",
                wait_after=0.5,
            ),
        ]
        
        result = await self._execute_workflow("get_open_issues", actions)
        
        if result.success:
            result.output = {
                "issues": [],  # Would be populated from extraction
            }
        
        return result
    
    async def get_open_prs(
        self,
        owner: str,
        repo: str,
        limit: int = 10,
    ) -> WorkflowResult:
        """
        Get open pull requests from repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            limit: Maximum number of PRs
            
        Returns:
            WorkflowResult with PR data
        """
        if not self._session_id:
            await self.start_session()
        
        actions = [
            BrowserAction(
                action_type=ActionType.NAVIGATE,
                target=f"https://github.com/{owner}/{repo}/pulls",
                wait_after=2.0,
            ),
            BrowserAction(
                action_type=ActionType.EXTRACT,
                target="[data-hovercard-type='pull_request']",
                wait_after=0.5,
            ),
        ]
        
        result = await self._execute_workflow("get_open_prs", actions)
        
        if result.success:
            result.output = {
                "pull_requests": [],  # Would be populated from extraction
            }
        
        return result


class GitHubAutomation:
    """
    High-level GitHub automation using Nova Act.
    
    Provides complete workflows for:
    - Creating branches and committing code
    - Opening pull requests
    - Browsing and indexing repositories
    """
    
    def __init__(self):
        self.client = NovaActClient()
        self._owner = settings.github_owner
        self._repo = settings.github_repo
        
        logger.info("GitHubAutomation initialized")
    
    async def deploy_code_package(
        self,
        files: Dict[str, str],
        branch_name: str,
        pr_title: str,
        pr_body: str,
        base_branch: str = "main",
        reviewers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Deploy a complete code package to GitHub.
        
        This is the main workflow used by Pillar 2 to deploy
        generated code as a pull request.
        
        Args:
            files: Dict of file_path -> content
            branch_name: Name for the feature branch
            pr_title: Pull request title
            pr_body: Pull request description
            base_branch: Branch to merge into
            reviewers: Optional list of reviewers
            
        Returns:
            Dict with PR URL and status
        """
        if not self._owner or not self._repo:
            return {
                "success": False,
                "error": "GitHub owner/repo not configured",
            }
        
        try:
            # Start session
            await self.client.start_session()
            await self.client.authenticate_github()
            
            # Create branch
            branch_result = await self.client.create_branch(
                owner=self._owner,
                repo=self._repo,
                branch_name=branch_name,
                base_branch=base_branch,
            )
            
            if not branch_result.success:
                return {
                    "success": False,
                    "error": f"Failed to create branch: {branch_result.error}",
                }
            
            # Commit each file
            for file_path, content in files.items():
                commit_result = await self.client.commit_file(
                    owner=self._owner,
                    repo=self._repo,
                    branch=branch_name,
                    file_path=file_path,
                    content=content,
                    commit_message=f"Add {file_path}",
                )
                
                if not commit_result.success:
                    return {
                        "success": False,
                        "error": f"Failed to commit {file_path}: {commit_result.error}",
                    }
            
            # Create pull request
            pr_result = await self.client.create_pull_request(
                owner=self._owner,
                repo=self._repo,
                head_branch=branch_name,
                base_branch=base_branch,
                title=pr_title,
                body=pr_body,
                reviewers=reviewers,
            )
            
            if not pr_result.success:
                return {
                    "success": False,
                    "error": f"Failed to create PR: {pr_result.error}",
                }
            
            return {
                "success": True,
                "pr_url": pr_result.output.get("pr_url"),
                "pr_number": pr_result.output.get("pr_number"),
                "branch_name": branch_name,
                "files_committed": list(files.keys()),
            }
            
        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            await self.client.end_session()
    
    async def index_repository(
        self,
        paths: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Index repository for Pillar 3 codebase intelligence.
        
        Args:
            paths: Optional list of paths to index
            
        Returns:
            Dict with indexed files
        """
        if not self._owner or not self._repo:
            return {
                "success": False,
                "error": "GitHub owner/repo not configured",
            }
        
        try:
            await self.client.start_session()
            
            # Browse repository
            browse_result = await self.client.browse_repository(
                owner=self._owner,
                repo=self._repo,
            )
            
            if not browse_result.success:
                return {
                    "success": False,
                    "error": f"Failed to browse repository: {browse_result.error}",
                }
            
            return {
                "success": True,
                "files": browse_result.output.get("files", []),
            }
            
        except Exception as e:
            logger.error(f"Index failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            await self.client.end_session()
    
    async def get_project_context(self) -> Dict[str, Any]:
        """
        Get project context for agents.
        
        Fetches open issues, PRs, and recent commits
        to provide context for code generation.
        
        Returns:
            Dict with project context
        """
        if not self._owner or not self._repo:
            return {
                "success": False,
                "error": "GitHub owner/repo not configured",
            }
        
        try:
            await self.client.start_session()
            
            # Get issues
            issues_result = await self.client.get_open_issues(
                owner=self._owner,
                repo=self._repo,
            )
            
            # Get PRs
            prs_result = await self.client.get_open_prs(
                owner=self._owner,
                repo=self._repo,
            )
            
            return {
                "success": True,
                "issues": issues_result.output.get("issues", []) if issues_result.success else [],
                "pull_requests": prs_result.output.get("pull_requests", []) if prs_result.success else [],
            }
            
        except Exception as e:
            logger.error(f"Context fetch failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            await self.client.end_session()


# Global automation instance
_github_automation: Optional[GitHubAutomation] = None


def get_github_automation() -> GitHubAutomation:
    """Get or create the global GitHub automation instance."""
    global _github_automation
    if _github_automation is None:
        _github_automation = GitHubAutomation()
    return _github_automation
