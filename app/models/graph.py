from pydantic import BaseModel, Field


class GraphAccessToken(BaseModel):
    access_token: str = Field(min_length=1)
    token_type: str = Field(default="Bearer")
    expires_in: int = Field(ge=0)
    scope: str | None = None


class GraphTokenStatus(BaseModel):
    authenticated: bool
    token_type: str
    expires_in: int = Field(ge=0)
    scope: str | None = None

