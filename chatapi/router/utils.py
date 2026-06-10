from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from chatapi.workflow.chat_history import BaseChatHistory

load_dotenv()
with BaseChatHistory() as chat:

    def get_session() -> Generator[Session]:
        with chat.conn() as session:
            try:
                yield session
            finally:
                session.close()


# Add content type mapping
CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
}


def get_exts(content_type: str) -> str:
    return CONTENT_TYPE_TO_EXT.get(content_type.lower(), ".bin")
