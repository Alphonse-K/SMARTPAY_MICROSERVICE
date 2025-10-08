from django.contrib import admin
from .models import SmartPayToken, APILog


@admin.register(SmartPayToken)
class SmartPayTokenAdmin(admin.ModelAdmin):
    list_display = ("token", "seed", "start_time", "end_time", "is_active")
    list_filter = ("is_active", "start_time", "end_time")
    search_fields = ("token", "seed")
    ordering = ("-start_time",)
    readonly_fields = ("token", "seed")  # optional: prevent accidental edits

    fieldsets = (
        (None, {
            "fields": ("token", "seed"),
        }),
        ("Validity Period", {
            "fields": ("start_time", "end_time"),
        }),
        ("Status", {
            "fields": ("is_active",),
        }),
    )


@admin.register(APILog)
class APILogAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "status_code", "created_at", "duration")
    list_filter = ("status_code", "created_at")
    search_fields = ("endpoint", "request_data", "response_data")
    ordering = ("-created_at",)
    readonly_fields = ("endpoint", "request_data", "response_data", "status_code", "created_at", "duration")

    fieldsets = (
        (None, {
            "fields": ("endpoint", "status_code", "duration"),
        }),
        ("Request/Response", {
            "fields": ("request_data", "response_data"),
        }),
        ("Metadata", {
            "fields": ("created_at",),
        }),
    )
