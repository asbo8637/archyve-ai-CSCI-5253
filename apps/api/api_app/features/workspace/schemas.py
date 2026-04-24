from pydantic import BaseModel


class WorkspaceContextRead(BaseModel):
    app_name: str
    auth_enabled: bool
