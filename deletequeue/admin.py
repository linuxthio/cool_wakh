from django.contrib import admin

from .models import DeleteQueueEntry


@admin.register(DeleteQueueEntry)
class DeleteQueueEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender_number",
        "recipient_number",
        "group_id",
        "target_message_id",
        "created_at",
    )
    search_fields = ("sender_number", "recipient_number", "target_message_id")
    readonly_fields = ("id", "created_at")
