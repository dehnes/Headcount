from django.contrib import admin

from employees.models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("corp_id", "first_name", "last_name", "email", "status")
    list_filter = ("status",)
    search_fields = ("=corp_id", "first_name", "last_name", "email")
    ordering = ("last_name", "first_name", "corp_id")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("corp_id", "first_name", "last_name", "email", "status")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
