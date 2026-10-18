"""
Завантажує документацію (стандарти стилю та OWASP) у doc_chunks як векторні embeddings.
Таблицю створює міграція Alembic.

Запуск:  python scripts/seed_docs.py            (пропускає, якщо вже завантажено)
         python scripts/seed_docs.py --reset    (перезавантажує з нуля)

language=None означає "для всіх мов".
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHUNKS = [
    # --- PEP 8 ---
    ("PEP 8", "python", "Indentation: Use 4 spaces per indentation level. Spaces are the preferred indentation method. Tabs should be used solely to remain consistent with code that is already indented with tabs."),
    ("PEP 8", "python", "Maximum Line Length: Limit all lines to a maximum of 79 characters. For docstrings or comments, the line length should be limited to 72 characters."),
    ("PEP 8", "python", "Imports: Always put at the top of the file. Group in order: standard library, third party, local application imports. Each group separated by a blank line."),
    ("PEP 8", "python", "Whitespace in Expressions: Avoid extraneous whitespace immediately inside parentheses, brackets or braces. Avoid trailing whitespace anywhere."),
    ("PEP 8", "python", "Naming Conventions: Function names lowercase with underscores. Constants in ALL_CAPS. Class names use CapWords convention."),
    ("PEP 8", "python", "Comments: Should be complete sentences. Inline comments separated by at least two spaces from the statement. Use docstrings for public modules, functions, classes."),
    ("PEP 8", "python", "Programming Recommendations: Comparisons to singletons like None should always be done with is or is not, never the equality operators."),
    ("PEP 8", "python", "Programming Recommendations: Do not use a bare except clause. Catch the most specific exception you can handle, otherwise KeyboardInterrupt and SystemExit are caught and bugs are hidden."),
    ("PEP 343", "python", "Context Managers: Use the with statement for resource management, especially for files and database connections, so resources are released even when an exception occurs."),
    ("PEP 8", "python", "Function length: Keep functions short and focused. Each function should do one thing. If a function is longer than 20-30 lines, consider refactoring."),
    # --- JavaScript / TypeScript ---
    ("Google JavaScript Style Guide", "javascript", "Use const by default and let if a variable is reassigned. Never use var: it has function scope and is hoisted, which causes subtle bugs."),
    ("Google JavaScript Style Guide", "javascript", "Always use strict equality (=== and !==). Loose equality (== and !=) performs implicit type coercion; the only accepted exception is comparing against null."),
    ("Google JavaScript Style Guide", "javascript", "Naming: lowerCamelCase for variables, functions and methods; UpperCamelCase for classes; CONSTANT_CASE for deeply immutable constants."),
    ("Google JavaScript Style Guide", "javascript", "Semicolons are required. Every statement must be terminated with a semicolon; do not rely on automatic semicolon insertion."),
    ("Google JavaScript Style Guide", "javascript", "Do not use eval or the Function constructor with dynamic strings. They execute arbitrary code and enable code injection."),
    ("Google JavaScript Style Guide", "javascript", "Promises: always await or handle rejections with catch. Floating promises hide errors and cause unhandled rejections."),
    ("OWASP XSS Prevention Cheat Sheet", "javascript", "Do not assign untrusted data to innerHTML or document.write. Use textContent, or sanitize HTML with a trusted library such as DOMPurify, to prevent cross-site scripting."),
    ("Google TypeScript Style Guide", "typescript", "Avoid the any type. Prefer unknown or a specific type so the compiler can check usage; any disables type checking."),
    ("Google TypeScript Style Guide", "typescript", "Do not use the non-null assertion operator (!) to silence the compiler without justification; handle null and undefined explicitly."),
    ("Google TypeScript Style Guide", "typescript", "Use const and let, never var. Use === and !==. Prefer interfaces for object shapes and avoid enums with mixed values."),
    # --- Java ---
    ("Google Java Style Guide", "java", "Braces are required with if, else, for, do and while statements, even when the body is empty or contains only a single statement."),
    ("Google Java Style Guide", "java", "Caught exceptions are not ignored. It is very rarely correct to do nothing in response to a caught exception; log it or handle it, and if ignoring is truly appropriate explain why in a comment."),
    ("Google Java Style Guide", "java", "Naming: UpperCamelCase for classes, lowerCamelCase for methods and variables, UPPER_SNAKE_CASE for constants. Package names are all lowercase."),
    ("Effective Java", "java", "Item 9: Prefer try-with-resources to try-finally. It closes resources automatically and does not lose the original exception."),
    ("OWASP SQL Injection Prevention Cheat Sheet", "java", "Use PreparedStatement with bound parameters. Never concatenate user input into SQL strings passed to Statement.executeQuery."),
    ("Google Java Style Guide", "java", "Always use the @Override annotation when it is legal. Do not call printStackTrace; use a logging framework."),
    # --- OWASP Top 10 (для всіх мов) ---
    ("OWASP Top 10", None, "A01:2021 Broken Access Control: Users cannot act outside of their intended permissions. Implement access control mechanisms once and re-use them throughout the application."),
    ("OWASP Top 10", None, "A02:2021 Cryptographic Failures: Do not use MD5 or SHA1 for passwords. Use bcrypt, scrypt, or Argon2. Encrypt sensitive data in transit and at rest."),
    ("OWASP Top 10", None, "A03:2021 Injection: SQL injection occurs when untrusted data is sent to an interpreter. Use parameterized queries. Never use string concatenation to build SQL queries with user input. The same applies to OS commands and eval of user data."),
    ("OWASP Top 10", None, "A04:2021 Insecure Design: Use threat modeling for critical authentication, access control, business logic. Integrate security into user stories."),
    ("OWASP Top 10", None, "A05:2021 Security Misconfiguration: Default accounts and passwords still enabled. Error handling reveals stack traces to users. Unnecessary features enabled."),
    ("OWASP Top 10", None, "A06:2021 Vulnerable and Outdated Components: Continuously inventory versions of all components. Monitor CVE and NVD for vulnerabilities in the components you use."),
    ("OWASP Top 10", None, "A07:2021 Identification and Authentication Failures: Implement multi-factor authentication. Never store passwords in plain text or hard-code credentials. Protect against brute force attacks with rate limiting."),
    ("OWASP Top 10", None, "A08:2021 Software and Data Integrity Failures: Verify integrity of software and data. Do not deserialize untrusted data (for example pickle, Java serialization) and do not rely on plugins from untrusted sources."),
    ("OWASP Top 10", None, "A09:2021 Security Logging and Monitoring Failures: Log all login, access control, and input validation failures with sufficient context to identify suspicious accounts."),
    ("OWASP Top 10", None, "A10:2021 Server-Side Request Forgery: Validate and sanitize all client-supplied URLs. Enforce URL schema, port, and destination with a positive allow list to prevent SSRF attacks."),
]


async def seed(reset: bool = False) -> None:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.agent.tools.rag_search import _client, to_vector_literal
    from app.core.config import settings
    from google.genai import types

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as db:
            if reset:
                await db.execute(text("TRUNCATE doc_chunks RESTART IDENTITY"))
                await db.commit()

            count = (await db.execute(text("SELECT COUNT(*) FROM doc_chunks"))).scalar()
            if count:
                print(f"Документація вже завантажена ({count} фрагментів). Використайте --reset для перезавантаження.")
                return

            print(f"Генерація embeddings для {len(CHUNKS)} фрагментів...")
            response = await _client().aio.models.embed_content(
                model=settings.EMBEDDING_MODEL,
                contents=[content for _, _, content in CHUNKS],
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=settings.EMBEDDING_DIM,
                ),
            )

            for (source, language, content), emb in zip(CHUNKS, response.embeddings):
                await db.execute(
                    text(
                        "INSERT INTO doc_chunks (source, language, content, embedding) "
                        "VALUES (:source, :language, :content, CAST(:embedding AS vector))"
                    ),
                    {
                        "source": source,
                        "language": language,
                        "content": content,
                        "embedding": to_vector_literal(emb.values),
                    },
                )
            await db.commit()
            print("Документацію завантажено.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed(reset="--reset" in sys.argv))
