# applications/admin.py
from django.contrib import admin
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    Application Admin - Manage visa applications
    """
    list_display = ('full_name', 'package', 'user', 'status', 'submitted_at', 'updated_at')
    list_filter = ('status', 'submitted_at', 'package')
    search_fields = ('full_name', 'email', 'passport_number', 'user__username', 'package__title')
    readonly_fields = ('submitted_at', 'updated_at')
    ordering = ('-submitted_at',)
    
    fieldsets = (
        ('Application Info', {
            'fields': ('user', 'package', 'status', 'admin_notes')
        }),
        ('Personal Information', {
            'fields': ('full_name', 'email', 'phone', 'nationality', 'passport_number', 'date_of_birth')
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'country')
        }),
        ('Documents', {
            'fields': ('passport_copy', 'passport_photo', 'additional_documents')
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Allow admin to change status and add notes
    list_editable = ('status',)
    
    def has_add_permission(self, request):
        """
        Users submit applications from frontend, not admin panel
        """
        return False