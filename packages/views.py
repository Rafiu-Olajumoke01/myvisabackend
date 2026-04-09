# packages/views.py
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from .models import Package, PackageImage
from .serializers import PackageListSerializer, PackageDetailSerializer


class PackageListView(generics.ListAPIView):
    """
    GET /api/packages/
    List all active packages with filtering and search
    
    Query Parameters:
    - search: Search by country or title (e.g., ?search=canada)
    - visa_type: Filter by visa type (e.g., ?visa_type=Student)
    - min_price: Minimum price (e.g., ?min_price=1000)
    - max_price: Maximum price (e.g., ?max_price=5000)
    - ordering: Sort by price (e.g., ?ordering=price or ?ordering=-price)
    """
    serializer_class = PackageListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Package.objects.filter(is_active=True).prefetch_related('images')
        
        # ─── SEARCH (by country or title) ────────────────────────────────
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(country__icontains=search) | Q(title__icontains=search)
            )
        
        # ─── FILTER BY VISA TYPE ─────────────────────────────────────────
        visa_type = self.request.query_params.get('visa_type', None)
        if visa_type:
            queryset = queryset.filter(visa_type__icontains=visa_type)
        
        # ─── FILTER BY PRICE RANGE ───────────────────────────────────────
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # ─── ORDERING (sort by price) ────────────────────────────────────
        ordering = self.request.query_params.get('ordering', '-created_at')
        valid_orderings = ['price', '-price', 'created_at', '-created_at']
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'packages': serializer.data,
            'count': queryset.count(),
            'message': 'Packages retrieved successfully!'
        }, status=status.HTTP_200_OK)


class PackageDetailView(generics.RetrieveAPIView):
    """
    GET /api/packages/<id>/
    Get single package with all images (for detail page with carousel)
    """
    queryset = Package.objects.filter(is_active=True).prefetch_related('images')
    serializer_class = PackageDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'package': serializer.data,
            'message': 'Package details retrieved successfully!'
        }, status=status.HTTP_200_OK)


# ============================================
# ADMIN ENDPOINTS - NO AUTHENTICATION NEEDED
# Security: Protected by secret/complex URL
# ============================================

class AdminPackageListCreateView(generics.ListCreateAPIView):
    """
    GET /api/packages/admin/
    List ALL packages (including inactive) for admin
    
    POST /api/packages/admin/
    Create new package with images
    
    🔓 NO AUTHENTICATION - URL is secret!
    
    Request body (multipart/form-data):
    - title: string (required)
    - country: string (required)
    - visa_type: string (required)
    - price: decimal (required)
    - processing_time: string (optional)
    - description: text (optional)
    - requirements: text (optional)
    - is_active: boolean (default: true)
    - images: file[] (multiple images, max 20)
    """
    serializer_class = PackageDetailSerializer
    permission_classes = [permissions.AllowAny]  # ✅ CHANGED: No auth needed
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        # Return ALL packages for admin (including inactive)
        queryset = Package.objects.all().prefetch_related('images')
        
        # Apply same filters as public view
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(country__icontains=search) | Q(title__icontains=search)
            )
        
        visa_type = self.request.query_params.get('visa_type', None)
        if visa_type:
            queryset = queryset.filter(visa_type__icontains=visa_type)
        
        ordering = self.request.query_params.get('ordering', '-created_at')
        valid_orderings = ['price', '-price', 'created_at', '-created_at']
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'packages': serializer.data,
            'count': queryset.count(),
            'message': 'Admin packages retrieved successfully!'
        }, status=status.HTTP_200_OK)
    
    def create(self, request, *args, **kwargs):
        # Extract images from request
        images = request.FILES.getlist('images')
        
        # Validate image count (max 20)
        if len(images) > 20:
            return Response({
                'error': 'Maximum 20 images allowed per package'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(images) == 0:
            return Response({
                'error': 'At least one image is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create package
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        package = serializer.save()
        
        # Create package images
        for image in images:
            PackageImage.objects.create(package=package, image=image)
        
        # Return created package with images
        response_serializer = self.get_serializer(package)
        return Response({
            'package': response_serializer.data,
            'message': 'Package created successfully!'
        }, status=status.HTTP_201_CREATED)


class AdminPackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/packages/admin/<id>/
    Retrieve single package (admin can see inactive)
    
    PUT /api/packages/admin/<id>/
    Update package
    
    DELETE /api/packages/admin/<id>/
    Delete package
    
    🔓 NO AUTHENTICATION - URL is secret!
    """
    queryset = Package.objects.all().prefetch_related('images')
    serializer_class = PackageDetailSerializer
    permission_classes = [permissions.AllowAny]  # ✅ CHANGED: No auth needed
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Handle images if provided
        images = request.FILES.getlist('images')
        
        # Update package fields
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        package = serializer.save()
        
        # If new images are provided, add them (don't replace old ones unless specified)
        if images:
            if len(images) > 20:
                return Response({
                    'error': 'Maximum 20 images allowed per package'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Option 1: Add new images without deleting old ones
            # for image in images:
            #     PackageImage.objects.create(package=package, image=image)
            
            # Option 2: Replace all images (uncomment if you want this behavior)
            package.images.all().delete()
            for image in images:
                PackageImage.objects.create(package=package, image=image)
        
        # Return updated package
        response_serializer = self.get_serializer(package)
        return Response({
            'package': response_serializer.data,
            'message': 'Package updated successfully!'
        }, status=status.HTTP_200_OK)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            'message': 'Package deleted successfully!'
        }, status=status.HTTP_200_OK)