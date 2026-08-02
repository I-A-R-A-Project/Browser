import sqlite3
import uuid
from datetime import datetime

class Database:
    """Historial y marcadores en sqlite.

    Las apps de barra lateral y los juegos NO viven acá: se guardan en
    archivos JSON (ver json_store.py) para que sean fáciles de editar a
    mano, exportar e importar.

    El historial se guarda "plano" (una fila por navegación), pero cada
    fila tiene un session_id que agrupa todas las URLs visitadas dentro
    de una misma pestaña/sesión de navegación. Así se puede reconstruir
    el recorrido completo (inicio -> ... -> fin) y no solo la última
    página, y mostrarlo agrupado/desplegable en la UI."""

    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT,
                visited_at TEXT NOT NULL,
                session_id TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Migración: bases de datos creadas antes de que existiera
        # session_id no tienen la columna. La agregamos y, a las filas
        # viejas que quedan con session_id NULL, les asignamos un id
        # aleatorio distinto por fila (no un único id compartido), para
        # que sigan viéndose como entradas individuales en vez de
        # agruparse todas juntas por accidente.
        cur.execute("PRAGMA table_info(history)")
        cols = [row[1] for row in cur.fetchall()]
        if "session_id" not in cols:
            cur.execute("ALTER TABLE history ADD COLUMN session_id TEXT")
        cur.execute(
            "UPDATE history SET session_id = lower(hex(randomblob(16))) "
            "WHERE session_id IS NULL"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_history_session ON history(session_id)")

        self.conn.commit()

    # -- Historial ------------------------------------------------------
    def new_session_id(self):
        return uuid.uuid4().hex

    def add_history(self, url, title, session_id=None):
        if session_id is None:
            session_id = self.new_session_id()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO history (url, title, visited_at, session_id) VALUES (?, ?, ?, ?)",
            (url, title, datetime.now().isoformat(timespec="seconds"), session_id)
        )
        self.conn.commit()

    def get_history_grouped(self, search=None, limit_sessions=300):
        """Devuelve el historial agrupado por sesión de navegación (una
        sesión = todo lo navegado dentro de una misma pestaña). Cada
        elemento es un dict con:
            session_id, visits (cantidad de páginas), last_visited,
            entries: lista de (url, title, visited_at) en orden
                     cronológico (la primera visitada primero).
        Se ordena por sesión más reciente primero. Si se pasa `search`,
        solo se incluyen sesiones que tengan al menos una visita cuyo
        título o url matchee (pero se muestran TODAS las visitas de esa
        sesión, no solo la que matcheó, para no perder contexto)."""
        cur = self.conn.cursor()
        if search:
            like = f"%{search}%"
            cur.execute(
                "SELECT DISTINCT session_id FROM history WHERE url LIKE ? OR title LIKE ?",
                (like, like)
            )
            session_ids = [row[0] for row in cur.fetchall()]
            if not session_ids:
                return []
            placeholders = ",".join("?" for _ in session_ids)
            cur.execute(
                f"SELECT session_id, MAX(id) AS last_id, MAX(visited_at) AS last_visited, "
                f"COUNT(*) AS visits FROM history WHERE session_id IN ({placeholders}) "
                f"GROUP BY session_id ORDER BY last_id DESC LIMIT ?",
                (*session_ids, limit_sessions)
            )
        else:
            cur.execute(
                "SELECT session_id, MAX(id) AS last_id, MAX(visited_at) AS last_visited, "
                "COUNT(*) AS visits FROM history GROUP BY session_id "
                "ORDER BY last_id DESC LIMIT ?",
                (limit_sessions,)
            )
        sessions = cur.fetchall()

        result = []
        for session_id, _last_id, last_visited, visits in sessions:
            cur.execute(
                "SELECT url, title, visited_at FROM history WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            )
            entries = cur.fetchall()
            if not entries:
                continue
            result.append({
                "session_id": session_id,
                "visits": visits,
                "last_visited": last_visited,
                "entries": entries,
            })
        return result

    def clear_history(self):
        self.conn.execute("DELETE FROM history")
        self.conn.commit()

    # Marcadores
    def add_bookmark(self, url, title):
        try:
            self.conn.execute(
                "INSERT INTO bookmarks (url, title, created_at) VALUES (?, ?, ?)",
                (url, title, datetime.now().isoformat(timespec="seconds"))
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # ya existe

    def remove_bookmark(self, url):
        self.conn.execute("DELETE FROM bookmarks WHERE url = ?", (url,))
        self.conn.commit()

    def is_bookmarked(self, url):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM bookmarks WHERE url = ?", (url,))
        return cur.fetchone() is not None

    def get_bookmarks(self):
        cur = self.conn.cursor()
        cur.execute("SELECT url, title FROM bookmarks ORDER BY id DESC")
        return cur.fetchall()

    def search_bookmarks(self, query):
        like = f"%{query}%"
        cur = self.conn.cursor()
        cur.execute(
            "SELECT url, title FROM bookmarks WHERE url LIKE ? OR title LIKE ? ORDER BY id DESC",
            (like, like)
        )
        return cur.fetchall()
