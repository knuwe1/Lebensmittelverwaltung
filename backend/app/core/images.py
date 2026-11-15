"""Sichere Verarbeitung hochgeladener Bilder (NFR-SEC-006).

Bilder werden niemals unverändert gespeichert: Pillow dekodiert sie vollständig und
kodiert sie neu als WebP. Dadurch werden eingebettete Inhalte und Metadaten (EXIF,
GPS-Position) verworfen, und nur tatsächlich gültige Rasterbilder werden akzeptiert.
"""

import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import ValidationFailed

Image.MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "GIF", "BMP"}


def media_root() -> Path:
    root = Path(get_settings().media_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def load_image(data: bytes) -> Image.Image:
    if len(data) > get_settings().max_upload_bytes:
        raise ValidationFailed("Das Bild ist zu groß.", code="image_too_large")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()
        if fmt not in ALLOWED_FORMATS:
            raise ValidationFailed("Dieses Bildformat wird nicht unterstützt.", code="image_format")
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as exc:
        raise ValidationFailed("Die Datei ist kein gültiges Bild.", code="invalid_image") from exc
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def save_image(data: bytes, subdir: str, max_size: int = 1024) -> str:
    """Speichert ein Bild verkleinert als WebP und liefert den relativen Pfad."""
    img = load_image(data)
    img.thumbnail((max_size, max_size))
    rel = Path(subdir) / f"{uuid.uuid4().hex}.webp"
    target = media_root() / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target, "WEBP", quality=82, method=4)
    return rel.as_posix()


def resolve(rel_path: str) -> Path:
    root = media_root().resolve()
    path = (root / rel_path).resolve()
    if root not in path.parents:
        raise ValidationFailed("Ungültiger Dateipfad.", code="invalid_path")
    return path


def delete_image(rel_path: str | None) -> None:
    if rel_path:
        resolve(rel_path).unlink(missing_ok=True)
