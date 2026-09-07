import uuid

from django.db import models


class AudioQueueEntry(models.Model):
    """
    Message vocal mis en attente TEMPORAIREMENT car le destinataire était
    hors ligne au moment de l'envoi (mode hybride).

    Cycle de vie :
      1. L'expéditeur envoie le fichier via /audioqueue/upload -> une
         entrée est créée avec status=PENDING et le fichier posé sur
         disque dans MEDIA_ROOT.
      2. Quand le destinataire se reconnecte, le serveur de signalisation
         (FastAPI) le notifie ; le client télécharge le fichier via
         /audioqueue/download/<id>.
      3. Le destinataire confirme la réception via /audioqueue/ack/<id>
         -> le fichier est supprimé du disque ET la ligne supprimée de
         la base. Rien n'est conservé après livraison.
      4. Une tâche de purge (voir audioqueue/tasks.py) supprime aussi les
         entrées trop anciennes jamais réclamées (TTL de confidentialité).
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
    # Renseigné uniquement si ce message a été envoyé dans le cadre d'un
    # groupe (concept purement local à l'app, voir Android GroupEntity) —
    # permet au destinataire de le rattacher à la bonne conversation de
    # groupe une fois récupéré depuis la file d'attente.
    group_id = models.CharField(max_length=64, blank=True, default="")
    audio_file = models.FileField(upload_to="", max_length=255)
    duration_ms = models.PositiveIntegerField(default=0)
    size_bytes = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Message vocal en attente"
        verbose_name_plural = "Messages vocaux en attente"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.sender_number} -> {self.recipient_number} ({self.status})"
