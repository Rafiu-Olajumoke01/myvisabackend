# applications/models.py
from django.db import models
from django.contrib.auth import get_user_model
from packages.models import Package
from providers.models import ServiceProvider  

User = get_user_model()


class Application(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('started', 'Started'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    ]

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

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    
    # ✅ package is now optional
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications'
    )

    # ✅ All personal fields are now optional
    full_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    admin_notes = models.TextField(blank=True, null=True)

    consultant_name = models.CharField(max_length=255, blank=True, null=True)
    consultant_title = models.CharField(max_length=255, blank=True, null=True, default='Visa Consultant')

    meeting_date = models.DateField(blank=True, null=True)
    meeting_time = models.CharField(max_length=100, blank=True, null=True)
    meeting_status = models.CharField(
        max_length=20,
        choices=MEETING_STATUS_CHOICES,
        default='scheduled'
    )
    cancellations_used = models.PositiveSmallIntegerField(default=0)

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'

    def __str__(self):
        name = self.full_name or 'No Name'
        package = self.package.title if self.package else 'No Package'
        return f"{name} - {package} ({self.status})"

    @property
    def cancellations_left(self):
        return max(0, 3 - self.cancellations_used)

    @property
    def can_cancel_meeting(self):
        return self.cancellations_used < 3


class Document(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file = models.FileField(upload_to='applications/documents/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return f"{self.file_name} — {self.application}"


class ApplicationMessage(models.Model):
    SENDER_ROLE_CHOICES = [
        ('client', 'Client'),
        ('consultant', 'Consultant'),
    ]

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
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    sender_role = models.CharField(max_length=20, choices=SENDER_ROLE_CHOICES)
    content = models.TextField(blank=True)
    message_type = models.CharField(
        max_length=20,
        default='text',
        choices=[('text', 'Text'), ('file', 'File')]
    )
    file_url = models.FileField(upload_to='applications/chat/%Y/%m/%d/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_role}] {self.application} — {self.created_at:%Y-%m-%d %H:%M}"


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