# reviews/views.py
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg, Count, Q
from .models import Review
from .serializers import ReviewSerializer, ReviewListSerializer, PackageRatingSerializer
from packages.models import Package
from .models import SPReview
from providers.models import ServiceProvider


class ReviewListView(generics.ListAPIView):
    """
    GET /api/reviews/?package_id=1
    Get all reviews for a specific package
    Anyone can view reviews (no login required)
    """
    serializer_class = ReviewListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        package_id = self.request.query_params.get('package_id')
        if package_id:
            return Review.objects.filter(package_id=package_id).select_related('user')
        return Review.objects.all().select_related('user')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'reviews': serializer.data,
            'count': queryset.count(),
            'message': 'Reviews retrieved successfully!'
        }, status=status.HTTP_200_OK)


class ReviewCreateView(APIView):
    """
    POST /api/reviews/create/
    Create a review (must be logged in)
    
    Body: {
        "package_id": 1,
        "rating": 5,
        "comment": "Great service!"
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        package_id = request.data.get('package_id')
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')
        
        # Validate required fields
        if not package_id or not rating:
            return Response({
                'error': 'package_id and rating are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate rating range
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return Response({
                    'error': 'Rating must be between 1 and 5'
                }, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({
                'error': 'Rating must be a number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if package exists
        try:
            package = Package.objects.get(id=package_id, is_active=True)
        except Package.DoesNotExist:
            return Response({
                'error': 'Package not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user already reviewed this package
        if Review.objects.filter(user=request.user, package=package).exists():
            return Response({
                'error': 'You have already reviewed this package'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create review
        review = Review.objects.create(
            user=request.user,
            package=package,
            rating=rating,
            comment=comment
        )
        
        serializer = ReviewSerializer(review)
        
        return Response({
            'review': serializer.data,
            'message': 'Review submitted successfully!'
        }, status=status.HTTP_201_CREATED)


class ReviewUpdateView(APIView):
    """
    PUT /api/reviews/<id>/
    Update your own review (must be logged in and owner)
    
    Body: {
        "rating": 4,
        "comment": "Updated review"
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request, id):
        try:
            review = Review.objects.get(id=id, user=request.user)
        except Review.DoesNotExist:
            return Response({
                'error': 'Review not found or you are not the owner'
            }, status=status.HTTP_404_NOT_FOUND)
        
        rating = request.data.get('rating')
        comment = request.data.get('comment')
        
        # Update rating if provided
        if rating:
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    return Response({
                        'error': 'Rating must be between 1 and 5'
                    }, status=status.HTTP_400_BAD_REQUEST)
                review.rating = rating
            except ValueError:
                return Response({
                    'error': 'Rating must be a number'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update comment if provided
        if comment is not None:
            review.comment = comment
        
        review.save()
        serializer = ReviewSerializer(review)
        
        return Response({
            'review': serializer.data,
            'message': 'Review updated successfully!'
        }, status=status.HTTP_200_OK)


class ReviewDeleteView(APIView):
    """
    DELETE /api/reviews/<id>/
    Delete your own review (must be logged in and owner)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, id):
        try:
            review = Review.objects.get(id=id, user=request.user)
            review.delete()
            
            return Response({
                'message': 'Review deleted successfully!'
            }, status=status.HTTP_200_OK)
        
        except Review.DoesNotExist:
            return Response({
                'error': 'Review not found or you are not the owner'
            }, status=status.HTTP_404_NOT_FOUND)


class PackageRatingView(APIView):
    """
    GET /api/reviews/rating/?package_id=1
    Get average rating and star breakdown for a package
    Anyone can view (no login required)
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        package_id = request.query_params.get('package_id')
        
        if not package_id:
            return Response({
                'error': 'package_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if package exists
        try:
            package = Package.objects.get(id=package_id, is_active=True)
        except Package.DoesNotExist:
            return Response({
                'error': 'Package not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get reviews for this package
        reviews = Review.objects.filter(package=package)
        
        # Calculate average rating
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Count reviews by star rating
        rating_counts = {
            'five_star': reviews.filter(rating=5).count(),
            'four_star': reviews.filter(rating=4).count(),
            'three_star': reviews.filter(rating=3).count(),
            'two_star': reviews.filter(rating=2).count(),
            'one_star': reviews.filter(rating=1).count(),
        }
        
        data = {
            'average_rating': round(avg_rating, 1),
            'total_reviews': reviews.count(),
            **rating_counts
        }
        
        serializer = PackageRatingSerializer(data)
        
        return Response({
            'rating_summary': serializer.data,
            'message': 'Package rating retrieved successfully!'
        }, status=status.HTTP_200_OK)

class SPReviewListView(APIView):
    """
    GET /api/reviews/sp/?provider_id=<id>
    Get all reviews for a specific SP
    Anyone can view
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({'error': 'provider_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            provider = ServiceProvider.objects.get(id=provider_id)
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'Service provider not found'}, status=404)

        reviews = SPReview.objects.filter(provider=provider).select_related('user')

        # Calculate average rating
        from django.db.models import Avg
        avg = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

        data = [
            {
                'id': str(r.id),
                'user_name': r.user.get_full_name() or r.user.email,
                'rating': r.rating,
                'comment': r.comment,
                'created_at': r.created_at.isoformat(),
            }
            for r in reviews
        ]

        return Response({
            'reviews': data,
            'count': reviews.count(),
            'average_rating': round(avg, 1),
        })


class SPReviewCreateView(APIView):
    """
    POST /api/reviews/sp/create/
    User rates an SP after a completed call
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from calls.models import CallSession

        provider_id = request.data.get('provider_id')
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')

        if not provider_id or not rating:
            return Response({'error': 'provider_id and rating are required'}, status=400)

        # Validate rating
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return Response({'error': 'Rating must be between 1 and 5'}, status=400)
        except ValueError:
            return Response({'error': 'Rating must be a number'}, status=400)

        # Check SP exists
        try:
            provider = ServiceProvider.objects.get(id=provider_id)
        except ServiceProvider.DoesNotExist:
            return Response({'error': 'Service provider not found'}, status=404)

        # Check user had a completed call with this SP
        had_call = CallSession.objects.filter(
            user=request.user,
            service_provider=provider,
            status='completed'
        ).exists()

        if not had_call:
            return Response(
                {'error': 'You can only rate an SP after a completed call with them.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if already reviewed
        if SPReview.objects.filter(user=request.user, provider=provider).exists():
            return Response({'error': 'You have already reviewed this service provider.'}, status=400)

        review = SPReview.objects.create(
            user=request.user,
            provider=provider,
            rating=rating,
            comment=comment
        )

        return Response({
            'message': 'Review submitted successfully!',
            'review': {
                'id': str(review.id),
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.isoformat(),
            }
        }, status=201)


class SPReviewDeleteView(APIView):
    """
    DELETE /api/reviews/sp/<id>/
    User deletes their own SP review
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, id):
        try:
            review = SPReview.objects.get(id=id, user=request.user)
            review.delete()
            return Response({'message': 'Review deleted successfully!'})
        except SPReview.DoesNotExist:
            return Response({'error': 'Review not found or you are not the owner.'}, status=404)