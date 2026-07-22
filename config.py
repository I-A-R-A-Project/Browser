import os
import ssl
import urllib.request

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

APP_NAME = "MiniBrowser"

BASE_DIR = os.path.join(os.path.expanduser("~"), ".minibrowser")
USERSCRIPTS_DIR = os.path.join(BASE_DIR, "userscripts")
DB_PATH = os.path.join(BASE_DIR, "browser.db")
PROFILE_STORAGE = os.path.join(BASE_DIR, "profile")
ICONS_DIR = os.path.join(BASE_DIR, "icons")

SIDEBAR_APPS_FILE = os.path.join(BASE_DIR, "sidebar_apps.json")
GAMES_FILE = os.path.join(BASE_DIR, "games.json")

# Carpeta donde se cachean los juegos offline (.zip descargados y
# descomprimidos). Cada juego offline vive en su propia subcarpeta
# GAMES_CACHE_DIR/<id>/
GAMES_CACHE_DIR = os.path.join(BASE_DIR, "games_cache")

for _dir in (BASE_DIR, USERSCRIPTS_DIR, PROFILE_STORAGE, ICONS_DIR, GAMES_CACHE_DIR):
    os.makedirs(_dir, exist_ok=True)


# ---------------------------------------------------------------------------
# Cache de íconos (SVG) para las apps ancladas de la barra lateral
# ---------------------------------------------------------------------------
YT_MUSIC_ICON_URL = "https://upload.wikimedia.org/wikipedia/commons/6/6a/Youtube_Music_icon.svg"
YT_MUSIC_ICON_PATH = os.path.join(ICONS_DIR, "youtube_music.svg")


def ensure_icon_cached(url, path):
    """Descarga el ícono SVG una sola vez y lo deja en cache local.
    En llamadas siguientes, si el archivo ya existe, no vuelve a bajarlo."""
    if os.path.exists(path):
        return path
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (MiniBrowser icon cache)"}
        )
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:
        print(f"No se pudo descargar/cachear el ícono ({url}): {e}")
        return None
    return path


# ---------------------------------------------------------------------------
# Valores por defecto para los archivos JSON (solo se usan la primera vez,
# cuando el archivo todavía no existe)
# ---------------------------------------------------------------------------
DEFAULT_SIDEBAR_APPS = [
    {"name": "YouTube Music", "url": "https://music.youtube.com"},
]

DEFAULT_GAMES = [
    {"name": "Cookie Clicker", "url": "https://orteil.dashnet.org/cookieclicker/"},
    {"name": "Universal Paperclips", "url": "https://www.decisionproblem.com/paperclips/"},
    {"name": "Bitburner", "url": "https://bitburner-official.github.io/"},
]
