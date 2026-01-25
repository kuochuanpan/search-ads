"""FastAPI application for Search-ADS Web UI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.web.routers import papers, projects, citations, notes, search, import_, pdf, settings

app = FastAPI(
    title="Search-ADS API",
    description="API for scientific paper citation management",
    version="0.1.0",
)

# CORS middleware for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
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
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Search-ADS API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
