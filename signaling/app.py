from asgiref.sync import sync_to_async
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from wakh_server.stats import get_dashboard_stats

from .audio_queue_router import router as audio_queue_router
from .auth_router import router as auth_router
from .delete_queue_router import router as delete_queue_router
from .fastapi_app import router as signaling_router
from .homepage import render_homepage
from .media_queue_router import router as media_queue_router
from .text_queue_router import router as text_queue_router

fastapi_app = FastAPI(
    title="Wakh - Serveur de signalisation",
    description=(
        "Relaie uniquement les métadonnées WebRTC (SDP/ICE) et gère le "
        "dépôt temporaire d'un message vocal quand le destinataire est "
        "hors ligne. Ne stocke jamais de contenu audio de façon "
        "permanente."
    ),
    version="1.0.0",
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(auth_router)
fastapi_app.include_router(signaling_router)
fastapi_app.include_router(audio_queue_router)
fastapi_app.include_router(text_queue_router)
fastapi_app.include_router(media_queue_router)
fastapi_app.include_router(delete_queue_router)


@fastapi_app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def homepage():
    stats = await sync_to_async(get_dashboard_stats)()
    return render_homepage(stats)


@fastapi_app.get("/stats")
async def stats_endpoint():
    """Compteurs publics et non sensibles, utilisés pour rafraîchir la page d'accueil."""
    return await sync_to_async(get_dashboard_stats)()


@fastapi_app.get("/health")
async def health():
    return {"status": "ok"}
