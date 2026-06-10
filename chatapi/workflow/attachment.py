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

logger.info(f"Allow image domain:{policy.IMAGE_WISHLIST.split(',')}")
logger.info(f"Allow image type:{VALID_TYPES}")


_client = httpx.Client(
    verify=False,  # noqa: S501
    timeout=httpx.Timeout(10.0),
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
)


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
        allow_domain = uri.hostname in [domain.strip() for domain in policy.IMAGE_WISHLIST.split(",")]
        allow_schema = uri.scheme in policy.IMAGE_SCHEMA_WISHLIST

        if not (allow_domain or allow_schema):
            raise HTTPException(status_code=400, detail="Unsafe URL")
        del uri

        # First, check content type with HEAD request
        try:
            head_res = _client.head(url)
            print(f" --- {head_res.headers}")
            self.content_type = head_res.headers.get("Content-Type", "")
            logger.info(f" - Content type: {self.content_type}")

            # Handle binary/octet-stream by checking file extension
            if self.content_type == "binary/octet-stream" or not self.content_type:
                file_ext = url.lower().split(".")[-1] if "." in url else ""
                if file_ext in ["jpg", "jpeg"]:
                    self.content_type = "image/jpeg"
                elif file_ext in ["png"]:
                    self.content_type = "image/png"
                elif file_ext in ["webp"]:
                    self.content_type = "image/webp"
                elif file_ext in ["gif"]:
                    self.content_type = "image/gif"
                logger.info(f" - Adjusted content type from extension: {self.content_type}")
        except Exception as e:
            logger.error(f" - Error checking content type: {e!s}")
            raise HTTPException(status_code=400, detail=f"Error accessing URL: {e!s}") from e

        # Then download the file
        res = _client.get(url)
        elapsed.stop()
        logger.info(f" - Download completed: {float(elapsed)}s")

        if res.status_code != 200:
            raise HTTPException(status_code=404, detail="File not found at the provided URL")

        if len(res.content) > policy.IMAGE_MAX_SIZE:
            raise HTTPException(status_code=413, detail="File too large (max 20MB)")

        self.blob = res.content

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
        self.blob = self.convert(self.blob, policy.IMAGE_RESOLUTION_MAX)

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
