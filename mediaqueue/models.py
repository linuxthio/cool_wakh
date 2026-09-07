import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models

# Stockage dédié : les images/vidéos en attente vivent dans
# MEDIA_QUEUE_ROOT, séparément du MEDIA_ROOT réservé à l'audio (voir
# wakh_server/settings.py), même si les deux sont du même type
# (FileSystemStorage) et suivent le même principe de suppression après
# livraison.
media_queue_storage = FileSystemStorage(location=str(settings.MEDIA_QUEUE_ROOT))


class MediaQueueEntry(models.Model):
    """
    Image, vidéo ou document mis en attente TEMPORAIREMENT car le
    destinataire était hors ligne au moment de l'envoi — exactement le
    même principe que AudioQueueEntry (voir audioqueue/models.py) :
    supprimé du disque et de la base dès l'accusé de réception, ou purgé
    automatiquement après QUEUED_MEDIA_TTL_HOURS si jamais réclamé.

    Images, vidéos et documents partagent la même file d'attente (à la
    différence de l'audio et du texte qui ont chacun la leur) car ce sont
    trois pièces jointes binaires avec exactement la même forme de
    métadonnées ; [media_kind] les distingue.
    """

    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    MEDIA_KIND_CHOICES = [
        (IMAGE, "Image"),
        (VIDEO, "Vidéo"),
        (DOCUMENT, "Document"),
    ]

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
    media_kind = models.CharField(max_length=8, choices=MEDIA_KIND_CHOICES)
    media_file = models.FileField(upload_to="", max_length=255, storage=media_queue_storage)
    # Nom de fichier d'origine — uniquement pertinent pour un document
    # (l'utilisateur a besoin de le reconnaître), vide pour image/vidéo.
    original_file_name = models.CharField(max_length=255, blank=True, default="")
    # Uniquement pertinent pour une vidéo ; reste à 0 pour une image/document.
    duration_ms = models.PositiveIntegerField(default=0)
    size_bytes = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Média en attente"
        verbose_name_plural = "Médias en attente"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.sender_number} -> {self.recipient_number} ({self.media_kind}, {self.status})"
