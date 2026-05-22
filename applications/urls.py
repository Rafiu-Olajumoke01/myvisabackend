# applications/urls.py
from django.urls import path
from .views import (
    ApplicationListView,
    ApplicationCreateView,
    ApplicationDetailView,
    ApplicationDeleteView,
    ApplicationStartView,
    MeetingCancelView,
    MeetingCompleteView,
    DocumentUploadView,
    DocumentDeleteView,
    AdminApplicationListView,
    ApplicationMessagesView,
    ApplicationMessageFileView,
    AdminRecommendPackageView,
    UserRecommendationsView,
)

urlpatterns = [
    # ── Application ──────────────────────────────────────────
    path('', ApplicationListView.as_view(), name='application-list'),
    path('create/', ApplicationCreateView.as_view(), name='application-create'),
    path('<int:id>/', ApplicationDetailView.as_view(), name='application-detail'),
    path('<int:id>/delete/', ApplicationDeleteView.as_view(), name='application-delete'),

    # ── Start Application ─────────────────────────────────────
    path('<int:id>/start/', ApplicationStartView.as_view(), name='application-start'),

    # ── Discovery Meeting ─────────────────────────────────────
    path('<int:id>/meeting/cancel/', MeetingCancelView.as_view(), name='meeting-cancel'),
    path('<int:id>/meeting/complete/', MeetingCompleteView.as_view(), name='meeting-complete'),

    # ── Documents ─────────────────────────────────────────────
    path('<int:id>/documents/', DocumentUploadView.as_view(), name='document-upload'),
    path('<int:id>/documents/<int:doc_id>/', DocumentDeleteView.as_view(), name='document-delete'),
    path('admin/all/', AdminApplicationListView.as_view(), name='admin-application-list'),

    path('<int:id>/messages/', ApplicationMessagesView.as_view(), name='application-messages'),
    path('<int:id>/messages/file/', ApplicationMessageFileView.as_view(), name='application-messages-file'),

    path('admin/recommend/<int:user_id>/', AdminRecommendPackageView.as_view(), name='recommend-package'),
    path('recommendations/', UserRecommendationsView.as_view(), name='user-recommendations'),
    path('recommendations/<int:rec_id>/', UserRecommendationsView.as_view(), name='user-recommendation-update'),

]