from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import ServiceProvider
from .serializers import SPRegistrationSerializer, SPProfileSerializer



from notifications.utils import send_notification  # 👈 ADD THIS

class SPRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if ServiceProvider.objects.filter(user=request.user).exists():
            sp = ServiceProvider.objects.get(user=request.user)
            return Response({
                'error': 'You already have an SP application.',
                'status': sp.status,
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = SPRegistrationSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            sp = serializer.save()

            # 🔥🔥 ADD THIS BLOCK
            send_notification(
                user=request.user,
                type='sp_application_received',
                title='Application Received',
                message='Your service provider application has been received and is under review.',
                data={'provider_id': str(sp.id)}
            )

            return Response({
                'message': 'Application submitted successfully. We will be in touch shortly.',
                'status': sp.status,
                'id': str(sp.id),
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SPApplicationStatusView(APIView):
    """
    User checks their SP application status.
    GET /providers/status/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sp = ServiceProvider.objects.get(user=request.user)
            return Response({
                'has_application': True,
                'status': sp.status,
                'is_active': sp.is_active,
                'verification_call_scheduled': sp.verification_call_scheduled,
                'rejection_reason': sp.rejection_reason if sp.status == 'rejected' else None,
                'business_name': sp.business_name,
            })
        except ServiceProvider.DoesNotExist:
            return Response({
                'has_application': False,
                'status': None,
            })


class SPProfileView(APIView):
    """
    Approved SP views and updates their profile.
    GET  /providers/profile/
    PATCH /providers/profile/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sp = ServiceProvider.objects.get(user=request.user)
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'No SP profile found.'}, status=404)

        serializer = SPProfileSerializer(sp)
        return Response(serializer.data)

    def patch(self, request):
        try:
            sp = ServiceProvider.objects.get(user=request.user)
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'No SP profile found.'}, status=404)

        # Only approved SPs can update their profile
        if sp.status != 'approved':
            return Response({
                'error': 'Only approved service providers can update their profile.'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = SPProfileSerializer(sp, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class AdminSPListView(APIView):
    """
    Admin sees all SP applications
    GET /api/providers/admin/list/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get('status', None)
        providers = ServiceProvider.objects.select_related('user').all()

        if status_filter:
            providers = providers.filter(status=status_filter)

        data = [
            {
                'id': str(sp.id),
                'business_name': sp.business_name,
                'business_type': sp.business_type,
                'email': sp.user.email if sp.user else '',
                'phone': sp.phone or '',
                'country': sp.country or '',
                'status': sp.status,
                'is_active': sp.is_active,
                'verification_call_scheduled': sp.verification_call_scheduled,
                'rejection_reason': sp.rejection_reason,
                'created_at': sp.created_at.isoformat(),
            }
            for sp in providers
        ]

        return Response({
            'providers': data,
            'total': len(data),
            'pending': providers.filter(status='pending').count(),
            'approved': providers.filter(status='approved').count(),
            'rejected': providers.filter(status='rejected').count(),
        })

class AdminSPScheduleCallView(APIView):
    """
    Admin schedules verification call for an SP
    POST /api/providers/admin/<provider_id>/schedule-call/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, provider_id):
        try:
            provider = ServiceProvider.objects.select_related('user').get(id=provider_id)
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'Service provider not found.'}, status=404)

        if provider.verification_call_scheduled:
            return Response({'message': 'Verification call already scheduled.'}, status=400)

        provider.verification_call_scheduled = True
        provider.save(update_fields=['verification_call_scheduled'])

        if provider.user:
            from notifications.utils import send_notification
            send_notification(
                user=provider.user,
                type='sp_call_scheduled',
                title='Verification Call Scheduled',
                message='Your verification call has been scheduled. Please be available.',
                data={'provider_id': str(provider.id)}
            )

        return Response({
            'message': f'Verification call scheduled for {provider.business_name}.',
            'verification_call_scheduled': True,
        })


class AdminSPApproveRejectView(APIView):
    """
    Admin approves or rejects an SP after verification call
    POST /api/providers/admin/<provider_id>/approve/
    POST /api/providers/admin/<provider_id>/reject/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, provider_id, action):
        if action not in ('approve', 'reject'):
            return Response({'error': 'Invalid action. Use approve or reject.'}, status=400)

        try:
            provider = ServiceProvider.objects.select_related('user').get(id=provider_id)
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'Service provider not found.'}, status=404)

        if action == 'approve':
            provider.status = 'approved'
            provider.is_active = True
            provider.rejection_reason = None
            message = 'Your service provider application has been approved! You can now start creating packages and accepting calls.'
        else:
            rejection_reason = request.data.get('rejection_reason', 'Your application did not meet our requirements.')
            provider.status = 'rejected'
            provider.is_active = False
            provider.rejection_reason = rejection_reason
            message = f'Your service provider application has been rejected. Reason: {rejection_reason}'

        provider.save()

        if provider.user:
            from notifications.utils import send_notification
            send_notification(
                user=provider.user,
                type='sp_approved' if action == 'approve' else 'sp_rejected',
                title='Application Approved!' if action == 'approve' else 'Application Rejected',
                message=message,
                data={'provider_id': str(provider.id)}
            )

        return Response({
            'message': f'Service provider {action}d successfully.',
            'status': provider.status,
            'is_active': provider.is_active,
        })
    
class SPPublicProfileView(APIView):
    """
    Anyone can view an SP's public profile
    GET /api/providers/<provider_id>/profile/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, provider_id):
        try:
            provider = ServiceProvider.objects.select_related('user').get(
                id=provider_id,
                status='approved',
                is_active=True
            )
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'Service provider not found.'}, status=404)

        # Get their packages
        from packages.models import Package
        packages = Package.objects.filter(
            service_provider=provider,
            is_active=True
        ).prefetch_related('images')

        from packages.serializers import PackageListSerializer
        packages_data = PackageListSerializer(packages, many=True).data

        # Get call stats
        from calls.models import CallSession
        completed_calls = CallSession.objects.filter(
            service_provider=provider,
            status='completed'
        ).count()

        total_clients = CallSession.objects.filter(
            service_provider=provider
        ).values('user').distinct().count()

        # Get ratings
        from django.db.models import Avg
        from reviews.models import SPReview
        reviews = SPReview.objects.filter(provider=provider).select_related('user')
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

        recent_reviews = [
            {
                'id': str(r.id),
                'user_name': r.user.get_full_name() or r.user.email,
                'rating': r.rating,
                'comment': r.comment,
                'created_at': r.created_at.isoformat(),
            }
            for r in reviews[:5]  # latest 5 reviews
        ]

        rating_breakdown = {
            'five_star':  reviews.filter(rating=5).count(),
            'four_star':  reviews.filter(rating=4).count(),
            'three_star': reviews.filter(rating=3).count(),
            'two_star':   reviews.filter(rating=2).count(),
            'one_star':   reviews.filter(rating=1).count(),
        }

        return Response({
            'id': str(provider.id),
            'business_name': provider.business_name,
            'business_type': provider.business_type,
            'bio': provider.bio,
            'country': provider.country,
            'phone': provider.phone,
            'profile_picture': provider.profile_picture.url if provider.profile_picture else None,
            'packages': packages_data,
            'stats': {
                'completed_calls': completed_calls,
                'total_clients': total_clients,
                'total_packages': packages.count(),
            },
            'ratings': {
                'average': round(avg_rating, 1),
                'total_reviews': reviews.count(),
                'breakdown': rating_breakdown,
                'recent_reviews': recent_reviews,
            }
        })