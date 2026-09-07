from django.apps import AppConfig


class AudioqueueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audioqueue"
    verbose_name = "File d'attente audio (mode hors-ligne)"
