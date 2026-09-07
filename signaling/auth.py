"""
Vérification de l'authentification pour les routes REST protégées.

Un compte est créé via POST /auth/register puis un jeton est obtenu via
POST /auth/register ou /auth/login (voir auth_router.py). Ce jeton doit
être présenté dans l'en-tête `Authorization: Bearer <token>` pour tout
appel aux routes protégées (dépôt/retrait en file d'attente), et en
paramètre de requête `?token=...` pour la connexion WebSocket (voir
fastapi_app.py).
"""

from __future__ import annotations

from asgiref.sync import sync_to_async
from fastapi import Header, HTTPException, status


@sync_to_async
def _lookup_token(token: str) -> str | None:
    from registry.models import PhoneRegistry

    if not token:
        return None
    try:
        return PhoneRegistry.objects.exclude(auth_token="").get(auth_token=token).phone_number
    except PhoneRegistry.DoesNotExist:
        return None


async def get_current_phone_number(authorization: str = Header(default="")) -> str:
    """Dépendance FastAPI : renvoie le numéro authentifié ou lève une 401."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise")

    token = authorization.removeprefix("Bearer ").strip()
    phone_number = await _lookup_token(token)
    if not phone_number:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalide ou expiré")

    return phone_number


@sync_to_async
def verify_token_for_phone(phone_number: str, token: str) -> bool:
    """Utilisé par le WebSocket de signalisation (voir fastapi_app.py)."""
    from registry.models import PhoneRegistry

    if not token:
        return False
    return (
        PhoneRegistry.objects.exclude(auth_token="")
        .filter(phone_number=phone_number, auth_token=token)
        .exists()
    )
