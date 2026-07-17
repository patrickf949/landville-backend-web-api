"""ASGI entrypoint: HTTP is served by Django, websockets by Channels."""
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'landville.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from chat.middleware import JWTAuthMiddleware  # noqa: E402
from chat.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': JWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
})
