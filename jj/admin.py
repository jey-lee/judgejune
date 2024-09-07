from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Session

class SessionInline(admin.TabularInline):
    model = Session
    extra = 0  # Number of empty forms to display

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (SessionInline,)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    search_fields = ('name', 'created_by__username')
    list_filter = ('created_at', 'created_by')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('name', 'resolution', 'details')
        }),
        ('Meta Data', {
            'fields': ('created_by', 'created_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
