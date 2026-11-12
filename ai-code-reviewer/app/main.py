from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, chats, projects, reviews, users
from app.core.config import settings

app = FastAPI(
    title="AI Code Reviewer",
    description="API для автоматичного аналізу коду за допомогою AI-агента",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Підключаємо роутери
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
app.include_router(chats.router, prefix="/chats", tags=["Chats"])


@app.get("/", tags=["Health"])
async def root():
    return {"message": "AI Code Reviewer API", "status": "running", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
