# bookmarks/admin.py
from django.contrib import admin
from .models import Bookmark


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    """
    Bookmark Admin - View all saved packages
    """
    list_display = ('user', 'package', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'user__email', 'package__title', 'package__country')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def has_add_permission(self, request):
        """
        Users save packages from frontend, not admin panel
        So we disable manual adding in admin
        """
        return False