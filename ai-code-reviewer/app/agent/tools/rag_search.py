from dataclasses import dataclass

from sqlalchemy import text

from app.core.config import settings


@dataclass
class DocChunk:
    source: str
    content: str


def _client():
    from google import genai
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def get_embedding(text_content: str, task_type: str = "RETRIEVAL_QUERY") -> list[float]:
    """Embedding однією моделлю і розмірністю, і для документів (seed), і для запитів."""
    from google.genai import types

    response = await _client().aio.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=text_content,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=settings.EMBEDDING_DIM,
        ),
    )
    return response.embeddings[0].values


def build_query(code: str, language: str, lint_messages: list[str]) -> str:
    """Запит для пошуку залежить від самого коду та знахідок лінтера."""
    parts = [f"{language} code review"]
    parts += lint_messages[:5]
    parts.append(code[:800])
    return "\n".join(parts)


def to_vector_literal(values: list[float]) -> str:
    return "[" + ",".join(str(x) for x in values) + "]"


async def search_docs(query: str, db, language: str, limit: int = 4) -> list[DocChunk]:
    """Шукає релевантні фрагменти документації: загальні (language IS NULL) та для мови."""
    embedding = to_vector_literal(await get_embedding(query))

    sql = text("""
        SELECT source, content
        FROM doc_chunks
        WHERE language IS NULL OR language = :language
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :limit
    """)
    result = await db.execute(sql, {"embedding": embedding, "language": language, "limit": limit})
    return [DocChunk(source=row.source, content=row.content) for row in result.fetchall()]


def format_rag_context(chunks: list[DocChunk]) -> str:
    if not chunks:
        return ""
    lines = ["Релевантна документація (посилайся на джерело в полі reference):"]
    for chunk in chunks:
        lines.append(f"\n[{chunk.source}]\n{chunk.content}")
    return "\n".join(lines)
