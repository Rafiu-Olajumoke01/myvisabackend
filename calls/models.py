# calls/models.py
from django.db import models
from django.conf import settings
# from providers.models import ServiceProvider  ← keep commented out
import uuid


class CallSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='call_sessions'
    )
    service_provider = models.ForeignKey(
        'providers.ServiceProvider',  # ← string reference instead
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='call_sessions'
    )
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    meet_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.id} — {self.status}"


class CallDecline(models.Model):
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session          = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name='declines')
    service_provider = models.ForeignKey(
        'providers.ServiceProvider',
        on_delete=models.CASCADE,
        related_name='declines',
        null=True,   # ← inside the ForeignKey brackets
        blank=True,  # ← inside the ForeignKey brackets
    )
    reason           = models.TextField(blank=True, null=True)
    declined_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Decline by {self.service_provider} for session {self.session.id}"

class CallEvaluation(models.Model):
    RECOMMENDATION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('more_documents', 'Need More Documents'),
    ]

    id                      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session                 = models.OneToOneField(CallSession, on_delete=models.CASCADE, related_name='evaluation')
    service_provider        = models.ForeignKey(
        'providers.ServiceProvider',  # ← string reference
        on_delete=models.SET_NULL,
        null=True,
        related_name='evaluations_given'
    )
    applicant               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='evaluations_received')
    has_right_documents     = models.BooleanField()
    meets_eligibility       = models.BooleanField()
    communication_score     = models.PositiveSmallIntegerField()
    understands_process     = models.BooleanField()
    answered_satisfactorily = models.BooleanField()
    recommendation          = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES)
    readiness_score         = models.FloatField()
    created_at              = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evaluation — Session {self.session.id} | Score: {self.readiness_score}%"


class ChatMessage(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session    = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name='messages')
    sender     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']