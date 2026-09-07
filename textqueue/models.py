import uuid

from django.conf import settings
from django.db import models


class TextQueueEntry(models.Model):
    """
    Message texte mis en attente TEMPORAIREMENT car le destinataire était
    hors ligne au moment de l'envoi — exactement le même principe que
    AudioQueueEntry (voir audioqueue/models.py) : supprimé du disque et de
    la base dès l'accusé de réception, ou purgé automatiquement après
    QUEUED_TEXT_TTL_HOURS s'il n'est jamais réclamé.

    Contrairement à l'audio, le contenu tient directement dans la ligne
    (pas de fichier séparé) : pas d'étape de téléchargement nécessaire, le
    texte est renvoyé directement dans la liste des messages en attente.
    """

    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    STATUS_CHOICES = [
        (PENDING, "En attente"),
        (DELIVERED, "Livré"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender_number = models.CharField(max_length=32, db_index=True)
    recipient_number = models.CharField(max_length=32, db_index=True)
    # Voir AudioQueueEntry.group_id : même principe.
    group_id = models.CharField(max_length=64, blank=True, default="")
    content = models.TextField(max_length=settings.TEXT_MESSAGE_MAX_LENGTH)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Message texte en attente"
        verbose_name_plural = "Messages texte en attente"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.sender_number} -> {self.recipient_number} ({self.status})"
