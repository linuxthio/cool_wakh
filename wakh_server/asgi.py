"""
Point d'entrée ASGI unique du serveur Wakh, servi par uvicorn.

Combine :
  - Django (ORM + admin) monté sous /admin, /static
  - FastAPI (WebSocket de signalisation + REST audioqueue) monté sur le
    reste des chemins (/ws/..., /audioqueue/..., /health)

via le routage Starlette, comme demandé dans le cahier des charges.
"""

import os

import django
from django.conf import settings
from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wakh_server.settings")
django.setup()

django_asgi_app = get_asgi_application()

# Importé après django.setup() : ce module touche aux modèles Django.
from signaling.app import fastapi_app  # noqa: E402

routes = [
    Mount("/admin", app=django_asgi_app),
]

# Fichiers statiques de l'admin Django (CSS/JS). En développement, lancez
# `python manage.py collectstatic` une fois pour peupler STATIC_ROOT.
if os.path.isdir(settings.STATIC_ROOT):
    routes.append(
        Mount("/static", app=StaticFiles(directory=str(settings.STATIC_ROOT)))
    )

# Tout le reste (WebSocket de signalisation + REST audioqueue) va à FastAPI.
routes.append(Mount("/", app=fastapi_app))

application = Starlette(routes=routes)
