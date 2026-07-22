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

    def count(self):
        return len(self._items)

    def _add_no_save(self, name, url):
        item = {"id": self._next_id, "name": name, "url": url}
        self._items.append(item)
        self._next_id += 1
        return item

    def add(self, name, url):
        item = self._add_no_save(name, url)
        self.save()
        return item

    def remove(self, item_id):
        self._items = [i for i in self._items if i["id"] != item_id]
        self.save()

    # -- exportar / importar ------------------------------------------------------
    def export_to(self, dest_path):
        """Copia el archivo JSON tal cual a dest_path."""
        shutil.copyfile(self.path, dest_path)

    def import_from(self, src_path):
        """Reemplaza la lista actual con el contenido de src_path.
        Acepta tanto el formato propio ({"items": [...]}) como una lista
        simple ([{"name":.., "url":..}, ...]) para facilitar ediciones a mano."""
        with open(src_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_items = data.get("items", data) if isinstance(data, dict) else data
        normalized = []
        next_id = 1
        for entry in raw_items:
            normalized.append({
                "id": next_id,
                "name": entry.get("name", "Sin nombre"),
                "url": entry.get("url", ""),
            })
            next_id += 1

        self._items = normalized
        self._next_id = next_id
        self.save()


class SidebarAppsStore(JsonListStore):
    """Apps ancladas a la barra lateral."""
    pass


class GamesStore(JsonListStore):
    """Lista de juegos para el botón 'Juegos'."""
    pass
