import io
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from chatapi.models.files import FileDeleteResponse, FileUploadResponse
from chatapi.router.middleware import api_key_authentication, param_get_file, param_upload_file
from chatapi.router.queries import create_file, delete_checksum, get_checksum
from chatapi.router.utils import get_session
from chatapi.workflow.attachment import LOCAL_BLOB, policy

router = APIRouter(prefix="/api/files")
logger = logging.getLogger("fastapi.files")


@router.post(
    "/{session_id}",
    response_model=FileUploadResponse,
    dependencies=[Depends(api_key_authentication)],
    tags=["Files"],
)
async def upload_file(
    request: Request,
    query: Annotated[dict, Depends(param_upload_file)],
    db: Annotated[Session, Depends(get_session)],
) -> FileUploadResponse:
    """
    Handles file upload requests by reading the file data from the request stream,
    validating its size, and storing it in the database if it does not already exist.
    """

    try:
        file_data = bytearray()

        # Read chunks from request stream
        total_size = 0
        async for chunk in request.stream():
            total_size += len(chunk)
            if total_size > policy.IMAGE_MAX_SIZE:
                raise HTTPException(status_code=413, detail="File too large")
            file_data.extend(chunk)

        file = get_checksum(db, query.get("session_id", ""), file_data)
        if file:
            return FileUploadResponse(
                url=f"{LOCAL_BLOB}{file.checkSum}",
                checkSum=f"{file.checkSum}",
                type=str(file.fileType),
            )

        if not file_data:
            raise HTTPException(status_code=400, detail="Empty file")

        file_type = request.headers.get("content-type", "application/octet-stream")
        file = create_file(db, query.get("session_id", ""), file_data, file_type)

        return FileUploadResponse(url=f"{LOCAL_BLOB}{file.checkSum}", type=file_type, checkSum=f"{file.checkSum}")

    except Exception as e:
        logger.error(e, extra={"session_id": ""})
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{session_id}/{check_sum}", tags=["Files"])
async def get_file(
    query: Annotated[dict, Depends(param_get_file)],
    db: Annotated[Session, Depends(get_session)],
) -> StreamingResponse:
    """Asynchronously retrieves a file from the database based on its checksum."""

    store = get_checksum(db, query.get("session_id", ""), query.get("check_sum", ""))

    if not store:
        raise HTTPException(status_code=404, detail="File not found")

    return StreamingResponse(
        content=io.BytesIO(store.blob),  # type: ignore
        headers={"Content-Disposition": f"attachment; filename={store.fileName}"},
        media_type=str(store.fileType),
    )


@router.delete(
    "/{session_id}/{check_sum}",
    response_model=FileDeleteResponse,
    dependencies=[Depends(api_key_authentication)],
    tags=["Files"],
)
async def delete_file(
    query: Annotated[dict, Depends(param_get_file)],
    db: Annotated[Session, Depends(get_session)],
) -> FileDeleteResponse:
    """Deletes a file record from the database based on its checksum."""
    ok = delete_checksum(db, query)
    return FileDeleteResponse(ok=True, detail="exists" if ok else "not exists")
