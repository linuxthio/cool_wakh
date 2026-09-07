from django.contrib import admin

from .models import TextQueueEntry


@admin.register(TextQueueEntry)
class TextQueueEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender_number",
        "recipient_number",
        "group_id",
        "status",
        "content_preview",
        "created_at",
        "delivered_at",
    )
    list_filter = ("status",)
    search_fields = ("sender_number", "recipient_number")
    readonly_fields = ("id", "created_at")

    @admin.display(description="Aperçu")
    def content_preview(self, obj: TextQueueEntry) -> str:
        return (obj.content[:40] + "…") if len(obj.content) > 40 else obj.content
