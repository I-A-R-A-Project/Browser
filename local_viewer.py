from config import ARCHIVES_CACHE_DIR
from iara_common.local_viewer import (
    extract_7z as _extract_7z,
    extract_epub_root as _extract_epub_root,
    extract_zip as _extract_zip,
    format_size,
    render_error,
    render_missing_dependency,
    render_rar_listing,
)


def extract_zip(path):
    return _extract_zip(path, ARCHIVES_CACHE_DIR)


def extract_7z(path):
    return _extract_7z(path, ARCHIVES_CACHE_DIR)


def extract_epub_root(path):
    return _extract_epub_root(path, ARCHIVES_CACHE_DIR)
