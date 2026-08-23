# AI Code Reviewer

REST API для автоматичного аналізу коду за допомогою AI-агента.

## Технології
- **FastAPI** — веб фреймворк
- **PostgreSQL + pgvector** — база даних + векторний пошук
- **Pydantic v2** — валідація даних
- **Celery + Redis** — асинхронна обробка
- **Google Gemini** — AI агент
- **Docker Compose** — оркестрація

## Запуск

```bash
# 1. Скопіюй .env файл
cp .env.example .env
# Заповни GEMINI_API_KEY та SECRET_KEY

# 2. Запусти всі сервіси
docker-compose up --build

# 3. Застосуй міграції
docker-compose exec api alembic upgrade head

# 4. Документація доступна на
http://localhost:8000/docs
```

## API Endpoints

| Метод | URL | Опис |
|-------|-----|-------|
| POST | `/auth/register` | Реєстрація |
| POST | `/auth/login` | Логін (JWT) |
| GET | `/users/me` | Профіль |
| POST | `/projects/` | Створити проект |
| GET | `/projects/` | Список проектів |
| POST | `/reviews/` | Надіслати код на рев'ю |
| GET | `/reviews/{id}` | Результат рев'ю |

## Структура проекту

```
app/
├── api/routes/     # Роутери (auth, projects, reviews)
├── core/           # Конфігурація, безпека (JWT)
├── db/             # SQLAlchemy сесія
├── models/         # ORM моделі
├── schemas/        # Pydantic схеми
├── agent/          # AI агент + tools
│   └── tools/      # linter, github_fetcher, rag_search
└── tasks.py        # Celery задачі
```
