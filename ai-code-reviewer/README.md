# AI Code Reviewer

REST API для автоматичного рев'ю коду за допомогою AI-агента.
Підтримувані мови: **Python, JavaScript, TypeScript, Java** (повний аналіз зі статичним лінтером).
Інші мови приймаються в режимі `other`: лише AI-аналіз, без лінтера.

## Технології
- **FastAPI**, **Pydantic v2**, **SQLAlchemy (async)**, **Alembic**
- **PostgreSQL + pgvector** — дані та векторний пошук (RAG)
- **Celery + Redis** — асинхронна обробка рев'ю
- **Google Gemini** — генерація звіту та embeddings
- **Semgrep + pyflakes** — статичний аналіз (код лише аналізується, ніколи не виконується)
- **Docker Compose** — оркестрація

## Запуск

```bash
cp .env.example .env        # заповни GEMINI_API_KEY та SECRET_KEY
docker compose up --build   # міграції та наповнення RAG виконуються автоматично
```

Документація API: http://localhost:8000/docs

Перезавантажити документацію для RAG: `docker compose exec api python scripts/seed_docs.py --reset`

## Тести

```bash
pytest          # AI та GitHub підміняються заглушками, Postgres не потрібен
```

Тести правил Semgrep виконуються лише там, де встановлено `semgrep` (в Docker-образі).

## Як працює рев'ю

1. `POST /reviews/` зберігає рев'ю зі статусом `pending` і одразу повертає його id.
2. Celery-воркер запускає агента: завантаження з GitHub (лише allowlist доменів) → статичний аналіз → RAG-пошук по PEP 8/OWASP/стилю мови → Gemini повертає структурований JSON.
3. Результат валідується й зберігається; статус `done` або `failed` (з повідомленням про причину).
4. Клієнт опитує `GET /reviews/{id}`.

Мова рев'ю: явно вказана > визначена за розширенням файлу з GitHub > мова проєкту.

## API

| Метод | URL | Опис |
|-------|-----|------|
| POST | `/auth/register` | Реєстрація (пароль від 8 символів) |
| POST | `/auth/login` | Логін, повертає JWT |
| GET | `/users/me` | Профіль |
| POST / GET | `/projects/` | Створити проєкт / список |
| GET / PATCH / DELETE | `/projects/{id}` | Перегляд / зміна / видалення |
| GET | `/projects/{id}/reviews` | Історія рев'ю проєкту |
| GET | `/projects/{id}/stats` | Середня оцінка, категорії проблем, динаміка оцінки |
| POST | `/reviews/` | Надіслати код або GitHub-посилання (202) |
| GET | `/reviews/{id}` | Статус, оцінка, коментарі |
| POST | `/reviews/{id}/ask` | Питання до AI по рев'ю або по коментарю (`comment_id`) |

## Структура

```
app/
├── api/routes/     # Роутери
├── core/           # Конфігурація, безпека (JWT), підтримувані мови
├── models/         # ORM-моделі
├── schemas/        # Pydantic-схеми
├── services/       # Бізнес-логіка
├── agent/          # AI-агент
│   ├── tools/      # linter, github_fetcher, rag_search
│   └── rules/      # Правила Semgrep (python, javascript, java)
└── tasks.py        # Celery-задачі
alembic/versions/   # Міграції
scripts/seed_docs.py # Наповнення RAG
mockups/            # HTML-макет інтерфейсу
```
