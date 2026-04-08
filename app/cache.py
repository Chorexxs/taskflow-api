"""
TaskFlow API - Cache Service

This module provides a caching layer using Redis for improved performance.
The CacheService class wraps Redis operations with error handling and
provides simple methods for caching and invalidating data.

Features:
- Optional Redis integration (gracefully degrades if Redis unavailable)
- JSON serialization for cached data
- TTL (Time To Live) support for cache entries
- Team and project cache invalidation methods

Environment Variables:
- REDIS_URL: Redis connection string (default: redis://localhost:6379/0)

The cache is currently used for:
- Team data caching
- Project data caching

Note: Currently imported but not actively used in most endpoints.
Can be extended for caching frequently accessed data like team members.
"""

import json
import os
from typing import Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from datetime import timedelta

# Redis connection URL from environment
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Default cache TTL in seconds (1 minute)
CACHE_TTL = 60


class CacheService:
    """
    Redis-based caching service with graceful degradation.
    
    This service provides a simple interface for caching data with
    automatic JSON serialization and TTL support. If Redis is not
    available, all operations silently fail (return None/True).
    
    Attributes:
        _client (Optional[redis.Redis]): The Redis client instance.
        _enabled (bool): Whether Redis is available and enabled.
    
    Example:
        >>> cache_service = CacheService()
        >>> cache_service.set("key", {"data": "value"}, ttl=60)
        >>> data = cache_service.get("key")
        >>> cache_service.delete("key")
    """
    
    def __init__(self):
        """
        Initialize the CacheService.
        
        Sets up the initial state. The Redis client is not connected
        until the first operation is attempted.
        """
        self._client: Optional[redis.Redis] = None
        self._enabled = REDIS_AVAILABLE

    @property
    def client(self) -> Optional[redis.Redis]:
        """
        Get or create the Redis client.
        
        Lazy initialization of the Redis connection. If Redis is
        not available or connection fails, _enabled is set to False
        and subsequent operations will be no-ops.
        
        Returns:
            Optional[redis.Redis]: The Redis client if available, None otherwise.
        """
        if not self._enabled:
            return None
        if self._client is None:
            try:
                self._client = redis.from_url(REDIS_URL, decode_responses=True)
            except Exception:
                # Disable cache on connection failure
                self._enabled = False
                return None
        return self._client

    def get(self, key: str) -> Optional[dict]:
        """
        Get a value from cache.
        
        Retrieves a JSON-decoded value from Redis. If the key doesn't
        exist or Redis is unavailable, returns None.
        
        Args:
            key (str): The cache key to retrieve.
        
        Returns:
            Optional[dict]: The cached value as a dictionary, or None if not found/unavailable.
        
        Example:
            >>> data = cache_service.get("team:1")
            >>> if data:
            ...     print(data["name"])
        """
        if not self._enabled:
            return None
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return None

    def set(self, key: str, value: dict, ttl: int = CACHE_TTL) -> None:
        """
        Set a value in cache with TTL.
        
        Serializes the value to JSON and stores it in Redis with
        the specified time-to-live.
        
        Args:
            key (str): The cache key.
            value (dict): The value to cache (will be JSON serialized).
            ttl (int): Time to live in seconds. Default: 60.
        
        Returns:
            None: This function doesn't return anything.
        
        Example:
            >>> cache_service.set("team:1", {"name": "My Team"}, ttl=120)
        """
        if not self._enabled:
            return None
        try:
            self.client.setex(key, ttl, json.dumps(value))
        except Exception:
            pass

    def delete(self, key: str) -> None:
        """
        Delete a key from cache.
        
        Removes a specific key from the Redis cache.
        
        Args:
            key (str): The cache key to delete.
        
        Returns:
            None: This function doesn't return anything.
        
        Example:
            >>> cache_service.delete("team:1")
        """
        if not self._enabled:
            return None
        try:
            self.client.delete(key)
        except Exception:
            pass

    def invalidate_team(self, team_id: int) -> None:
        """
        Invalidate all cache entries related to a team.
        
        Called when team data is modified to ensure stale data
        is not served from cache.
        
        Args:
            team_id (int): ID of the team to invalidate cache for.
        
        Returns:
            None: This function doesn't return anything.
        
        Example:
            >>> cache_service.invalidate_team(team_id=1)
            # Deletes: team:1, team:slug:*
        """
        if not self._enabled:
            return None
        self.delete(f"team:{team_id}")
        self.delete(f"team:slug:*")

    def invalidate_project(self, project_id: int) -> None:
        """
        Invalidate all cache entries related to a project.
        
        Called when project data is modified to ensure stale data
        is not served from cache.
        
        Args:
            project_id (int): ID of the project to invalidate cache for.
        
        Returns:
            None: This function doesn't return anything.
        
        Example:
            >>> cache_service.invalidate_project(project_id=1)
            # Deletes: project:1
        """
        if not self._enabled:
            return None
        self.delete(f"project:{project_id}")


# Singleton instance of the cache service
cache_service = CacheService()
