from enum import Enum


class RespondedType(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    STICKER = "STICKER"
    DOCUMENT = "DOCUMENT"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
