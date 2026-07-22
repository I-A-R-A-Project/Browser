import os
import fnmatch

from PyQt6.QtWebEngineCore import QWebEngineScript

class UserScript:
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.matches = []
        self.run_at = "document-idle"
        self.enabled = True
        self.code = ""
        self._parse()

    def _parse(self):
        with open(self.path, "r", encoding="utf-8") as f:
            self.code = f.read()
        for line in self.code.splitlines():
            stripped = line.strip()
            if not stripped.startswith("//"):
                continue
            if "@name" in stripped:
                self.name = stripped.split("@name", 1)[1].strip()
            elif "@match" in stripped:
                self.matches.append(stripped.split("@match", 1)[1].strip())
            elif "@run-at" in stripped:
                self.run_at = stripped.split("@run-at", 1)[1].strip()

    def matches_url(self, url: str) -> bool:
        if not self.matches:
            return False
        return any(fnmatch.fnmatch(url, pattern) for pattern in self.matches)

    def to_qwebengine_script(self):
        script = QWebEngineScript()
        script.setName(self.name)
        script.setSourceCode(self.code)
        # MainWorld: el script comparte el contexto JS de la página (puede
        # leer/modificar variables de la página, igual que Tampermonkey en
        # modo "unsafeWindow"). Si preferís aislamiento, cambiar a ApplicationWorld.
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        injection_map = {
            "document-start": QWebEngineScript.InjectionPoint.DocumentCreation,
            "document-end": QWebEngineScript.InjectionPoint.DocumentReady,
            "document-idle": QWebEngineScript.InjectionPoint.Deferred,
        }
        script.setInjectionPoint(
            injection_map.get(self.run_at, QWebEngineScript.InjectionPoint.Deferred)
        )
        script.setRunsOnSubFrames(False)
        return script


class UserScriptManager:
    def __init__(self, directory):
        self.directory = directory
        self.scripts = []
        self.reload()

    def reload(self):
        self.scripts = []
        if not os.path.isdir(self.directory):
            return
        for fname in sorted(os.listdir(self.directory)):
            if fname.endswith(".js"):
                try:
                    self.scripts.append(UserScript(os.path.join(self.directory, fname)))
                except Exception as e:
                    print(f"Error cargando userscript {fname}: {e}")

    def scripts_for_url(self, url: str):
        return [s for s in self.scripts if s.enabled and s.matches_url(url)]

    def create_example_script(self):
        example_path = os.path.join(self.directory, "ejemplo.js")
        if os.path.exists(example_path):
            return
        content = (
            "// ==UserScript==\n"
            "// @name    Ejemplo\n"
            "// @match   *://*.example.com/*\n"
            "// @run-at  document-idle\n"
            "// ==/UserScript==\n\n"
            "console.log('Userscript de ejemplo cargado en', location.hostname);\n"
        )
        with open(example_path, "w", encoding="utf-8") as f:
            f.write(content)
