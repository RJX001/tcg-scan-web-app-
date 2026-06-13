"""Crop a base64-encoded image using a normalized bounding box from detect."""

from __future__ import annotations

import base64
import io

from PIL import Image, UnidentifiedImageError


def crop_image_b64(
    image_b64: str,
    bbox: dict[str, float],
    *,
    min_size: int = 32,
) -> str:
    """Return base64 of cropped region. bbox keys: x, y, w, h (0–1 normalized)."""
    raw = base64.b64decode(image_b64)
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        return image_b64

    w, h = img.size

    x0 = max(0, int(bbox.get("x", 0) * w))
    y0 = max(0, int(bbox.get("y", 0) * h))
    x1 = min(w, int((bbox.get("x", 0) + bbox.get("w", 1.0)) * w))
    y1 = min(h, int((bbox.get("y", 0) + bbox.get("h", 1.0)) * h))

    if x1 - x0 < min_size or y1 - y0 < min_size:
        return image_b64

    cropped = img.crop((x0, y0, x1, y1))
    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode("ascii")
