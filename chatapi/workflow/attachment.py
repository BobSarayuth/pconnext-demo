import base64
import io
import logging
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from PIL import Image

from chatapi.models.policy import ImagePolicy
from chatapi.workflow.utils import Timer

logger = logging.getLogger("fastapi.attachment")

policy = ImagePolicy()

LOCAL_BLOB = "local-blob://"

VALID_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"]
AUDIO_TYPES = [
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/aac",
]

logger.info(f"Allow image domain:{policy.IMAGE_WISHLIST.split(',')}")
logger.info(f"Allow image type:{VALID_TYPES}")


_client = httpx.Client(
    verify=False,  # noqa: S501
    timeout=httpx.Timeout(10.0),
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
)


def _trim_log_value(value: str | None, max_len: int = 160) -> str:
    text = str(value or "")
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}...<truncated {len(text) - max_len} chars>"


def _domain_allowed(hostname: str, allowed_domains: list[str]) -> bool:
    for domain in allowed_domains:
        if hostname == domain:
            return True
        if domain.startswith("*.") and hostname.endswith(domain[1:]):
            return True
        if domain.startswith(".") and hostname.endswith(domain):
            return True
    return False


def _content_type_from_extension(url: str) -> str:
    path = url.split("?", maxsplit=1)[0]
    file_ext = path.rsplit(".", maxsplit=1)[-1].lower() if "." in path else ""
    if file_ext in ["jpg", "jpeg"]:
        return "image/jpeg"
    if file_ext in ["png"]:
        return "image/png"
    if file_ext in ["webp"]:
        return "image/webp"
    if file_ext in ["gif"]:
        return "image/gif"
    if file_ext in ["mp3"]:
        return "audio/mpeg"
    if file_ext in ["m4a", "mp4"]:
        return "audio/mp4"
    if file_ext in ["wav"]:
        return "audio/wav"
    if file_ext in ["webm"]:
        return "audio/webm"
    if file_ext in ["ogg", "oga"]:
        return "audio/ogg"
    if file_ext in ["aac"]:
        return "audio/aac"
    return ""


def _content_type_from_magic(blob: bytes) -> str:
    if blob.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if blob.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if blob.startswith(b"GIF87a") or blob.startswith(b"GIF89a"):
        return "image/gif"
    if len(blob) >= 12 and blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "image/webp"
    if len(blob) >= 12 and blob[:4] == b"RIFF" and blob[8:12] == b"WAVE":
        return "audio/wav"
    if blob.startswith(b"ID3") or blob.startswith(b"\xff\xfb"):
        return "audio/mpeg"
    return ""


def _normalize_download_content_type(content_type: str, url: str, blob: bytes | None = None) -> str:
    normalized = content_type.split(";", maxsplit=1)[0].strip().lower()
    if normalized and normalized not in ["binary/octet-stream", "application/octet-stream", "application/xml", "text/xml"]:
        return normalized
    if blob:
        detected = _content_type_from_magic(blob)
        if detected:
            return detected
    return _content_type_from_extension(url) or normalized


class FileAttachment:
    def __init__(self, url: str = "", blob: bytes | bytearray | None = None, content_type: str = "") -> None:
        self.content_type: str = content_type
        self.blob: bytes = b""

        if blob is None:
            blob = bytearray()

        if blob:
            self.blob = bytes(blob)
        elif url:
            self._process_url(url)

    def _process_url(self, url: str) -> None:
        """Process a URL to fetch the file content"""
        elapsed = Timer()

        # Validate the URL
        uri = urlparse(url)
        logger.info(url[:50] + "..." if len(url) > 50 else url)
        allowed_domains = [domain.strip().lower() for domain in policy.IMAGE_WISHLIST.split(",") if domain.strip()]
        hostname = (uri.hostname or "").lower()
        allow_domain = _domain_allowed(hostname, allowed_domains)
        allow_schema = uri.scheme in policy.IMAGE_SCHEMA_WISHLIST

        if uri.scheme == LOCAL_BLOB.rstrip("://"):
            logger.warning(
                {
                    "event": "attachment_url_rejected",
                    "reason": "local_blob_without_db",
                    "url": _trim_log_value(url),
                }
            )
            raise HTTPException(status_code=400, detail="Local blob attachment requires database context")

        if not allow_schema:
            logger.warning(
                {
                    "event": "attachment_url_rejected",
                    "reason": "unsafe_scheme",
                    "scheme": uri.scheme or "missing",
                    "url": _trim_log_value(url),
                }
            )
            raise HTTPException(status_code=400, detail=f"Unsafe URL scheme: {uri.scheme or 'missing'}")

        if not allow_domain:
            logger.warning(
                {
                    "event": "attachment_url_rejected",
                    "reason": "unsafe_domain",
                    "domain": hostname or "missing",
                    "url": _trim_log_value(url),
                }
            )
            raise HTTPException(status_code=400, detail=f"Unsafe URL domain: {hostname or 'missing'}")
        logger.info(
            {
                "event": "attachment_url_allowed",
                "domain": hostname,
                "scheme": uri.scheme,
                "url": _trim_log_value(url),
            }
        )
        del uri

        # First, check content type with HEAD request
        try:
            head_res = _client.head(url)
            head_content_type = head_res.headers.get("Content-Type", "")
            if 200 <= head_res.status_code < 300:
                self.content_type = _normalize_download_content_type(head_content_type, url)
            logger.info(
                {
                    "event": "attachment_head_checked",
                    "status_code": head_res.status_code,
                    "content_type": head_content_type,
                    "normalized_content_type": self.content_type,
                    "url": _trim_log_value(url),
                }
            )
        except Exception as e:
            logger.error(f" - Error checking content type: {e!s}")
            raise HTTPException(status_code=400, detail=f"Error accessing URL: {e!s}") from e

        # Then download the file
        res = _client.get(url)
        elapsed.stop()
        get_content_type = res.headers.get("Content-Type", "")
        logger.info(
            {
                "event": "attachment_get_completed",
                "status_code": res.status_code,
                "content_type": get_content_type,
                "elapsed": float(elapsed),
                "url": _trim_log_value(url),
            }
        )

        if res.status_code != 200:
            raise HTTPException(status_code=404, detail="File not found at the provided URL")

        if len(res.content) > policy.IMAGE_MAX_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 20MB)")

        self.blob = res.content
        self.content_type = _normalize_download_content_type(get_content_type or self.content_type, url, self.blob)
        logger.info(
            {
                "event": "attachment_content_type_resolved",
                "content_type": self.content_type,
                "size": len(self.blob),
                "url": _trim_log_value(url),
            }
        )

    def to_image(self) -> "ImageMessage":
        """Convert this FileAttachment to an ImageMessage"""
        return ImageMessage(blob=self.blob, content_type=self.content_type)


class ImageMessage(FileAttachment):
    def __init__(self, url: str = "", blob: bytes | bytearray | None = None, content_type: str = "") -> None:
        super().__init__(url, blob, content_type)
        self.content_type: str = "image/jpg"
        self.thumbnail: bytes = b""

        if blob is None:
            blob = bytearray()

        # Validate that this is an image
        if not self.is_valid():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {self.content_type}. Only image files are supported.",
            )

        # Process the image
        try:
            self.blob = self.convert(self.blob, policy.IMAGE_RESOLUTION_MAX)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail="Attachment is not a valid image or the URL returned a non-image response.",
            ) from e

    def is_valid(self) -> bool:
        """Check if the file is a valid image based on content type"""
        return self.content_type in VALID_TYPES

    def to_dict(self) -> dict:
        return {"type": "image_url", "image_url": {"url": self.get_data()}}

    def get_data(self) -> str:
        return f"data:{self.content_type};base64,{self.to_base64(self.blob)}"

    def get_thumbnail(self) -> str:
        self.thumbnail = self.convert(self.blob, policy.IMAGE_RESOLUTION_THUMBNAIL)
        return f"data:{self.content_type};base64,{self.to_base64(self.thumbnail)}"

    def to_base64(self, image_data: bytes | bytearray) -> str:
        """Converts binary image content to a base64-encoded data URL"""
        return base64.b64encode(image_data).decode("utf-8")

    # Function to resize the image, keeping the aspect ratio with the shortest dimension set to 250px
    def convert(self, image_data: bytes | bytearray, thumbnail_size: int = 0) -> bytes:
        """Resize the image while maintaining its aspect ratio with the shortest dimension set to target_size.
        Supports RGB and RGBA."""
        img_output = io.BytesIO()
        img_input = Image.open(io.BytesIO(image_data))

        output_format = "JPEG"
        # if img_input.mode == "RGBA" or (img_input.mode == "P" and "transparency" in img_input.info):
        if img_input.mode in ["RGBA", "P"]:
            output_format = "PNG"

        width, height = img_input.size
        if thumbnail_size > 0 and (thumbnail_size < width or thumbnail_size < height):
            # Calculate the new dimensions while maintaining aspect ratio
            if width < height:
                new_width = thumbnail_size
                new_height = int((thumbnail_size / width) * height)
            else:
                new_height = thumbnail_size
                new_width = int((thumbnail_size / height) * width)

            # Resize the image
            resized = img_input.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized.save(img_output, format=output_format)
        else:
            img_input.save(img_output, format=output_format)

        img_output.seek(0)
        return img_output.read()
