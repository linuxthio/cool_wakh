"""
Purge des demandes de suppression en attente trop anciennes — même
principe que audioqueue/tasks.py.

À exécuter périodiquement, par exemple via cron :
    */30 * * * * cd /path/to/wakh-server && .venv/bin/python manage.py purge_delete_queue
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import DeleteQueueEntry


def purge_expired_queue() -> int:
    cutoff = timezone.now() - timedelta(hours=settings.QUEUED_DELETE_TTL_HOURS)
    expired = DeleteQueueEntry.objects.filter(created_at__lt=cutoff)
    count = expired.count()
    expired.delete()
    return count
