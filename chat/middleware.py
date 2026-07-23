"""JWT authentication for websocket connections.

The frontend connects with the same token used for REST calls,
passed as a query parameter: ws://host/ws/chat/<id>/?token=<jwt>
"""
from urllib.parse import parse_qs

import jwt
from channels.db import database_sync_to_async
from django.conf import settings


@database_sync_to_async
def get_user(token):
    from django.contrib.auth.models import AnonymousUser
    from authentication.models import BlackList, User

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=['HS256'])
        user = User.objects.get(pk=payload['id'])
    except Exception:
        return AnonymousUser()
    if not user.is_active:
        return AnonymousUser()
    if BlackList.objects.filter(token=token).exists():
        return AnonymousUser()
    return user


class JWTAuthMiddleware:
    """Populate scope['user'] from a `token` query parameter."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser

        query = parse_qs(scope.get('query_string', b'').decode())
        token = (query.get('token') or [None])[0]
        scope['user'] = await get_user(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)
