import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.models import Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    role: Role
    can_do_inventory: bool
    active: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=200)
    role: Role = Role.MEMBER
    can_do_inventory: bool = False


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=8, max_length=200)
    role: Role | None = None
    can_do_inventory: bool | None = None
    active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)
