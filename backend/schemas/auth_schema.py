from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

class TokenResponse(BaseModel):
    access_token:str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr

