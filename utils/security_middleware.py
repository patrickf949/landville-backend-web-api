"""
Security and origin protection middleware for Landville API.

Protects against:
- Unauthorized third-party web clients (enforces that web requests originate from
  landville.vercel.app, atterville.vercel.app, or authorized dev environments).
- Known automated attack tools and vulnerability scanners (e.g. sqlmap, nikto, dirbuster).
- Missing HTTP security headers (nosniff, clickjacking, referrer policy).
"""
import re
from urllib.parse import urlparse

from django.conf import settings
from django.http import JsonResponse

# Known automated security vulnerability scanners and exploit tools
BLOCKED_USER_AGENTS = (
    'sqlmap',
    'nikto',
    'dirbuster',
    'wpscan',
    'masscan',
    'nmap',
    'acunetix',
    'nessus',
    'havij',
)

# Paths exempt from strict origin/browser enforcement (docs, admin, static, ws)
EXEMPT_PATH_PREFIXES = (
    '/landville/adm/',
    '/api/v1/documentation/',
    '/static/',
    '/ws/',
    '/favicon.ico',
)


class SecurityAndOriginProtectionMiddleware:
    """
    Validates origin, user-agent, and enforces security headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # 1. Block known scanner/exploit user agents
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        if user_agent and any(scanner in user_agent for scanner in BLOCKED_USER_AGENTS):
            return JsonResponse(
                {'errors': 'Request blocked due to suspicious client signature.'},
                status=403
            )

        # 2. Strict Origin / Referer validation for web API calls
        if not path.startswith(EXEMPT_PATH_PREFIXES) and path != '/':
            origin = request.META.get('HTTP_ORIGIN')
            referer = request.META.get('HTTP_REFERER')

            # Normalize origin
            check_origin = origin
            if not check_origin and referer:
                parsed = urlparse(referer)
                if parsed.scheme and parsed.netloc:
                    check_origin = f"{parsed.scheme}://{parsed.netloc}"

            if check_origin:
                allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
                allowed_regexes = getattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES', [])

                is_allowed = check_origin in allowed_origins

                if not is_allowed and allowed_regexes:
                    is_allowed = any(re.match(rgx, check_origin) for rgx in allowed_regexes)

                # In debug mode, allow localhost/127.0.0.1
                if not is_allowed and settings.DEBUG:
                    parsed = urlparse(check_origin)
                    if parsed.hostname in ('localhost', '127.0.0.1', '0.0.0.0'):
                        is_allowed = True

                if not is_allowed:
                    return JsonResponse(
                        {'errors': 'Access from this origin is not permitted.'},
                        status=403
                    )

        # Process request
        response = self.get_response(request)

        # 3. Add defensive security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

        return response
