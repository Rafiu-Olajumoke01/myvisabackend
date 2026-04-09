from django.urls import path
from . import views

urlpatterns = [
    path('request/', views.RequestCallView.as_view(), name='request-call'),
    path('accept/<str:session_id>/', views.AcceptCallView.as_view(), name='accept-call'),
    path('decline/<str:session_id>/', views.DeclineCallView.as_view(), name='decline-call'),
    path('agents/available/', views.AvailableAgentsView.as_view(), name='available-agents'),
    path('session/<str:session_id>/', views.CallSessionStatusView.as_view(), name='session-status'),
    path('agent/status/', views.AgentStatusView.as_view(), name='agent-status'),
    path('history/', views.CallHistoryView.as_view(), name='call-history'),
    path('end/<str:session_id>/', views.EndCallView.as_view(), name='end-call'),
    path('evaluate/<str:session_id>/', views.CallEvaluationCreateView.as_view(), name='call-evaluate'),
    path('clients/', views.ClientsListView.as_view(), name='clients-list'),
    path('clients/<int:user_id>/', views.ClientDetailView.as_view(), name='client-detail'),
    path('agents/<str:agent_id>/approved/', views.AgentStatusUpdateView.as_view(), name='agent-approve'),
    path('agents/<str:agent_id>/rejected/', views.AgentStatusUpdateView.as_view(), name='agent-reject'),
    path('agents/', views.AgentsListView.as_view(), name='agents-list'),

    # ✅ NEW — Unlock chat after discovery call
    path('unlock-chat/<str:session_id>/', views.UnlockChatView.as_view(), name='unlock-chat'),
]