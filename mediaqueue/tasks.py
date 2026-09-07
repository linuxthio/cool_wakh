"""
Purge des images/vidéos en attente trop anciennes — même principe que
audioqueue/tasks.py.

À exécuter périodiquement, par exemple via cron :
    */30 * * * * cd /path/to/wakh-server && .venv/bin/python manage.py purge_media_queue
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import MediaQueueEntry


def purge_expired_queue() -> int:
    cutoff = timezone.now() - timedelta(hours=settings.QUEUED_MEDIA_TTL_HOURS)
    expired = MediaQueueEntry.objects.filter(created_at__lt=cutoff)
    count = 0
    for entry in expired:
        if entry.media_file:
            entry.media_file.delete(save=False)
        entry.delete()
        count += 1
    return count
