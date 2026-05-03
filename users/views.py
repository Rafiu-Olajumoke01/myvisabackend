from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'fullname': user.fullname,
                'country': user.country,
                'is_service_provider': False,  # always False on fresh registration
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful!'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        user = authenticate(username=user.username, password=password)

        if user is None:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check if user has an approved service provider profile
        is_service_provider = False
        sp_status = None
        try:
            from calls.models import ServiceProvider
            sp = ServiceProvider.objects.get(user=user)
            sp_status = sp.status
            is_service_provider = sp.status == 'approved'
        except Exception:
            pass

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'fullname': user.fullname,
                'is_staff': user.is_staff,
                'country': user.country,
                'is_service_provider': is_service_provider,
                'sp_status': sp_status,  # None | 'pending' | 'approved' | 'rejected'
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Login successful!'
        }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class AdminUserListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        users = User.objects.all()
        return Response({
            'users': [
                {
                    'id': u.id,
                    'email': u.email,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'fullname': u.fullname,
                    'is_staff': u.is_staff,
                    'is_service_provider': hasattr(u, 'sp_profile') and u.sp_profile.status == 'approved',
                }
                for u in users
            ]
        }, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)

            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

            send_mail(
                subject="Reset Your Password",
                message=(
                    f"Hi {user.first_name or user.username},\n\n"
                    f"Click the link below to reset your password:\n\n"
                    f"{reset_link}\n\n"
                    f"This link expires in 24 hours.\n\n"
                    f"If you didn't request this, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

        except User.DoesNotExist:
            pass

        return Response({
            "message": "If that email is registered, a reset link has been sent."
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid          = serializer.validated_data['uid']
        token        = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            user_pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_pk)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({
                "error": "This reset link has expired or already been used. Please request a new one."
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({
            "message": "Password reset successful! You can now log in with your new password."
        }, status=status.HTTP_200_OK)

class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

        email = user_info.get('email')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': first_name,
                'last_name': last_name,
            }
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'email': user.email,
            'name': f"{user.first_name} {user.last_name}",
            'created': created,
        }, status=status.HTTP_200_OK)