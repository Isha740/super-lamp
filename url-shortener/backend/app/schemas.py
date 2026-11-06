from datetime import datetime

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class LinkIn(BaseModel):
    long_url: str = Field(min_length=1, max_length=4096)


class LinkOut(BaseModel):
    short_code: str
    short_url: str
    long_url: str
    clicks: int
    created_at: datetime


class ClickStats(BaseModel):
    short_code: str
    clicks: int
