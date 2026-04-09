# reviews/serializers.py
from rest_framework import serializers
from .models import Review
from django.db.models import Avg


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating reviews
    """
    user_name = serializers.CharField(source='user.fullname', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'user', 'user_name', 'user_username', 'package', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class ReviewListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing reviews (with user details)
    """
    user_name = serializers.CharField(source='user.fullname', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'user_name', 'user_username', 'rating', 'comment', 'created_at']


class PackageRatingSerializer(serializers.Serializer):
    """
    Serializer for package average rating and review count
    """
    average_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    five_star = serializers.IntegerField()
    four_star = serializers.IntegerField()
    three_star = serializers.IntegerField()
    two_star = serializers.IntegerField()
    one_star = serializers.IntegerField()