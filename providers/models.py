from django.db import models
from django.conf import settings
import uuid


class ServiceProvider(models.Model):
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    AVAILABILITY_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline'),
    ]

    BUSINESS_TYPE_CHOICES = [
        ('travel_consultant', 'Travel Consultant'),
        ('visa_agency', 'Visa Agency'),
        ('tour_operator', 'Tour Operator'),
        ('immigration_consultant', 'Immigration Consultant'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sp_profile',
        null=True,
        blank=True,
    )

    # Business information
    business_name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPE_CHOICES, default='other')
    country       = models.CharField(max_length=100, blank=True, null=True)
    bio           = models.TextField(blank=True, null=True)
    phone         = models.CharField(max_length=20, blank=True, null=True)

    # Media & Documents
    profile_picture = models.ImageField(upload_to='service_providers/profiles/', blank=True, null=True)
    id_document     = models.FileField(upload_to='service_providers/documents/', blank=True, null=True)

    # Approval — admin approves or rejects the SP
    status                      = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    is_active                   = models.BooleanField(default=False)
    verification_call_scheduled = models.BooleanField(default=False)
    rejection_reason            = models.TextField(blank=True, null=True)

    # Availability — automatically managed by the call system
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='offline')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} — {self.status}"

    @property
    def fullname(self):
        return self.user.fullname if self.user else self.business_name