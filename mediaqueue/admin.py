from django.contrib import admin

from .models import MediaQueueEntry


@admin.register(MediaQueueEntry)
class MediaQueueEntryAdmin(admin.ModelAdmin):
    # Le contenu (image/vidéo) n'est jamais affiché ici : uniquement les
    # métadonnées utiles à la supervision — ce stockage est transitoire.
    list_display = (
        "id",
        "sender_number",
        "recipient_number",
        "group_id",
        "media_kind",
        "status",
        "duration_ms",
        "size_bytes",
        "created_at",
        "delivered_at",
    )
    list_filter = ("media_kind", "status")
    search_fields = ("sender_number", "recipient_number")
    readonly_fields = ("id", "created_at")
