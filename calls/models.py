from django.db import models
from django.conf import settings
import uuid


class Agent(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # ✅ Link to User model
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_profile',
        null=True,
        blank=True,
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='agents/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.status}"


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
    agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='call_sessions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    meet_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.id} — {self.status}"


class CallDecline(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name='declines')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='declines')
    reason = models.TextField(blank=True, null=True)
    declined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Decline by {self.agent} for session {self.session.id}"


class CallEvaluation(models.Model):
    RECOMMENDATION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('more_documents', 'Need More Documents'),
    ]

    id                      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session                 = models.OneToOneField(CallSession, on_delete=models.CASCADE, related_name='evaluation')
    agent                   = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, related_name='evaluations_given')
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