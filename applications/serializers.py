# applications/serializers.py
from rest_framework import serializers
from .models import Application, Document, PackageRecommendation

# ─── Document Serializer ──────────────────────────────────────────────────────

class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for a single uploaded document row
    """
    class Meta:
        model = Document
        fields = [
            'id',
            'file',
            'file_name',
            'file_size',
            'uploaded_at',
        ]
        read_only_fields = ['id', 'file_name', 'file_size', 'uploaded_at']

    def create(self, validated_data):
        file = validated_data.get('file')
        # Auto-fill file_name and file_size from the uploaded file
        validated_data['file_name'] = file.name
        size = file.size
        if size > 1024 * 1024:
            validated_data['file_size'] = f"{size / (1024 * 1024):.1f} MB"
        else:
            validated_data['file_size'] = f"{size / 1024:.0f} KB"
        return super().create(validated_data)

    def validate_file(self, value):
        """Max file size: 10MB"""
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File must be less than 10MB")
        return value


# ─── Application Serializers ──────────────────────────────────────────────────
class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            'package',
            'full_name',
            'email',
            'phone',
            'nationality',
            'passport_number',
            'date_of_birth',
            'address',
            'city',
            'country',
        ]
    
    # ✅ Make package optional
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['package'].required = False
        self.fields['package'].allow_null = True
        self.fields['full_name'].required = False
        self.fields['email'].required = False
        self.fields['phone'].required = False
        self.fields['nationality'].required = False
        self.fields['passport_number'].required = False
        self.fields['date_of_birth'].required = False
        self.fields['address'].required = False
        self.fields['city'].required = False
        self.fields['country'].required = False


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """
    Used when viewing a single application in full detail.
    Includes consultant info, meeting info, cancellations, and all documents.
    """
    package_title = serializers.CharField(source='package.title', read_only=True)
    package_country = serializers.CharField(source='package.country', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    meeting_status_display = serializers.CharField(source='get_meeting_status_display', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    cancellations_left = serializers.IntegerField(read_only=True)
    can_cancel_meeting = serializers.BooleanField(read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = [
            'id',
            'user',
            'user_username',
            'package',
            'package_title',
            'package_country',
            'full_name',
            'email',
            'phone',
            'nationality',
            'passport_number',
            'date_of_birth',
            'address',
            'city',
            'country',
            # Status
            'status',
            'status_display',
            'admin_notes',
            # Consultant
            'consultant_name',
            'consultant_title',
            # Meeting
            'meeting_date',
            'meeting_time',
            'meeting_status',
            'meeting_status_display',
            'cancellations_used',
            'cancellations_left',
            'can_cancel_meeting',
            # Documents
            'documents',
            # Timestamps
            'submitted_at',
            'updated_at',
        ]
        read_only_fields = [
            'user', 'status', 'admin_notes',
            'consultant_name', 'consultant_title',
            'meeting_date', 'meeting_time',
            'submitted_at', 'updated_at',
        ]


class ApplicationStartSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    full_name = serializers.CharField(source='user.fullname', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'status', 'user_id', 'full_name', 'email']
        read_only_fields = ['id', 'status', 'user_id', 'full_name', 'email']


class MeetingCancelSerializer(serializers.ModelSerializer):
    """
    Used when a student cancels a discovery meeting.
    Increments cancellations_used and sets meeting_status to 'cancelled'.
    """
    class Meta:
        model = Application
        fields = ['meeting_status', 'cancellations_used']
        read_only_fields = ['meeting_status', 'cancellations_used']


class MeetingCompleteSerializer(serializers.ModelSerializer):
    """
    Used when the discovery call is marked as done.
    Sets meeting_status to 'completed' and application status to 'processing'.
    """
    class Meta:
        model = Application
        fields = ['meeting_status', 'status']
        read_only_fields = ['meeting_status', 'status']

class PackageRecommendationSerializer(serializers.ModelSerializer):
    package_title = serializers.CharField(source='package.title', read_only=True)
    package_country = serializers.CharField(source='package.country', read_only=True)
    package_id = serializers.IntegerField(source='package.id', read_only=True)
    recommended_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PackageRecommendation
        fields = [
            'id',
            'user',
            'package_id',
            'package_title',
            'package_country',
            'recommended_by_name',
            'status',
            'admin_note',
            'created_at',
            'updated_at',
        ]

    def get_recommended_by_name(self, obj):
        if obj.recommended_by:
            return obj.recommended_by.get_full_name() or obj.recommended_by.email
        return 'Admin'