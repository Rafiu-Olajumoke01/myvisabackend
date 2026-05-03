from django.urls import path
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    AdminUserListView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    GoogleAuthView, 
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),

    # Forgot password
    path('forgot-password/', PasswordResetRequestView.as_view(), name='forgot-password'),
    path('reset-password/', PasswordResetConfirmView.as_view(), name='reset-password'),
    path('google/', GoogleAuthView.as_view(), name='google-auth'), 
]