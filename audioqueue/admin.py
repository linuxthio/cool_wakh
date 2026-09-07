from django.contrib import admin

from .models import AudioQueueEntry


@admin.register(AudioQueueEntry)
class AudioQueueEntryAdmin(admin.ModelAdmin):
    # Le contenu audio n'est jamais affiché ici : uniquement les
    # métadonnées utiles à la supervision, pour rappeler que ce stockage
    # est transitoire et ne doit pas devenir un historique de contenu.
    list_display = (
        "id",
        "sender_number",
        "recipient_number",
        "group_id",
        "status",
        "duration_ms",
        "size_bytes",
        "created_at",
        "delivered_at",
    )
    list_filter = ("status",)
    search_fields = ("sender_number", "recipient_number")
    readonly_fields = ("id", "created_at")
