import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class CallConsumer(AsyncWebsocketConsumer):

    # ✅ ADDED: safe defaults (fixes your crash)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.user_group = None
        self.is_agent = False

    # ─────────────────────────────────────────────────────────────────────────
    # CONNECT
    # ─────────────────────────────────────────────────────────────────────────
    async def connect(self):
        user = self.scope['user']

        if not user or not user.is_authenticated:
            await self.close()
            return

        self.user = user
        self.user_group = f'user_{user.id}'

        await self.channel_layer.group_add(self.user_group, self.channel_name)

        self.is_agent = await self.check_if_agent(user)
        if self.is_agent:
            await self.channel_layer.group_add('agents_room', self.channel_name)

        await self.accept()
        print(f'[WS] Connected: user={user.id} is_agent={self.is_agent}')

    # ─────────────────────────────────────────────────────────────────────────
    # DISCONNECT (FIXED ONLY HERE)
    # ─────────────────────────────────────────────────────────────────────────
    async def disconnect(self, close_code):
        if self.user_group:
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

        if getattr(self, 'is_agent', False):
            await self.channel_layer.group_discard('agents_room', self.channel_name)

            if self.user:
                await self.set_agent_status(self.user, 'available')

        user_id = self.user.id if self.user else 'unknown'
        print(f'[WS] Disconnected: user={user_id} code={close_code}')

    # ─────────────────────────────────────────────────────────────────────────
    # RECEIVE — main router
    # ─────────────────────────────────────────────────────────────────────────
    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type')
        print(f'[WS] receive: type={event_type} from user={self.user.id}')

        # ── CALL EVENTS ───────────────────────────────────────────────────────

        if event_type == 'call_request':
            has_free_agent = await self.any_agent_available()
            if not has_free_agent:
                await self.send(text_data=json.dumps({
                    'type':    'no_agents',
                    'message': 'No agents are available right now. Please try again shortly.',
                }))
                return

            session = await self.create_session(self.user)
            print(f'[WS] Created session {session.id} for user {self.user.id}')
            await self.channel_layer.group_send('agents_room', {
                'type':       'call_request',
                'user_id':    str(self.user.id),
                'user_name':  self._get_display_name(self.user),
                'session_id': str(session.id),
                'package':    data.get('package', 'Discovery Call'),
            })

        elif event_type == 'call_accepted':
            session_id = data.get('session_id')
            meet_link  = data.get('meet_link', '')
            session    = await self.get_session(session_id)

            if session:
                success = await self.attach_agent_to_session(session, self.user)
                if not success:
                    await self.send(text_data=json.dumps({
                        'type':       'call_accept_failed',
                        'reason':     'This call was already accepted or you are currently busy.',
                        'session_id': session_id,
                    }))
                    return

                session = await self.get_session(session_id)
                user_group = f'user_{session.user_id}'
                await self.channel_layer.group_send(user_group, {
                    'type':       'call_accepted',
                    'session_id': session_id,
                    'meet_link':  meet_link,
                    'agent_name': self._get_display_name(self.user),
                })
                print(f'[WS] call_accepted sent to {user_group}')

        elif event_type == 'call_declined':
            session_id = data.get('session_id')
            session    = await self.get_session(session_id)
            if session:
                user_group = f'user_{session.user_id}'
                await self.channel_layer.group_send(user_group, {
                    'type':       'call_declined',
                    'session_id': session_id,
                    'reason':     data.get('reason', ''),
                })

        elif event_type == 'call_completed':
            session_id = data.get('session_id')
            session    = await self.get_session(session_id)
            if session:
                await self.mark_session_completed(session)

                user_group = f'user_{session.user_id}'
                await self.channel_layer.group_send(user_group, {
                    'type':       'call_completed',
                    'session_id': session_id,
                    'agent_name': self._get_display_name(self.user),
                })
                print(f'[WS] call_completed sent to {user_group}')

        # ── ONBOARDING EVENTS ─────────────────────────────────────────────────

        elif event_type == 'onboarding_started':
            session_id = data.get('session_id')
            print(f'[WS] onboarding_started for session {session_id}')

        elif event_type == 'onboarding_complete':
            session_id      = data.get('session_id')
            readiness_score = data.get('readiness_score', 0)
            recommendation  = data.get('recommendation', '')
            session         = await self.get_session(session_id)

            if session:
                applicant_name = await self.get_applicant_name(session)
                user_group     = f'user_{session.user_id}'
                is_positive    = (recommendation == 'approve') and (readiness_score >= 50)

                await self.channel_layer.group_send(user_group, {
                    'type':            'evaluation_result',
                    'session_id':      session_id,
                    'is_positive':     is_positive,
                    'readiness_score': readiness_score,
                    'recommendation':  recommendation,
                    'applicant_name':  applicant_name,
                })
                print(f'[WS] evaluation_result → {user_group}')

        # ── CHAT EVENTS ───────────────────────────────────────────────────────

        elif event_type == 'chat_message':
            session_id = data.get('session_id')
            message    = data.get('message', '').strip()

            if not session_id or not message:
                return

            session = await self.get_session(session_id)
            if not session:
                return

            await self.save_message(session, self.user, message)

            payload = {
                'type':        'chat_message',
                'session_id':  session_id,
                'message':     message,
                'sender_id':   str(self.user.id),
                'sender_name': self._get_display_name(self.user),
            }

            if self.is_agent:
                recipient_group = f'user_{session.user_id}'
                await self.channel_layer.group_send(recipient_group, payload)
            else:
                agent_user_id = await self.get_agent_user_id(session)
                if agent_user_id:
                    recipient_group = f'user_{agent_user_id}'
                    await self.channel_layer.group_send(recipient_group, payload)

            await self.send(text_data=json.dumps(payload))

        elif event_type == 'chat_history':
            session_id = data.get('session_id')
            if not session_id:
                return
            messages = await self.get_chat_history(session_id)
            await self.send(text_data=json.dumps({
                'type':       'chat_history',
                'session_id': session_id,
                'messages':   messages,
            }))

    # ─────────────────────────────────────────────────────────────────────────
    # CHANNEL LAYER EVENT HANDLERS
    # ─────────────────────────────────────────────────────────────────────────

    async def call_request(self, event):
        await self.send(text_data=json.dumps(event))

    async def call_accepted(self, event):
        await self.send(text_data=json.dumps(event))

    async def call_declined(self, event):
        await self.send(text_data=json.dumps(event))

    async def call_completed(self, event):
        await self.send(text_data=json.dumps(event))

    async def call_accept_failed(self, event):
        await self.send(text_data=json.dumps(event))

    async def no_agents(self, event):
        await self.send(text_data=json.dumps(event))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def onboarding_complete(self, event):
        await self.send(text_data=json.dumps(event))

    async def evaluation_result(self, event):
        await self.send(text_data=json.dumps(event))

    async def agent_approved(self, event):
        await self.send(text_data=json.dumps(event))

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _get_display_name(self, user):
        return (
            getattr(user, 'fullname', None)
            or user.get_full_name()
            or user.email
        )

    # ─────────────────────────────────────────────────────────────────────────
    # DATABASE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    @database_sync_to_async
    def check_if_agent(self, user):
        from .models import Agent
        return Agent.objects.filter(email=user.email).exists()

    @database_sync_to_async
    def any_agent_available(self):
        from .models import Agent
        return Agent.objects.filter(is_active=True, status='available').exists()

    @database_sync_to_async
    def create_session(self, user):
        from .models import CallSession
        return CallSession.objects.create(user=user, status='pending')

    @database_sync_to_async
    def get_session(self, session_id):
        from .models import CallSession
        try:
            return CallSession.objects.select_related('user', 'agent__user').get(id=session_id)
        except:
            return None

    @database_sync_to_async
    def attach_agent_to_session(self, session, user):
        from .models import Agent, CallSession
        from django.db import transaction
        try:
            with transaction.atomic():
                locked_session = CallSession.objects.select_for_update().get(id=session.id)

                if locked_session.status == 'accepted':
                    return False

                agent = Agent.objects.get(email=user.email, is_active=True)

                if agent.status == 'busy':
                    return False

                agent.status = 'busy'
                agent.save(update_fields=['status'])

                locked_session.agent  = agent
                locked_session.status = 'accepted'
                locked_session.save(update_fields=['agent', 'status'])
                return True
        except:
            return False

    @database_sync_to_async
    def mark_session_completed(self, session):
        from .models import Agent
        session.status = 'completed'
        session.save(update_fields=['status'])
        try:
            if session.agent_id:
                agent        = Agent.objects.get(id=session.agent_id)
                agent.status = 'available'
                agent.save(update_fields=['status'])
        except:
            pass

    @database_sync_to_async
    def set_agent_status(self, user, status):
        from .models import Agent
        try:
            agent        = Agent.objects.get(email=user.email, is_active=True)
            agent.status = status
            agent.save(update_fields=['status'])
        except:
            pass

    @database_sync_to_async
    def get_agent_user_id(self, session):
        try:
            return session.agent.user_id
        except:
            return None

    @database_sync_to_async
    def get_applicant_name(self, session):
        try:
            user = session.user
            return getattr(user, 'fullname', None) or user.get_full_name() or user.email
        except:
            return 'Applicant'

    @database_sync_to_async
    def save_message(self, session, sender, message):
        from .models import ChatMessage
        return ChatMessage.objects.create(
            session=session,
            sender=sender,
            message=message,
        )

    @database_sync_to_async
    def get_chat_history(self, session_id):
        from .models import ChatMessage
        messages = ChatMessage.objects.filter(
            session_id=session_id
        ).select_related('sender').order_by('created_at')
        return [
            {
                'sender_id':   str(msg.sender_id),
                'sender_name': (
                    getattr(msg.sender, 'fullname', None)
                    or msg.sender.get_full_name()
                    or msg.sender.email
                ),
                'message':    msg.message,
                'created_at': msg.created_at.isoformat(),
            }
            for msg in messages
        ]