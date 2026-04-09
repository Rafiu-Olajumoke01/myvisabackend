# packages/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Package, PackageImage


class PackageImageInline(admin.TabularInline):
    model = PackageImage
    extra = 5
    fields = ['image', 'alt_text', 'order', 'image_preview']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 150px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'price', 'processing_time', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'created_at']
    search_fields = ['title', 'category', 'country', 'university_name']

    inlines = [PackageImageInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'category', 'is_active', 'is_free', 'price', 'service_fee', 'processing_time')
        }),
        ('Student Fields', {
            'classes': ('collapse',),
            'fields': ('university_name', 'university_logo', 'location', 'tuition_fees', 'course', 'course_duration', 'application_fees', 'post_study_work_visa', 'admission_requirement', 'visa_required')
        }),
        ('Tourist Fields', {
            'classes': ('collapse',),
            'fields': ('trip_duration', 'cost', 'covers_visa', 'covers_flight', 'covers_airport_pickup', 'covers_accommodation', 'covers_daily_tours', 'covers_food', 'covers_local_transport')
        }),
        ('Business / Medical Fields', {
            'classes': ('collapse',),
            'fields': ('country', 'visa_duration')
        }),
        ('Details', {
            'fields': ('description', 'requirements')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            if hasattr(obj, 'created_by'):
                obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PackageImage)
class PackageImageAdmin(admin.ModelAdmin):
    list_display = ['package', 'order', 'uploaded_at', 'image_preview_thumb']
    list_filter = ['package', 'uploaded_at']
    search_fields = ['package__title', 'alt_text']
    fields = ['package', 'image', 'alt_text', 'order']

    def image_preview_thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "No image"
    image_preview_thumb.short_description = 'Preview'