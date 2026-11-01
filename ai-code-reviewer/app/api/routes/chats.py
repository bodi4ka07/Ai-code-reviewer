import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatCreate,
    ChatDetailResponse,
    ChatResponse,
    ChatUpdate,
    MessageCreate,
    MessagePairResponse,
)
from app.services import chat_service

router = APIRouter()


@router.get("/", response_model=list[ChatResponse])
async def list_chats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await chat_service.list_chats(db, current_user.id)


@router.post("/", response_model=ChatResponse, status_code=201)
async def create_chat(
    data: ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await chat_service.create_chat(db, current_user.id, data.title)


@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def get_chat(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await chat_service.get_owned_chat(db, chat_id, current_user.id)


@router.patch("/{chat_id}", response_model=ChatResponse)
async def rename_chat(
    chat_id: uuid.UUID,
    data: ChatUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = await chat_service.get_owned_chat(db, chat_id, current_user.id)
    chat.title = data.title
    await db.commit()
    await db.refresh(chat)
    return chat


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = await chat_service.get_owned_chat(db, chat_id, current_user.id)
    await db.delete(chat)
    await db.commit()


@router.post("/{chat_id}/messages", response_model=MessagePairResponse)
async def send_message(
    chat_id: uuid.UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Надіслати питання в чат і отримати відповідь AI. Історія чату передається моделі."""
    chat = await chat_service.get_owned_chat(db, chat_id, current_user.id)
    user_msg, assistant_msg = await chat_service.send_message(db, chat, data.content.strip())
    return {"user_message": user_msg, "assistant_message": assistant_msg, "chat": chat}
