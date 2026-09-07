"""
Serveur de signalisation WebRTC (FastAPI).

Rôle STRICT de ce fichier : mettre deux téléphones en relation en
relayant des métadonnées techniques (offres/réponses SDP, ICE
candidates) pour qu'ils établissent une connexion P2P directe. Aucun
contenu de message n'y transite ni n'y est stocké — seul le protocole
audioqueue/textqueue (fichiers ou texte séparés) gère la sauvegarde
temporaire en cas de destinataire hors ligne.

Un compte (POST /auth/register) et une connexion (POST /auth/login) sont
nécessaires avant d'ouvrir cette connexion : le jeton obtenu doit être
passé en paramètre de requête `?token=...` — voir auth.py/auth_router.py.
Sans jeton valide pour ce numéro, la connexion est refusée
(code de fermeture 4401).

Protocole WebSocket (JSON), une connexion par numéro de téléphone,
sur `/ws/{phone_number}?token=...` :

  Client -> Serveur
    {"type": "presence_check", "target": "+221771234567"}
    {"type": "offer",          "target": "...", "sdp": "..."}
    {"type": "answer",         "target": "...", "sdp": "..."}
    {"type": "ice_candidate",  "target": "...", "candidate": {...}}
    {"type": "hangup",         "target": "..."}

  Serveur -> Client
    {"type": "presence_status", "target": "...", "online": true|false}
    {"type": "offer",           "from": "...", "sdp": "..."}
    {"type": "answer",          "from": "...", "sdp": "..."}
    {"type": "ice_candidate",   "from": "...", "candidate": {...}}
    {"type": "hangup",          "from": "..."}
    {"type": "pending_audio",   "count": N}   # à la connexion, s'il y a
                                               # des messages audio en
                                               # attente pour ce numéro
    {"type": "pending_text",    "count": N}   # idem, pour les messages
                                               # texte en attente
    {"type": "pending_media",   "count": N}   # idem, pour les images et
                                               # vidéos en attente
    {"type": "pending_delete",  "count": N}   # idem, pour les demandes de
                                               # suppression en attente
    {"type": "error",           "message": "..."}
"""

from __future__ import annotations

import logging

from asgiref.sync import sync_to_async
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .auth import verify_token_for_phone
from .connection_manager import manager

logger = logging.getLogger("wakh.signaling")

router = APIRouter()

RELAYED_TYPES = {"offer", "answer", "ice_candidate", "hangup"}

# Code de fermeture WebSocket dédié à un jeton absent/invalide (plage
# privée 4000-4999 réservée aux applications, voir RFC 6455 §7.4.2).
WS_CLOSE_UNAUTHORIZED = 4401


@sync_to_async
def _mark_online(phone_number: str) -> None:
    from registry.models import PhoneRegistry

    PhoneRegistry.objects.filter(phone_number=phone_number).update(is_online=True)


@sync_to_async
def _mark_offline(phone_number: str) -> None:
    from registry.models import PhoneRegistry

    PhoneRegistry.objects.filter(phone_number=phone_number).update(is_online=False)


@sync_to_async
def _pending_audio_count(phone_number: str) -> int:
    from audioqueue.models import AudioQueueEntry

    return AudioQueueEntry.objects.filter(
        recipient_number=phone_number, status=AudioQueueEntry.PENDING
    ).count()


@sync_to_async
def _pending_text_count(phone_number: str) -> int:
    from textqueue.models import TextQueueEntry

    return TextQueueEntry.objects.filter(
        recipient_number=phone_number, status=TextQueueEntry.PENDING
    ).count()


@sync_to_async
def _pending_media_count(phone_number: str) -> int:
    from mediaqueue.models import MediaQueueEntry

    return MediaQueueEntry.objects.filter(
        recipient_number=phone_number, status=MediaQueueEntry.PENDING
    ).count()


@sync_to_async
def _pending_delete_count(phone_number: str) -> int:
    from deletequeue.models import DeleteQueueEntry

    return DeleteQueueEntry.objects.filter(recipient_number=phone_number).count()


@router.websocket("/ws/{phone_number}")
async def signaling_socket(websocket: WebSocket, phone_number: str) -> None:
    token = websocket.query_params.get("token", "")
    await websocket.accept()

    if not await verify_token_for_phone(phone_number, token):
        await websocket.send_json({"type": "error", "message": "Authentification invalide"})
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        logger.info("rejected (jeton invalide) %s", phone_number)
        return

    await manager.connect(phone_number, websocket)
    await _mark_online(phone_number)
    logger.info("connect %s", phone_number)

    pending_audio = await _pending_audio_count(phone_number)
    if pending_audio:
        await websocket.send_json({"type": "pending_audio", "count": pending_audio})

    pending_text = await _pending_text_count(phone_number)
    if pending_text:
        await websocket.send_json({"type": "pending_text", "count": pending_text})

    pending_media = await _pending_media_count(phone_number)
    if pending_media:
        await websocket.send_json({"type": "pending_media", "count": pending_media})

    pending_delete = await _pending_delete_count(phone_number)
    if pending_delete:
        await websocket.send_json({"type": "pending_delete", "count": pending_delete})

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "presence_check":
                target = message.get("target")
                await websocket.send_json(
                    {
                        "type": "presence_status",
                        "target": target,
                        "online": manager.is_online(target) if target else False,
                    }
                )

            elif msg_type in RELAYED_TYPES:
                target = message.get("target")
                if not target:
                    await websocket.send_json({"type": "error", "message": "target manquant"})
                    continue
                outgoing = dict(message)
                outgoing.pop("target", None)
                outgoing["from"] = phone_number
                delivered = await manager.send_json(target, outgoing)
                if not delivered:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"{target} est hors ligne",
                            "target": target,
                            "in_response_to": msg_type,
                        }
                    )

            else:
                await websocket.send_json(
                    {"type": "error", "message": f"type de message inconnu: {msg_type}"}
                )

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(phone_number)
        await _mark_offline(phone_number)
        logger.info("disconnect %s", phone_number)
