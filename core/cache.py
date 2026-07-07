import logging
from django.core.cache.backends.redis import RedisCache
from redis.exceptions import ConnectionError, TimeoutError, RedisError
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

logger = logging.getLogger(__name__)

class SafeRedisCache(RedisCache):
    """
    SaaS-grade custom Redis cache backend that catches Redis connection/timeout errors,
    logs warnings instead of throwing exceptions (preventing server crash),
    and falls back to standard default/cache-miss behaviors.
    
    It also implements connection retry mechanism with exponential backoff.
    """
    def __init__(self, server, params):
        options = params.setdefault('OPTIONS', {})
        
        # Configure retry strategy: retry up to 3 times with exponential backoff
        # (e.g., 0.5s, 1.0s, 2.0s) when connection fails or times out
        if 'retry' not in options:
            options['retry'] = Retry(ExponentialBackoff(cap=2.0, base=0.5), 3)
        if 'retry_on_timeout' not in options:
            options['retry_on_timeout'] = True
            
        super().__init__(server, params)

    def _safe_call(self, method, fallback_value, *args, **kwargs):
        try:
            return method(*args, **kwargs)
        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                f"[Redis Cache Warning] Connection or Timeout failed. "
                f"Falling back to default/cache-miss. Error: {e}"
            )
            return fallback_value
        except RedisError as e:
            logger.error(
                f"[Redis Cache Error] Redis client error. "
                f"Falling back to default/cache-miss. Error: {e}"
            )
            return fallback_value

    def add(self, key, value, timeout=None, version=None):
        return self._safe_call(super().add, False, key, value, timeout=timeout, version=version)

    def get(self, key, default=None, version=None):
        return self._safe_call(super().get, default, key, default=default, version=version)

    def set(self, key, value, timeout=None, version=None):
        return self._safe_call(super().set, None, key, value, timeout=timeout, version=version)

    def touch(self, key, timeout=None, version=None):
        return self._safe_call(super().touch, False, key, timeout=timeout, version=version)

    def delete(self, key, version=None):
        return self._safe_call(super().delete, False, key, version=version)

    def get_many(self, keys, version=None):
        return self._safe_call(super().get_many, {}, keys, version=version)

    def set_many(self, data, timeout=None, version=None):
        return self._safe_call(super().set_many, None, data, timeout=timeout, version=version)

    def delete_many(self, keys, version=None):
        return self._safe_call(super().delete_many, None, keys, version=version)

    def clear(self):
        return self._safe_call(super().clear, None)

    def incr(self, key, delta=1, version=None):
        try:
            return super().incr(key, delta, version)
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"[Redis Cache Warning] Increment failed. Error: {e}")
            raise ValueError(f"Redis connection failed: {e}")

    def decr(self, key, delta=1, version=None):
        try:
            return super().decr(key, delta, version)
        except (ConnectionError, TimeoutError, RedisError) as e:
            logger.warning(f"[Redis Cache Warning] Decrement failed. Error: {e}")
            raise ValueError(f"Redis connection failed: {e}")

    def has_key(self, key, version=None):
        return self._safe_call(super().has_key, False, key, version=version)
