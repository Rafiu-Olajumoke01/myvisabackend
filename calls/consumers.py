import json
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class CallConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.user_group = None
        self.is_provider = False

    # ─────────────────────────────────────────
    # CONNECT
    # ─────────────────────────────────────────
    async def connect(self):
        user = self.scope['user']

        if not user or not user.is_authenticated:
            await self.close()
            return

        self.user = user
        self.user_group = f"user_{user.id}"

        await self.channel_layer.group_add(self.user_group, self.channel_name)

        self.is_provider = await self.check_if_provider(user)
        if self.is_provider:
            await self.channel_layer.group_add('providers_room', self.channel_name)

        # ✅ Admin joins admin_room
        if user.is_staff:
            await self.channel_layer.group_add('admin_room', self.channel_name)

        await self.accept()
        print(f"[WS] Connected user={user.id} provider={self.is_provider} staff={user.is_staff}")

    # ─────────────────────────────────────────
    # DISCONNECT
    # ─────────────────────────────────────────
    async def disconnect(self, close_code):
        if self.user_group:
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

        if getattr(self, 'is_provider', False):
            await self.channel_layer.group_discard('providers_room', self.channel_name)
            if self.user:
                await self.set_provider_status(self.user, 'available')

        # ✅ Admin leaves admin_room
        if self.user and self.user.is_staff:
            await self.channel_layer.group_discard('admin_room', self.channel_name)

        user_id = self.user.id if self.user else "unknown"
        print(f"[WS] Disconnected user={user_id}")

    # ─────────────────────────────────────────
    # RECEIVE
    # ─────────────────────────────────────────
    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type')

        print(f"[WS] event={event_type} user={self.user.id}")

        # ───────── CALL REQUEST ─────────
        if event_type == 'call_request':
            session = await self.create_session(self.user)
            await self.channel_layer.group_send('providers_room', {
                'type': 'call_request',
                'session_id': str(session.id),
                'user_id': str(self.user.id),
                'user_name': self.get_display_name(self.user),
                'package': data.get('package', 'Discovery Call'),
            })

        # ───────── CALL ACCEPTED ─────────
        elif event_type == 'call_accepted':
            session_id = data.get('session_id')
            meet_link = data.get('meet_link', '')
            session = await self.get_session(session_id)
            if not session:
                return

            success = await self.attach_provider_to_session(session, self.user)
            if not success:
                await self.send(text_data=json.dumps({
                    'type': 'call_accept_failed',
                    'session_id': session_id,
                    'reason': 'Already accepted or busy'
                }))
                return

            user_group = f"user_{session.user_id}"
            await self.channel_layer.group_send(user_group, {
                'type': 'call_accepted',
                'session_id': session_id,
                'meet_link': meet_link,
                'provider_name': self.get_display_name(self.user),
            })

        # ───────── CALL DECLINED ─────────
        elif event_type == 'call_declined':
            session_id = data.get('session_id')
            session = await self.get_session(session_id)
            if session:
                user_group = f"user_{session.user_id}"
                await self.channel_layer.group_send(user_group, {
                    'type': 'call_declined',
                    'session_id': session_id,
                    'reason': data.get('reason', '')
                })

        # ───────── CALL COMPLETED ─────────
        elif event_type == 'call_completed':
            session_id = data.get('session_id')
            session = await self.get_session(session_id)
            if session:
                await self.mark_session_completed(session)
                user_group = f"user_{session.user_id}"
                await self.channel_layer.group_send(user_group, {
                    'type': 'call_completed',
                    'session_id': session_id,
                    'provider_name': self.get_display_name(self.user),
                })

        # ───────── CALL CHAT MESSAGE (session-based) ─────────
        elif event_type == 'chat_message':
            session_id = data.get('session_id')
            message = data.get('message', '').strip()

            if not session_id or not message:
                return

            session = await self.get_session(session_id)
            if not session:
                return

            await self.save_message(session, self.user, message)

            payload = {
                'type': 'chat_message',
                'session_id': session_id,
                'message': message,
                'sender_id': str(self.user.id),
                'sender_name': self.get_display_name(self.user),
            }

            if self.is_provider:
                await self.channel_layer.group_send(
                    f"user_{session.user_id}", payload
                )
            else:
                if session.service_provider:
                    await self.channel_layer.group_send(
                        f"user_{session.service_provider.user_id}", payload
                    )

            await self.send(text_data=json.dumps(payload))

        # ───────── CHAT HISTORY ─────────
        elif event_type == 'chat_history':
            session_id = data.get('session_id')
            messages = await self.get_chat_history(session_id)
            await self.send(text_data=json.dumps({
                'type': 'chat_history',
                'session_id': session_id,
                'messages': messages
            }))

        # ───────── RECOMMEND PACKAGE ─────────
        elif event_type == 'recommend_package':
            target_user_id = data.get('target_user_id')
            package = data.get('package')
            session_id = data.get('session_id')

            if not target_user_id or not package:
                return

            if not self.user.is_staff:
                return

            await self.save_recommendation(target_user_id, package, self.user)

            payload = {
                'type': 'package_recommendation',
                'package': package,
                'recommended_by': self.get_display_name(self.user),
                'session_id': session_id,
            }

            await self.channel_layer.group_send(
                f"user_{target_user_id}", {
                    'type': 'package_recommendation',
                    **payload
                }
            )

            await self.send(text_data=json.dumps({
                'type': 'recommend_success',
                'target_user_id': target_user_id,
                'package_title': package.get('title'),
            }))

        # ───────── NEW CHAT MESSAGE (admin ↔ user application chat) ─────────
        elif event_type == 'new_chat_message':
            application_id = data.get('application_id')
            message = data.get('message', '').strip()
            target_user_id = data.get('target_user_id')
            sender_role = data.get('sender_role', 'consultant')

            if not message:
                return

            payload = {
                'type': 'new_chat_message',
                'application_id': application_id,
                'message': message,
                'sender_role': sender_role,
                'client_name': self.get_display_name(self.user),
                'created_at': datetime.datetime.now().isoformat(),
                'sender_user_id': str(self.user.id),
            }

            # ✅ Admin sending to user
            if sender_role == 'consultant' and target_user_id:
                await self.channel_layer.group_send(
                    f"user_{target_user_id}", {
                        'type': 'new_chat_message',
                        **payload
                    }
                )
                await self.send(text_data=json.dumps(payload))

            # ✅ User sending to admin_room
            elif sender_role == 'client':
                await self.channel_layer.group_send(
                    'admin_room', {
                        'type': 'new_chat_message',
                        **payload
                    }
                )
                # Echo back to sender so they see their message confirmed
                await self.send(text_data=json.dumps({**payload, 'sender_role': 'client'}))
    # ─────────────────────────────────────────
    # CHANNEL EVENTS
    # ─────────────────────────────────────────
    async def call_request(self, event):
        await self.send(json.dumps(event))

    async def call_accepted(self, event):
        await self.send(json.dumps(event))

    async def call_declined(self, event):
        await self.send(json.dumps(event))

    async def call_completed(self, event):
        await self.send(json.dumps(event))

    async def call_accept_failed(self, event):
        await self.send(json.dumps(event))

    async def chat_message(self, event):
        await self.send(json.dumps(event))

    async def package_recommendation(self, event):
        await self.send(json.dumps(event))

    async def verification_call_scheduled(self, event):
        await self.send(json.dumps(event))

    async def sp_application_update(self, event):
        await self.send(json.dumps(event))

    async def new_notification(self, event):
        await self.send(json.dumps(event))

    async def chat_unlocked(self, event):
        await self.send(json.dumps(event))

    # ✅ Handles incoming new_chat_message from channel layer
    async def new_chat_message(self, event):
        await self.send(json.dumps({
            'type': 'new_chat_message',
            'application_id': event['application_id'],
            'client_name': event['client_name'],
            'message': event['message'],
            'sender_role': event['sender_role'],
            'sender_user_id': event.get('sender_user_id'), 
            'created_at': event['created_at'],
        }))

    # ─────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────
    def get_display_name(self, user):
        return (
            getattr(user, 'fullname', None)
            or user.get_full_name()
            or user.email
        )

    # ─────────────────────────────────────────
    # DB HELPERS
    # ─────────────────────────────────────────
    @database_sync_to_async
    def check_if_provider(self, user):
        from providers.models import ServiceProvider
        return ServiceProvider.objects.filter(user=user, is_active=True).exists()

    @database_sync_to_async
    def create_session(self, user):
        from .models import CallSession
        return CallSession.objects.create(user=user, status='pending')

    @database_sync_to_async
    def get_session(self, session_id):
        from .models import CallSession
        try:
            return CallSession.objects.select_related(
                'user',
                'service_provider__user'
            ).get(id=session_id)
        except:
            return None

    @database_sync_to_async
    def attach_provider_to_session(self, session, user):
        try:
            provider = user.sp_profile
            if session.status == 'accepted':
                return False
            session.service_provider = provider
            session.status = 'accepted'
            session.save(update_fields=['service_provider', 'status'])
            return True
        except:
            return False

    @database_sync_to_async
    def mark_session_completed(self, session):
        if session.service_provider:
            provider = session.service_provider
            provider.availability = 'available'
            provider.save(update_fields=['availability'])
        session.status = 'completed'
        session.save(update_fields=['status'])

    @database_sync_to_async
    def set_provider_status(self, user, status):
        try:
            provider = user.sp_profile
            provider.availability = status
            provider.save(update_fields=['availability'])
        except:
            pass

    @database_sync_to_async
    def save_message(self, session, sender, message):
        from .models import ChatMessage
        return ChatMessage.objects.create(
            session=session,
            sender=sender,
            message=message
        )

    @database_sync_to_async
    def get_chat_history(self, session_id):
        from .models import ChatMessage
        messages = ChatMessage.objects.filter(
            session_id=session_id
        ).select_related('sender').order_by('created_at')
        return [
            {
                'sender_id': str(m.sender_id),
                'sender_name': self.get_display_name(m.sender),
                'message': m.message,
                'created_at': m.created_at.isoformat()
            }
            for m in messages
        ]

    @database_sync_to_async
    def save_recommendation(self, target_user_id, package, admin_user):
        from applications.models import PackageRecommendation
        from packages.models import Package
        try:
            pkg = Package.objects.get(id=package.get('id'))
            PackageRecommendation.objects.create(
                user_id=target_user_id,
                package=pkg,
                recommended_by=admin_user,
                admin_note='Recommended via chat',
                status='pending'
            )
        except Package.DoesNotExist:
            pass