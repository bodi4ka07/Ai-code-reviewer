import logging

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


async def generate_text(contents, system_instruction: str | None = None, client=None) -> str:
    """Звичайна текстова відповідь Gemini. Помилки сервісу перетворюються на 503 без технічних деталей."""
    if client is None:
        from google import genai

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

    config = None
    if system_instruction:
        from google.genai import types

        config = types.GenerateContentConfig(system_instruction=system_instruction)

    try:
        response = await client.aio.models.generate_content(model=settings.GEMINI_MODEL, contents=contents, config=config)
    except Exception:
        logger.exception("Помилка Gemini")
        raise HTTPException(status_code=503, detail="Сервіс AI тимчасово недоступний")
    return response.text or ""
