from django.urls import path
from . import views

urlpatterns = [
    path('request/', views.RequestCallView.as_view(), name='request-call'),
    path('accept/<str:session_id>/', views.AcceptCallView.as_view(), name='accept-call'),
    path('decline/<str:session_id>/', views.DeclineCallView.as_view(), name='decline-call'),
    path('providers/available/', views.AvailableProvidersView.as_view(), name='available-providers'),
    path('session/<str:session_id>/', views.CallSessionStatusView.as_view(), name='session-status'),
    path('provider/availability/', views.ProviderAvailabilityView.as_view(), name='provider-availability'),
    path('history/', views.CallHistoryView.as_view(), name='call-history'),
    path('end/<str:session_id>/', views.EndCallView.as_view(), name='end-call'),
    path('evaluate/<str:session_id>/', views.CallEvaluationCreateView.as_view(), name='call-evaluate'),
    path('clients/', views.ClientsListView.as_view(), name='clients-list'),
    path('clients/<int:user_id>/', views.ClientDetailView.as_view(), name='client-detail'),
    path('providers/', views.ProvidersListView.as_view(), name='providers-list'),
    path('providers/<str:provider_id>/<str:action>/', views.ProviderStatusUpdateView.as_view(), name='provider-status-update'),
    path('unlock-chat/<str:session_id>/', views.UnlockChatView.as_view(), name='unlock-chat'),
]