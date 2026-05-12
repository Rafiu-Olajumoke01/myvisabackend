from django.urls import path
from .views import (
    InfluencerApplyView,
    InfluencerStatusView,
    InfluencerDashboardView,
    AdminInfluencerListView,
    AdminInfluencerApproveView,
    AdminInfluencerRejectView,
)

urlpatterns = [
    path('apply/', InfluencerApplyView.as_view(), name='influencer-apply'),
    path('status/', InfluencerStatusView.as_view(), name='influencer-status'),
    path('dashboard/', InfluencerDashboardView.as_view(), name='influencer-dashboard'),
    path('admin/list/', AdminInfluencerListView.as_view(), name='admin-influencer-list'),
    path('admin/<int:pk>/approve/', AdminInfluencerApproveView.as_view(), name='admin-influencer-approve'),
    path('admin/<int:pk>/reject/', AdminInfluencerRejectView.as_view(), name='admin-influencer-reject'),
]