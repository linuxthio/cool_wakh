from django.core.management.base import BaseCommand

from deletequeue.tasks import purge_expired_queue


class Command(BaseCommand):
    help = "Supprime les demandes de suppression en attente plus vieilles que QUEUED_DELETE_TTL_HOURS."

    def handle(self, *args, **options):
        count = purge_expired_queue()
        self.stdout.write(self.style.SUCCESS(f"{count} demande(s) de suppression en attente purgée(s)."))
