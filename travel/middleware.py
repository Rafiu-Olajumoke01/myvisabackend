from urllib.parse import parse_qs
from channels.db import database_sync_to_async


@database_sync_to_async
def get_user_from_token(token_key):
    # ✅ All Django imports inside the function — loads after app registry is ready
    from django.contrib.auth.models import AnonymousUser
    from rest_framework_simplejwt.tokens import AccessToken
    from users.models import User
    try:
        token = AccessToken(token_key)
        return User.objects.get(id=token['user_id'])
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser
        query_string = parse_qs(scope['query_string'].decode())
        token = query_string.get('token', [None])[0]
        scope['user'] = await get_user_from_token(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)