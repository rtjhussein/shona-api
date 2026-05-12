import math
import time

from django.core.cache import caches
from rest_framework.throttling import BaseThrottle


class APIKeyRateThrottle(BaseThrottle):
    cache_alias = "default"
    window_seconds = 60

    def allow_request(self, request, view):
        api_key = getattr(request, "auth", None)
        if api_key is None:
            return True

        now = time.time()
        limit = api_key.rate_limit_per_minute
        window_id = int(now // self.window_seconds)
        reset_at = int((window_id + 1) * self.window_seconds)
        cache_key = f"api-auth:rate:{api_key.prefix}:{window_id}"
        cache = caches[self.cache_alias]

        cache.add(cache_key, 0, timeout=self.window_seconds + 1)
        request_count = cache.incr(cache_key)
        remaining = max(limit - request_count, 0)

        self.wait_seconds = max(reset_at - now, 0)
        self.rate_limit_headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_at),
            "X-RateLimit-Plan": api_key.plan,
        }
        request._request.api_rate_limit_headers = self.rate_limit_headers
        request._request.api_rate_limit_wait = self.wait()

        return request_count <= limit

    def wait(self):
        return math.ceil(getattr(self, "wait_seconds", 0))
