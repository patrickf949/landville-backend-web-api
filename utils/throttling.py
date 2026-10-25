"""
Rate limiting and throttling classes for Landville API.

Implements multi-tiered protection:
- Standard anonymous & authenticated burst protection.
- Method-scoped throttling (intense limits on POST/PUT/PATCH/DELETE mutations).
- Sensitive endpoint throttling (brute force and spam protection for auth & enquiries).
"""
import sys

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle


def is_test_mode():
    """Detect if running under automated tests to prevent self-throttling in test suites."""
    return (
        'test' in sys.argv
        or getattr(settings, 'TESTING', False)
        or getattr(settings, 'DISABLE_THROTTLING', False)
    )


class BurstAnonRateThrottle(AnonRateThrottle):
    """General burst limit for anonymous visitors."""
    scope = 'anon'

    def allow_request(self, request, view):
        if is_test_mode():
            return True
        return super().allow_request(request, view)


class BurstUserRateThrottle(UserRateThrottle):
    """General burst limit for authenticated users."""
    scope = 'user'

    def allow_request(self, request, view):
        if is_test_mode():
            return True
        return super().allow_request(request, view)


class PostRequestRateThrottle(SimpleRateThrottle):
    """
    Intense rate limiting specifically for POST, PUT, PATCH, and DELETE requests.
    Safe methods (GET, HEAD, OPTIONS) pass through untouched.
    """
    scope = 'post_request'

    def allow_request(self, request, view):
        if is_test_mode():
            return True
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"user_{request.user.pk}"
        else:
            ident = f"anon_{self.get_ident(request)}"

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class SensitiveActionRateThrottle(SimpleRateThrottle):
    """
    Strict rate limit for sensitive actions:
    - User registration
    - Login / Authentication
    - Password reset requests
    - Property enquiry submissions
    """
    scope = 'sensitive_action'

    def allow_request(self, request, view):
        if is_test_mode():
            return True
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
