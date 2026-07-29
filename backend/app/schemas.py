from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DocumentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    chunk_count: int
    created_at: dt.datetime
    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatSource(BaseModel):
    document_id: int
    filename: str
    chunk_preview: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]


class ChatHistoryItem(BaseModel):
    role: str
    content: str
    created_at: dt.datetime
    model_config = {"from_attributes": True}
