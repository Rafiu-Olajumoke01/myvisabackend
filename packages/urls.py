# packages/urls.py
from django.urls import path
from .views import (
    # Public endpoints
    PackageListView,
    PackageDetailView,
    # Admin endpoints
    AdminPackageListCreateView,
    AdminPackageDetailView,
    # Service Provider endpoints
    SPPackageListCreateView,
    SPPackageDetailView,
)

urlpatterns = [
    # ─── PUBLIC ENDPOINTS ────────────────────────────────────────────────
    path('', PackageListView.as_view(), name='package-list'),
    path('<int:id>/', PackageDetailView.as_view(), name='package-detail'),

    # ─── ADMIN ENDPOINTS ─────────────────────────────────────────────────
    path('admin/', AdminPackageListCreateView.as_view(), name='admin-package-list-create'),
    path('admin/<int:id>/', AdminPackageDetailView.as_view(), name='admin-package-detail'),

    # ─── SERVICE PROVIDER ENDPOINTS ──────────────────────────────────────
    path('sp/', SPPackageListCreateView.as_view(), name='sp-package-list-create'),
    path('sp/<str:id>/', SPPackageDetailView.as_view(), name='sp-package-detail'),
]