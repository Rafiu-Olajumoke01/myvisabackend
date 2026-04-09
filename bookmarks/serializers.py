# bookmarks/serializers.py
from rest_framework import serializers
from .models import Bookmark
from packages.serializers import PackageListSerializer


class BookmarkSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/deleting bookmarks
    """
    class Meta:
        model = Bookmark
        fields = ['id', 'user', 'package', 'created_at']
        read_only_fields = ['user', 'created_at']


class BookmarkListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing user's saved packages
    Shows full package details
    """
    package = PackageListSerializer(read_only=True)
    
    class Meta:
        model = Bookmark
        fields = ['id', 'package', 'created_at']