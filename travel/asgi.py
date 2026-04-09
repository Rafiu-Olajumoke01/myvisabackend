import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel.settings')

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()  # ✅ Must be called before any app imports

from channels.routing import ProtocolTypeRouter, URLRouter
from travel.middleware import JWTAuthMiddleware
import calls.routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddleware(
        URLRouter(
            calls.routing.websocket_urlpatterns
        )
    ),
})