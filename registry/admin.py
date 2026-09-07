from django.contrib import admin

from .models import PhoneRegistry


@admin.register(PhoneRegistry)
class PhoneRegistryAdmin(admin.ModelAdmin):
    # pin_hash et auth_token sont gérés exclusivement par
    # signaling/auth_router.py — jamais exposés ni modifiables ici.
    list_display = ("phone_number", "is_online", "last_seen_at", "first_registered_at")
    list_filter = ("is_online",)
    search_fields = ("phone_number",)
    ordering = ("-last_seen_at",)
    readonly_fields = ("first_registered_at",)
    exclude = ("pin_hash", "auth_token")
