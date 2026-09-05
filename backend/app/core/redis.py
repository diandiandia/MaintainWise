import time
from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class InMemoryRedisMock:
    """轻量内存模拟器 (当无物理 Redis 实例时作为平滑降级支持)"""
    def __init__(self):
        self._store = {}
        self._expire = {}

    def get(self, key: str) -> Optional[str]:
        now = time.time()
        if key in self._expire and now > self._expire[key]:
            del self._store[key]
            del self._expire[key]
            return None
        return self._store.get(key)

    def set(self, key: str, value: str):
        self._store[key] = str(value)

    def setex(self, key: str, time_sec: int, value: str):
        self._store[key] = str(value)
        self._expire[key] = time.time() + time_sec

    def delete(self, key: str):
        self._store.pop(key, None)
        self._expire.pop(key, None)

    def incr(self, key: str) -> int:
        val = int(self.get(key) or 0) + 1
        self._store[key] = str(val)
        return val

    def expire(self, key: str, time_sec: int):
        self._expire[key] = time.time() + time_sec

def get_redis_client():
    try:
        import redis
        client = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=1)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"无法连接到物理 Redis ({str(e)})，自动降级启用内存缓存模拟器。")
        return InMemoryRedisMock()

redis_client = get_redis_client()
