"""
Statistiques légères du tableau de bord, utilisées à la fois par le
tableau de bord de l'admin Django (rendu de façon synchrone, dans le
cycle de requête Django normal) et par la page d'accueil FastAPI (appelée
via asgiref.sync.sync_to_async depuis un contexte async).

Volontairement minimal : uniquement des compteurs, jamais de contenu de
message ni de numéro de téléphone individuel.
"""


def get_dashboard_stats() -> dict:
    # Imports différés : ce module peut être importé avant que le
    # registre d'applications Django ne soit prêt (ex: au chargement de
    # wakh_server.admin_site pendant INSTALLED_APPS).
    from audioqueue.models import AudioQueueEntry
    from deletequeue.models import DeleteQueueEntry
    from mediaqueue.models import MediaQueueEntry
    from registry.models import PhoneRegistry
    from textqueue.models import TextQueueEntry

    return {
        "total_numbers": PhoneRegistry.objects.count(),
        "online_now": PhoneRegistry.objects.filter(is_online=True).count(),
        "pending_audio": AudioQueueEntry.objects.filter(status=AudioQueueEntry.PENDING).count(),
        "pending_text": TextQueueEntry.objects.filter(status=TextQueueEntry.PENDING).count(),
        "pending_media": MediaQueueEntry.objects.filter(status=MediaQueueEntry.PENDING).count(),
        "pending_delete": DeleteQueueEntry.objects.count(),
    }
