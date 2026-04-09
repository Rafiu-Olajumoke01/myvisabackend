# reviews/admin.py
from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Review Admin - View and manage all reviews
    """
    list_display = ('user', 'package', 'rating', 'created_at', 'updated_at')
    list_filter = ('rating', 'created_at', 'package')
    search_fields = ('user__username', 'user__email', 'package__title', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Review Info', {
            'fields': ('user', 'package', 'rating', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )