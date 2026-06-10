from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class MainThought(BaseModel):
    type: str


class LanguageType(str, Enum):
    KOREAN = "Korean"
    CHINESE = "Chinese"
    JAPANESE = "Japanese"
    ENGLISH = "English"
    THAI = "Thai"


class EventType(str, Enum):
    TOOL_CALLS = "tool_calls"
    ASSISTANCE = "assistance"
    FOLLOW_UP = "follow_up"
    CONFIRM_OPTION = "confirm_option"
    OPTION_PICKUP = "option_pickup"
    CONTACT_OPERATOR = "contact_operator"
    GENERAL = "general"


class AttachmentType(str, Enum):
    FILE = "FILE"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class ActionType(str, Enum):
    AGENT = "AGENT"
    FASTTRACK = "FASTTRACK"
    NORMAL = "NORMAL"


class MainLanguage(BaseModel):
    language: LanguageType = Field(
        default=LanguageType.THAI,
        description="Analyze to determine the language. If there is no Thai word present, use English only.",
    )


class MainTrusted(BaseModel):
    event: EventType = Field(
        default=EventType.GENERAL,
        description="Classify the answer into one of the predefined categories based on its content and intent.",
        examples=[EventType.FOLLOW_UP, EventType.GENERAL],
    )
    query: bool = Field(
        description="It should be true if the user's intent is to search for a product or service, even with just the name.",
    )


class RespondedAttachment(BaseModel):
    name: str = Field(
        description="The name or title of the attachment, providing a brief identifier or label.",
        examples=["Profile Picture", "User Manual", "Holiday Video"],
    )
    type: AttachmentType = Field(
        description="The media type of the attachment representing different forms of content.",
        examples=[AttachmentType.IMAGE, AttachmentType.VIDEO],
    )
    urls: List[str] = Field(
        default_factory=list,
        description="List of URLs pointing to the attachment resources. Can include CDN links, S3 paths, or direct URLs.",
        examples=["https://storage.cloud.com/media/image123.jpg", "s3://bucket/videos/clip456.mp4"],
    )


class MainResponded(BaseModel):
    action: ActionType = Field(
        description="The action to be taken. Must be one of: 'AGENT', 'FASTTRACK', or 'NORMAL'.",
        examples=[ActionType.NORMAL],
    )
    attachments: List[RespondedAttachment] = Field(
        default_factory=list,
        description="A list of attachments. Default is an empty list.",
        examples=[
            {"type": "IMAGE", "urls": ["https://example.com/images/pic1.jpg", "https://example.com/images/pic2.png"]},
            {"type": "FILE", "urls": ["https://example.com/files/doc1.pdf", "https://example.com/files/guide.txt"]},
        ],
    )


class FileExtensions:
    EXTENSIONS = [
        # Documents & Text Files
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".xls",
        ".xlsx",
        ".csv",
        ".ppt",
        ".pptx",
        ".odt",
        ".rtf",
        ".md",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".log",
        # Compressed Files
        ".zip",
        ".rar",
        ".tar",
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".tiff",
        ".tif",
        ".svg",
        # Photoshop File
        ".psd",
        # Audio Files
        ".mp3",
        ".wav",
        ".ogg",
        ".flac",
        ".aac",
        ".m4a",
        # Video Files
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".wmv",
        ".flv",
        ".webm",
    ]
