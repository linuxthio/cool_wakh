"""
Routes REST pour le dépôt/retrait TEMPORAIRE d'un message texte quand le
destinataire est hors ligne au moment de l'envoi — même principe que
audio_queue_router.py, en plus simple : le contenu tient directement dans
la réponse de /textqueue/pending, pas besoin d'endpoint de téléchargement
séparé.

Toutes les routes sont protégées par authentification (voir auth.py), avec
les mêmes vérifications de propriétaire que pour l'audio.
"""

from __future__ import annotations

import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from fastapi import APIRouter, Depends, Form, HTTPException
from starlette import status as http_status

from .auth import get_current_phone_number
from .connection_manager import manager

logger = logging.getLogger("wakh.textqueue")

router = APIRouter(prefix="/textqueue")


@sync_to_async
def _create_entry(sender: str, recipient: str, group_id: str, content: str) -> str:
    from textqueue.models import TextQueueEntry

    entry = TextQueueEntry.objects.create(
        sender_number=sender,
        recipient_number=recipient,
        group_id=group_id,
        content=content,
    )
    return str(entry.id)


@sync_to_async
def _list_pending(recipient: str) -> list[dict]:
    from textqueue.models import TextQueueEntry

    qs = TextQueueEntry.objects.filter(
        recipient_number=recipient, status=TextQueueEntry.PENDING
    ).order_by("created_at")
    return [
        {
            "id": str(e.id),
            "sender_number": e.sender_number,
            "group_id": e.group_id,
            "content": e.content,
            "created_at": e.created_at.isoformat(),
        }
        for e in qs
    ]


@sync_to_async
def _acknowledge_and_delete(entry_id: str, expected_recipient: str) -> str:
    """Renvoie 'ok', 'not_found' ou 'forbidden'."""
    from textqueue.models import TextQueueEntry

    try:
        entry = TextQueueEntry.objects.get(id=entry_id)
    except TextQueueEntry.DoesNotExist:
        return "not_found"
    if entry.recipient_number != expected_recipient:
        return "forbidden"
    entry.delete()
    return "ok"


@router.post("/upload", status_code=http_status.HTTP_201_CREATED)
async def upload_text(
    sender_number: str = Form(...),
    recipient_number: str = Form(...),
    content: str = Form(...),
    group_id: str = Form(""),
    current_phone: str = Depends(get_current_phone_number),
):
    """Dépose un message texte en attente car le destinataire est hors
    ligne. Appelé par le client seulement après échec (ou absence) de
    connexion P2P directe — même principe que /audioqueue/upload."""
    if sender_number != current_phone:
        raise HTTPException(status_code=403, detail="Le numéro expéditeur ne correspond pas au compte connecté")

    trimmed = content.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="Message texte vide")
    if len(trimmed) > settings.TEXT_MESSAGE_MAX_LENGTH:
        raise HTTPException(status_code=413, detail="Message texte trop long")

    entry_id = await _create_entry(sender_number, recipient_number, group_id.strip(), trimmed)

    # Si le destinataire est déjà en ligne (cas limite, ex: relance rapide
    # après un échec P2P), on le notifie immédiatement.
    await manager.send_json(recipient_number, {"type": "pending_text", "count": 1})

    return {"queued_message_id": entry_id}


@router.get("/pending/{phone_number}")
async def list_pending(phone_number: str, current_phone: str = Depends(get_current_phone_number)):
    """Liste les messages texte en attente pour ce numéro, contenu inclus
    directement (pas d'étape de téléchargement séparée nécessaire)."""
    if phone_number != current_phone:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return {"pending": await _list_pending(phone_number)}


@router.post("/ack/{entry_id}")
async def acknowledge(entry_id: str, current_phone: str = Depends(get_current_phone_number)):
    """Confirme la réception : l'entrée est supprimée immédiatement, rien
    n'est conservé côté serveur après livraison."""
    result = await _acknowledge_and_delete(entry_id, current_phone)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Message introuvable")
    if result == "forbidden":
        raise HTTPException(status_code=403, detail="Accès refusé")
    return {"status": "deleted"}
