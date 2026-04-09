# reviews/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from packages.models import Package

User = get_user_model()


class Review(models.Model):
    """
    Package Reviews and Ratings
    Users can rate and review packages they've used
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    comment = models.TextField(blank=True, null=True, help_text="Optional review text")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at'] 
        unique_together = ('user', 'package')  
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
    
    def __str__(self):
        return f"{self.user.username} - {self.package.title} ({self.rating}⭐)"