from django.apps import AppConfig


class MediaqueueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mediaqueue"
    verbose_name = "File d'attente images/vidéos (mode hors-ligne)"
