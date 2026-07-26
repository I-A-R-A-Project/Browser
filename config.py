import os

APP_NAME = "MiniBrowser"

BASE_DIR = os.path.join(os.path.expanduser("~"), ".minibrowser")
USERSCRIPTS_DIR = os.path.join(BASE_DIR, "userscripts")
DB_PATH = os.path.join(BASE_DIR, "browser.db")
PROFILE_STORAGE = os.path.join(BASE_DIR, "profile")
ICONS_DIR = os.path.join(BASE_DIR, "icons")

SIDEBAR_APPS_FILE = os.path.join(BASE_DIR, "sidebar_apps.json")
GAMES_FILE = os.path.join(BASE_DIR, "games.json")

# Carpeta donde se extraen (una sola vez) los .zip / .7z / .epub que se
# abren desde el navegador, para poder navegarlos como si fueran carpetas.
ARCHIVES_CACHE_DIR = os.path.join(BASE_DIR, "archivos_extraidos")

for _dir in (BASE_DIR, USERSCRIPTS_DIR, PROFILE_STORAGE, ICONS_DIR, ARCHIVES_CACHE_DIR):
    os.makedirs(_dir, exist_ok=True)


# ---------------------------------------------------------------------------
# Íconos para las apps ancladas de la barra lateral: el usuario elige el
# archivo (svg/png/jpg/ico) a mano desde Ajustes -> Apps de barra lateral.
# Se copian a ICONS_DIR y la ruta local se guarda en el item (icon_path).
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
