from django.core.management.base import BaseCommand

from textqueue.tasks import purge_expired_queue


class Command(BaseCommand):
    help = "Supprime les messages texte en attente plus vieux que QUEUED_TEXT_TTL_HOURS."

    def handle(self, *args, **options):
        count = purge_expired_queue()
        self.stdout.write(self.style.SUCCESS(f"{count} message(s) texte en attente purgé(s)."))
