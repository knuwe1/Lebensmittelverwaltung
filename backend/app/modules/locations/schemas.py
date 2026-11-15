import uuid

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    location_type: str | None = Field(default=None, max_length=50)


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    location_type: str | None = Field(default=None, max_length=50)


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    description: str | None
    location_type: str | None
    active: bool
    path: str = ""
