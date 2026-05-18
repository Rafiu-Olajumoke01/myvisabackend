# applications/models.py
from django.db import models
from django.contrib.auth import get_user_model
from packages.models import Package
from providers.models import ServiceProvider  

User = get_user_model()


class Application(models.Model):
    """
    Visa Application Model
    Users submit applications for visa packages
    """

    # Application Status Choices
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('started', 'Started'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    ]

    # Meeting Status Choices
    MEETING_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    service_provider = models.ForeignKey(
        'providers.ServiceProvider',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='applications'
    )
    # Relationship Fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='applications')

    # Personal Information
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    nationality = models.CharField(max_length=100)
    passport_number = models.CharField(max_length=50)
    date_of_birth = models.DateField()

    # Address Information
    address = models.TextField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    # Application Status & Management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    admin_notes = models.TextField(blank=True, null=True, help_text="Internal notes from admin")

    # Consultant Assignment
    consultant_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of the consultant assigned to this application"
    )
    consultant_title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default='Visa Consultant'
    )

    # Discovery Meeting
    meeting_date = models.DateField(
        blank=True,
        null=True,
        help_text="Scheduled date of the discovery meeting"
    )
    meeting_time = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g. 10:00 AM - 10:30 AM"
    )
    meeting_status = models.CharField(
        max_length=20,
        choices=MEETING_STATUS_CHOICES,
        default='scheduled'
    )
    cancellations_used = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of times the student has cancelled the discovery meeting (max 3)"
    )

    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'

    def __str__(self):
        return f"{self.full_name} - {self.package.title} ({self.status})"

    @property
    def cancellations_left(self):
        """How many cancellations the student still has remaining"""
        return max(0, 3 - self.cancellations_used)

    @property
    def can_cancel_meeting(self):
        """Whether the student is still allowed to cancel"""
        return self.cancellations_used < 3


class Document(models.Model):
    """
    Document Model
    Each uploaded file by a student is stored as its own row
    linked to their application
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file = models.FileField(upload_to='applications/documents/%Y/%m/%d/')
    file_name = models.CharField(max_length=255, help_text="Original name of the uploaded file")
    file_size = models.CharField(max_length=50, help_text="e.g. 1.2 MB or 340 KB")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return f"{self.file_name} — {self.application.full_name}"

class ApplicationMessage(models.Model):
    SENDER_ROLE_CHOICES = [
        ('client', 'Client'),
        ('consultant', 'Consultant'),
    ]

    # ✅ ADD THIS — links the chat to an assigned provider session
    chat_session = models.ForeignKey(
        'calls.CallSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application_messages'
        )

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender      = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    sender_role = models.CharField(max_length=20, choices=SENDER_ROLE_CHOICES)
    content     = models.TextField(blank=True)
    message_type = models.CharField(
        max_length=20,
        default='text',
        choices=[('text', 'Text'), ('file', 'File')]
    )
    file_url    = models.FileField(upload_to='applications/chat/%Y/%m/%d/', blank=True, null=True)
    file_name   = models.CharField(max_length=255, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_role}] {self.application.full_name} — {self.created_at:%Y-%m-%d %H:%M}"

class PackageRecommendation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('viewed', 'Viewed'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    recommended_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recommendations_made'
    )
    admin_note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.package.title} → {self.user.email}"


