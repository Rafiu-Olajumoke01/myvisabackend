import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class CallConsumer(AsyncWebsocketConsumer):

    # ─────────────────────────────────────────────────────────────────────────
    # CONNECT
    # Runs when a user/agent opens a WebSocket connection.
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
    # DISCONNECT
    # Runs when a user/agent closes the connection or drops off.
    #
    # FIX: If an agent disconnects while on a call (e.g. closed browser tab),
    #      we set their status back to 'available' so new clients can reach them
    #      when they reconnect. Without this, a crashed agent stays 'busy' forever.
    # ─────────────────────────────────────────────────────────────────────────

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if getattr(self, 'is_agent', False):
            await self.channel_layer.group_discard('agents_room', self.channel_name)
            await self.set_agent_status(self.user, 'available')
        print(f'[WS] Disconnected: user={self.user.id} code={close_code}')

    # ─────────────────────────────────────────────────────────────────────────
    # RECEIVE — main router
    # Every message sent from the frontend arrives here first.
    # ─────────────────────────────────────────────────────────────────────────

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type')
        print(f'[WS] receive: type={event_type} from user={self.user.id}')

        # ── CALL EVENTS ───────────────────────────────────────────────────────

        if event_type == 'call_request':
            # FIX: Check if any agent is free before creating a session.
            #      Before this, a call would broadcast even if all agents were busy,
            #      and the client would just hang forever with no feedback.
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
                # FIX: Atomic check — locks the session row in the DB so two agents
                #      cannot both accept the same call at the same time (race condition).
                #      Also checks if this agent is already busy — all in one DB transaction.
                success = await self.attach_agent_to_session(session, self.user)
                if not success:
                    await self.send(text_data=json.dumps({
                        'type':       'call_accept_failed',
                        'reason':     'This call was already accepted or you are currently busy.',
                        'session_id': session_id,
                    }))
                    return

                # Refresh session from DB so we have the latest agent/user info
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
                # FIX: mark_session_completed now also sets agent status back
                #      to 'available'. Before this fix, the agent stayed 'busy'
                #      after a call ended, so no new clients could ever reach them.
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
            # Legacy: kept for backward compatibility
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
                print(f'[WS] evaluation_result (via onboarding_complete) → {user_group}')

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

            # Echo back to sender
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
    # Called automatically when group_send() dispatches a message here.
    # Method name must match the 'type' field (dots → underscores).
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
    # All DB calls must use @database_sync_to_async because Django ORM is
    # synchronous but this consumer runs in async mode.
    # ─────────────────────────────────────────────────────────────────────────

    @database_sync_to_async
    def check_if_agent(self, user):
        from .models import Agent
        return Agent.objects.filter(email=user.email).exists() 

    # Returns True if at least one agent has status='available'.
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
        except (CallSession.DoesNotExist, Exception):
            return None

    # FIX: Atomic version — locks the session row so two agents cannot accept
    #      the same call simultaneously. Also checks if agent is already busy.
    #      Returns True if successful, False if the call was already taken or agent is busy.
    @database_sync_to_async
    def attach_agent_to_session(self, session, user):
        from .models import Agent, CallSession
        from django.db import transaction
        try:
            with transaction.atomic():
                # Lock session row — no other agent can read/write it until we're done
                locked_session = CallSession.objects.select_for_update().get(id=session.id)

                if locked_session.status == 'accepted':
                    return False  # Another agent already got it

                agent = Agent.objects.get(email=user.email, is_active=True)

                if agent.status == 'busy':
                    return False  # This agent is already on a call

                agent.status = 'busy'
                agent.save(update_fields=['status'])

                locked_session.agent  = agent
                locked_session.status = 'accepted'
                locked_session.save(update_fields=['agent', 'status'])
                return True
        except (Agent.DoesNotExist, CallSession.DoesNotExist):
            return False

    # FIX: Sets agent.status = 'available' when the call ends.
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
        except Agent.DoesNotExist:
            pass

    # Resets agent to 'available' if they disconnect mid-call.
    @database_sync_to_async
    def set_agent_status(self, user, status):
        from .models import Agent
        try:
            agent        = Agent.objects.get(email=user.email, is_active=True)
            agent.status = status
            agent.save(update_fields=['status'])
        except Agent.DoesNotExist:
            pass

    @database_sync_to_async
    def get_agent_user_id(self, session):
        try:
            return session.agent.user_id
        except Exception:
            return None

    @database_sync_to_async
    def get_applicant_name(self, session):
        try:
            user = session.user
            return (
                getattr(user, 'fullname', None)
                or user.get_full_name()
                or user.email
            )
        except Exception:
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