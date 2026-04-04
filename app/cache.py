import json
import os
from typing import Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from datetime import timedelta

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CACHE_TTL = 60


class CacheService:
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._enabled = REDIS_AVAILABLE

    @property
    def client(self) -> Optional[redis.Redis]:
        if not self._enabled:
            return None
        if self._client is None:
            try:
                self._client = redis.from_url(REDIS_URL, decode_responses=True)
            except Exception:
                self._enabled = False
                return None
        return self._client

    def get(self, key: str) -> Optional[dict]:
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
        if not self._enabled:
            return None
        try:
            self.client.setex(key, ttl, json.dumps(value))
        except Exception:
            pass

    def delete(self, key: str) -> None:
        if not self._enabled:
            return None
        try:
            self.client.delete(key)
        except Exception:
            pass

    def invalidate_team(self, team_id: int) -> None:
        if not self._enabled:
            return None
        self.delete(f"team:{team_id}")
        self.delete(f"team:slug:*")

    def invalidate_project(self, project_id: int) -> None:
        if not self._enabled:
            return None
        self.delete(f"project:{project_id}")


cache_service = CacheService()
