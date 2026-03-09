"""
Redis Storage Module for Helix

Provides a unified interface for Redis storage that works with:
- Local Redis (development) - localhost:6379
- Live Redis (production) - configurable URL

Features:
- Automatic JSON serialization/deserialization
- TTL support for session data
- Fallback to in-memory storage if Redis unavailable
- Environment-based configuration
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TypeVar, Generic
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        """Set a value with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""
        pass


class InMemoryStorage(StorageBackend):
    """
    In-memory storage backend for development/testing.
    
    Note: Data is lost on restart. Use Redis for persistence.
    """
    
    def __init__(self):
        self._data: Dict[str, str] = {}
        self._expiry: Dict[str, datetime] = {}
        logger.info("Using in-memory storage backend")
    
    async def get(self, key: str) -> Optional[str]:
        # Check expiry
        if key in self._expiry:
            if datetime.utcnow() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return None
        return self._data.get(key)
    
    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        self._data[key] = value
        if ttl_seconds:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        elif key in self._expiry:
            del self._expiry[key]
        return True
    
    async def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            if key in self._expiry:
                del self._expiry[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        # Check expiry
        if key in self._expiry:
            if datetime.utcnow() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return False
        return key in self._data
    
    async def keys(self, pattern: str) -> List[str]:
        import fnmatch
        # Clean up expired keys first
        now = datetime.utcnow()
        expired = [k for k, exp in self._expiry.items() if now > exp]
        for k in expired:
            if k in self._data:
                del self._data[k]
            del self._expiry[k]
        
        # Convert Redis pattern to fnmatch pattern
        fnmatch_pattern = pattern.replace('*', '*')
        return [k for k in self._data.keys() if fnmatch.fnmatch(k, fnmatch_pattern)]
    
    async def close(self) -> None:
        self._data.clear()
        self._expiry.clear()


class RedisStorage(StorageBackend):
    """
    Redis storage backend for production use.
    
    Supports both local Redis and cloud Redis (e.g., AWS ElastiCache, Redis Cloud).
    """
    
    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._client = None
        logger.info(f"Initializing Redis storage with URL: {self._mask_url(redis_url)}")
    
    def _mask_url(self, url: str) -> str:
        """Mask password in URL for logging."""
        if '@' in url:
            parts = url.split('@')
            return f"redis://***@{parts[-1]}"
        return url
    
    async def _get_client(self):
        """Lazy initialization of Redis client."""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._client.ping()
                logger.info("Redis connection established successfully")
            except ImportError:
                logger.error("redis package not installed. Run: pip install redis")
                raise
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        return self._client
    
    async def get(self, key: str) -> Optional[str]:
        client = await self._get_client()
        return await client.get(key)
    
    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        client = await self._get_client()
        if ttl_seconds:
            await client.setex(key, ttl_seconds, value)
        else:
            await client.set(key, value)
        return True
    
    async def delete(self, key: str) -> bool:
        client = await self._get_client()
        result = await client.delete(key)
        return result > 0
    
    async def exists(self, key: str) -> bool:
        client = await self._get_client()
        return await client.exists(key) > 0
    
    async def keys(self, pattern: str) -> List[str]:
        client = await self._get_client()
        return await client.keys(pattern)
    
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None


class HelixStorage:
    """
    High-level storage interface for Helix application.
    
    Provides typed methods for storing and retrieving application data
    with automatic JSON serialization.
    
    Usage:
        storage = await get_storage()
        
        # Store OAuth state
        await storage.set_oauth_state("state123", {"redirect_uri": "/dashboard"})
        
        # Get OAuth state
        state = await storage.get_oauth_state("state123")
        
        # Store user token
        await storage.set_user_token("user123", {"access_token": "...", "scope": "..."})
    """
    
    # Key prefixes for different data types
    PREFIX_OAUTH_STATE = "oauth:state:"
    PREFIX_USER_TOKEN = "oauth:token:"
    PREFIX_USER_WORKSPACE = "workspace:user:"
    PREFIX_SESSION = "session:"
    PREFIX_CONVERSATION = "conversation:"
    
    # Default TTLs (in seconds)
    TTL_OAUTH_STATE = 600  # 10 minutes
    TTL_SESSION = 1800  # 30 minutes
    TTL_CONVERSATION = 86400  # 24 hours
    
    def __init__(self, backend: StorageBackend):
        self._backend = backend
    
    # =========================================================================
    # OAuth State Management
    # =========================================================================
    
    async def set_oauth_state(
        self, 
        state: str, 
        data: Dict[str, Any],
        ttl_seconds: int = TTL_OAUTH_STATE
    ) -> bool:
        """Store OAuth state for CSRF protection."""
        key = f"{self.PREFIX_OAUTH_STATE}{state}"
        return await self._backend.set(key, json.dumps(data), ttl_seconds)
    
    async def get_oauth_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Get and delete OAuth state (one-time use)."""
        key = f"{self.PREFIX_OAUTH_STATE}{state}"
        value = await self._backend.get(key)
        if value:
            await self._backend.delete(key)  # One-time use
            return json.loads(value)
        return None
    
    # =========================================================================
    # User Token Management
    # =========================================================================
    
    async def set_user_token(
        self, 
        user_id: str, 
        token_data: Dict[str, Any]
    ) -> bool:
        """Store user's OAuth token (no TTL - persists until logout)."""
        key = f"{self.PREFIX_USER_TOKEN}{user_id}"
        return await self._backend.set(key, json.dumps(token_data))
    
    async def get_user_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's OAuth token."""
        key = f"{self.PREFIX_USER_TOKEN}{user_id}"
        value = await self._backend.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def delete_user_token(self, user_id: str) -> bool:
        """Delete user's OAuth token (logout)."""
        key = f"{self.PREFIX_USER_TOKEN}{user_id}"
        return await self._backend.delete(key)
    
    async def get_all_user_ids(self) -> List[str]:
        """Get all user IDs with stored tokens."""
        keys = await self._backend.keys(f"{self.PREFIX_USER_TOKEN}*")
        return [k.replace(self.PREFIX_USER_TOKEN, "") for k in keys]
    
    # =========================================================================
    # Workspace Management
    # =========================================================================
    
    async def set_user_workspaces(
        self, 
        user_id: str, 
        workspaces: List[Dict[str, Any]]
    ) -> bool:
        """Store user's workspace configurations."""
        key = f"{self.PREFIX_USER_WORKSPACE}{user_id}"
        return await self._backend.set(key, json.dumps(workspaces))
    
    async def get_user_workspaces(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's workspace configurations."""
        key = f"{self.PREFIX_USER_WORKSPACE}{user_id}"
        value = await self._backend.get(key)
        if value:
            return json.loads(value)
        return []
    
    async def add_user_workspace(
        self, 
        user_id: str, 
        workspace: Dict[str, Any]
    ) -> bool:
        """Add a workspace to user's list."""
        workspaces = await self.get_user_workspaces(user_id)
        workspaces.append(workspace)
        return await self.set_user_workspaces(user_id, workspaces)
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    async def set_session(
        self, 
        session_id: str, 
        data: Dict[str, Any],
        ttl_seconds: int = TTL_SESSION
    ) -> bool:
        """Store session data."""
        key = f"{self.PREFIX_SESSION}{session_id}"
        return await self._backend.set(key, json.dumps(data), ttl_seconds)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        key = f"{self.PREFIX_SESSION}{session_id}"
        value = await self._backend.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        key = f"{self.PREFIX_SESSION}{session_id}"
        return await self._backend.delete(key)
    
    # =========================================================================
    # Conversation History (for cross-pillar persistence)
    # =========================================================================
    
    async def set_conversation(
        self, 
        session_id: str, 
        messages: List[Dict[str, Any]],
        ttl_seconds: int = TTL_CONVERSATION
    ) -> bool:
        """Store conversation history."""
        key = f"{self.PREFIX_CONVERSATION}{session_id}"
        return await self._backend.set(key, json.dumps(messages), ttl_seconds)
    
    async def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history."""
        key = f"{self.PREFIX_CONVERSATION}{session_id}"
        value = await self._backend.get(key)
        if value:
            return json.loads(value)
        return []
    
    async def append_to_conversation(
        self, 
        session_id: str, 
        message: Dict[str, Any],
        ttl_seconds: int = TTL_CONVERSATION
    ) -> bool:
        """Append a message to conversation history."""
        messages = await self.get_conversation(session_id)
        messages.append(message)
        return await self.set_conversation(session_id, messages, ttl_seconds)
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    async def close(self) -> None:
        """Close storage connection."""
        await self._backend.close()


# =============================================================================
# Storage Factory
# =============================================================================

_storage_instance: Optional[HelixStorage] = None


async def get_storage() -> HelixStorage:
    """
    Get the storage instance based on environment configuration.
    
    Uses Redis in production, falls back to in-memory in development
    or if Redis is unavailable.
    
    Returns:
        HelixStorage instance
    """
    global _storage_instance
    
    if _storage_instance is not None:
        return _storage_instance
    
    from src.core.config import settings
    
    # Check if Redis URL is configured
    redis_url = getattr(settings, 'redis_url', None)
    
    if redis_url:
        try:
            backend = RedisStorage(redis_url)
            # Test connection
            await backend._get_client()
            _storage_instance = HelixStorage(backend)
            logger.info("Using Redis storage backend")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, falling back to in-memory: {e}")
            _storage_instance = HelixStorage(InMemoryStorage())
    else:
        # No Redis URL configured, use in-memory
        if settings.is_production:
            logger.warning("No REDIS_URL configured in production! Using in-memory storage.")
        else:
            logger.info("Development mode: Using in-memory storage")
        _storage_instance = HelixStorage(InMemoryStorage())
    
    return _storage_instance


async def close_storage() -> None:
    """Close the storage connection."""
    global _storage_instance
    if _storage_instance:
        await _storage_instance.close()
        _storage_instance = None
