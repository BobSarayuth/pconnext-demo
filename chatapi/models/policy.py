from typing import ClassVar

from pydantic_settings import BaseSettings

from chatapi.config import DEFAULT_MODEL_CONFIG


class ImagePolicy(BaseSettings):
    IMAGE_RESOLUTION_MAX: int = 800
    IMAGE_RESOLUTION_THUMBNAIL: int = 240  # pixel
    IMAGE_MAX_SIZE: int = 10485760  # maximum size at 10MB
    IMAGE_WISHLIST: str = (
        "localhost,api-data.line.me,*.line-scdn.net,scg.teemchat.net,i.ibb.co,"
        "do-common-consolidate-chat-dev.s3.ap-southeast-1.amazonaws.com"
    )
    IMAGE_SCHEMA_WISHLIST: ClassVar[list[str]] = ["http", "https"]

    model_config = DEFAULT_MODEL_CONFIG
