"""
Page d'accueil du serveur, servie par FastAPI sur GET /. Design autonome
(pas de dépendance externe/CDN) pour rester fiable même sans accès
Internet sortant, dans la même palette bleu ciel que l'application Wakh.
"""


def render_homepage(stats: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wakh — Serveur de signalisation</title>
<style>
  :root {{
    --sky: #0EA5E9;
    --sky-dark: #0284C7;
    --sky-light: #7DD3FC;
    --bg: #F8FBFF;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: #0F172A;
  }}
  .hero {{
    background: linear-gradient(135deg, var(--sky), var(--sky-light));
    color: #fff;
    padding: 72px 24px 96px;
    text-align: center;
    border-radius: 0 0 40px 40px;
  }}
  .hero h1 {{ font-size: 42px; margin: 0 0 10px; font-weight: 800; letter-spacing: -1px; }}
  .hero p {{ font-size: 17px; opacity: .95; margin: 0 auto; max-width: 520px; line-height: 1.5; }}
  .status-pill {{
    display: inline-flex; align-items: center; gap: 8px; margin-top: 22px;
    background: rgba(255,255,255,.18); padding: 8px 18px; border-radius: 999px; font-size: 14px;
  }}
  .dot {{
    width: 8px; height: 8px; border-radius: 50%; background: #22C55E;
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0%   {{ box-shadow: 0 0 0 0 rgba(34,197,94,.6); }}
    70%  {{ box-shadow: 0 0 0 8px rgba(34,197,94,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(34,197,94,0); }}
  }}

  .container {{ max-width: 960px; margin: -56px auto 0; padding: 0 24px 64px; }}

  .stats {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px; margin-bottom: 40px;
  }}
  .stat-card {{
    background: #fff; border-radius: 18px; padding: 26px; text-align: center;
    box-shadow: 0 10px 30px rgba(14,165,233,.12);
  }}
  .stat-value {{ font-size: 36px; font-weight: 800; color: var(--sky-dark); }}
  .stat-label {{ font-size: 13px; color: #64748B; margin-top: 6px; }}

  .cards {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 20px; margin-bottom: 40px;
  }}
  .card {{
    background: #fff; border-radius: 18px; padding: 24px;
    box-shadow: 0 6px 20px rgba(15,23,42,.06);
    transition: transform .2s ease, box-shadow .2s ease;
  }}
  .card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 28px rgba(14,165,233,.18); }}
  .card .icon {{
    width: 44px; height: 44px; border-radius: 12px;
    background: linear-gradient(135deg, var(--sky), var(--sky-dark));
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 20px; margin-bottom: 14px;
  }}
  .card h3 {{ margin: 0 0 8px; font-size: 16px; }}
  .card p {{ margin: 0; font-size: 14px; color: #475569; line-height: 1.5; }}

  .links {{ display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; }}
  .btn {{
    text-decoration: none; padding: 12px 22px; border-radius: 12px;
    font-weight: 600; font-size: 14px; transition: transform .15s ease;
  }}
  .btn:hover {{ transform: translateY(-2px); }}
  .btn-primary {{ background: var(--sky); color: #fff; }}
  .btn-secondary {{ background: #fff; color: var(--sky-dark); border: 1px solid #E0F2FE; }}

  footer {{ text-align: center; padding: 24px; color: #94A3B8; font-size: 13px; }}
</style>
</head>
<body>
  <div class="hero">
    <h1>Wakh</h1>
    <p>Serveur de signalisation pour la messagerie vocale peer-to-peer.
       Relaie uniquement les métadonnées WebRTC — jamais le contenu audio.</p>
    <div class="status-pill"><span class="dot"></span> Serveur actif</div>
  </div>

  <div class="container">
    <div class="stats">
      <div class="stat-card">
        <div class="stat-value" id="stat-total">{stats['total_numbers']}</div>
        <div class="stat-label">Numéros enregistrés</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-online">{stats['online_now']}</div>
        <div class="stat-label">En ligne actuellement</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-pending-audio">{stats['pending_audio']}</div>
        <div class="stat-label">Messages vocaux en attente</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-pending-text">{stats['pending_text']}</div>
        <div class="stat-label">Messages texte en attente</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-pending-media">{stats['pending_media']}</div>
        <div class="stat-label">Images/vidéos/documents en attente</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" id="stat-pending-delete">{stats['pending_delete']}</div>
        <div class="stat-label">Suppressions en attente</div>
      </div>
    </div>

    <div class="cards">
      <div class="card">
        <div class="icon">&#8644;</div>
        <h3>Relais de signalisation</h3>
        <p>Met en relation deux téléphones via WebSocket pour échanger offres, réponses et candidats ICE, afin d'établir une connexion P2P directe.</p>
      </div>
      <div class="card">
        <div class="icon">&#128274;</div>
        <h3>Aucun stockage permanent</h3>
        <p>Le contenu audio transite de téléphone à téléphone. En file d'attente hors-ligne, un message est supprimé dès sa livraison confirmée.</p>
      </div>
      <div class="card">
        <div class="icon">&#128225;</div>
        <h3>Présence en temps réel</h3>
        <p>Un registre léger (Django) garde trace des numéros en ligne, sans jamais contenir de contenu de message.</p>
      </div>
    </div>

    <div class="links">
      <a class="btn btn-primary" href="/admin/">Administration</a>
      <a class="btn btn-secondary" href="/docs">Documentation API</a>
      <a class="btn btn-secondary" href="/health">Statut (JSON)</a>
    </div>
  </div>

  <footer>Wakh — messagerie vocale peer-to-peer</footer>

  <script>
    async function refreshStats() {{
      try {{
        const res = await fetch('/stats');
        const data = await res.json();
        document.getElementById('stat-total').textContent = data.total_numbers;
        document.getElementById('stat-online').textContent = data.online_now;
        document.getElementById('stat-pending-audio').textContent = data.pending_audio;
        document.getElementById('stat-pending-text').textContent = data.pending_text;
        document.getElementById('stat-pending-media').textContent = data.pending_media;
        document.getElementById('stat-pending-delete').textContent = data.pending_delete;
      }} catch (e) {{ /* silencieux : on garde les dernières valeurs affichées */ }}
    }}
    setInterval(refreshStats, 5000);
  </script>
</body>
</html>"""
