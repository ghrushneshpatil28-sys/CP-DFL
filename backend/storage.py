import hashlib
import io
import warnings
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 16_000_000


def protected_path(root, key):
    root = Path(root).resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Invalid storage reference")
    return path


def validate_image(upload):
    content = upload.file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Maximum image size is 10 MiB")
    suffix = Path(upload.filename or "").suffix.lower()
    allowed = {"PNG": ({".png"}, "image/png"), "JPEG": ({".jpg", ".jpeg"}, "image/jpeg")}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in allowed:
                    raise HTTPException(415, "Only PNG and JPEG research images are supported")
                extensions, mime = allowed[image.format]
                if suffix not in extensions or upload.content_type != mime:
                    raise HTTPException(415, "Image extension, MIME type and decoded content must match")
                if image.width * image.height > MAX_PIXELS or min(image.size) < 32:
                    raise HTTPException(422, "Image must be at least 32 pixels per side and at most 16 megapixels")
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                clean = ImageOps.exif_transpose(image).convert("RGB")
                clean.load()
                result = io.BytesIO()
                clean.save(result, format="PNG")
                return result.getvalue(), clean.width, clean.height, hashlib.sha256(content).hexdigest()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, "Cannot decode this image safely")
