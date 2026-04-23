from django.urls import path
from . import views

urlpatterns = [
    # User endpoints
    path('register/', views.SPRegistrationView.as_view(), name='sp-register'),
    path('status/', views.SPApplicationStatusView.as_view(), name='sp-status'),
    path('profile/', views.SPProfileView.as_view(), name='sp-profile'),

    # Admin endpoints
    path('admin/list/', views.AdminSPListView.as_view(), name='admin-sp-list'),
    path('admin/<str:provider_id>/schedule-call/', views.AdminSPScheduleCallView.as_view(), name='admin-sp-schedule-call'),
    path('admin/<str:provider_id>/<str:action>/', views.AdminSPApproveRejectView.as_view(), name='admin-sp-approve-reject'),
    path('<str:provider_id>/profile/', views.SPPublicProfileView.as_view(), name='sp-public-profile'),
]