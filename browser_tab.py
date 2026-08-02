import os
import uuid

from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

from userscripts import UserScriptManager

# Extensiones de video: se abren en VideoTab (reproductor nativo
# QtMultimedia) en vez del <video> HTML5 de Chromium, porque muchas builds
# de QtWebEngine no traen codecs propietarios (H.264/AAC) y el video se
# queda con los controles trabados en 0:00 sin reproducir nada.
VIDEO_EXTS = (".mp4", ".m4v", ".webm", ".mkv", ".avi", ".mov")

# Extensiones que NO queremos que Chromium navegue/descargue directamente:
# las maneja MainWindow (zip/7z/epub se extraen y se muestran como
# carpeta; rar se lista; pdf se abre con el visor nativo QtPdf en una
# pestaña propia; los videos se abren con QtMultimedia en una pestaña
# propia).
SPECIAL_LOCAL_EXTS = (".zip", ".rar", ".7z", ".epub", ".pdf") + VIDEO_EXTS


class BrowserPage(QWebEnginePage):
    """QWebEnginePage que intercepta la navegación (tanto la que dispara
    el propio código como la que ocurre al hacer clic en un link, por
    ejemplo dentro del listado nativo de una carpeta file://) hacia
    archivos locales "especiales", para evitar que Chromium los trate
    como una descarga o los muestre en blanco."""

    def __init__(self, profile, tab, main_window):
        super().__init__(profile, tab)
        self.tab = tab
        self.main_window = main_window

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame):
        if is_main_frame and url.isLocalFile():
            ext = os.path.splitext(url.toLocalFile())[1].lower()
            if ext in SPECIAL_LOCAL_EXTS:
                self.main_window.handle_special_local_file(self.tab, url.toLocalFile())
                return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class BrowserTab(QWebEngineView):
    def __init__(self, profile, script_manager: UserScriptManager, main_window):
        super().__init__()
        self.script_manager = script_manager
        self.main_window = main_window

        # Identifica todas las navegaciones que ocurren dentro de esta
        # misma pestaña, para poder agruparlas como una sola "sesión" en
        # el historial (en vez de perder el recorrido y quedarse solo
        # con la última página).
        self.session_id = uuid.uuid4().hex

        page = QWebEnginePage(profile, self)
        self.setPage(page)
        page.newWindowRequested.connect(self._on_new_window_requested)

        self.urlChanged.connect(self._on_url_changed)
        self.loadFinished.connect(self._on_load_finished)
        self.titleChanged.connect(self._on_title_changed)
        self.iconChanged.connect(self._on_icon_changed)

    def _on_url_changed(self, qurl: QUrl):
        self._inject_matching_userscripts(qurl.toString())
        self.main_window.update_address_bar(self, qurl)

    def _on_load_finished(self, ok):
        if ok:
            url = self.url().toString()
            title = self.title() or url
            if url and url != "about:blank":
                self.main_window.db.add_history(url, title, self.session_id)

    def _on_title_changed(self, title):
        self.main_window.update_tab_title(self, title)

    def _on_icon_changed(self, icon):
        self.main_window.update_tab_icon(self, icon)

    def _on_new_window_requested(self, request):
        # Se dispara con "Abrir enlace en nueva pestaña", target="_blank",
        # window.open(), etc. Sin este handler, Qt6 simplemente descarta
        # el pedido y no pasa nada.
        self.main_window.handle_new_window_request(request)

    def _inject_matching_userscripts(self, url):
        # Se recalculan en cada navegación: solo quedan cargados los
        # scripts cuyo @match coincide con la URL actual de ESTA pestaña.
        collection = self.page().scripts()
        collection.clear()
        for user_script in self.script_manager.scripts_for_url(url):
            collection.insert(user_script.to_qwebengine_script())
