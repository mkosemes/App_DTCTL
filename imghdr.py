"""Remplacement minimal du module imghdr supprime en Python 3.13."""

from __future__ import annotations

import io
from typing import Optional

from PIL import Image


def what(file, h: Optional[bytes] = None) -> Optional[str]:
    """Detecte le format d'une image et retourne l'extension."""
    try:
        if h is not None:
            data = h if isinstance(h, (bytes, bytearray)) else bytes(h)
            with Image.open(io.BytesIO(data)) as img:
                return img.format.lower()

        if isinstance(file, (str, bytes, bytearray)):
            with Image.open(file) as img:
                return img.format.lower()

        if hasattr(file, "read"):
            pos = file.tell() if hasattr(file, "tell") else None
            data = file.read()
            if pos is not None and hasattr(file, "seek"):
                file.seek(pos)
            with Image.open(io.BytesIO(data)) as img:
                return img.format.lower()
    except Exception:
        return None

    return None
