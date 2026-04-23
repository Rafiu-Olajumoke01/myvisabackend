from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('read-all/', views.MarkAllReadView.as_view(), name='mark-all-read'),
    path('<str:notification_id>/read/', views.MarkNotificationReadView.as_view(), name='mark-read'),
    path('<str:notification_id>/delete/', views.DeleteNotificationView.as_view(), name='delete-notification'),
]