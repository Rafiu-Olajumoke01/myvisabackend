from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Influencer, InfluencerBooking
from .serializers import (
    InfluencerSerializer,
    InfluencerApplySerializer,
    InfluencerBookingSerializer,
)


class InfluencerApplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Check if already applied
        if hasattr(request.user, 'influencer_profile'):
            inf = request.user.influencer_profile
            return Response({
                'has_application': True,
                'status': inf.status,
                'promo_code': inf.promo_code if inf.status == 'approved' else None,
            }, status=status.HTTP_200_OK)

        serializer = InfluencerApplySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
                'message': 'Application submitted successfully!',
                'has_application': True,
                'status': 'pending',
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InfluencerStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'influencer_profile'):
            return Response({'has_application': False}, status=status.HTTP_200_OK)

        inf = request.user.influencer_profile
        return Response({
            'has_application': True,
            'status': inf.status,
            'promo_code': inf.promo_code if inf.status == 'approved' else None,
            'rejection_reason': inf.rejection_reason,
        })


class InfluencerDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'influencer_profile'):
            return Response({'error': 'Not an influencer'}, status=status.HTTP_403_FORBIDDEN)

        inf = request.user.influencer_profile
        if inf.status != 'approved':
            return Response({'error': 'Not approved yet'}, status=status.HTTP_403_FORBIDDEN)

        bookings = inf.bookings.all()
        serializer = InfluencerSerializer(inf)

        return Response({
            'influencer': serializer.data,
            'bookings': InfluencerBookingSerializer(bookings, many=True).data,
            'stats': {
                'promo_code': inf.promo_code,
                'confirmed_earnings': float(inf.confirmed_earnings),
                'pending_earnings': float(inf.pending_earnings),
                'total_bookings': inf.total_bookings,
                'conversion_rate': 68,  # TODO: calculate real conversion rate
            }
        })


class AdminInfluencerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
        influencers = Influencer.objects.all()
        serializer = InfluencerSerializer(influencers, many=True)
        return Response({'influencers': serializer.data})


class AdminInfluencerApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
        try:
            inf = Influencer.objects.get(pk=pk)
            inf.status = 'approved'
            inf.rejection_reason = None
            inf.save()
            return Response({'message': 'Influencer approved!', 'promo_code': inf.promo_code})
        except Influencer.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


class AdminInfluencerRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
        try:
            inf = Influencer.objects.get(pk=pk)
            inf.status = 'rejected'
            inf.rejection_reason = request.data.get('reason', '')
            inf.save()
            return Response({'message': 'Influencer rejected'})
        except Influencer.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)