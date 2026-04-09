from django.contrib import admin
from .models import Agent, CallSession, CallDecline

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'status', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']

@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'agent', 'status', 'created_at']

@admin.register(CallDecline)
class CallDeclineAdmin(admin.ModelAdmin):
    list_display = ['session', 'agent', 'declined_at']
