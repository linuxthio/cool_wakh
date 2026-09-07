"""
Routes REST pour le dépôt/retrait TEMPORAIRE d'un message vocal quand le
destinataire est hors ligne au moment de l'envoi (mode hybride).

Ce n'est PAS un historique : chaque fichier est supprimé dès qu'il a été
livré et accusé de réception (voir /audioqueue/ack/{id}), et les entrées
trop anciennes sont purgées automatiquement (voir audioqueue/tasks.py).

Toutes les routes sont protégées : il faut un compte (POST /auth/register)
et être connecté (POST /auth/login) pour les utiliser. On vérifie en plus
que le numéro authentifié correspond bien à l'expéditeur (upload) ou au
destinataire (pending/download/ack) concerné, pour qu'un compte ne puisse
jamais lire ou manipuler les messages d'un autre.
"""

from __future__ import annotations

import logging
import os
import uuid

from asgiref.sync import sync_to_async
from django.conf import settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette import status as http_status

from .auth import get_current_phone_number
from .connection_manager import manager

logger = logging.getLogger("wakh.audioqueue")

router = APIRouter(prefix="/audioqueue")


@sync_to_async
def _create_entry(sender: str, recipient: str, group_id: str, duration_ms: int, size_bytes: int, relative_path: str):
    from audioqueue.models import AudioQueueEntry

    entry = AudioQueueEntry.objects.create(
        sender_number=sender,
        recipient_number=recipient,
        group_id=group_id,
        duration_ms=duration_ms,
        size_bytes=size_bytes,
        audio_file=relative_path,
    )
    return str(entry.id)


@sync_to_async
def _list_pending(recipient: str) -> list[dict]:
    from audioqueue.models import AudioQueueEntry

    qs = AudioQueueEntry.objects.filter(
        recipient_number=recipient, status=AudioQueueEntry.PENDING
    ).order_by("created_at")
    return [
        {
            "id": str(e.id),
            "sender_number": e.sender_number,
            "group_id": e.group_id,
            "duration_ms": e.duration_ms,
            "size_bytes": e.size_bytes,
            "created_at": e.created_at.isoformat(),
        }
        for e in qs
    ]


@sync_to_async
def _get_entry_for_download(entry_id: str):
    from audioqueue.models import AudioQueueEntry

    try:
        entry = AudioQueueEntry.objects.get(id=entry_id)
    except AudioQueueEntry.DoesNotExist:
        return None, None
    return entry.audio_file.path, entry.recipient_number


@sync_to_async
def _acknowledge_and_delete(entry_id: str, expected_recipient: str) -> str:
    """Renvoie 'ok', 'not_found' ou 'forbidden'."""
    from audioqueue.models import AudioQueueEntry

    try:
        entry = AudioQueueEntry.objects.get(id=entry_id)
    except AudioQueueEntry.DoesNotExist:
        return "not_found"
    if entry.recipient_number != expected_recipient:
        return "forbidden"
    if entry.audio_file:
        entry.audio_file.delete(save=False)
    entry.delete()
    return "ok"


@router.post("/upload", status_code=http_status.HTTP_201_CREATED)
async def upload_audio(
    sender_number: str = Form(...),
    recipient_number: str = Form(...),
    duration_ms: int = Form(...),
    group_id: str = Form(""),
    audio: UploadFile = File(...),
    current_phone: str = Depends(get_current_phone_number),
):
    """Dépose un message vocal en attente car le destinataire est hors
    ligne. Appelé par le client seulement après échec (ou absence) de
    connexion P2P directe."""
    if sender_number != current_phone:
        raise HTTPException(status_code=403, detail="Le numéro expéditeur ne correspond pas au compte connecté")

    body = await audio.read()
    size_bytes = len(body)

    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Fichier audio vide")
    if size_bytes > settings.QUEUED_AUDIO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Fichier audio trop volumineux")

    filename = f"{uuid.uuid4().hex}.m4a"
    absolute_path = os.path.join(settings.MEDIA_ROOT, filename)
    with open(absolute_path, "wb") as f:
        f.write(body)

    entry_id = await _create_entry(
        sender=sender_number,
        recipient=recipient_number,
        group_id=group_id.strip(),
        duration_ms=duration_ms,
        size_bytes=size_bytes,
        relative_path=filename,
    )

    # Si le destinataire se reconnecte pendant que ce message patiente,
    # le websocket le lui signale au moment du "register" (pending_audio).
    # On tente aussi une notification immédiate au cas où il serait déjà
    # en ligne (ex: message précédent échoué puis relance rapide).
    await manager.send_json(recipient_number, {"type": "pending_audio", "count": 1})

    return {"queued_message_id": entry_id}


@router.get("/pending/{phone_number}")
async def list_pending(phone_number: str, current_phone: str = Depends(get_current_phone_number)):
    """Liste les messages vocaux en attente pour ce numéro (appelé par
    le client juste après s'être reconnecté)."""
    if phone_number != current_phone:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return {"pending": await _list_pending(phone_number)}


@router.get("/download/{entry_id}")
async def download_audio(entry_id: str, current_phone: str = Depends(get_current_phone_number)):
    path, recipient = await _get_entry_for_download(entry_id)
    if path is None or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Message introuvable ou déjà livré")
    if recipient != current_phone:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return FileResponse(path, media_type="audio/mp4", filename=f"{entry_id}.m4a")


@router.post("/ack/{entry_id}")
async def acknowledge(entry_id: str, current_phone: str = Depends(get_current_phone_number)):
    """Confirme la réception : le fichier et son entrée sont supprimés
    immédiatement, rien n'est conservé côté serveur après livraison."""
    result = await _acknowledge_and_delete(entry_id, current_phone)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Message introuvable")
    if result == "forbidden":
        raise HTTPException(status_code=403, detail="Accès refusé")
    return {"status": "deleted"}
