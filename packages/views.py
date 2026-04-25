from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from .models import Package, PackageImage
from .serializers import PackageListSerializer, PackageDetailSerializer


class PackageListView(generics.ListAPIView):
    serializer_class = PackageListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Package.objects.filter(
            is_active=True,
        ).prefetch_related('images')
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(country__icontains=search) |
                Q(title__icontains=search) |
                Q(service_id__icontains=search)
            )
        visa_type = self.request.query_params.get('visa_type', None)
        if visa_type:
            queryset = queryset.filter(visa_type__icontains=visa_type)
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
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
    queryset = Package.objects.filter(
        is_active=True,
    ).prefetch_related('images')
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
# ADMIN ENDPOINTS
# ============================================

class AdminPackageListCreateView(generics.ListCreateAPIView):
    serializer_class = PackageDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Package.objects.all().prefetch_related('images')
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(country__icontains=search) |
                Q(title__icontains=search) |
                Q(service_id__icontains=search)
            )
        service_id = self.request.query_params.get('service_id', None)
        if service_id:
            queryset = queryset.filter(service_id__icontains=service_id)
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
        images = request.FILES.getlist('images')
        if len(images) > 20:
            return Response({'error': 'Maximum 20 images allowed per package'}, status=status.HTTP_400_BAD_REQUEST)
        if len(images) == 0:
            return Response({'error': 'At least one image is required'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ✅ Admin packages go live immediately
        package = serializer.save(post_status='approved', created_by=request.user)
        for image in images:
            PackageImage.objects.create(package=package, image=image)
        response_serializer = self.get_serializer(package)
        return Response({
            'package': response_serializer.data,
            'message': 'Package created successfully!'
        }, status=status.HTTP_201_CREATED)


class AdminPackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Package.objects.all().prefetch_related('images')
    serializer_class = PackageDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        images = request.FILES.getlist('images')
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        package = serializer.save()
        if images:
            if len(images) > 20:
                return Response({'error': 'Maximum 20 images allowed per package'}, status=status.HTTP_400_BAD_REQUEST)
            package.images.all().delete()
            for image in images:
                PackageImage.objects.create(package=package, image=image)
        response_serializer = self.get_serializer(package)
        return Response({
            'package': response_serializer.data,
            'message': 'Package updated successfully!'
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({'message': 'Package deleted successfully!'}, status=status.HTTP_200_OK)


class AdminPendingPackagesView(generics.ListAPIView):
    """Lists all SP packages waiting for admin review"""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = PackageDetailSerializer

    def get_queryset(self):
        return Package.objects.filter(
            post_status='pending_review'
        ).prefetch_related('images').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'packages': serializer.data,
            'count': queryset.count(),
            'message': 'Pending packages retrieved successfully!'
        }, status=status.HTTP_200_OK)


class AdminPackageApproveRejectView(generics.UpdateAPIView):
    """Admin approves or rejects an SP package"""
    permission_classes = [permissions.IsAdminUser]
    queryset = Package.objects.all()
    lookup_field = 'id'

    def patch(self, request, *args, **kwargs):
        action = kwargs.get('action')
        if action not in ['approve', 'reject']:
            return Response(
                {'error': 'Invalid action. Use approve or reject.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        package = self.get_object()
        if action == 'approve':
            package.post_status = 'approved'
            package.is_active = True
        else:
            package.post_status = 'rejected'
            package.is_active = False
        package.save()
        return Response({
            'message': f'Package {action}d successfully!',
            'post_status': package.post_status,
            'package_id': package.id,
        }, status=status.HTTP_200_OK)


# ============================================
# SERVICE PROVIDER ENDPOINTS
# ============================================

class SPPackageListCreateView(generics.ListCreateAPIView):
    serializer_class = PackageDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        try:
            provider = self.request.user.sp_profile
            return Package.objects.filter(
                service_provider=provider
            ).prefetch_related('images')
        except Exception:
            return Package.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'packages': serializer.data,
            'count': queryset.count(),
            'message': 'Your packages retrieved successfully!'
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        try:
            provider = request.user.sp_profile
        except Exception:
            return Response(
                {'error': 'You do not have a service provider profile.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if not provider.is_active or provider.status != 'approved':
            return Response(
                {'error': 'Your service provider account must be approved before creating packages.'},
                status=status.HTTP_403_FORBIDDEN
            )
        images = request.FILES.getlist('images')
        if len(images) == 0:
            return Response({'error': 'At least one image is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(images) > 20:
            return Response({'error': 'Maximum 20 images allowed per package.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # ✅ SP packages go to pending review — not live until admin approves
        package = serializer.save(
            service_provider=provider,
            created_by=request.user,
            post_status='pending_review'
        )
        for image in images:
            PackageImage.objects.create(package=package, image=image)
        response_serializer = self.get_serializer(package)
        return Response({
            'package': response_serializer.data,
            'message': 'Package submitted for review! Admin will approve it shortly.'
        }, status=status.HTTP_201_CREATED)


class SPPackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PackageDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'id'

    def get_queryset(self):
        try:
            provider = self.request.user.sp_profile
            return Package.objects.filter(
                service_provider=provider
            ).prefetch_related('images')
        except Exception:
            return Package.objects.none()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        images = request.FILES.getlist('images')
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        package = serializer.save()
        if images:
            if len(images) > 20:
                return Response({'error': 'Maximum 20 images allowed per package.'}, status=status.HTTP_400_BAD_REQUEST)
            package.images.all().delete()
            for image in images:
                PackageImage.objects.create(package=package, image=image)
        response_serializer = self.get_serializer(package)
        return Response({
            'package': response_serializer.data,
            'message': 'Package updated successfully!'
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({'message': 'Package deleted successfully!'}, status=status.HTTP_200_OK)