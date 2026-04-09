# bookmarks/models.py
from django.db import models
from django.contrib.auth import get_user_model
from packages.models import Package

User = get_user_model()


class Bookmark(models.Model):
    """
    Bookmark/Saved Packages
    Users can save packages for later viewing
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']  
        unique_together = ('user', 'package')  
        verbose_name = 'Bookmark'
        verbose_name_plural = 'Bookmarks'
    
    def __str__(self):
        return f"{self.user.username} saved {self.package.title}"