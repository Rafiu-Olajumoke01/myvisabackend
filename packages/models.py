# packages/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Package(models.Model):
    CATEGORY_CHOICES = [
        ('student',  'Student'),
        ('tourist',  'Tourist'),
        ('business', 'Business'),
        ('medical',  'Medical'),
    ]

    # ── Always present ─────────────────────────────────────────
    title           = models.CharField(max_length=255)
    category        = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)
    description     = models.TextField(blank=True, null=True)
    requirements    = models.TextField(blank=True, null=True)
    processing_time = models.CharField(max_length=100, blank=True, null=True)
    is_active       = models.BooleanField(default=True)
    is_free         = models.BooleanField(default=False)
    price           = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    service_fee     = models.CharField(max_length=50, blank=True, null=True)

    # ── Student fields ─────────────────────────────────────────
    university_name       = models.CharField(max_length=255, blank=True, null=True)
    university_logo       = models.URLField(blank=True, null=True)
    location              = models.CharField(max_length=255, blank=True, null=True)
    tuition_fees          = models.CharField(max_length=100, blank=True, null=True)
    course                = models.CharField(max_length=255, blank=True, null=True)
    course_duration       = models.CharField(max_length=100, blank=True, null=True)
    application_fees      = models.CharField(max_length=100, blank=True, null=True)
    post_study_work_visa  = models.CharField(max_length=10, blank=True, null=True)
    admission_requirement = models.TextField(blank=True, null=True)
    visa_required         = models.CharField(max_length=10, blank=True, null=True)

    # ── New student fields ─────────────────────────────────────
    degree_type         = models.CharField(max_length=50, blank=True, null=True)   # e.g. BSc, MSc, MBA
    course_city         = models.CharField(max_length=100, blank=True, null=True)  # city of the school
    course_expectations = models.TextField(blank=True, null=True)                  # what to expect

    # ── Tourist fields ─────────────────────────────────────────
    trip_duration          = models.PositiveIntegerField(blank=True, null=True)
    cost                   = models.CharField(max_length=100, blank=True, null=True)
    covers_visa            = models.BooleanField(default=False)
    covers_flight          = models.BooleanField(default=False)
    covers_airport_pickup  = models.BooleanField(default=False)
    covers_accommodation   = models.BooleanField(default=False)
    covers_daily_tours     = models.BooleanField(default=False)
    covers_food            = models.BooleanField(default=False)
    covers_local_transport = models.BooleanField(default=False)

    # ── Business / Medical fields ───────────────────────────────
    country       = models.CharField(max_length=100, blank=True, null=True)
    visa_duration = models.CharField(max_length=100, blank=True, null=True)

    # ── New medical fields ─────────────────────────────────────
    hospital_name        = models.CharField(max_length=255, blank=True, null=True)  # hospital name
    hospital_city        = models.CharField(max_length=100, blank=True, null=True)  # city of hospital
    medical_expectations = models.TextField(blank=True, null=True)                  # what to expect

    # ── Meta ───────────────────────────────────────────────────
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='packages')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Package'
        verbose_name_plural = 'Packages'

    def __str__(self):
        return f"{self.title} - {self.category}"


class PackageImage(models.Model):
    package     = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='images')
    image       = models.ImageField(upload_to='packages/%Y/%m/%d/')
    alt_text    = models.CharField(max_length=255, blank=True)
    order       = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Package Image'
        verbose_name_plural = 'Package Images'

    def __str__(self):
        return f"Image for {self.package.title} (Order: {self.order})"