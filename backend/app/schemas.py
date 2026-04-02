# Schemas for URLCreate ,URLResponse ,URLRedirect 

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl


class UrlCreate(BaseModel):
    url: HttpUrl
    custom_code: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

class UrlResponse(BaseModel):
    id: UUID
    short_code: str
    original_url: HttpUrl
    created_at: datetime
    clicks: int

    model_config = ConfigDict(from_attributes=True)


class UrlRedirect(BaseModel):
    short_code: str
