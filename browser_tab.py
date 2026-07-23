import os

from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

from userscripts import UserScriptManager

# Extensiones que NO queremos que Chromium navegue/descargue directamente:
# las maneja MainWindow (zip/7z/epub se extraen y se muestran como
# carpeta; rar se lista; pdf se abre con el visor nativo QtPdf en una
# pestaña propia).
SPECIAL_LOCAL_EXTS = (".zip", ".rar", ".7z", ".epub", ".pdf")


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

        page = BrowserPage(profile, self, main_window)
        self.setPage(page)

        self.urlChanged.connect(self._on_url_changed)
        self.loadFinished.connect(self._on_load_finished)
        self.titleChanged.connect(self._on_title_changed)

    def _on_url_changed(self, qurl: QUrl):
        self._inject_matching_userscripts(qurl.toString())
        self.main_window.update_address_bar(self, qurl)

    def _on_load_finished(self, ok):
        if ok:
            url = self.url().toString()
            title = self.title() or url
            if url and url != "about:blank":
                self.main_window.db.add_history(url, title)

    def _on_title_changed(self, title):
        self.main_window.update_tab_title(self, title)

    def _inject_matching_userscripts(self, url):
        # Se recalculan en cada navegación: solo quedan cargados los
        # scripts cuyo @match coincide con la URL actual de ESTA pestaña.
        collection = self.page().scripts()
        collection.clear()
        for user_script in self.script_manager.scripts_for_url(url):
            collection.insert(user_script.to_qwebengine_script())
