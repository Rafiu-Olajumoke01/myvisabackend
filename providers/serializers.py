from rest_framework import serializers
from .models import ServiceProvider


class SPRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = [
            'business_name',
            'business_type',
            'country',
            'bio',
            'phone',
            'profile_picture',
            'id_document',
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        # Prevent duplicate applications
        if ServiceProvider.objects.filter(user=user).exists():
            raise serializers.ValidationError('You already have an SP application.')
        return ServiceProvider.objects.create(user=user, **validated_data)


class SPProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    fullname = serializers.CharField(read_only=True)

    class Meta:
        model = ServiceProvider
        fields = [
            'id',
            'fullname',
            'email',
            'business_name',
            'business_type',
            'country',
            'bio',
            'phone',
            'profile_picture',
            'id_document',
            'status',
            'is_active',
            'availability',
            'verification_call_scheduled',
            'rejection_reason',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'is_active',
            'availability',
            'verification_call_scheduled',
            'rejection_reason',
            'created_at',
        ]