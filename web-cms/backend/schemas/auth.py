"""Auth schemas for login/logout."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str
