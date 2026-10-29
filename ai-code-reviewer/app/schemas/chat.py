import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)


class ChatResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatDetailResponse(ChatResponse):
    messages: list[ChatMessageResponse] = []


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessagePairResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    chat: ChatResponse
