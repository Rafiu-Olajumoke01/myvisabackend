# packages/urls.py
from django.urls import path
from .views import (
    # Public endpoints
    PackageListView,
    PackageDetailView,
    # Admin endpoints
    AdminPackageListCreateView,
    AdminPackageDetailView,
    AdminPendingPackagesView,
    AdminPackageApproveRejectView,
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
    path('admin/pending/', AdminPendingPackagesView.as_view(), name='admin-pending-packages'),
    path('admin/<int:id>/', AdminPackageDetailView.as_view(), name='admin-package-detail'),
    path('admin/<int:id>/<str:action>/', AdminPackageApproveRejectView.as_view(), name='admin-package-approve-reject'),

    # ─── SERVICE PROVIDER ENDPOINTS ──────────────────────────────────────
    path('sp/', SPPackageListCreateView.as_view(), name='sp-package-list-create'),
    path('sp/<str:id>/', SPPackageDetailView.as_view(), name='sp-package-detail'),
]