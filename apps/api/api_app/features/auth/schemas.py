from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AuthSessionUserRead(BaseModel):
    id: UUID
    auth0_user_id: str
    email: str | None
    full_name: str | None
    status: str


class AuthSessionMembershipRead(BaseModel):
    company_id: UUID
    company_name: str
    role: str
    status: str


class ActiveCompanyRead(BaseModel):
    id: UUID
    name: str
    role: str


class AuthSessionRead(BaseModel):
    user: AuthSessionUserRead
    memberships: list[AuthSessionMembershipRead]
    active_company: ActiveCompanyRead | None
    permissions: list[str]
    needs_company_setup: bool
    company_selection_required: bool


class CreateCompanyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("A company name is required.")
        return normalized


class SelectCompanyRequest(BaseModel):
    company_id: UUID
