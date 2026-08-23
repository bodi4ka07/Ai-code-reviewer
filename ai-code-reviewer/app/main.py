from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, projects, reviews, users
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключаємо роутери
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])


@app.get("/", tags=["Health"])
async def root():
    return {"message": "AI Code Reviewer API", "status": "running", "docs": "/docs"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
