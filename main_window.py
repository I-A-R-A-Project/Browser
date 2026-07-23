import os
import re

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QToolBar, QLineEdit, QFileDialog
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineSettings, QWebEngineDownloadRequest
)
from PyQt6.QtCore import QUrl

from config import (
    APP_NAME, USERSCRIPTS_DIR, DB_PATH, PROFILE_STORAGE,
    SIDEBAR_APPS_FILE, GAMES_FILE, DEFAULT_SIDEBAR_APPS, DEFAULT_GAMES,
    YT_MUSIC_ICON_URL, YT_MUSIC_ICON_PATH, ensure_icon_cached,
)
from database import Database
from json_store import SidebarAppsStore, GamesStore
from userscripts import UserScriptManager
from downloads import DownloadManager
from browser_tab import BrowserTab
from pdf_tab import PdfTab
from sidebar import SidebarRail, AppPanelOverlay, SidebarContainer
from dialogs import ListDialog, DownloadsDialog, SettingsDialog
import local_viewer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1150, 780)

        # Historial y marcadores en sqlite.
        self.db = Database(DB_PATH)
        # Apps de barra lateral y juegos en archivos JSON (fácil de
        # editar/exportar/importar).
        self.sidebar_apps_store = SidebarAppsStore(SIDEBAR_APPS_FILE, DEFAULT_SIDEBAR_APPS)
        self.games_store = GamesStore(GAMES_FILE, DEFAULT_GAMES)

        self.script_manager = UserScriptManager(USERSCRIPTS_DIR)
        self.script_manager.create_example_script()
        self.script_manager.reload()
        self.download_manager = DownloadManager()

        # Cachea el ícono SVG de YouTube Music (solo se descarga una vez)
        yt_icon_path = ensure_icon_cached(YT_MUSIC_ICON_URL, YT_MUSIC_ICON_PATH)

        self.profile = self._build_profile()

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_current_tab_changed)

        # Riel de íconos: FIJO, docked, parte del layout normal (no flota).
        self.rail = SidebarRail(icon_paths={"youtube_music": yt_icon_path})
        self.rail.on_toggle = self._on_sidebar_app_clicked
        self.rail.rebuild(self.sidebar_apps_store.all())

        # Panel de la app anclada: esto SÍ es overlay, flota por encima de
        # las pestañas sin modificar su tamaño.
        self.app_panel = AppPanelOverlay(self.profile)

        container = SidebarContainer(self.rail, self.tabs, self.app_panel)
        self.setCentralWidget(container)

        self._build_toolbar()
        self._build_shortcuts()

        self.new_tab("https://www.google.com")

    # -- perfil con cookies persistentes y descargas -------------------------
    def _build_profile(self):
        profile = QWebEngineProfile("MiniBrowserProfile", self)
        profile.setPersistentStoragePath(PROFILE_STORAGE)
        profile.setCachePath(os.path.join(PROFILE_STORAGE, "cache"))
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        settings = profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        # Permite que las páginas cargadas desde file:// (por ejemplo un
        # archivo .txt o un listado de carpeta) puedan referenciar otros
        # recursos locales o remotos sin ser bloqueadas.
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        # Visor de PDF integrado de Chromium (permite ver .pdf directamente
        # en la pestaña en lugar de descargarlo).
        settings.setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        profile.downloadRequested.connect(self.on_download_requested)
        return profile

    # -- barra lateral --------------------------------------------------------
    def _on_sidebar_app_clicked(self, app):
        app_id = app["id"]
        if self.app_panel.is_open_for(app_id):
            # ya estaba abierta -> colapsar panel, dejar solo el riel
            self.app_panel.close_panel()
            self.rail.set_checked(app_id, False)
        else:
            self.rail.uncheck_all()
            self.app_panel.open_app(app)
            self.rail.set_checked(app_id, True)

    def refresh_sidebar(self):
        self.rail.rebuild(self.sidebar_apps_store.all(), self.app_panel.active_app_id)

    def toggle_sidebar_visibility(self, visible):
        self.rail.setVisible(visible)
        if not visible:
            self.app_panel.close_panel()
            self.rail.uncheck_all()

    # -- toolbar --------------------------------------------------------------
    def _build_toolbar(self):
        toolbar = QToolBar("Navegación")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        back_action = QAction("←", self)
        back_action.triggered.connect(lambda: self.current_tab().back())
        toolbar.addAction(back_action)

        forward_action = QAction("→", self)
        forward_action.triggered.connect(lambda: self.current_tab().forward())
        toolbar.addAction(forward_action)

        reload_action = QAction("⟳", self)
        reload_action.triggered.connect(lambda: self.current_tab().reload())
        toolbar.addAction(reload_action)

        new_tab_action = QAction("+", self)
        new_tab_action.triggered.connect(lambda: self.new_tab())
        toolbar.addAction(new_tab_action)

        self.address_bar = QLineEdit()
        self.address_bar.returnPressed.connect(self.navigate_to_address)
        toolbar.addWidget(self.address_bar)

        self.bookmark_action = QAction("☆", self)
        self.bookmark_action.triggered.connect(self.toggle_bookmark)
        toolbar.addAction(self.bookmark_action)

        bookmarks_action = QAction("Marcadores", self)
        bookmarks_action.triggered.connect(self.show_bookmarks)
        toolbar.addAction(bookmarks_action)

        games_action = QAction("🎮 Juegos", self)
        games_action.setToolTip("Juegos")
        games_action.triggered.connect(self.show_games)
        toolbar.addAction(games_action)

        history_action = QAction("Historial", self)
        history_action.triggered.connect(self.show_history)
        toolbar.addAction(history_action)

        downloads_action = QAction("⬇", self)
        downloads_action.setToolTip("Descargas")
        downloads_action.triggered.connect(self.show_downloads)
        toolbar.addAction(downloads_action)

        sidebar_toggle = QAction("▥", self)
        sidebar_toggle.setToolTip("Mostrar/ocultar barra lateral")
        sidebar_toggle.setCheckable(True)
        sidebar_toggle.setChecked(True)
        sidebar_toggle.toggled.connect(self.toggle_sidebar_visibility)
        toolbar.addAction(sidebar_toggle)

        zoom_in = QAction("🔎+", self)
        zoom_in.triggered.connect(lambda: self.adjust_zoom(0.1))
        toolbar.addAction(zoom_in)

        zoom_out = QAction("🔎-", self)
        zoom_out.triggered.connect(lambda: self.adjust_zoom(-0.1))
        toolbar.addAction(zoom_out)

        settings_action = QAction("⚙", self)
        settings_action.setToolTip("Ajustes y personalizaciones")
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)

    def _build_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self, activated=lambda: self.new_tab())
        QShortcut(QKeySequence("Ctrl+W"), self, activated=lambda: self.close_tab(self.tabs.currentIndex()))
        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: self.address_bar.setFocus())
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.toggle_bookmark)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self.show_history)
        QShortcut(QKeySequence("Ctrl+J"), self, activated=self.show_downloads)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.open_local_file)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, activated=self.open_local_folder)

    # -- pestañas ---------------------------------------------------------
    def current_tab(self) -> BrowserTab:
        return self.tabs.currentWidget()

    def new_tab(self, url="https://www.google.com"):
        tab = BrowserTab(self.profile, self.script_manager, self)
        index = self.tabs.addTab(tab, "Nueva pestaña")
        self.tabs.setCurrentIndex(index)
        tab.setUrl(QUrl(url))
        return tab

    def close_tab(self, index):
        if self.tabs.count() <= 1:
            self.close()
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        widget.deleteLater()

    def update_tab_title(self, tab, title):
        index = self.tabs.indexOf(tab)
        if index != -1:
            short = (title[:22] + "…") if len(title) > 22 else title
            self.tabs.setTabText(index, short or "Nueva pestaña")

    def _on_current_tab_changed(self, index):
        tab = self.tabs.widget(index)
        if tab:
            self.update_address_bar(tab, tab.url())

    # -- barra de direcciones -----------------------------------------------
    def update_address_bar(self, tab, qurl: QUrl):
        if tab != self.current_tab():
            return
        self.address_bar.setText(qurl.toString())
        self.address_bar.setCursorPosition(0)
        self._refresh_bookmark_icon(qurl.toString())

    # Ruta de Windows (C:\..., C:/...) o Unix (/..., ~/...)
    _WINDOWS_PATH_RE = re.compile(r"^[a-zA-Z]:[\\/]")

    def _looks_like_local_path(self, text):
        if text.startswith("file://"):
            return True
        if self._WINDOWS_PATH_RE.match(text):
            return True
        if text.startswith("/") or text.startswith("~"):
            return True
        return False

    def navigate_to_address(self):
        text = self.address_bar.text().strip()
        if not text:
            return

        if self._looks_like_local_path(text):
            if text.startswith("file://"):
                local_path = QUrl(text).toLocalFile()
            else:
                local_path = os.path.expanduser(text)
            # Si es uno de nuestros tipos especiales (pdf/zip/rar/7z/epub),
            # BrowserPage.acceptNavigationRequest intercepta esta misma
            # navegación y llama a handle_special_local_file; para el
            # resto (carpetas, texto, html, imágenes...) Chromium la
            # muestra directamente.
            self.current_tab().setUrl(QUrl.fromLocalFile(local_path))
            return

        if "." in text and " " not in text:
            if not text.startswith(("http://", "https://")):
                text = "https://" + text
            url = QUrl(text)
        else:
            query = QUrl.toPercentEncoding(text).data().decode()
            url = QUrl(f"https://www.google.com/search?q={query}")
        self.current_tab().setUrl(url)

    # -- abrir archivos/carpetas locales --------------------------------------
    def open_local_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir archivo")
        if path:
            self.open_path_in_new_tab(path)

    def open_local_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Abrir carpeta")
        if path:
            self.open_path_in_new_tab(path)

    def open_path_in_new_tab(self, path):
        """Abre una ruta local (usada por el diálogo de Descargas y por los
        selectores de archivo/carpeta) en una pestaña nueva."""
        if os.path.splitext(path)[1].lower() == ".pdf":
            self.open_pdf_tab(path)
            return
        tab = self.new_tab("about:blank")
        tab.setUrl(QUrl.fromLocalFile(path))

    def handle_special_local_file(self, tab, local_path):
        """Llamado por BrowserPage cuando una pestaña de navegación (la
        barra de direcciones, o un clic dentro del listado nativo de una
        carpeta file://) intenta ir a un .pdf/.zip/.rar/.7z/.epub. Acá
        decidimos cómo mostrarlo en lugar de dejar que Chromium lo trate
        como una descarga."""
        ext = os.path.splitext(local_path)[1].lower()
        if ext == ".pdf":
            # El PDF necesita un visor propio (QtPdf), así que se abre en
            # una pestaña nueva y la pestaña que intentó navegar se deja
            # tal cual estaba.
            self.open_pdf_tab(local_path)
            return
        self._open_local_target(tab, local_path)

    def open_pdf_tab(self, path):
        """Abre un PDF en una pestaña propia con el visor nativo QtPdf."""
        tab = PdfTab(path, self)
        title = os.path.basename(path)
        short = (title[:22] + "…") if len(title) > 22 else title
        index = self.tabs.addTab(tab, short or "PDF")
        self.tabs.setCurrentIndex(index)
        file_url = tab.url().toString()
        self.db.add_history(file_url, title)
        return tab

    def _open_local_target(self, tab, local_path):
        """Decide cómo mostrar una ruta local que NO es un pdf. Los .zip
        y .7z se descomprimen y se navegan como carpeta; los .rar se
        listan (no se pueden extraer sin una herramienta externa); los
        .epub se abren en su primer capítulo. El resto (carpetas, .txt,
        .html, imágenes, etc.) se lo dejamos directamente a Chromium."""
        ext = os.path.splitext(local_path)[1].lower()
        try:
            if ext == ".zip":
                dest = local_viewer.extract_zip(local_path)
                tab.setUrl(QUrl.fromLocalFile(dest))
                return

            if ext == ".7z":
                dest = local_viewer.extract_7z(local_path)
                if dest is None:
                    tab.page().setHtml(
                        local_viewer.render_missing_dependency(local_path, "py7zr"),
                        QUrl.fromLocalFile(local_path),
                    )
                else:
                    tab.setUrl(QUrl.fromLocalFile(dest))
                return

            if ext == ".rar":
                try:
                    html = local_viewer.render_rar_listing(local_path)
                except ImportError:
                    html = local_viewer.render_missing_dependency(
                        local_path, "rarfile",
                        "Además necesitás tener instalado `unrar` o `unar` en el sistema "
                        "para que rarfile pueda leer el archivo.",
                    )
                tab.page().setHtml(html, QUrl.fromLocalFile(local_path))
                return

            if ext == ".epub":
                target = local_viewer.extract_epub_root(local_path)
                tab.setUrl(QUrl.fromLocalFile(target))
                return
        except Exception as e:
            tab.page().setHtml(
                local_viewer.render_error(local_path, f"Error al procesar el archivo: {e}"),
                QUrl.fromLocalFile(local_path),
            )
            return

        # Carpetas, .txt, .html, imágenes, etc.
        tab.setUrl(QUrl.fromLocalFile(local_path))

    # -- zoom -----------------------------------------------------------------
    def adjust_zoom(self, delta):
        tab = self.current_tab()
        tab.setZoomFactor(max(0.25, min(3.0, tab.zoomFactor() + delta)))

    # -- marcadores -----------------------------------------------------------
    def toggle_bookmark(self):
        tab = self.current_tab()
        url = tab.url().toString()
        title = tab.title() or url
        if self.db.is_bookmarked(url):
            self.db.remove_bookmark(url)
        else:
            self.db.add_bookmark(url, title)
        self._refresh_bookmark_icon(url)

    def _refresh_bookmark_icon(self, url):
        self.bookmark_action.setText("★" if self.db.is_bookmarked(url) else "☆")

    def show_bookmarks(self):
        items = [(title or url, url) for url, title in self.db.get_bookmarks()]
        dialog = ListDialog(
            "Marcadores", items,
            on_open=lambda url: self.new_tab(url),
            on_delete=lambda url: self.db.remove_bookmark(url),
        )
        dialog.exec()

    # -- juegos -----------------------------------------------------------------
    def show_games(self):
        items = [(g["name"], g["url"]) for g in self.games_store.all()]
        dialog = ListDialog(
            "Juegos", items,
            on_open=lambda url: self.new_tab(url),
        )
        dialog.exec()

    # -- historial --------------------------------------------------------------
    def show_history(self):
        items = [(f"{title or url}   [{ts}]", url) for url, title, ts in self.db.get_history()]
        dialog = ListDialog(
            "Historial", items,
            on_open=lambda url: self.new_tab(url),
            on_clear=self.db.clear_history,
        )
        dialog.exec()

    # -- descargas --------------------------------------------------------------
    def on_download_requested(self, request: QWebEngineDownloadRequest):
        item = self.download_manager.handle_download(request)
        self.statusBar().showMessage(f"Descargando: {item.filename}", 5000)

    def show_downloads(self):
        dialog = DownloadsDialog(self.download_manager, on_open=self.open_path_in_new_tab)
        dialog.exec()

    # -- ajustes / personalizaciones --------------------------------------------
    def show_settings(self):
        dialog = SettingsDialog(
            self.script_manager, self.sidebar_apps_store, self.games_store,
            on_sidebar_change=self.refresh_sidebar,
        )
        dialog.exec()
        self.script_manager.reload()
        self.refresh_sidebar()
