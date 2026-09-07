# Wakh — Serveur de signalisation

Serveur ASGI combinant **Django** (ORM + admin) et **FastAPI** (WebSocket
temps réel + REST), servi par **uvicorn**.

## Rôle (et ce qu'il ne fait PAS)

Ce serveur met deux téléphones en relation pour qu'ils établissent une
connexion **WebRTC P2P directe** (DataChannel) et s'échangent messages
vocaux et texte **de téléphone à téléphone**, sans jamais transiter par
le serveur en fonctionnement normal.

Le serveur ne fait que :
1. **Authentifier** les comptes (numéro de téléphone + code PIN à 4 chiffres) —
   un compte est obligatoire pour utiliser le service.
2. **Relayer** les métadonnées WebRTC (offres/réponses SDP, ICE candidates)
   via WebSocket — rien n'est persisté, c'est un simple pont temps réel.
3. Tenir un **registre léger de présence** (numéro connu, en ligne ou non,
   dernière connexion) via Django/SQLite, pour la supervision.
4. **Mode hybride hors-ligne** : si le destinataire n'est pas connecté au
   moment de l'envoi, le message (audio, texte, image ou vidéo) est
   déposé temporairement sur le serveur. Il est supprimé dès qu'il a été
   livré et accusé de réception, ou automatiquement après son TTL (72h
   par défaut) s'il n'est jamais réclamé. Ce n'est **pas un historique de
   conversation**.

**Les groupes sont un concept purement côté application** : ce serveur
n'a aucune notion de "groupe". Un message envoyé à un groupe est
simplement envoyé individuellement à chaque membre (P2P ou file
d'attente, exactement comme un message 1-à-1) ; le champ optionnel
`group_id` transporté par les files d'attente sert uniquement à ce que
l'app du destinataire sache rattacher le message reçu à la bonne
conversation de groupe une fois récupéré.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py collectstatic --noinput   # CSS/JS de l'admin Django
python manage.py createsuperuser           # compte pour /admin (distinct des comptes Wakh)
```

## Lancer le serveur

```bash
uvicorn wakh_server.asgi:application --host 0.0.0.0 --port 8000
```

- **Page d'accueil** : `http://<host>:8000/` — statistiques en direct (numéros enregistrés, en ligne, messages audio/texte en attente), rafraîchies automatiquement toutes les 5 secondes.
- **Tableau de bord admin** : `http://<host>:8000/admin/` — mêmes statistiques en cartes, au-dessus de la liste habituelle des applications.
- Documentation API interactive (générée par FastAPI) : `http://<host>:8000/docs`
- Healthcheck : `http://<host>:8000/health`
- WebSocket de signalisation : `ws://<host>:8000/ws/{numero_de_telephone}?token=...`
- Files d'attente hors-ligne : `http://<host>:8000/audioqueue/...`, `/textqueue/...` et `/mediaqueue/...`

## Authentification — obligatoire pour utiliser le service

Un compte Wakh, c'est un numéro de téléphone et un code PIN à 4 chiffres
(comme un PIN de carte SIM ou de mobile money). **Aucune
vérification par SMS n'est effectuée par ce serveur de référence** (pas de
passerelle SMS configurée) : le numéro sert d'identifiant unique, comme
décrit dans le cahier des charges. Pour un déploiement destiné au grand
public, ajoutez une étape de vérification du numéro (OTP par SMS) avant de
considérer le compte actif — ce serveur ne fait pas cette vérification.

| Méthode | Route | Champs | Usage |
|---|---|---|---|
| POST | `/auth/register` | `phone_number`, `pin` (4 chiffres) | Crée le compte, renvoie un jeton |
| POST | `/auth/login` | `phone_number`, `pin` (4 chiffres) | Connexion, renvoie un nouveau jeton |
| POST | `/auth/logout` | *(en-tête `Authorization`)* | Invalide le jeton en cours |

Le jeton renvoyé doit ensuite être fourni :
- en paramètre de requête `?token=...` pour le WebSocket de signalisation
  (rejeté avec le code de fermeture `4401` si absent/invalide) ;
- en en-tête `Authorization: Bearer <token>` pour toutes les routes REST
  protégées (`/audioqueue/*`, `/textqueue/*`). Le serveur vérifie en plus
  que le compte authentifié correspond bien à l'expéditeur (upload) ou au
  destinataire (pending/download/ack) concerné : un compte ne peut jamais
  usurper un autre expéditeur ni lire les messages d'un autre destinataire.

Les mots de passe sont hachés avec les hashers standard de Django
(PBKDF2 par défaut) — jamais stockés ni renvoyés en clair, et exclus de
l'admin Django.

## Protocole WebSocket

Une connexion par numéro de téléphone, sur `/ws/{phone_number}?token=...`.

| Direction | type | Champs |
|---|---|---|
| Client → Serveur | `presence_check` | `target` |
| Client → Serveur | `offer` / `answer` / `ice_candidate` / `hangup` | `target`, `sdp` / `candidate` |
| Serveur → Client | `presence_status` | `target`, `online` |
| Serveur → Client | `offer` / `answer` / `ice_candidate` / `hangup` | `from`, `sdp` / `candidate` |
| Serveur → Client | `pending_audio` | `count` (message(s) vocaux en attente) |
| Serveur → Client | `pending_text` | `count` (message(s) texte en attente) |
| Serveur → Client | `pending_media` | `count` (image(s)/vidéo(s)/document(s) en attente) |
| Serveur → Client | `pending_delete` | `count` (demande(s) de suppression en attente) |
| Serveur → Client | `error` | `message` |

## Endpoints REST — files d'attente hors-ligne (protégées, voir Authentification)

| Méthode | Route | Usage |
|---|---|---|
| POST | `/audioqueue/upload` | Dépose un message vocal — `multipart/form-data` : `sender_number`, `recipient_number`, `duration_ms`, `group_id` (optionnel), `audio` |
| GET | `/audioqueue/pending/{phone_number}` | Liste les messages vocaux en attente pour ce numéro |
| GET | `/audioqueue/download/{id}` | Télécharge le fichier |
| POST | `/audioqueue/ack/{id}` | Confirme la réception → suppression immédiate côté serveur |
| POST | `/textqueue/upload` | Dépose un message texte — `sender_number`, `recipient_number`, `content`, `group_id` (optionnel) |
| GET | `/textqueue/pending/{phone_number}` | Liste les messages texte en attente, contenu inclus |
| POST | `/textqueue/ack/{id}` | Confirme la réception → suppression immédiate côté serveur |
| POST | `/mediaqueue/upload` | Dépose une image/vidéo/document — `multipart/form-data` : `sender_number`, `recipient_number`, `media_kind` (`IMAGE`/`VIDEO`/`DOCUMENT`), `duration_ms` (vidéo uniquement), `group_id` (optionnel), `media` |
| GET | `/mediaqueue/pending/{phone_number}` | Liste les images/vidéos/documents en attente pour ce numéro (`original_file_name` inclus pour un document) |
| GET | `/mediaqueue/download/{id}` | Télécharge le fichier |
| POST | `/mediaqueue/ack/{id}` | Confirme la réception → suppression immédiate côté serveur |
| POST | `/deletequeue/upload` | Dépose une demande de "suppression pour tout le monde" — `sender_number`, `recipient_number`, `target_message_id`, `group_id` (optionnel) |
| GET | `/deletequeue/pending/{phone_number}` | Liste les demandes de suppression en attente pour ce numéro |
| POST | `/deletequeue/ack/{id}` | Confirme la prise en compte → suppression immédiate côté serveur |

## Purge automatique

Ajouter des tâches cron pour purger les messages en attente jamais
réclamés au-delà de leur TTL de confidentialité :

```
*/30 * * * * cd /path/to/wakh-server && .venv/bin/python manage.py purge_audio_queue
*/30 * * * * cd /path/to/wakh-server && .venv/bin/python manage.py purge_text_queue
*/30 * * * * cd /path/to/wakh-server && .venv/bin/python manage.py purge_media_queue
```

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `WAKH_SECRET_KEY` | clé de dev | Clé secrète Django (à définir en prod) |
| `WAKH_DEBUG` | `1` | Mode debug Django |
| `WAKH_ALLOWED_HOSTS` | `*` | Hôtes autorisés, séparés par des virgules |
| `WAKH_QUEUE_TTL_HOURS` | `72` | Durée de rétention max d'un message vocal en attente |
| `WAKH_QUEUE_MAX_BYTES` | `15728640` (15 Mo) | Taille max d'un message vocal en attente |
| `WAKH_TEXT_QUEUE_TTL_HOURS` | `72` | Durée de rétention max d'un message texte en attente |
| `WAKH_TEXT_MESSAGE_MAX_LENGTH` | `4000` | Longueur max d'un message texte |
| `WAKH_MEDIA_QUEUE_TTL_HOURS` | `72` | Durée de rétention max d'une image/vidéo en attente |
| `WAKH_IMAGE_MAX_BYTES` | `10485760` (10 Mo) | Taille max d'une image en attente |
| `WAKH_VIDEO_MAX_BYTES` | `52428800` (50 Mo) | Taille max d'une vidéo en attente |
| `WAKH_DOCUMENT_MAX_BYTES` | `31457280` (30 Mo) | Taille max d'un document en attente |
| `WAKH_DELETE_QUEUE_TTL_HOURS` | `72` | Durée de rétention max d'une demande de suppression en attente |

## Limites connues de cette authentification

Ce schéma est adapté à un projet personnel/démonstration, pas audité pour
une mise en production grand public : pas de vérification du numéro par
SMS, pas de limitation de débit sur `/auth/login` (permettrait en théorie
un essai de mots de passe par force brute), un seul jeton actif à la fois
par compte (une nouvelle connexion invalide la précédente). À durcir avant
tout déploiement réel.
# cool_wakh
# cool_wakh
