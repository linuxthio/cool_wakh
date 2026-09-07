"""
Purge des messages texte en attente trop anciens — même principe que
audioqueue/tasks.py.

À exécuter périodiquement, par exemple via cron :
    */30 * * * * cd /path/to/wakh-server && .venv/bin/python manage.py purge_text_queue
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import TextQueueEntry


def purge_expired_queue() -> int:
    cutoff = timezone.now() - timedelta(hours=settings.QUEUED_TEXT_TTL_HOURS)
    expired = TextQueueEntry.objects.filter(created_at__lt=cutoff)
    count = expired.count()
    expired.delete()
    return count
