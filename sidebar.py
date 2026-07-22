import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QToolButton
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QUrl, QSize, QRect, QPropertyAnimation, QEasingCurve
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage


class SidebarRail(QWidget):
    WIDTH = 52

    def __init__(self, icon_paths=None, parent=None):
        super().__init__(parent)
        # icon_paths: dict opcional {clave -> ruta de ícono} para casos
        # especiales (ej: YouTube Music con su SVG cacheado)
        self.icon_paths = icon_paths or {}
        self.buttons = {}     # app_id -> QToolButton
        self.on_toggle = None  # callback(app) asignado desde afuera

        self.setFixedWidth(self.WIDTH)
        self.setStyleSheet("""
            SidebarRail { background-color: #202124; }
            QToolButton { border: none; border-radius: 8px; color: #e8eaed; }
            QToolButton:checked { background-color: #3c4043; }
            QToolButton:hover { background-color: #303134; }
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 6, 4, 6)
        self._layout.setSpacing(4)
        self._layout.addStretch()

    def _icon_for_app(self, app):
        name = (app["name"] or "").strip().lower()
        url = (app["url"] or "").lower()
        if "music.youtube.com" in url or name == "youtube music":
            path = self.icon_paths.get("youtube_music")
            if path and os.path.exists(path):
                return QIcon(path)
        return None

    def rebuild(self, apps, active_app_id=None):
        for btn in self.buttons.values():
            btn.deleteLater()
        self.buttons.clear()
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for app in apps:
            btn = QToolButton()
            icon = self._icon_for_app(app)
            if icon is not None:
                btn.setIcon(icon)
                btn.setIconSize(QSize(28, 28))
            else:
                btn.setText(app["name"][:2].upper())
            btn.setToolTip(app["name"])
            btn.setCheckable(True)
            btn.setFixedSize(44, 44)
            btn.clicked.connect(lambda checked, a=app: self._emit_toggle(a))
            self._layout.insertWidget(self._layout.count() - 1, btn)
            self.buttons[app["id"]] = btn
            if app["id"] == active_app_id:
                btn.setChecked(True)

    def _emit_toggle(self, app):
        if self.on_toggle:
            self.on_toggle(app)

    def set_checked(self, app_id, checked):
        if app_id in self.buttons:
            self.buttons[app_id].setChecked(checked)

    def uncheck_all(self):
        for btn in self.buttons.values():
            btn.setChecked(False)


class AppPanelOverlay(QWidget):
    EXPANDED_WIDTH = 563  # 615px totales - 52px del riel fijo

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.views = {}  # app_id -> QWebEngineView
        self.active_app_id = None

        self.setAutoFillBackground(True)
        self.setStyleSheet("AppPanelOverlay { background-color: #202124; }")

        self.stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def open_app(self, app):
        app_id = app["id"]
        if app_id not in self.views:
            view = QWebEngineView()
            page = QWebEnginePage(self.profile, view)
            view.setPage(page)
            view.setUrl(QUrl(app["url"]))
            self.views[app_id] = view
            self.stack.addWidget(view)

        self.stack.setCurrentWidget(self.views[app_id])
        self.active_app_id = app_id
        self.show()
        self._animate_to(self.EXPANDED_WIDTH)

    def close_panel(self):
        self.active_app_id = None
        self._animate_to(0)

    def is_open_for(self, app_id):
        return self.active_app_id == app_id

    def _animate_to(self, target_w):
        g = self.geometry()
        if g.width() == target_w:
            return
        self._anim.stop()
        self._anim.setStartValue(g)
        self._anim.setEndValue(QRect(g.x(), g.y(), target_w, g.height()))
        try:
            self._anim.finished.disconnect(self._hide_if_collapsed)
        except TypeError:
            pass
        self._anim.finished.connect(self._hide_if_collapsed)
        self._anim.start()
        self.raise_()

    def _hide_if_collapsed(self):
        if self.geometry().width() <= 0:
            self.hide()

    def set_height(self, height):
        """Llamado cuando la ventana cambia de tamaño: mantiene el ancho
        actual (o el objetivo si hay animación en curso) y ajusta el alto."""
        g = self.geometry()
        self.setGeometry(g.x(), g.y(), g.width(), height)


# ---------------------------------------------------------------------------
# Contenedor: layout real [riel fijo | pestañas] + el panel overlay
# posicionado a mano justo a la derecha del riel, flotando por encima de
# las pestañas sin modificar su ancho.
# ---------------------------------------------------------------------------
class SidebarContainer(QWidget):
    def __init__(self, rail, tabs, app_panel, parent=None):
        super().__init__(parent)
        self.rail = rail
        self.tabs = tabs
        self.app_panel = app_panel

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(rail)
        layout.addWidget(tabs, 1)

        self.app_panel.setParent(self)
        self.app_panel.setGeometry(rail.width(), 0, 0, self.height() or 780)
        self.app_panel.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.app_panel.set_height(self.height())
        self.app_panel.raise_()
