"""
Réglages Django pour le serveur de signalisation Wakh.

Rôle de ce serveur (rappel) :
- Il ne stocke JAMAIS le contenu audio de façon permanente.
- Il sert uniquement à (1) relayer les métadonnées WebRTC (SDP/ICE) via
  FastAPI/WebSocket pour établir une connexion P2P directe entre deux
  téléphones, et (2) faire transiter temporairement un message vocal
  lorsque le destinataire est hors ligne au moment de l'envoi (mode
  "file d'attente" hybride). Un fichier mis en file d'attente est
  supprimé du disque et de la base dès qu'il a été livré et accusé de
  réception par le destinataire (ou après expiration, voir
  audioqueue.tasks.purge_expired_queue).
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "WAKH_SECRET_KEY",
    "dev-secret-key-changez-moi-en-production",
)

DEBUG = os.environ.get("WAKH_DEBUG", "1") == "1"

ALLOWED_HOSTS = os.environ.get("WAKH_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "wakh_server.apps.WakhAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "registry",
    "audioqueue",
    "textqueue",
    "mediaqueue",
    "deletequeue",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "wakh_server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "wakh_server.wsgi.application"
ASGI_APPLICATION = "wakh_server.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Spécifique Wakh -------------------------------------------------------

# Dossier où les fichiers audio sont posés TEMPORAIREMENT quand le
# destinataire est hors ligne (mode file d'attente hybride).
MEDIA_ROOT = BASE_DIR / "media" / "queued_audio"
os.makedirs(MEDIA_ROOT, exist_ok=True)

# Emplacement dédié pour les images/vidéos en attente, distinct de
# MEDIA_ROOT (réservé à l'audio) pour garder les fichiers bien séparés
# sur le disque malgré le stockage Django global partagé par défaut.
MEDIA_QUEUE_ROOT = BASE_DIR / "media" / "queued_media"
os.makedirs(MEDIA_QUEUE_ROOT, exist_ok=True)

# Durée max pendant laquelle un message en attente est conservé avant
# purge automatique (confidentialité : on ne garde pas le contenu audio
# indéfiniment si le destinataire ne se reconnecte jamais).
QUEUED_AUDIO_TTL_HOURS = int(os.environ.get("WAKH_QUEUE_TTL_HOURS", "72"))

# Taille max acceptée pour un message vocal en file d'attente (octets).
QUEUED_AUDIO_MAX_BYTES = int(os.environ.get("WAKH_QUEUE_MAX_BYTES", str(15 * 1024 * 1024)))

# Même principe pour les messages texte : durée de rétention max en file
# d'attente hors-ligne, et longueur max acceptée.
QUEUED_TEXT_TTL_HOURS = int(os.environ.get("WAKH_TEXT_QUEUE_TTL_HOURS", "72"))
TEXT_MESSAGE_MAX_LENGTH = int(os.environ.get("WAKH_TEXT_MESSAGE_MAX_LENGTH", "4000"))

# Même principe pour les images/vidéos : durée de rétention max en file
# d'attente hors-ligne, et tailles max acceptées (une vidéo pèse
# naturellement plus lourd qu'une image, d'où deux limites distinctes).
QUEUED_MEDIA_TTL_HOURS = int(os.environ.get("WAKH_MEDIA_QUEUE_TTL_HOURS", "72"))
QUEUED_IMAGE_MAX_BYTES = int(os.environ.get("WAKH_IMAGE_MAX_BYTES", str(10 * 1024 * 1024)))
QUEUED_VIDEO_MAX_BYTES = int(os.environ.get("WAKH_VIDEO_MAX_BYTES", str(50 * 1024 * 1024)))
QUEUED_DOCUMENT_MAX_BYTES = int(os.environ.get("WAKH_DOCUMENT_MAX_BYTES", str(30 * 1024 * 1024)))
QUEUED_DELETE_TTL_HOURS = int(os.environ.get("WAKH_DELETE_QUEUE_TTL_HOURS", "72"))
