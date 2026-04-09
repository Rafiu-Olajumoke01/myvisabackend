# bookmarks/views.py
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Bookmark
from .serializers import BookmarkSerializer, BookmarkListSerializer
from packages.models import Package


class BookmarkListView(generics.ListAPIView):
    """
    GET /api/bookmarks/
    Get all saved packages for the logged-in user
    """
    serializer_class = BookmarkListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only return bookmarks for the current user
        return Bookmark.objects.filter(user=self.request.user).select_related('package')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'bookmarks': serializer.data,
            'count': queryset.count(),
            'message': 'Saved packages retrieved successfully!'
        }, status=status.HTTP_200_OK)


class BookmarkCreateView(APIView):
    """
    POST /api/bookmarks/
    Save a package (add to bookmarks)
    
    Body: { "package_id": 1 }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        package_id = request.data.get('package_id')
        
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
        
        # Check if already bookmarked
        if Bookmark.objects.filter(user=request.user, package=package).exists():
            return Response({
                'error': 'Package already saved'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create bookmark
        bookmark = Bookmark.objects.create(user=request.user, package=package)
        serializer = BookmarkSerializer(bookmark)
        
        return Response({
            'bookmark': serializer.data,
            'message': 'Package saved successfully!'
        }, status=status.HTTP_201_CREATED)


class BookmarkDeleteView(APIView):
    """
    DELETE /api/bookmarks/<package_id>/
    Remove a package from saved (unsave)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, package_id):
        try:
            bookmark = Bookmark.objects.get(user=request.user, package_id=package_id)
            bookmark.delete()
            
            return Response({
                'message': 'Package removed from saved!'
            }, status=status.HTTP_200_OK)
        
        except Bookmark.DoesNotExist:
            return Response({
                'error': 'Bookmark not found'
            }, status=status.HTTP_404_NOT_FOUND)
