from rest_framework.throttling import SimpleRateThrottle

from .utils import get_client_ip


class SubmitPerIPThrottle(SimpleRateThrottle):
    scope = "submit_ip"

    def get_cache_key(self, request, view):
        ip = get_client_ip(request)
        if not ip:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ip}

