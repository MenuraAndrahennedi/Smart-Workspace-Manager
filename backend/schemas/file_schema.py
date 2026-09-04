from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime

class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_name: str
    stored_name: str
    extension: str
    category: str
    size_bytes: int
    status: str
    created_at: datetime
    updated_at: datetime

class FileDeleteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    message: str





