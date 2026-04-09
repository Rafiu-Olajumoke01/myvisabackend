import random
import string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from applications.models import Application as App
from rest_framework import status, permissions

User = get_user_model()


def generate_meet_link():
    def part(n):
        return ''.join(random.choices(string.ascii_lowercase, k=n))
    room = f"myvisa-{part(4)}-{part(4)}-{part(4)}"
    return f"https://meet.jit.si/{room}"


class AvailableAgentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import Agent
        agents = Agent.objects.filter(status='available', is_active=True)
        data = [
            {
                'id': str(agent.id),
                'name': f"{agent.first_name} {agent.last_name}",
                'status': agent.status,
            }
            for agent in agents
        ]
        return Response({'agents': data, 'count': len(data)})


class RequestCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .models import Agent, CallSession

        agents = Agent.objects.filter(status='available', is_active=True).order_by('updated_at')

        if not agents.exists():
            return Response(
                {'error': 'No agents available right now. Please try again in a few minutes.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        agent = agents.first()

        session = CallSession.objects.create(
            user=request.user,
            agent=agent,
            status='pending',
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'agents_room',
            {
                'type': 'call_request',
                'session_id': str(session.id),
                'user_id': str(request.user.id),
                'user_name': getattr(request.user, 'fullname', None) or request.user.get_full_name() or request.user.email,
                'package': request.data.get('package', 'Discovery Call'),
            }
        )

        return Response({
            'session_id': str(session.id),
            'message': 'Call request sent. Connecting you to an agent...',
            'status': 'pending',
        }, status=status.HTTP_201_CREATED)


class AcceptCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from .models import CallSession, Agent
        from django.db import transaction

        print(f"[ACCEPT] session_id received: {session_id}")
        print(f"[ACCEPT] requesting user: {request.user.id} / {request.user.email}")

        try:
            with transaction.atomic():
                session = CallSession.objects.select_for_update().select_related('user').get(
                    id=session_id
                )

                print(f"[ACCEPT] session found. status={session.status}, agent_id={session.agent_id}")

                if session.status != 'pending':
                    print(f"[ACCEPT] BLOCKED — status is '{session.status}', not pending")
                    return Response(
                        {'error': 'Session not found or already handled.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                try:
                    agent = request.user.agent_profile
                    print(f"[ACCEPT] agent profile found via agent_profile: {agent.id}")
                except Exception as e:
                    print(f"[ACCEPT] agent_profile FAILED for user {request.user.id} / {request.user.email}: {e}")
                    try:
                        agent = Agent.objects.get(email=request.user.email)
                        print(f"[ACCEPT] fallback agent found via email: {agent.id}")
                    except Agent.DoesNotExist:
                        print(f"[ACCEPT] no agent found at all for {request.user.email}")
                        return Response({'error': 'Agent profile not found.'}, status=404)

                meet_link = generate_meet_link()
                session.status = 'accepted'
                session.meet_link = meet_link
                session.agent = agent
                session.save()

        except CallSession.DoesNotExist:
            print(f"[ACCEPT] session {session_id} does NOT exist in DB")
            return Response(
                {'error': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        channel_layer = get_channel_layer()
        user_group = f'user_{session.user.id}'
        async_to_sync(channel_layer.group_send)(
            user_group,
            {
                'type': 'call_accepted',
                'session_id': str(session.id),
                'meet_link': meet_link,
                'agent_name': f"{agent.first_name} {agent.last_name}",
            }
        )

        return Response({
            'session_id': str(session.id),
            'meet_link': meet_link,
            'status': 'accepted',
        })


class DeclineCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from .models import Agent, CallSession, CallDecline
        try:
            session = CallSession.objects.select_related('user').get(
                id=session_id, status='pending'
            )
        except CallSession.DoesNotExist:
            return Response(
                {'error': 'Session not found or already handled.'},
                status=status.HTTP_404_NOT_FOUND
            )

        CallDecline.objects.create(
            session=session,
            agent=session.agent,
            reason=request.data.get('reason', 'No reason provided'),
        )

        declined_agent_ids = session.declines.values_list('agent_id', flat=True)
        next_agent = Agent.objects.filter(
            status='available',
            is_active=True,
        ).exclude(id__in=declined_agent_ids).order_by('updated_at').first()

        channel_layer = get_channel_layer()

        if next_agent:
            session.agent = next_agent
            session.status = 'pending'
            session.save()

            async_to_sync(channel_layer.group_send)(
                'agents_room',
                {
                    'type': 'call_request',
                    'session_id': str(session.id),
                    'user_id': str(session.user.id),
                    'user_name': getattr(session.user, 'fullname', None) or session.user.get_full_name() or session.user.email,
                    'package': 'Discovery Call',
                }
            )

            return Response({
                'message': 'Call rerouted to next available agent.',
                'session_id': str(session.id),
                'status': 'pending',
            })

        else:
            session.status = 'missed'
            session.save()

            user_group = f'user_{session.user.id}'
            async_to_sync(channel_layer.group_send)(
                user_group,
                {
                    'type': 'call_declined',
                    'session_id': str(session.id),
                    'message': 'No agents available right now. Please try again shortly.',
                }
            )

            return Response({
                'message': 'No agents available. User has been notified.',
                'status': 'missed',
            })


class CallSessionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        from .models import CallSession
        try:
            session = CallSession.objects.select_related('agent').get(id=session_id)
        except CallSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'session_id': str(session.id),
            'status': session.status,
            'meet_link': session.meet_link,
            'agent_name': f"{session.agent.first_name} {session.agent.last_name}" if session.agent else None,
        })


class AgentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        from .models import Agent
        new_status = request.data.get('status')
        if not new_status:
            return Response({'error': 'Status is required'}, status=400)

        try:
            agent = request.user.agent_profile
            agent.status = new_status
            agent.save()
            return Response({'message': 'Status updated', 'status': new_status})
        except Exception as e:
            print("AgentStatusView error:", e)
            return Response({'error': 'Agent profile not found'}, status=404)


class CallHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import CallSession, Agent
        try:
            try:
                agent = request.user.agent_profile
                sessions = CallSession.objects.filter(agent=agent).select_related('user').order_by('-created_at')
            except Exception as e:
                print("agent_profile lookup failed, trying Agent model directly:", e)
                agent = Agent.objects.get(email=request.user.email)
                sessions = CallSession.objects.filter(agent=agent).select_related('user').order_by('-created_at')

            total     = sessions.count()
            completed = sessions.filter(status='completed').count()
            missed    = sessions.filter(status='missed').count()

            data = [
                {
                    'id': str(s.id),
                    'user_name': getattr(s.user, 'fullname', None) or s.user.get_full_name() or s.user.email,
                    'status': s.status,
                    'created_at': s.created_at.isoformat(),
                    'meet_link': s.meet_link,
                }
                for s in sessions[:20]
            ]

            print(f"✅ History: found {total} sessions for agent {agent.id}")

            return Response({
                'sessions': data,
                'total': total,
                'completed': completed,
                'missed': missed,
            })
        except Exception as e:
            print("CallHistoryView error:", e)
            return Response({'sessions': [], 'total': 0, 'completed': 0, 'missed': 0})


class EndCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from .models import CallSession
        try:
            session = CallSession.objects.select_related('agent').get(id=session_id)
            session.status = 'completed'
            session.save()

            if session.agent:
                session.agent.status = 'available'
                session.agent.save(update_fields=['status'])

            return Response({'message': 'Call ended', 'status': 'completed'})
        except CallSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)


class CallEvaluationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from .models import CallSession, CallEvaluation

        try:
            session = CallSession.objects.select_related('user', 'agent').get(id=session_id)
        except CallSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=404)

        if hasattr(session, 'evaluation'):
            return Response({'error': 'This session has already been evaluated.'}, status=400)

        readiness_score = request.data.get('readiness_score', 0)
        recommendation  = request.data.get('recommendation', '')

        evaluation = CallEvaluation.objects.create(
            session=session,
            agent=session.agent,
            applicant=session.user,
            has_right_documents=request.data.get('has_right_documents'),
            meets_eligibility=request.data.get('meets_eligibility'),
            communication_score=request.data.get('communication_score'),
            understands_process=request.data.get('understands_process'),
            answered_satisfactorily=request.data.get('answered_satisfactorily'),
            recommendation=recommendation,
            readiness_score=readiness_score,
        )

        if session.status != 'completed':
            session.status = 'completed'
            session.save()

        is_positive = (recommendation == 'approve') and (readiness_score >= 50)

        applicant = session.user
        applicant_name = (
            getattr(applicant, 'fullname', None)
            or applicant.get_full_name()
            or applicant.email
        )

        channel_layer = get_channel_layer()
        user_group = f'user_{session.user_id}'

        async_to_sync(channel_layer.group_send)(
            user_group,
            {
                'type':            'evaluation_result',
                'session_id':      str(session.id),
                'is_positive':     is_positive,
                'readiness_score': readiness_score,
                'recommendation':  recommendation,
                'applicant_name':  applicant_name,
            }
        )

        return Response({
            'message': 'Evaluation saved successfully.',
            'evaluation_id': str(evaluation.id),
            'readiness_score': readiness_score,
            'is_positive': is_positive,
        }, status=201)


class ClientsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import CallSession, CallEvaluation
        try:
            agent = request.user.agent_profile
            sessions = CallSession.objects.filter(
                agent=agent
            ).select_related('user').order_by('-created_at')

            seen = set()
            clients = []
            for s in sessions:
                if s.user_id not in seen:
                    seen.add(s.user_id)
                    u = s.user
                    eval_obj = None
                    try:
                        eval_obj = s.evaluation
                    except:
                        pass

                    # ✅ Get the latest application ID for this client
                    latest_app = App.objects.filter(user=u).order_by('-submitted_at').first()

                    clients.append({
                        'id': u.id,
                        'name': u.get_full_name() or u.email,
                        'email': u.email,
                        'phone': getattr(u, 'phone', ''),
                        'country': getattr(u, 'country', ''),
                        'total_calls': sessions.filter(user=u).count(),
                        'last_call': s.created_at.isoformat(),
                        'last_status': s.status,
                        'readiness_score': eval_obj.readiness_score if eval_obj else None,
                        'recommendation': eval_obj.recommendation if eval_obj else None,
                        'latest_application_id': latest_app.id if latest_app else None,  # ✅ NEW
                    })

            return Response({'clients': clients, 'total': len(clients)})
        except Exception as e:
            print('ClientsListView error:', e)
            return Response({'clients': [], 'total': 0})


class ClientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from .models import CallSession, CallEvaluation
        try:
            agent = request.user.agent_profile
            user = User.objects.get(id=user_id)

            sessions = CallSession.objects.filter(
                agent=agent, user=user
            ).order_by('-created_at')

            session_data = []
            for s in sessions:
                eval_obj = None
                try:
                    eval_obj = s.evaluation
                except:
                    pass
                session_data.append({
                    'id': str(s.id),
                    'status': s.status,
                    'meet_link': s.meet_link,
                    'created_at': s.created_at.isoformat(),
                    'readiness_score': eval_obj.readiness_score if eval_obj else None,
                    'recommendation': eval_obj.recommendation if eval_obj else None,
                })

            # ✅ Get the latest application ID for this client
            latest_app = App.objects.filter(user=user).order_by('-submitted_at').first()

            return Response({
                'id': user.id,
                'name': user.get_full_name() or user.email,
                'email': user.email,
                'phone': getattr(user, 'phone', ''),
                'country': getattr(user, 'country', ''),
                'date_joined': user.date_joined.isoformat(),
                'sessions': session_data,
                'total_calls': sessions.count(),
                'completed_calls': sessions.filter(status='completed').count(),
                'latest_application_id': latest_app.id if latest_app else None,  # ✅ NEW
            })
        except Exception as e:
            print('ClientDetailView error:', e)
            return Response({'error': str(e)}, status=404)


class UnlockChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from .models import CallSession
        from applications.models import Application

        try:
            session = CallSession.objects.select_related('user').get(id=session_id)
        except CallSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=404)

        application = Application.objects.filter(
            user=session.user,
            status__in=['started', 'processing']
        ).order_by('-submitted_at').first()

        if not application:
            return Response({'error': 'No active application found for this client.'}, status=404)

        if application.meeting_status == 'completed':
            return Response({'message': 'Chat already unlocked.'}, status=200)

        application.meeting_status = 'completed'
        application.status = 'processing'
        application.save()

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{session.user.id}',
            {
                'type': 'chat_unlocked',
                'message': 'Your chat has been unlocked by your consultant!',
            }
        )

        return Response({
            'message': 'Chat unlocked successfully!',
            'application_id': application.id,
            'meeting_status': 'completed',
        }, status=200)
    
class AgentsListView(APIView):
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        from .models import Agent
        agents = Agent.objects.all().select_related('user')
        return Response({
            'agents': [
                {
                    'id': a.id,
                    'full_name': f"{a.user.first_name} {a.user.last_name}".strip() or a.user.username,
                    'email': a.user.email,
                    'phone': a.user.phone if hasattr(a.user, 'phone') else '',
                    'status': a.status,
                    'created_at': a.user.date_joined,
                }
                for a in agents
            ]
        })

class AgentStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, agent_id, **kwargs):
        from .models import Agent
        try:
            agent = Agent.objects.get(id=agent_id)
            new_status = 'approved' if 'approved' in request.path else 'rejected'
            agent.status = new_status
            agent.is_active = (new_status == 'approved')
            agent.save()

            # 👇 Notify the agent via WebSocket
            if agent.user:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'user_{agent.user.id}',
                    {
                        'type': 'agent_approved',
                        'message': 'Your application has been approved!',
                        'status': new_status,
                    }
                )

            return Response({'message': f'Agent {new_status} successfully'})
        except Agent.DoesNotExist:
            return Response({'error': 'Agent not found'}, status=404)