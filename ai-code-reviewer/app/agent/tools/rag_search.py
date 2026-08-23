from sqlalchemy import text
from app.core.config import settings


async def get_embedding(text_content: str) -> list[float]:
    from google import genai
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.embed_content(
        model="text-embedding-001",
        contents=text_content,
    )
    return response.embeddings[0].values


async def search_docs(query: str, db, limit: int = 4) -> list[str]:
    query_embedding = await get_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    sql = text("""
        SELECT content, source
        FROM doc_chunks
        ORDER BY embedding <=> :embedding::vector
        LIMIT :limit
    """)

    result = await db.execute(sql, {"embedding": embedding_str, "limit": limit})
    rows = result.fetchall()

    if not rows:
        return []

    return [f"[{row.source}]\n{row.content}" for row in rows]


async def format_rag_context(chunks: list[str]) -> str:
    if not chunks:
        return ""

    lines = ["Релевантна документація:"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n--- Документ {i} ---")
        lines.append(chunk)

    return "\n".join(lines)