from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    checkSum: str = Field(description="checksum of the uploaded file")
    url: str = Field(description="URL file can be accessed")
    type: str = Field(description="type or format file")


class FileDeleteResponse(BaseModel):
    ok: bool = Field(description="Session deletion status", default=True)
    detail: str = Field(description="Details of session cleanup")
