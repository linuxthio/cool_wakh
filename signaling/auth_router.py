"""
Création de compte et connexion — obligatoires pour utiliser le service.

Un compte Wakh, c'est un numéro de téléphone et un code PIN à 4 chiffres
(comme un code PIN de carte SIM ou de mobile money). Aucune vérification
par SMS n'est effectuée par ce serveur de référence (il n'y a pas de
passerelle SMS configurée) : le numéro sert uniquement d'identifiant
unique, comme décrit dans le cahier des charges. Pour un déploiement réel
destiné au grand public, ajoutez une étape de vérification du numéro
(OTP par SMS) avant de considérer le compte actif.

Le code PIN est haché avec les hashers standard de Django (PBKDF2 par
défaut) — jamais stocké ni renvoyé en clair. Le hachage fonctionne de la
même façon quelle que soit la nature de la valeur d'origine (mot de passe
classique ou PIN numérique court) ; c'est uniquement la validation de
format ci-dessous (exactement 4 chiffres) qui est spécifique au PIN.
"""

from __future__ import annotations

import re
import secrets

from asgiref.sync import sync_to_async
from django.contrib.auth.hashers import check_password, make_password
from fastapi import APIRouter, Depends, Form, HTTPException
from starlette import status as http_status

from .auth import get_current_phone_number

router = APIRouter(prefix="/auth")

PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")
PIN_REGEX = re.compile(r"^\d{4}$")


@sync_to_async
def _create_account(phone_number: str, pin: str) -> str:
    from registry.models import PhoneRegistry

    already_exists = (
        PhoneRegistry.objects.filter(phone_number=phone_number).exclude(pin_hash="").exists()
    )
    if already_exists:
        raise ValueError("already_exists")

    token = secrets.token_urlsafe(32)
    PhoneRegistry.objects.update_or_create(
        phone_number=phone_number,
        defaults={"pin_hash": make_password(pin), "auth_token": token},
    )
    return token


@sync_to_async
def _authenticate(phone_number: str, pin: str) -> str | None:
    from registry.models import PhoneRegistry

    try:
        entry = PhoneRegistry.objects.get(phone_number=phone_number)
    except PhoneRegistry.DoesNotExist:
        return None

    if not entry.pin_hash or not check_password(pin, entry.pin_hash):
        return None

    token = secrets.token_urlsafe(32)
    entry.auth_token = token
    entry.save(update_fields=["auth_token"])
    return token


@sync_to_async
def _clear_token(phone_number: str) -> None:
    from registry.models import PhoneRegistry

    PhoneRegistry.objects.filter(phone_number=phone_number).update(auth_token="")


def _validate_credentials(phone_number: str, pin: str) -> str:
    normalized = phone_number.strip()
    if not PHONE_REGEX.match(normalized):
        raise HTTPException(status_code=400, detail="Numéro de téléphone invalide")
    if not PIN_REGEX.match(pin):
        raise HTTPException(status_code=400, detail="Le code PIN doit contenir exactement 4 chiffres")
    return normalized


@router.post("/register", status_code=http_status.HTTP_201_CREATED)
async def register(phone_number: str = Form(...), pin: str = Form(...)):
    """Crée un compte. Le numéro sert d'identifiant unique sur Wakh."""
    normalized = _validate_credentials(phone_number, pin)
    try:
        token = await _create_account(normalized, pin)
    except ValueError:
        raise HTTPException(status_code=409, detail="Ce numéro possède déjà un compte")
    return {"phone_number": normalized, "token": token}


@router.post("/login")
async def login(phone_number: str = Form(...), pin: str = Form(...)):
    """Connexion : renvoie un nouveau jeton, à utiliser pour le WebSocket et les appels REST protégés."""
    normalized = phone_number.strip()
    token = await _authenticate(normalized, pin)
    if not token:
        raise HTTPException(status_code=401, detail="Numéro ou code PIN incorrect")
    return {"phone_number": normalized, "token": token}


@router.post("/logout")
async def logout(current_phone: str = Depends(get_current_phone_number)):
    """Invalide le jeton actuel — une nouvelle connexion sera nécessaire."""
    await _clear_token(current_phone)
    return {"status": "logged_out"}
