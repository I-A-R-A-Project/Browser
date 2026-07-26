import json
import os
import shutil

class JsonListStore:
    def __init__(self, path, default_items=None):
        self.path = path
        self.default_items = default_items or []
        self._items = []
        self._next_id = 1
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._items = data.get("items", [])
                self._next_id = data.get("next_id", self._compute_next_id())
                return
            except Exception as e:
                print(f"No se pudo leer {self.path}, se usan valores por defecto: {e}")

        # Primera vez (o archivo corrupto): sembrar con los valores por defecto.
        self._items = []
        self._next_id = 1
        for item in self.default_items:
            self._add_no_save(item["name"], item["url"])
        self.save()

    def save(self):
        data = {"next_id": self._next_id, "items": self._items}
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def _compute_next_id(self):
        return max((i["id"] for i in self._items), default=0) + 1

    # -- API pública ------------------------------------------------------------
    def all(self):
        return list(self._items)

    def get(self, item_id):
        for item in self._items:
            if item["id"] == item_id:
                return item
        return None

    def count(self):
        return len(self._items)

    def _add_no_save(self, name, url, **extra):
        item = {"id": self._next_id, "name": name, "url": url}
        item.update(extra)
        item.setdefault("kind", "link")
        self._items.append(item)
        self._next_id += 1
        return item

    def add(self, name, url, **extra):
        """extra permite guardar campos adicionales, por ejemplo para
        juegos offline: kind="offline_zip", download_url="...", local_entry=None"""
        item = self._add_no_save(name, url, **extra)
        self.save()
        return item

    def remove(self, item_id):
        self._items = [i for i in self._items if i["id"] != item_id]
        self.save()

    def update_item(self, item_id, **fields):
        """Actualiza (o agrega) campos de un item existente y guarda."""
        item = self.get(item_id)
        if item is None:
            return None
        item.update(fields)
        self.save()
        return item

    # -- exportar / importar ------------------------------------------------------
    def export_to(self, dest_path):
        """Copia el archivo JSON tal cual a dest_path."""
        shutil.copyfile(self.path, dest_path)

    def import_from(self, src_path):
        """Reemplaza la lista actual con el contenido de src_path.
        Acepta tanto el formato propio ({"items": [...]}) como una lista
        simple ([{"name":.., "url":..}, ...]) para facilitar ediciones a mano.
        Conserva campos extra (kind/download_url/local_entry) si vienen en
        el archivo importado."""
        with open(src_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_items = data.get("items", data) if isinstance(data, dict) else data
        normalized = []
        next_id = 1
        for entry in raw_items:
            item = {
                "id": next_id,
                "name": entry.get("name", "Sin nombre"),
                "url": entry.get("url", ""),
            }
            for extra_key in ("kind", "download_url", "local_entry", "icon_path"):
                if extra_key in entry:
                    item[extra_key] = entry[extra_key]
            item.setdefault("kind", "link")
            normalized.append(item)
            next_id += 1

        self._items = normalized
        self._next_id = next_id
        self.save()


class SidebarAppsStore(JsonListStore):
    """Apps ancladas a la barra lateral."""
    pass


class GamesStore(JsonListStore):
    """Lista de juegos para el botón 'Juegos'.

    Cada item puede ser:
    - un juego normal: {"kind": "link", "url": "https://..."}
    - un juego offline (.zip descargado de una página oficial, que se
      descomprime en caché): {"kind": "offline_zip", "download_url": "...",
      "local_entry": None | "/ruta/al/index.html"}
    """

    def add_offline_zip(self, name, download_url):
        return self.add(name, "", kind="offline_zip", download_url=download_url, local_entry=None)

    def set_local_entry(self, item_id, local_path):
        return self.update_item(item_id, local_entry=local_path)
