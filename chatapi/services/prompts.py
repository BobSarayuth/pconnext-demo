import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from chatapi.models.orm import DynamicPrompt
from chatapi.workflow.chat_history import BaseChatHistory

logger = logging.getLogger("fastapi.prompts")

PROMPT_ROOT = Path("./agentic/prompts")
PROMPT_FILE_SUFFIXES = {".md", ".txt"}
_prompt_store: BaseChatHistory | None = None


def normalize_prompt_path(file_path: str) -> str:
    clean_path = file_path.strip().lstrip("/")
    if not clean_path:
        raise HTTPException(status_code=400, detail="400: Prompt file path is required")

    path = Path(clean_path)
    if path.is_absolute() or ".." in path.parts:
        raise HTTPException(status_code=400, detail="400: Invalid prompt file path")
    if path.suffix not in PROMPT_FILE_SUFFIXES:
        raise HTTPException(status_code=400, detail="400: Prompt file must be .md or .txt")

    return path.as_posix()


def default_prompt_files() -> Iterator[tuple[str, str]]:
    if not PROMPT_ROOT.exists():
        return

    for path in sorted(PROMPT_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in PROMPT_FILE_SUFFIXES:
            continue

        yield path.relative_to(PROMPT_ROOT).as_posix(), path.read_text(encoding="utf-8")


def seed_default_prompts(db: Session) -> int:
    inserted = 0
    now = datetime.now(UTC)
    for path, content in default_prompt_files():
        exists = db.get(DynamicPrompt, path)
        if exists:
            continue

        db.add(DynamicPrompt(path=path, content=content, createdDate=now, updatedDate=now))
        inserted += 1

    if inserted:
        db.commit()
        logger.info("Seeded %s default prompts into database", inserted)
    return inserted


def list_prompts(db: Session) -> list[DynamicPrompt]:
    return db.query(DynamicPrompt).order_by(DynamicPrompt.path.asc()).all()


def get_prompt(db: Session, file_path: str) -> DynamicPrompt | None:
    return db.get(DynamicPrompt, normalize_prompt_path(file_path))


def update_prompt(db: Session, file_path: str, content: str, create: bool = False) -> DynamicPrompt:
    prompt_path = normalize_prompt_path(file_path)
    prompt = db.get(DynamicPrompt, prompt_path)
    if not prompt:
        if not create:
            raise HTTPException(status_code=404, detail="404: Prompt file not found")
        prompt = DynamicPrompt(path=prompt_path, content=content, createdDate=datetime.now(UTC), updatedDate=datetime.now(UTC))
        db.add(prompt)
    else:
        prompt.content = content
        prompt.updatedDate = datetime.now(UTC)

    try:
        db.commit()
    except SQLAlchemyError as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"500: Failed to update prompt: {ex}") from ex

    db.refresh(prompt)
    logger.info("Prompt updated in database: %s", prompt.path)
    return prompt


@contextmanager
def prompt_session() -> Iterator[Session]:
    global _prompt_store
    if _prompt_store is None:
        _prompt_store = BaseChatHistory()

    session = _prompt_store.conn()
    try:
        yield session
    finally:
        session.close()


def read_prompt_from_db(file_path: str) -> str | None:
    try:
        with prompt_session() as db:
            prompt = get_prompt(db, file_path)
            return prompt.content if prompt else None
    except Exception as ex:
        logger.warning("Unable to read prompt from database: %s", ex)
        return None
