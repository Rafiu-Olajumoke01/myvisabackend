# reviews/views.py
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Avg, Count, Q
from .models import Review
from .serializers import ReviewSerializer, ReviewListSerializer, PackageRatingSerializer
from packages.models import Package


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
