import uuid

from django.db import models


class DeleteQueueEntry(models.Model):
    """
    Demande de "suppression pour tout le monde" mise en attente
    TEMPORAIREMENT car le destinataire était hors ligne au moment de la
    demande — même principe que les autres files d'attente (audio, texte,
    média) : supprimée dès qu'elle a été relevée par le destinataire, ou
    purgée automatiquement après QUEUED_DELETE_TTL_HOURS si jamais
    réclamée.

    Contenu minimal (juste un identifiant) : contrairement aux autres
    files, il n'y a aucun contenu de message ici, seulement l'ordre de
    supprimer le message [target_message_id] déjà reçu précédemment (par
    P2P direct ou via une autre file d'attente).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender_number = models.CharField(max_length=32, db_index=True)
    recipient_number = models.CharField(max_length=32, db_index=True)
    # Voir AudioQueueEntry.group_id : même principe (vide pour un 1-à-1).
    group_id = models.CharField(max_length=64, blank=True, default="")
    # Identifiant du message à supprimer chez le destinataire — c'est le
    # même identifiant que celui utilisé lors de l'envoi initial (partagé
    # entre expéditeur et destinataire, voir Android MessageEntity.id).
    target_message_id = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Suppression en attente"
        verbose_name_plural = "Suppressions en attente"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.sender_number} -> {self.recipient_number} : supprimer {self.target_message_id}"
