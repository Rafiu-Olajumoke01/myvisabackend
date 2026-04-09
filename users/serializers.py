from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    role      = serializers.ChoiceField(choices=['user', 'agent'], default='user')

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone', 'country', 'role',
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name':  {'required': True},
            'email':      {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        validated_data.pop('password2')
        role = validated_data.pop('role', 'user')

        user = User.objects.create_user(**validated_data)
        user.role = role
        user.save()

        if role == 'agent':
            from calls.models import Agent
            Agent.objects.create(
                user=user,     
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                status='available',
                is_active=True,
            )

        return user


class UserLoginSerializer(serializers.Serializer):
    email    = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class UserProfileSerializer(serializers.ModelSerializer):
    fullname = serializers.SerializerMethodField()  

    def get_fullname(self, obj):                    
        return obj.fullname

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email',
            'first_name', 'last_name', 'fullname',
            'is_staff', 'phone', 'country', 'role',
            'date_of_birth', 'passport_number', 'address',
            'date_joined',
        ]
        read_only_fields = ['id', 'email', 'username', 'fullname', 'date_joined']


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid           = serializers.CharField(required=True)
    token         = serializers.CharField(required=True)
    new_password  = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Passwords didn't match."})
        return attrs