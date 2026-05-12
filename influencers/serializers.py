from rest_framework import serializers
from .models import Influencer, InfluencerBooking


class InfluencerBookingSerializer(serializers.ModelSerializer):
    booking_date = serializers.DateTimeField(format='%Y-%m-%d', read_only=True)

    class Meta:
        model = InfluencerBooking
        fields = [
            'id', 'client_name', 'package_name', 'package_type',
            'booking_amount', 'commission', 'status', 'booking_date',
        ]


class InfluencerSerializer(serializers.ModelSerializer):
    confirmed_earnings = serializers.ReadOnlyField()
    pending_earnings = serializers.ReadOnlyField()
    total_bookings = serializers.ReadOnlyField()

    class Meta:
        model = Influencer
        fields = [
            'id', 'full_name', 'email', 'phone', 'platform',
            'handle', 'audience_size', 'why', 'promo_code',
            'commission_rate', 'status', 'rejection_reason',
            'confirmed_earnings', 'pending_earnings', 'total_bookings',
            'created_at',
        ]
        read_only_fields = ['promo_code', 'status', 'commission_rate', 'created_at']


class InfluencerApplySerializer(serializers.ModelSerializer):
    promo_code = serializers.CharField(required=False, allow_blank=True)  # add this line explicitly

    class Meta:
        model = Influencer
        fields = ['full_name', 'email', 'phone', 'platform', 'handle', 'audience_size', 'why', 'promo_code']
    
    def validate_promo_code(self, value):
        if not value:  # if they left it blank, skip — model will auto-generate
            return value
        
        value = value.upper().strip().replace(' ', '')
        
        # length check
        if len(value) < 3:
            raise serializers.ValidationError("Promo code must be at least 3 characters.")
        
        # only letters and numbers
        if not value.isalnum():
            raise serializers.ValidationError("Promo code can only contain letters and numbers, no special characters.")
        
        # uniqueness check
        if Influencer.objects.filter(promo_code=value).exists():
            raise serializers.ValidationError("This promo code is already taken. Choose another.")
        
        return value