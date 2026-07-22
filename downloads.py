import os
from PyQt6.QtCore import QStandardPaths
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from config import BASE_DIR

class DownloadItem:
    STATE_NAMES = {
        QWebEngineDownloadRequest.DownloadState.DownloadRequested: "Solicitando",
        QWebEngineDownloadRequest.DownloadState.DownloadInProgress: "Descargando",
        QWebEngineDownloadRequest.DownloadState.DownloadCompleted: "Completado",
        QWebEngineDownloadRequest.DownloadState.DownloadCancelled: "Cancelado",
        QWebEngineDownloadRequest.DownloadState.DownloadInterrupted: "Interrumpido",
    }

    def __init__(self, request: QWebEngineDownloadRequest):
        self.request = request
        self.filename = request.downloadFileName()
        self.directory = request.downloadDirectory()

    @property
    def path(self):
        return os.path.join(self.directory, self.filename)

    def progress_text(self):
        received = self.request.receivedBytes()
        total = self.request.totalBytes()
        state_str = self.STATE_NAMES.get(self.request.state(), "?")
        if total > 0:
            pct = int(received / total * 100)
            size_mb = total / (1024 * 1024)
            return f"{self.filename} — {state_str} ({pct}% de {size_mb:.1f} MB)"
        received_mb = received / (1024 * 1024)
        return f"{self.filename} — {state_str} ({received_mb:.1f} MB)"


class DownloadManager:
    def __init__(self):
        self.items = []

    def handle_download(self, request: QWebEngineDownloadRequest):
        download_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        ) or os.path.join(BASE_DIR, "downloads")
        os.makedirs(download_dir, exist_ok=True)

        request.setDownloadDirectory(download_dir)
        final_name = self._unique_name(download_dir, request.downloadFileName())
        request.setDownloadFileName(final_name)
        request.accept()

        item = DownloadItem(request)
        self.items.insert(0, item)
        return item

    @staticmethod
    def _unique_name(directory, filename):
        base, ext = os.path.splitext(filename)
        candidate = filename
        i = 1
        while os.path.exists(os.path.join(directory, candidate)):
            candidate = f"{base} ({i}){ext}"
            i += 1
        return candidate
