# packages/serializers.py
from rest_framework import serializers
from .models import Package, PackageImage


class PackageImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageImage
        fields = ['id', 'image', 'alt_text', 'order']


COMMON_FIELDS = [
    'id', 'title', 'category', 'is_free', 'is_active',
    'price', 'service_fee', 'processing_time',
    'description', 'requirements', 'images', 'created_at',
]

STUDENT_FIELDS = [
    'university_name', 'university_logo', 'location',
    'tuition_fees', 'course', 'course_duration',
    'application_fees', 'post_study_work_visa',
    'admission_requirement', 'visa_required',
    # new
    'degree_type', 'course_city', 'course_expectations',
]

TOURIST_FIELDS = [
    'trip_duration', 'cost', 'location',
    'covers_visa', 'covers_flight', 'covers_airport_pickup',
    'covers_accommodation', 'covers_daily_tours',
    'covers_food', 'covers_local_transport', 'visa_required',
]

BUSINESS_MEDICAL_FIELDS = [
    'country', 'visa_duration',
    # new
    'hospital_name', 'hospital_city', 'medical_expectations',
]


class PackageListSerializer(serializers.ModelSerializer):
    """Used for listing packages (cards view)"""
    images = PackageImageSerializer(many=True, read_only=True)

    class Meta:
        model = Package
        fields = COMMON_FIELDS + STUDENT_FIELDS + TOURIST_FIELDS + BUSINESS_MEDICAL_FIELDS


class PackageDetailSerializer(serializers.ModelSerializer):
    """Used for create, update, retrieve (full detail)"""
    images = PackageImageSerializer(many=True, read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = Package
        fields = COMMON_FIELDS + STUDENT_FIELDS + TOURIST_FIELDS + BUSINESS_MEDICAL_FIELDS + ['updated_at']

    def to_representation(self, instance):
        """Convert requirements text to array when reading"""
        data = super().to_representation(instance)
        if data.get('requirements'):
            data['requirements'] = [
                req.strip() for req in data['requirements'].split('\n') if req.strip()
            ]
        else:
            data['requirements'] = []
        return data