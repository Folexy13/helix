"""
GitHub OAuth Integration

Provides OAuth flow for connecting user repositories to Helix.
This is the first point of contact for users who want to:
- Connect their GitHub repositories
- Grant Helix access to create branches and PRs
- Select repositories for codebase intelligence

Features:
- OAuth 2.0 flow with GitHub
- Token exchange and storage (Redis in production, in-memory for dev)
- Repository listing
- User profile access
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from src.core.config import settings
from src.core.redis_storage import get_storage, HelixStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


# =============================================================================
# Configuration
# =============================================================================

GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"

# OAuth scopes needed for Helix
GITHUB_SCOPES = [
    "repo",           # Full control of private repositories
    "read:user",      # Read user profile
    "user:email",     # Read user email
]


# =============================================================================
# Models
# =============================================================================

class GitHubUser(BaseModel):
    """GitHub user profile."""
    id: int
    login: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: str
    html_url: str


class GitHubRepository(BaseModel):
    """GitHub repository info."""
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool
    html_url: str
    clone_url: str
    default_branch: str
    language: Optional[str] = None
    stargazers_count: int = 0
    updated_at: str


class OAuthState(BaseModel):
    """OAuth state for CSRF protection."""
    state: str
    created_at: str  # ISO format string for JSON serialization
    redirect_uri: Optional[str] = None


class TokenInfo(BaseModel):
    """OAuth token information."""
    access_token: str
    token_type: str
    scope: str
    expires_at: Optional[str] = None  # ISO format string


class WorkspaceConfig(BaseModel):
    """Workspace configuration."""
    type: str  # "github" or "local"
    github_repo: Optional[str] = None
    github_owner: Optional[str] = None
    local_path: Optional[str] = None
    name: str
    created_at: str = ""  # ISO format string

    def __init__(self, **data):
        if "created_at" not in data or not data["created_at"]:
            data["created_at"] = datetime.utcnow().isoformat()
        super().__init__(**data)


# =============================================================================
# Storage Helper
# =============================================================================

async def _get_storage() -> HelixStorage:
    """Get the storage instance."""
    return await get_storage()


# =============================================================================
# OAuth Endpoints
# =============================================================================

@router.get("/auth/login")
async def github_login(
    redirect_uri: Optional[str] = Query(None, description="Where to redirect after auth"),
):
    """
    Initiate GitHub OAuth flow.
    
    Redirects user to GitHub for authorization.
    """
    storage = await _get_storage()
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state in Redis/storage
    state_data = {
        "state": state,
        "created_at": datetime.utcnow().isoformat(),
        "redirect_uri": redirect_uri,
    }
    await storage.set_oauth_state(state, state_data)
    
    # Build authorization URL
    params = {
        "client_id": settings.github_client_id if hasattr(settings, 'github_client_id') else "",
        "redirect_uri": f"{settings.app_url if hasattr(settings, 'app_url') else 'http://localhost:8000'}/api/github/auth/callback",
        "scope": " ".join(GITHUB_SCOPES),
        "state": state,
    }
    
    auth_url = f"{GITHUB_OAUTH_URL}?{urlencode(params)}"
    
    return RedirectResponse(url=auth_url)


@router.get("/auth/callback")
async def github_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: str = Query(..., description="State for CSRF verification"),
):
    """
    Handle GitHub OAuth callback.
    
    Exchanges authorization code for access token.
    """
    storage = await _get_storage()
    
    # Verify state (get_oauth_state automatically deletes it - one-time use)
    stored_state = await storage.get_oauth_state(state)
    if not stored_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Check state expiration (10 minutes)
    created_at = datetime.fromisoformat(stored_state["created_at"])
    if datetime.utcnow() - created_at > timedelta(minutes=10):
        raise HTTPException(status_code=400, detail="State expired")
    
    # Exchange code for token
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id if hasattr(settings, 'github_client_id') else "",
                    "client_secret": settings.github_client_secret if hasattr(settings, 'github_client_secret') else "",
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code")
            
            token_data = response.json()
            
            if "error" in token_data:
                raise HTTPException(
                    status_code=400,
                    detail=token_data.get("error_description", token_data["error"])
                )
    except httpx.RequestError as e:
        logger.error(f"GitHub token exchange failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to GitHub")
    
    # Get user info
    user = await _get_github_user(token_data["access_token"])
    
    # Store token in Redis/storage
    token_info = {
        "access_token": token_data["access_token"],
        "token_type": token_data.get("token_type", "bearer"),
        "scope": token_data.get("scope", ""),
    }
    await storage.set_user_token(str(user.id), token_info)
    
    # Redirect to frontend with user info
    redirect_uri = stored_state.get("redirect_uri") or "http://localhost:3000/onboarding"
    
    # In production, use secure session/JWT instead of query params
    return RedirectResponse(
        url=f"{redirect_uri}?github_user={user.login}&github_id={user.id}"
    )


@router.get("/auth/status")
async def auth_status(user_id: str = Query(...)):
    """Check if user is authenticated with GitHub."""
    storage = await _get_storage()
    token_data = await storage.get_user_token(user_id)
    
    if not token_data:
        return {"authenticated": False}
    
    # Verify token is still valid
    try:
        user = await _get_github_user(token_data["access_token"])
        return {
            "authenticated": True,
            "user": user.dict(),
        }
    except Exception:
        return {"authenticated": False}


@router.post("/auth/logout")
async def github_logout(user_id: str = Query(...)):
    """Revoke GitHub access."""
    storage = await _get_storage()
    await storage.delete_user_token(user_id)
    return {"status": "logged_out"}


# =============================================================================
# Repository Endpoints
# =============================================================================

@router.get("/repos", response_model=List[GitHubRepository])
async def list_repositories(
    user_id: str = Query(...),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
):
    """
    List user's GitHub repositories.
    
    Returns repositories the user has access to.
    """
    storage = await _get_storage()
    token_data = await storage.get_user_token(user_id)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/user/repos",
                params={
                    "page": page,
                    "per_page": per_page,
                    "sort": "updated",
                    "direction": "desc",
                },
                headers={
                    "Authorization": f"Bearer {token_data['access_token']}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch repos")
            
            repos = response.json()
            
            return [
                GitHubRepository(
                    id=repo["id"],
                    name=repo["name"],
                    full_name=repo["full_name"],
                    description=repo.get("description"),
                    private=repo["private"],
                    html_url=repo["html_url"],
                    clone_url=repo["clone_url"],
                    default_branch=repo.get("default_branch", "main"),
                    language=repo.get("language"),
                    stargazers_count=repo.get("stargazers_count", 0),
                    updated_at=repo["updated_at"],
                )
                for repo in repos
            ]
            
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch repos: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to GitHub")


@router.get("/repos/{owner}/{repo}")
async def get_repository(
    owner: str,
    repo: str,
    user_id: str = Query(...),
):
    """Get details of a specific repository."""
    storage = await _get_storage()
    token_data = await storage.get_user_token(user_id)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}",
                headers={
                    "Authorization": f"Bearer {token_data['access_token']}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Repository not found")
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch repo")
            
            repo_data = response.json()
            
            return GitHubRepository(
                id=repo_data["id"],
                name=repo_data["name"],
                full_name=repo_data["full_name"],
                description=repo_data.get("description"),
                private=repo_data["private"],
                html_url=repo_data["html_url"],
                clone_url=repo_data["clone_url"],
                default_branch=repo_data.get("default_branch", "main"),
                language=repo_data.get("language"),
                stargazers_count=repo_data.get("stargazers_count", 0),
                updated_at=repo_data["updated_at"],
            )
            
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch repo: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to GitHub")


@router.get("/repos/{owner}/{repo}/tree")
async def get_repository_tree(
    owner: str,
    repo: str,
    user_id: str = Query(...),
    branch: str = Query("main"),
):
    """Get file tree of a repository."""
    storage = await _get_storage()
    token_data = await storage.get_user_token(user_id)
    if not token_data:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": "1"},
                headers={
                    "Authorization": f"Bearer {token_data['access_token']}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch tree")
            
            tree_data = response.json()
            
            return {
                "sha": tree_data["sha"],
                "tree": [
                    {
                        "path": item["path"],
                        "type": item["type"],
                        "size": item.get("size", 0),
                    }
                    for item in tree_data.get("tree", [])
                ],
            }
            
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch tree: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to GitHub")


# =============================================================================
# Workspace Management
# =============================================================================

@router.post("/workspaces")
async def create_workspace(
    user_id: str = Query(...),
    workspace: WorkspaceConfig = ...,
):
    """
    Create a new workspace configuration.
    
    Workspace can be either a GitHub repository or a local folder.
    """
    storage = await _get_storage()
    
    workspace_dict = workspace.dict()
    workspace_dict["created_at"] = datetime.utcnow().isoformat()
    
    await storage.add_user_workspace(user_id, workspace_dict)
    
    return {"status": "created", "workspace": workspace_dict}


@router.get("/workspaces")
async def list_workspaces(user_id: str = Query(...)):
    """List user's workspaces."""
    storage = await _get_storage()
    workspaces = await storage.get_user_workspaces(user_id)
    return {"workspaces": workspaces}


@router.delete("/workspaces/{workspace_name}")
async def delete_workspace(
    workspace_name: str,
    user_id: str = Query(...),
):
    """Delete a workspace."""
    storage = await _get_storage()
    workspaces = await storage.get_user_workspaces(user_id)
    
    if not workspaces:
        raise HTTPException(status_code=404, detail="No workspaces found")
    
    # Filter out the workspace to delete
    updated_workspaces = [w for w in workspaces if w.get("name") != workspace_name]
    
    await storage.set_user_workspaces(user_id, updated_workspaces)
    
    return {"status": "deleted"}


# =============================================================================
# Local Folder Management
# =============================================================================

@router.post("/local/create")
async def create_local_folder(
    path: str = Query(..., description="Path where to create the folder"),
    name: str = Query(..., description="Name of the folder"),
):
    """
    Create a local folder for a new project.
    
    This is used when users don't have an existing repository.
    """
    import os
    
    full_path = os.path.join(path, name)
    
    try:
        os.makedirs(full_path, exist_ok=True)
        
        # Create basic project structure
        os.makedirs(os.path.join(full_path, "src"), exist_ok=True)
        os.makedirs(os.path.join(full_path, "tests"), exist_ok=True)
        os.makedirs(os.path.join(full_path, "docs"), exist_ok=True)
        
        # Create README
        readme_path = os.path.join(full_path, "README.md")
        with open(readme_path, "w") as f:
            f.write(f"# {name}\n\nCreated with Helix.\n")
        
        # Create .gitignore
        gitignore_path = os.path.join(full_path, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write("__pycache__/\n*.pyc\n.env\nnode_modules/\n.next/\n")
        
        return {
            "status": "created",
            "path": full_path,
            "structure": ["src/", "tests/", "docs/", "README.md", ".gitignore"],
        }
        
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        logger.error(f"Failed to create folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/local/browse")
async def browse_local_folders(
    path: str = Query("~", description="Path to browse"),
):
    """
    Browse local folders for workspace selection.
    
    Returns list of folders in the given path.
    """
    import os
    
    # Expand home directory
    path = os.path.expanduser(path)
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")
    
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    try:
        items = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path) and not item.startswith("."):
                items.append({
                    "name": item,
                    "path": item_path,
                    "is_git": os.path.exists(os.path.join(item_path, ".git")),
                })
        
        return {
            "current_path": path,
            "parent_path": os.path.dirname(path),
            "folders": sorted(items, key=lambda x: x["name"]),
        }
        
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")


# =============================================================================
# Helper Functions
# =============================================================================

async def _get_github_user(access_token: str) -> GitHubUser:
    """Get GitHub user profile."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_data = response.json()
        
        return GitHubUser(
            id=user_data["id"],
            login=user_data["login"],
            name=user_data.get("name"),
            email=user_data.get("email"),
            avatar_url=user_data["avatar_url"],
            html_url=user_data["html_url"],
        )


async def get_user_token(user_id: str) -> Optional[str]:
    """Get user's GitHub access token."""
    storage = await _get_storage()
    token_data = await storage.get_user_token(user_id)
    return token_data["access_token"] if token_data else None
