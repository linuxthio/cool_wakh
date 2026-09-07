"""
Purge des messages vocaux en attente trop anciens.

Par confidentialité, un message posé en file d'attente parce que le
destinataire était hors ligne n'est pas conservé indéfiniment : s'il
n'a pas été réclamé dans le délai `QUEUED_AUDIO_TTL_HOURS`, le fichier
et son entrée en base sont supprimés.

À exécuter périodiquement, par exemple via une tâche cron :
    */30 * * * * cd /path/to/wakh-server && .venv/bin/python manage.py purge_audio_queue
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import AudioQueueEntry


def purge_expired_queue() -> int:
    cutoff = timezone.now() - timedelta(hours=settings.QUEUED_AUDIO_TTL_HOURS)
    expired = AudioQueueEntry.objects.filter(created_at__lt=cutoff)
    count = 0
    for entry in expired:
        if entry.audio_file:
            entry.audio_file.delete(save=False)
        entry.delete()
        count += 1
    return count
