from django.core.management.base import BaseCommand

from mediaqueue.tasks import purge_expired_queue


class Command(BaseCommand):
    help = "Supprime les images/vidéos en attente plus vieilles que QUEUED_MEDIA_TTL_HOURS."

    def handle(self, *args, **options):
        count = purge_expired_queue()
        self.stdout.write(self.style.SUCCESS(f"{count} média(s) en attente purgé(s)."))
