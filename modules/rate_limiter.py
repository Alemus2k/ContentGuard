import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, max_requests=20, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def _clean_old_requests(self, key):
        now = time.time()
        cutoff = now - self.window_seconds
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

    def is_allowed(self, key="default"):
        self._clean_old_requests(key)
        if len(self.requests[key]) >= self.max_requests:
            return False
        self.requests[key].append(time.time())
        return True

    def get_remaining(self, key="default"):
        self._clean_old_requests(key)
        return max(0, self.max_requests - len(self.requests[key]))

    def get_reset_time(self, key="default"):
        self._clean_old_requests(key)
        if not self.requests[key]:
            return 0
        oldest = min(self.requests[key])
        return max(0, self.window_seconds - (time.time() - oldest))

    def get_status(self, key="default"):
        remaining = self.get_remaining(key)
        reset_time = self.get_reset_time(key)
        return {
            "remaining": remaining,
            "limit": self.max_requests,
            "reset_seconds": round(reset_time, 1),
            "allowed": remaining > 0
        }
