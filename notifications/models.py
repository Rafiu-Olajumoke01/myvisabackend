from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Notification(models.Model):
    TYPE_CHOICES = [
        # SP flow
        ('sp_application_received',     'SP Application Received'),
        ('sp_call_scheduled',           'Verification Call Scheduled'),
        ('sp_approved',                 'SP Application Approved'),
        ('sp_rejected',                 'SP Application Rejected'),

        # Call flow
        ('call_request',                'Call Request'),
        ('call_accepted',               'Call Accepted'),
        ('call_declined',               'Call Declined'),
        ('call_completed',              'Call Completed'),
        ('evaluation_submitted',        'Evaluation Submitted'),

        # Package flow
        ('package_application',         'New Package Application'),
        ('application_status_update',   'Application Status Update'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=255)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    data       = models.JSONField(blank=True, null=True)  # extra context e.g session_id, package_id
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"[{self.type}] {self.user} — {self.title}"