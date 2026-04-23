from django.contrib import admin
from .models import CallSession, CallDecline, CallEvaluation, ChatMessage


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'service_provider', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['user__email']


@admin.register(CallDecline)
class CallDeclineAdmin(admin.ModelAdmin):
    list_display = ['session', 'service_provider', 'declined_at']


@admin.register(CallEvaluation)
class CallEvaluationAdmin(admin.ModelAdmin):
    list_display = ['session', 'service_provider', 'recommendation', 'readiness_score', 'created_at']
    list_filter = ['recommendation']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'sender', 'created_at']