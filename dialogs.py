import os
import shutil

from PyQt6.QtWidgets import (
    QApplication, QDialog, QListWidget, QListWidgetItem, QPushButton,
    QHBoxLayout, QVBoxLayout, QMessageBox, QFileDialog, QLabel, QWidget,
    QLineEdit, QTabWidget
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import Qt, QUrl, QTimer

from config import USERSCRIPTS_DIR
from userscripts import UserScriptManager
from downloads import DownloadManager


# ---------------------------------------------------------------------------
# Diálogo genérico de lista (historial / marcadores / juegos)
# ---------------------------------------------------------------------------
class ListDialog(QDialog):
    def __init__(self, title, items, on_open=None, on_delete=None, on_clear=None):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(520, 420)
        self.on_open = on_open
        self.on_delete = on_delete

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        for label, url in items:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, url)
            self.list_widget.addItem(item)
        self.list_widget.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Abrir")
        open_btn.clicked.connect(lambda: self._open_item(self.list_widget.currentItem()))
        btn_row.addWidget(open_btn)

        if on_delete:
            del_btn = QPushButton("Eliminar")
            del_btn.clicked.connect(self._delete_item)
            btn_row.addWidget(del_btn)

        if on_clear:
            clear_btn = QPushButton("Vaciar todo")
            clear_btn.clicked.connect(lambda: (on_clear(), self.accept()))
            btn_row.addWidget(clear_btn)

        layout.addLayout(btn_row)

    def _open_item(self, item):
        if item and self.on_open:
            self.on_open(item.data(Qt.ItemDataRole.UserRole))
            self.accept()

    def _delete_item(self):
        item = self.list_widget.currentItem()
        if item and self.on_delete:
            self.on_delete(item.data(Qt.ItemDataRole.UserRole))
            self.list_widget.takeItem(self.list_widget.row(item))


# ---------------------------------------------------------------------------
# Diálogo de descargas
# ---------------------------------------------------------------------------
class DownloadsDialog(QDialog):
    def __init__(self, download_manager: DownloadManager):
        super().__init__()
        self.setWindowTitle("Descargas")
        self.resize(560, 420)
        self.download_manager = download_manager

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        open_folder_btn = QPushButton("Abrir carpeta contenedora")
        open_folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(open_folder_btn)

        cancel_btn = QPushButton("Cancelar selecc.")
        cancel_btn.clicked.connect(self._cancel_selected)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(500)
        self._refresh()

    def _refresh(self):
        current_row = self.list_widget.currentRow()
        self.list_widget.clear()
        if not self.download_manager.items:
            self.list_widget.addItem("(sin descargas todavía)")
        for item in self.download_manager.items:
            list_item = QListWidgetItem(item.progress_text())
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_widget.addItem(list_item)
        if 0 <= current_row < self.list_widget.count():
            self.list_widget.setCurrentRow(current_row)

    def _open_folder(self):
        item = self.list_widget.currentItem()
        download_item = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not download_item:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(download_item.directory))

    def _cancel_selected(self):
        item = self.list_widget.currentItem()
        download_item = item.data(Qt.ItemDataRole.UserRole) if item else None
        if download_item:
            download_item.request.cancel()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Panel de userscripts (usado dentro de Ajustes)
# ---------------------------------------------------------------------------
class UserScriptsPanel(QWidget):
    def __init__(self, script_manager: UserScriptManager):
        super().__init__()
        self.directory = USERSCRIPTS_DIR
        self.script_manager = script_manager

        layout = QVBoxLayout(self)
        info = QLabel(
            "Los scripts se cargan desde:\n" + self.directory +
            "\n\nFormato (estilo Tampermonkey), como comentarios al inicio del .js:\n"
            "// @name    Mi script\n// @match   *://*.dominio.com/*\n// @run-at  document-idle"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list_widget = QListWidget()
        self._populate()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Agregar script...")
        add_btn.clicked.connect(self._add_script)
        btn_row.addWidget(add_btn)

        open_folder_btn = QPushButton("Copiar ruta de carpeta")
        open_folder_btn.clicked.connect(self._copy_folder_path)
        btn_row.addWidget(open_folder_btn)

        reload_btn = QPushButton("Recargar")
        reload_btn.clicked.connect(self._reload)
        btn_row.addWidget(reload_btn)

        layout.addLayout(btn_row)

    def _populate(self):
        self.list_widget.clear()
        for s in self.script_manager.scripts:
            matches = ", ".join(s.matches) if s.matches else "(sin @match, no se inyecta en ningún sitio)"
            self.list_widget.addItem(f"{s.name}  —  {matches}")

    def _add_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "Elegir userscript (.js)", "", "JavaScript (*.js)")
        if path:
            dest = os.path.join(self.directory, os.path.basename(path))
            shutil.copy(path, dest)
            self.script_manager.reload()
            self._populate()

    def _copy_folder_path(self):
        QApplication.clipboard().setText(self.directory)
        QMessageBox.information(self, "Ruta copiada", f"Ruta copiada al portapapeles:\n{self.directory}")

    def _reload(self):
        self.script_manager.reload()
        self._populate()


# ---------------------------------------------------------------------------
# Panel genérico para editar una lista guardada en JSON (usado tanto para
# las apps de barra lateral como para los juegos). Permite agregar,
# eliminar, exportar e importar el archivo completo.
# ---------------------------------------------------------------------------
class JsonListEditorPanel(QWidget):
    def __init__(self, store, info_text, name_placeholder, url_placeholder, on_change=None):
        super().__init__()
        self.store = store
        self.on_change = on_change

        layout = QVBoxLayout(self)
        info = QLabel(info_text)
        info.setWordWrap(True)
        layout.addWidget(info)

        path_label = QLabel(f"Archivo: {self.store.path}")
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(path_label)

        self.list_widget = QListWidget()
        self._populate()
        layout.addWidget(self.list_widget)

        form_row = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(name_placeholder)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(url_placeholder)
        form_row.addWidget(self.name_input)
        form_row.addWidget(self.url_input)
        layout.addLayout(form_row)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Agregar")
        add_btn.clicked.connect(self._add_item)
        btn_row.addWidget(add_btn)

        del_btn = QPushButton("Eliminar seleccionado")
        del_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        io_row = QHBoxLayout()
        export_btn = QPushButton("Exportar...")
        export_btn.clicked.connect(self._export)
        io_row.addWidget(export_btn)

        import_btn = QPushButton("Importar...")
        import_btn.clicked.connect(self._import)
        io_row.addWidget(import_btn)
        layout.addLayout(io_row)

    def _populate(self):
        self.list_widget.clear()
        for item in self.store.all():
            list_item = QListWidgetItem(f'{item["name"]}  —  {item["url"]}')
            list_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.list_widget.addItem(list_item)

    def _add_item(self):
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        if not name or not url:
            QMessageBox.warning(self, "Faltan datos", "Completá nombre y URL.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self.store.add(name, url)
        self.name_input.clear()
        self.url_input.clear()
        self._populate()
        if self.on_change:
            self.on_change()

    def _remove_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        self.store.remove(item_id)
        self._populate()
        if self.on_change:
            self.on_change()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar a...", "", "JSON (*.json)")
        if not path:
            return
        try:
            self.store.export_to(path)
            QMessageBox.information(self, "Exportado", f"Guardado en:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar desde...", "", "JSON (*.json)")
        if not path:
            return
        try:
            self.store.import_from(path)
            self._populate()
            if self.on_change:
                self.on_change()
            QMessageBox.information(self, "Importado", "Lista actualizada correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error al importar", str(e))


# ---------------------------------------------------------------------------
# Diálogo de Ajustes y personalizaciones (ícono ⚙)
# ---------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, script_manager, sidebar_apps_store, games_store, on_sidebar_change):
        super().__init__()
        self.setWindowTitle("Ajustes y personalizaciones")
        self.resize(600, 520)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(UserScriptsPanel(script_manager), "Userscripts")
        tabs.addTab(
            JsonListEditorPanel(
                sidebar_apps_store,
                info_text=(
                    "Sitios anclados a la barra lateral izquierda. Se abren en un panel\n"
                    "propio que flota por encima de las pestañas y podés colapsarlos sin\n"
                    "perder la sesión. Se guardan en un archivo JSON: fácil de editar a\n"
                    "mano, exportar o importar."
                ),
                name_placeholder="Nombre (ej: YouTube Music)",
                url_placeholder="URL (ej: music.youtube.com)",
                on_change=on_sidebar_change,
            ),
            "Apps de barra lateral",
        )
        tabs.addTab(
            JsonListEditorPanel(
                games_store,
                info_text=(
                    "Lista de juegos para el botón 🎮 Juegos. Se guardan en un archivo\n"
                    "JSON: fácil de editar a mano, exportar o importar."
                ),
                name_placeholder="Nombre (ej: Cookie Clicker)",
                url_placeholder="URL",
            ),
            "Juegos",
        )
        layout.addWidget(tabs)

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
