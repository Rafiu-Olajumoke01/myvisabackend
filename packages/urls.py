# packages/urls.py
from django.urls import path
from .views import (
    # Public endpoints
    PackageListView,
    PackageDetailView,
    # Admin endpoints
    AdminPackageListCreateView,
    AdminPackageDetailView,
)

urlpatterns = [
    # ─── PUBLIC ENDPOINTS ────────────────────────────────────────────────
    # For regular users - only shows active packages
    path('', PackageListView.as_view(), name='package-list'),
    path('<int:id>/', PackageDetailView.as_view(), name='package-detail'),
    
    # ─── ADMIN ENDPOINTS ─────────────────────────────────────────────────
    # For admin panel - shows all packages and allows CRUD operations
    path('admin/', AdminPackageListCreateView.as_view(), name='admin-package-list-create'),
    path('admin/<int:id>/', AdminPackageDetailView.as_view(), name='admin-package-detail'),
]