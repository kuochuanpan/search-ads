"""FastAPI application for Search-ADS Web UI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from src.core.config import settings
from src.web.routers import papers, projects, citations, notes, search, import_, pdf, settings as settings_router, ai, latex, assistant

app = FastAPI(
    title="Search-ADS API",
    description="API for scientific paper citation management",
    version=settings.version,
)

# CORS middleware for React dev server and Tauri desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Development servers
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Tauri desktop app origins
        "http://tauri.localhost",   # macOS/Linux
        "https://tauri.localhost",  # Windows
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(citations.router, prefix="/api/citations", tags=["Citations"])
app.include_router(notes.router, prefix="/api/notes", tags=["Notes"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(import_.router, prefix="/api/import", tags=["Import"])
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(latex.router, prefix="/api/latex", tags=["LaTeX"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["Assistant"])


@app.on_event("startup")
async def startup_event():
    pass

@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Search-ADS API",
        "version": settings.version,
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
