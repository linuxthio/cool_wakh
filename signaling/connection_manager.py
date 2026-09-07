"""
Gestionnaire des connexions WebSocket actives.

Ce module ne fait que relayer : les connexions actives vivent en
mémoire (dict), rien n'est persisté ici. Seul le statut "en ligne /
hors ligne" et la dernière connexion sont répercutés dans le registre
Django (PhoneRegistry), pour la supervision.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, phone_number: str, websocket: WebSocket) -> None:
        async with self._lock:
            # Si une ancienne session existait pour ce numéro (ex: reconnexion
            # rapide), on la ferme proprement pour éviter les doublons.
            old = self._connections.get(phone_number)
            self._connections[phone_number] = websocket
        if old is not None and old is not websocket:
            try:
                await old.close()
            except Exception:
                pass

    async def disconnect(self, phone_number: str) -> None:
        async with self._lock:
            self._connections.pop(phone_number, None)

    def get(self, phone_number: str) -> Optional[WebSocket]:
        return self._connections.get(phone_number)

    def is_online(self, phone_number: str) -> bool:
        return phone_number in self._connections

    async def send_json(self, phone_number: str, payload: dict) -> bool:
        """Envoie un message JSON à un numéro s'il est connecté. Renvoie
        True si le message a pu être transmis, False sinon (hors ligne)."""
        ws = self._connections.get(phone_number)
        if ws is None:
            return False
        try:
            await ws.send_json(payload)
            return True
        except Exception:
            await self.disconnect(phone_number)
            return False


manager = ConnectionManager()
