"""
Routes REST pour la demande de "suppression pour tout le monde" quand le
destinataire est hors ligne au moment de la demande — même principe que
audio_queue_router.py, en plus simple : aucun contenu, juste un
identifiant de message à supprimer chez le destinataire.

Toutes les routes sont protégées par authentification (voir auth.py), avec
les mêmes vérifications de propriétaire que les autres files d'attente.
"""

from __future__ import annotations

import logging

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, Form, HTTPException
from starlette import status as http_status

from .auth import get_current_phone_number
from .connection_manager import manager

logger = logging.getLogger("wakh.deletequeue")

router = APIRouter(prefix="/deletequeue")


@sync_to_async
def _create_entry(sender: str, recipient: str, group_id: str, target_message_id: str) -> str:
    from deletequeue.models import DeleteQueueEntry

    entry = DeleteQueueEntry.objects.create(
        sender_number=sender,
        recipient_number=recipient,
        group_id=group_id,
        target_message_id=target_message_id,
    )
    return str(entry.id)


@sync_to_async
def _list_pending(recipient: str) -> list[dict]:
    from deletequeue.models import DeleteQueueEntry

    qs = DeleteQueueEntry.objects.filter(recipient_number=recipient).order_by("created_at")
    return [
        {
            "id": str(e.id),
            "sender_number": e.sender_number,
            "group_id": e.group_id,
            "target_message_id": e.target_message_id,
            "created_at": e.created_at.isoformat(),
        }
        for e in qs
    ]


@sync_to_async
def _acknowledge_and_delete(entry_id: str, expected_recipient: str) -> str:
    """Renvoie 'ok', 'not_found' ou 'forbidden'."""
    from deletequeue.models import DeleteQueueEntry

    try:
        entry = DeleteQueueEntry.objects.get(id=entry_id)
    except DeleteQueueEntry.DoesNotExist:
        return "not_found"
    if entry.recipient_number != expected_recipient:
        return "forbidden"
    entry.delete()
    return "ok"


@router.post("/upload", status_code=http_status.HTTP_201_CREATED)
async def upload_delete_request(
    sender_number: str = Form(...),
    recipient_number: str = Form(...),
    target_message_id: str = Form(...),
    group_id: str = Form(""),
    current_phone: str = Depends(get_current_phone_number),
):
    """Dépose une demande de suppression en attente car le destinataire
    est hors ligne — même principe que /audioqueue/upload."""
    if sender_number != current_phone:
        raise HTTPException(status_code=403, detail="Le numéro expéditeur ne correspond pas au compte connecté")

    entry_id = await _create_entry(sender_number, recipient_number, group_id.strip(), target_message_id)

    await manager.send_json(recipient_number, {"type": "pending_delete", "count": 1})

    return {"queued_message_id": entry_id}


@router.get("/pending/{phone_number}")
async def list_pending(phone_number: str, current_phone: str = Depends(get_current_phone_number)):
    """Liste les demandes de suppression en attente pour ce numéro."""
    if phone_number != current_phone:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return {"pending": await _list_pending(phone_number)}


@router.post("/ack/{entry_id}")
async def acknowledge(entry_id: str, current_phone: str = Depends(get_current_phone_number)):
    """Confirme la prise en compte : l'entrée est supprimée immédiatement."""
    result = await _acknowledge_and_delete(entry_id, current_phone)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Demande introuvable")
    if result == "forbidden":
        raise HTTPException(status_code=403, detail="Accès refusé")
    return {"status": "deleted"}
