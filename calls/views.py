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
from notifications.utils import send_notification

User = get_user_model()


def generate_meet_link():
    def part(n):
        return ''.join(random.choices(string.ascii_lowercase, k=n))
    room = f"myvisa-{part(4)}-{part(4)}-{part(4)}"
    return f"https://meet.jit.si/{room}"


class AvailableProvidersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from providers.models import ServiceProvider
        providers = ServiceProvider.objects.filter(availability='available', is_active=True)
        data = [
            {
                'id': str(sp.id),
                'name': sp.business_name,
                'availability': sp.availability,
                'business_type': sp.business_type,
            }
            for sp in providers
        ]
        return Response({'providers': data, 'count': len(data)})


class RequestCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from providers.models import ServiceProvider
        from .models import CallSession
        providers = ServiceProvider.objects.filter(
            availability='available',
            is_active=True,
            status='approved'
        ).order_by('updated_at')

        if not providers.exists():
            return Response(
                {'error': 'No service providers available right now. Please try again in a few minutes.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        provider = providers.first()
        session = CallSession.objects.create(
            user=request.user,
            service_provider=provider,
            status='pending'
        )

        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)('providers_room', {
                    'type': 'call_request',
                    'session_id': str(session.id),
                    'user_id': str(request.user.id),
                    'user_name': getattr(request.user, 'fullname', None) or request.user.get_full_name() or request.user.email,
                    'package': request.data.get('package', 'Discovery Call'),
                })
        except Exception as e:
            print(f"WebSocket notify failed: {e}")

        return Response(
            {'session_id': str(session.id), 'message': 'Call request sent.', 'status': 'pending'},
            status=status.HTTP_201_CREATED
        )


class AcceptCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from providers.models import ServiceProvider
        from .models import CallSession
        from django.db import transaction
        try:
            with transaction.atomic():
                session = CallSession.objects.select_for_update().get(id=session_id)
                if session.status != 'pending':
                    return Response(
                        {'error': 'Session not found or already handled.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                try:
                    provider = request.user.sp_profile
                except Exception:
                    return Response({'error': 'Service provider profile not found.'}, status=404)

                meet_link = generate_meet_link()
                session.status = 'accepted'
                session.meet_link = meet_link
                session.service_provider = provider
                session.save()

                provider.availability = 'busy'
                provider.save(update_fields=['availability'])

        except CallSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Notify user
        send_notification(
            user=session.user,
            type='call_accepted',
            title='Call Accepted',
            message=f'{provider.business_name} has accepted your call request.',
            data={'session_id': str(session.id), 'meet_link': meet_link}
        )

        return Response({
            'session_id': str(session.id),
            'meet_link': meet_link,
            'status': 'accepted'
        })


class DeclineCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from providers.models import ServiceProvider
        from .models import CallSession, CallDecline
        try:
            session = CallSession.objects.select_related('user').get(id=session_id, status='pending')
        except CallSession.DoesNotExist:
            return Response(
                {'error': 'Session not found or already handled.'},
                status=status.HTTP_404_NOT_FOUND
            )

        CallDecline.objects.create(
            session=session,
            service_provider=session.service_provider,
            reason=request.data.get('reason', 'No reason provided')
        )

        declined_provider_ids = session.declines.values_list('service_provider_id', flat=True)
        next_provider = ServiceProvider.objects.filter(
            availability='available',
            is_active=True,
            status='approved'
        ).exclude(id__in=declined_provider_ids).order_by('updated_at').first()

        try:
            channel_layer = get_channel_layer()
            if next_provider:
                session.service_provider = next_provider
                session.status = 'pending'
                session.save()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)('providers_room', {
                        'type': 'call_request',
                        'session_id': str(session.id),
                        'user_id': str(session.user.id),
                        'user_name': getattr(session.user, 'fullname', None) or session.user.get_full_name() or session.user.email,
                        'package': 'Discovery Call',
                    })
                return Response({
                    'message': 'Call rerouted.',
                    'session_id': str(session.id),
                    'status': 'pending'
                })
            else:
                session.status = 'missed'
                session.save()

                # Notify user no providers available
                send_notification(
                    user=session.user,
                    type='call_declined',
                    title='No Providers Available',
                    message='No service providers are available right now. Please try again later.',
                    data={'session_id': str(session.id)}
                )

                return Response({'message': 'No providers available.', 'status': 'missed'})
        except Exception as e:
            print(f"WebSocket notify failed: {e}")
            return Response({'message': 'Handled.', 'status': session.status})


class CallSessionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        from .models import CallSession
        try:
            session = CallSession.objects.select_related('service_provider').get(id=session_id)
        except CallSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'session_id': str(session.id),
            'status': session.status,
            'meet_link': session.meet_link,
            'provider_name': session.service_provider.business_name if session.service_provider else None,
        })


class ProviderAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        new_availability = request.data.get('availability')
        if not new_availability:
            return Response({'error': 'Availability is required'}, status=400)
        if new_availability not in ('available', 'offline', 'busy'):
            return Response({'error': 'Invalid availability value'}, status=400)
        try:
            provider = request.user.sp_profile
            provider.availability = new_availability
            provider.save(update_fields=['availability'])
            return Response({'message': 'Availability updated', 'availability': new_availability})
        except Exception as e:
            print("ProviderAvailabilityView error:", e)
            return Response({'error': 'Service provider profile not found'}, status=404)


class CallHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import CallSession
        try:
            provider = request.user.sp_profile
            sessions = CallSession.objects.filter(
                service_provider=provider
            ).select_related('user').order_by('-created_at')

            total = sessions.count()
            data = [
                {
                    'id': str(s.id),
                    'user_name': getattr(s.user, 'fullname', None) or s.user.get_full_name() or s.user.email,
                    'status': s.status,
                    'created_at': s.created_at.isoformat(),
                    'meet_link': s.meet_link
                }
                for s in sessions[:20]
            ]
            return Response({
                'sessions': data,
                'total': total,
                'completed': sessions.filter(status='completed').count(),
                'missed': sessions.filter(status='missed').count()
            })
        except Exception as e:
            print("CallHistoryView error:", e)
            return Response({'sessions': [], 'total': 0, 'completed': 0, 'missed': 0})


class EndCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from .models import CallSession
        try:
            session = CallSession.objects.select_related('service_provider').get(id=session_id)
            session.status = 'completed'
            session.save()

            if session.service_provider:
                session.service_provider.availability = 'available'
                session.service_provider.save(update_fields=['availability'])

            return Response({'message': 'Call ended', 'status': 'completed'})
        except CallSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)


class CallEvaluationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        from .models import CallSession, CallEvaluation
        try:
            session = CallSession.objects.select_related('user', 'service_provider').get(id=session_id)
        except CallSession.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=404)

        if hasattr(session, 'evaluation'):
            return Response({'error': 'Already evaluated.'}, status=400)

        readiness_score = request.data.get('readiness_score', 0)
        recommendation = request.data.get('recommendation', '')

        evaluation = CallEvaluation.objects.create(
            session=session,
            service_provider=session.service_provider,
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

        # Notify user of evaluation result
        send_notification(
            user=session.user,
            type='evaluation_submitted',
            title='Your Evaluation is Ready',
            message=f'Your readiness score is {readiness_score}%. Recommendation: {recommendation}.',
            data={
                'session_id': str(session.id),
                'readiness_score': readiness_score,
                'recommendation': recommendation,
                'is_positive': is_positive,
            }
        )

        return Response({
            'message': 'Evaluation saved.',
            'evaluation_id': str(evaluation.id),
            'readiness_score': readiness_score,
            'is_positive': is_positive
        }, status=201)


class ClientsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import CallSession
        try:
            provider = request.user.sp_profile
            sessions = CallSession.objects.filter(
                service_provider=provider
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
                    except Exception:
                        pass
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
                        'latest_application_id': latest_app.id if latest_app else None,
                    })
            return Response({'clients': clients, 'total': len(clients)})
        except Exception as e:
            print('ClientsListView error:', e)
            return Response({'clients': [], 'total': 0})


class ClientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from .models import CallSession
        try:
            provider = request.user.sp_profile
            user = User.objects.get(id=user_id)
            sessions = CallSession.objects.filter(
                service_provider=provider,
                user=user
            ).order_by('-created_at')

            session_data = []
            for s in sessions:
                eval_obj = None
                try:
                    eval_obj = s.evaluation
                except Exception:
                    pass
                session_data.append({
                    'id': str(s.id),
                    'status': s.status,
                    'meet_link': s.meet_link,
                    'created_at': s.created_at.isoformat(),
                    'readiness_score': eval_obj.readiness_score if eval_obj else None,
                    'recommendation': eval_obj.recommendation if eval_obj else None
                })

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
                'latest_application_id': latest_app.id if latest_app else None,
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
            return Response({'error': 'No active application found.'}, status=404)

        if application.meeting_status == 'completed':
            return Response({'message': 'Chat already unlocked.'}, status=200)

        application.meeting_status = 'completed'
        application.status = 'processing'
        application.save()

        # Notify user chat is unlocked
        send_notification(
            user=session.user,
            type='application_status_update',
            title='Chat Unlocked!',
            message='Your chat has been unlocked. You can now message your consultant.',
            data={'application_id': application.id, 'session_id': str(session.id)}
        )

        return Response({
            'message': 'Chat unlocked!',
            'application_id': application.id,
            'meeting_status': 'completed'
        }, status=200)


class ProvidersListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from providers.models import ServiceProvider
        providers = ServiceProvider.objects.all()
        return Response({
            'providers': [
                {
                    'id': str(sp.id),
                    'business_name': sp.business_name,
                    'business_type': sp.business_type,
                    'email': sp.user.email if sp.user else '',
                    'phone': sp.phone or '',
                    'status': sp.status,
                    'availability': sp.availability,
                    'is_active': sp.is_active,
                    'country': sp.country or '',
                    'created_at': sp.created_at.isoformat(),
                }
                for sp in providers
            ]
        })


class ProviderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, provider_id, action, **kwargs):
        from providers.models import ServiceProvider
        if action not in ('approved', 'rejected'):
            return Response({'error': 'Invalid action.'}, status=400)
        try:
            provider = ServiceProvider.objects.get(id=provider_id)
            provider.status = action
            provider.is_active = (action == 'approved')
            if action == 'approved':
                provider.availability = 'available'
            provider.save()

            if provider.user:
                send_notification(
                    user=provider.user,
                    type='sp_approved' if action == 'approved' else 'sp_rejected',
                    title='Application Approved!' if action == 'approved' else 'Application Rejected',
                    message='Your application has been approved!' if action == 'approved' else 'Your application was rejected.',
                    data={'provider_id': str(provider.id)}
                )

            return Response({
                'message': f'Service provider {action} successfully',
                'status': action
            })
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'Service provider not found'}, status=404)