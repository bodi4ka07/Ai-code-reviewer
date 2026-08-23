"""
Скрипт для завантаження документації в БД як векторні embeddings.
Запускати один раз: docker-compose exec api python scripts/seed_docs.py
"""

PEP8_CHUNKS = [
    {"source": "PEP8", "content": "Indentation: Use 4 spaces per indentation level. Spaces are the preferred indentation method. Tabs should be used solely to remain consistent with code that is already indented with tabs."},
    {"source": "PEP8", "content": "Maximum Line Length: Limit all lines to a maximum of 79 characters. For docstrings or comments, the line length should be limited to 72 characters."},
    {"source": "PEP8", "content": "Imports: Always put at the top of the file. Group in order: standard library, third party, local application imports. Each group separated by a blank line."},
    {"source": "PEP8", "content": "Whitespace in Expressions: Avoid extraneous whitespace immediately inside parentheses, brackets or braces. Avoid trailing whitespace anywhere."},
    {"source": "PEP8", "content": "Naming Conventions: Function names lowercase with underscores. Constants in ALL_CAPS. Class names use CapWords convention."},
    {"source": "PEP8", "content": "Comments: Should be complete sentences. Inline comments separated by at least two spaces from the statement. Use docstrings for public modules, functions, classes."},
    {"source": "PEP8", "content": "Comparisons to singletons like None should always be done with is or is not, never the equality operators."},
    {"source": "PEP8", "content": "Exception Handling: Use specific exception types rather than bare except clauses. Always catch the most specific exception you can handle."},
    {"source": "PEP8", "content": "Context Managers: Use with statement for resource management, especially for file operations and database connections."},
    {"source": "PEP8", "content": "Function length: Keep functions short and focused. Each function should do one thing. If a function is longer than 20-30 lines, consider refactoring."},
]

OWASP_CHUNKS = [
    {"source": "OWASP Top 10", "content": "A01 Broken Access Control: Users cannot act outside of their intended permissions. Implement access control mechanisms once and re-use them throughout the application."},
    {"source": "OWASP Top 10", "content": "A02 Cryptographic Failures: Do not use MD5 or SHA1 for passwords. Use bcrypt, scrypt, or Argon2. Encrypt sensitive data in transit and at rest."},
    {"source": "OWASP Top 10", "content": "A03 Injection: SQL injection occurs when untrusted data is sent to an interpreter. Use parameterized queries. Never use string concatenation to build SQL queries with user input."},
    {"source": "OWASP Top 10", "content": "A04 Insecure Design: Use threat modeling for critical authentication, access control, business logic. Integrate security into user stories."},
    {"source": "OWASP Top 10", "content": "A05 Security Misconfiguration: Default accounts and passwords still enabled. Error handling reveals stack traces to users. Unnecessary features enabled."},
    {"source": "OWASP Top 10", "content": "A06 Vulnerable Components: Continuously inventory versions of all components. Monitor CVE and NVD for vulnerabilities in the components you use."},
    {"source": "OWASP Top 10", "content": "A07 Authentication Failures: Implement multi-factor authentication. Never store passwords in plain text. Protect against brute force attacks with rate limiting."},
    {"source": "OWASP Top 10", "content": "A08 Software Integrity Failures: Verify integrity of software and data. Do not rely on plugins from untrusted sources."},
    {"source": "OWASP Top 10", "content": "A09 Security Logging Failures: Log all login, access control, and input validation failures with sufficient context to identify suspicious accounts."},
    {"source": "OWASP Top 10", "content": "A10 SSRF: Validate and sanitize all client-supplied URLs. Enforce URL schema, port, and destination with a positive allow list to prevent SSRF attacks."},
]

ALL_CHUNKS = PEP8_CHUNKS + OWASP_CHUNKS


async def seed():
    import sys
    sys.path.insert(0, "/app")

    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import text
    from app.core.config import settings
    from google import genai

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await db.commit()

        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS doc_chunks (
                id SERIAL PRIMARY KEY,
                source VARCHAR(100) NOT NULL,
                content TEXT NOT NULL,
                embedding vector(3072)
            )
        """))
        await db.commit()

        result = await db.execute(text("SELECT COUNT(*) FROM doc_chunks"))
        count = result.scalar()
        if count > 0:
            print(f"Документація вже завантажена ({count} чанків)")
            await engine.dispose()
            return

        print(f"Завантаження {len(ALL_CHUNKS)} чанків документації...")

        for i, chunk in enumerate(ALL_CHUNKS):
            response = client.models.embed_content(
                model="gemini-embedding-001",
                contents=chunk["content"],
            )
            embedding = response.embeddings[0].values
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            await db.execute(text("""
                INSERT INTO doc_chunks (source, content, embedding)
                VALUES (:source, :content, CAST(:embedding AS vector))
            """), {
                "source": chunk["source"],
                "content": chunk["content"],
                "embedding": embedding_str,
            })

            print(f"  ✓ {i+1}/{len(ALL_CHUNKS)}: {chunk['source']}")

        await db.commit()
        print("Документація успішно завантажена!")

    await engine.dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())