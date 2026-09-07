from django.core.management.base import BaseCommand

from audioqueue.tasks import purge_expired_queue


class Command(BaseCommand):
    help = "Supprime les messages vocaux en attente plus vieux que QUEUED_AUDIO_TTL_HOURS."

    def handle(self, *args, **options):
        count = purge_expired_queue()
        self.stdout.write(self.style.SUCCESS(f"{count} message(s) vocal(aux) en attente purgé(s)."))
