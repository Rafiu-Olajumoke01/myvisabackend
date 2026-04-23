from django.contrib import admin
from .models import ServiceProvider


@admin.register(ServiceProvider)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'business_type', 'status', 'is_active', 'created_at']
    list_filter = ['status', 'is_active', 'business_type']
    search_fields = ['business_name', 'user__email']