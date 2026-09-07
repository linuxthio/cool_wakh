from django.apps import AppConfig


class DeletequeueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "deletequeue"
    verbose_name = "File d'attente des suppressions (mode hors-ligne)"
