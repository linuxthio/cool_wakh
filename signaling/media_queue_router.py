"""
Routes REST pour le dépôt/retrait TEMPORAIRE d'une image, d'une vidéo ou
d'un document quand le destinataire est hors ligne au moment de l'envoi —
même principe que audio_queue_router.py. Les trois partagent cette file
d'attente unique (distinguées par `media_kind`) car elles ont exactement
la même forme de métadonnées.

Toutes les routes sont protégées par authentification (voir auth.py), avec
les mêmes vérifications de propriétaire que pour l'audio et le texte.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import uuid

from asgiref.sync import sync_to_async
from django.conf import settings
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette import status as http_status

from .auth import get_current_phone_number
from .connection_manager import manager

logger = logging.getLogger("wakh.mediaqueue")

router = APIRouter(prefix="/mediaqueue")

VALID_MEDIA_KINDS = {"IMAGE", "VIDEO", "DOCUMENT"}

MAX_BYTES_BY_KIND = {
    "IMAGE": lambda: settings.QUEUED_IMAGE_MAX_BYTES,
    "VIDEO": lambda: settings.QUEUED_VIDEO_MAX_BYTES,
    "DOCUMENT": lambda: settings.QUEUED_DOCUMENT_MAX_BYTES,
}


@sync_to_async
def _create_entry(
    sender: str,
    recipient: str,
    group_id: str,
    media_kind: str,
    duration_ms: int,
    size_bytes: int,
    relative_path: str,
    original_file_name: str,
) -> str:
    from mediaqueue.models import MediaQueueEntry

    entry = MediaQueueEntry.objects.create(
        sender_number=sender,
        recipient_number=recipient,
        group_id=group_id,
        media_kind=media_kind,
        duration_ms=duration_ms,
        size_bytes=size_bytes,
        media_file=relative_path,
        original_file_name=original_file_name,
    )
    return str(entry.id)


@sync_to_async
def _list_pending(recipient: str) -> list[dict]:
    from mediaqueue.models import MediaQueueEntry

    qs = MediaQueueEntry.objects.filter(
        recipient_number=recipient, status=MediaQueueEntry.PENDING
    ).order_by("created_at")
    return [
        {
            "id": str(e.id),
            "sender_number": e.sender_number,
            "group_id": e.group_id,
            "media_kind": e.media_kind,
            "original_file_name": e.original_file_name,
            "duration_ms": e.duration_ms,
            "size_bytes": e.size_bytes,
            "created_at": e.created_at.isoformat(),
        }
        for e in qs
    ]


@sync_to_async
def _get_entry_for_download(entry_id: str):
    from mediaqueue.models import MediaQueueEntry

    try:
        entry = MediaQueueEntry.objects.get(id=entry_id)
    except MediaQueueEntry.DoesNotExist:
        return None, None
    return entry.media_file.path, entry.recipient_number


@sync_to_async
def _acknowledge_and_delete(entry_id: str, expected_recipient: str) -> str:
    """Renvoie 'ok', 'not_found' ou 'forbidden'."""
    from mediaqueue.models import MediaQueueEntry

    try:
        entry = MediaQueueEntry.objects.get(id=entry_id)
    except MediaQueueEntry.DoesNotExist:
        return "not_found"
    if entry.recipient_number != expected_recipient:
        return "forbidden"
    if entry.media_file:
        entry.media_file.delete(save=False)
    entry.delete()
    return "ok"


@router.post("/upload", status_code=http_status.HTTP_201_CREATED)
async def upload_media(
    sender_number: str = Form(...),
    recipient_number: str = Form(...),
    media_kind: str = Form(...),
    duration_ms: int = Form(0),
    group_id: str = Form(""),
    media: UploadFile = File(...),
    current_phone: str = Depends(get_current_phone_number),
):
    """Dépose une image, une vidéo ou un document en attente car le
    destinataire est hors ligne. Appelé par le client seulement après
    échec (ou absence) de connexion P2P directe — même principe que
    /audioqueue/upload."""
    if sender_number != current_phone:
        raise HTTPException(status_code=403, detail="Le numéro expéditeur ne correspond pas au compte connecté")

    kind = media_kind.strip().upper()
    if kind not in VALID_MEDIA_KINDS:
        raise HTTPException(status_code=400, detail="media_kind doit être IMAGE, VIDEO ou DOCUMENT")

    body = await media.read()
    size_bytes = len(body)

    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Fichier vide")
    max_bytes = MAX_BYTES_BY_KIND[kind]()
    if size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail=f"Fichier trop volumineux (max {max_bytes} octets)")

    original_name = media.filename or ""
    extension = os.path.splitext(original_name)[1] or (".jpg" if kind == "IMAGE" else ".mp4" if kind == "VIDEO" else "")
    filename = f"{uuid.uuid4().hex}{extension}"
    absolute_path = os.path.join(settings.MEDIA_QUEUE_ROOT, filename)
    with open(absolute_path, "wb") as f:
        f.write(body)

    entry_id = await _create_entry(
        sender=sender_number,
        recipient=recipient_number,
        group_id=group_id.strip(),
        media_kind=kind,
        duration_ms=duration_ms,
        size_bytes=size_bytes,
        relative_path=filename,
        original_file_name=original_name if kind == "DOCUMENT" else "",
    )

    # Si le destinataire se reconnecte pendant que ce média patiente, le
    # websocket le lui signale au moment de sa connexion (pending_media).
    # On tente aussi une notification immédiate au cas où il serait déjà
    # en ligne (ex: message précédent échoué puis relance rapide).
    await manager.send_json(recipient_number, {"type": "pending_media", "count": 1})

    return {"queued_message_id": entry_id}


@router.get("/pending/{phone_number}")
async def list_pending(phone_number: str, current_phone: str = Depends(get_current_phone_number)):
    """Liste les images/vidéos en attente pour ce numéro (appelé par le
    client juste après s'être reconnecté)."""
    if phone_number != current_phone:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return {"pending": await _list_pending(phone_number)}


@router.get("/download/{entry_id}")
async def download_media(entry_id: str, current_phone: str = Depends(get_current_phone_number)):
    path, recipient = await _get_entry_for_download(entry_id)
    if path is None or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Média introuvable ou déjà livré")
    if recipient != current_phone:
        raise HTTPException(status_code=403, detail="Accès refusé")
    media_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=os.path.basename(path))


# NOTE : /download/{entry_id} ci-dessus sert le fichier avec son nom
# généré (UUID) — le nom d'origine du document (original_file_name) est
# transmis séparément via /pending/{phone_number}, à charge du client de
# renommer le fichier téléchargé pour l'afficher correctement.


@router.post("/ack/{entry_id}")
async def acknowledge(entry_id: str, current_phone: str = Depends(get_current_phone_number)):
    """Confirme la réception : le fichier et son entrée sont supprimés
    immédiatement, rien n'est conservé côté serveur après livraison."""
    result = await _acknowledge_and_delete(entry_id, current_phone)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Média introuvable")
    if result == "forbidden":
        raise HTTPException(status_code=403, detail="Accès refusé")
    return {"status": "deleted"}
