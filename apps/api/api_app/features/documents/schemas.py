from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from archyve_common.models import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: DocumentStatus
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
