import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import DEFAULT_TITLE, Chat, ChatMessage
from app.services.ai_service import generate_text

HISTORY_MESSAGES = 20  # скільки останніх повідомлень передається моделі
HISTORY_CHARS = 30000  # і скільки символів історії максимум
TITLE_CHARS = 60

SYSTEM_PROMPT = (
    "Ти — досвідчений наставник-програміст. Допомагаєш розібратися з кодом: пояснюєш, шукаєш помилки, "
    "пропонуєш виправлення. Відповідай українською мовою у форматі Markdown, код наводь у блоках "
    "із вказанням мови. Відповідай по суті."
)


async def list_chats(db: AsyncSession, user_id: uuid.UUID) -> list[Chat]:
    result = await db.execute(select(Chat).where(Chat.user_id == user_id).order_by(Chat.updated_at.desc()))
    return list(result.scalars().all())


async def create_chat(db: AsyncSession, user_id: uuid.UUID, title: str | None) -> Chat:
    chat = Chat(user_id=user_id, title=(title or "").strip() or DEFAULT_TITLE)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


async def get_owned_chat(db: AsyncSession, chat_id: uuid.UUID, user_id: uuid.UUID) -> Chat:
    """Повертає чат разом з повідомленнями або 404 (чужий чат неможливо відрізнити від неіснуючого)."""
    result = await db.execute(
        select(Chat).options(selectinload(Chat.messages)).where(Chat.id == chat_id, Chat.user_id == user_id)
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не знайдено")
    return chat


def _history_for_model(messages: list[ChatMessage]):
    """Останні повідомлення у форматі Gemini, обмежені за кількістю й загальним розміром."""
    from google.genai import types

    picked: list[ChatMessage] = []
    total = 0
    for m in reversed(messages[-HISTORY_MESSAGES:]):
        total += len(m.content)
        if picked and total > HISTORY_CHARS:
            break
        picked.append(m)
    picked.reverse()
    return [
        types.Content(role="user" if m.role == "user" else "model", parts=[types.Part(text=m.content)])
        for m in picked
    ]


async def send_message(db: AsyncSession, chat: Chat, content: str, client=None) -> tuple[ChatMessage, ChatMessage]:
    """Додає питання в чат, отримує відповідь AI і зберігає обидва повідомлення.

    Якщо AI недоступний, нічого не зберігається, а користувач може повторити те саме питання.
    """
    from google.genai import types

    history = _history_for_model(list(chat.messages))
    contents = [*history, types.Content(role="user", parts=[types.Part(text=content)])]
    answer = await generate_text(contents, system_instruction=SYSTEM_PROMPT, client=client)

    now = datetime.utcnow()
    user_msg = ChatMessage(chat_id=chat.id, role="user", content=content, created_at=now)
    assistant_msg = ChatMessage(
        chat_id=chat.id, role="assistant", content=answer or "(порожня відповідь)", created_at=datetime.utcnow()
    )
    db.add_all([user_msg, assistant_msg])
    if chat.title == DEFAULT_TITLE:
        chat.title = content.strip().replace("\n", " ")[:TITLE_CHARS]
    chat.updated_at = assistant_msg.created_at
    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)
    await db.refresh(chat)
    return user_msg, assistant_msg
