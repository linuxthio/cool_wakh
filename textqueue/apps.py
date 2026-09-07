from django.apps import AppConfig


class TextqueueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "textqueue"
    verbose_name = "File d'attente texte (mode hors-ligne)"
