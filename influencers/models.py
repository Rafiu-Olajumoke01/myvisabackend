from django.db import models
from django.conf import settings
import random
import string


def generate_promo_code(name):
    prefix = name.upper().split()[0][:6]
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"INGRESS-{prefix}{suffix}"


class Influencer(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='influencer_profile')
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    platform = models.CharField(max_length=500)
    handle = models.CharField(max_length=100)
    audience_size = models.CharField(max_length=20)
    why = models.TextField()
    promo_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.promo_code:
            self.promo_code = generate_promo_code(self.full_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} — {self.promo_code}"

    @property
    def confirmed_earnings(self):
        return sum(b.commission for b in self.bookings.filter(status='confirmed'))

    @property
    def pending_earnings(self):
        return sum(b.commission for b in self.bookings.filter(status='pending'))

    @property
    def total_bookings(self):
        return self.bookings.count()


class InfluencerBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    PACKAGE_TYPE_CHOICES = [
        ('student', 'Student'),
        ('tourist', 'Tourist'),
        ('business', 'Business'),
        ('medical', 'Medical'),
    ]

    influencer = models.ForeignKey(Influencer, on_delete=models.CASCADE, related_name='bookings')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    client_name = models.CharField(max_length=200)
    package_name = models.CharField(max_length=200)
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPE_CHOICES, default='tourist')
    promo_code_used = models.CharField(max_length=50)
    booking_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    booking_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_name} → {self.influencer.promo_code}"

    class Meta:
        ordering = ['-booking_date']