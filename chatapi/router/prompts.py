import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from chatapi.router.middleware import api_key_authentication
from chatapi.router.utils import get_session
from chatapi.services.prompts import get_prompt, list_prompts, normalize_prompt_path, seed_default_prompts, update_prompt

router = APIRouter(prefix="/api/prompts", dependencies=[Depends(api_key_authentication)])
logger = logging.getLogger("fastapi.prompts")


class PromptFileInfo(BaseModel):
    path: str = Field(description="Prompt file path relative to prompt directory")
    size: int = Field(description="File size in bytes")
    updatedAt: str = Field(description="Last modified time in ISO-8601")


class PromptFileResponse(BaseModel):
    path: str = Field(description="Prompt file path relative to prompt directory")
    content: str = Field(description="Prompt file content")
    updatedAt: str = Field(description="Last modified time in ISO-8601")


class PromptFileUpdateRequest(BaseModel):
    content: str = Field(description="Replacement prompt content")
    create: bool = Field(default=False, description="Create the file if it does not exist")


class PromptFileUpdateResponse(BaseModel):
    ok: bool = Field(default=True, description="Update status")
    path: str = Field(description="Prompt file path relative to prompt directory")
    updatedAt: str = Field(description="Last modified time in ISO-8601")


@router.get("/files", response_model=list[PromptFileInfo], tags=["Config"])
async def list_prompt_files(db: Annotated[Session, Depends(get_session)]) -> list[PromptFileInfo]:
    """List editable prompt records from database."""
    seed_default_prompts(db)
    return [
        PromptFileInfo(path=prompt.path, size=len(prompt.content.encode("utf-8")), updatedAt=prompt.updatedDate.isoformat())
        for prompt in list_prompts(db)
    ]


@router.get("/{file_path:path}", response_model=PromptFileResponse, tags=["Config"])
async def get_prompt_file(file_path: str, db: Annotated[Session, Depends(get_session)]) -> PromptFileResponse:
    """Read one prompt record from database."""
    seed_default_prompts(db)
    prompt = get_prompt(db, file_path)
    if not prompt:
        normalize_prompt_path(file_path)
        raise HTTPException(status_code=404, detail="404: Prompt file not found")

    return PromptFileResponse(path=prompt.path, content=prompt.content, updatedAt=prompt.updatedDate.isoformat())


@router.put("/{file_path:path}", response_model=PromptFileUpdateResponse, tags=["Config"])
async def update_prompt_file(
    file_path: str,
    payload: PromptFileUpdateRequest,
    db: Annotated[Session, Depends(get_session)],
) -> PromptFileUpdateResponse:
    """Replace one prompt record in database."""
    seed_default_prompts(db)
    prompt = update_prompt(db, file_path, payload.content, create=payload.create)
    return PromptFileUpdateResponse(ok=True, path=prompt.path, updatedAt=prompt.updatedDate.isoformat())
