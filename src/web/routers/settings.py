"""Settings API router."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.core.config import settings
from src.db.repository import PaperRepository, ProjectRepository, NoteRepository, ApiUsageRepository
from src.web.dependencies import (
    get_paper_repo,
    get_project_repo,
    get_note_repo,
    get_api_usage_repo,
    get_vector_store_dep,
)
from src.web.schemas.common import StatsResponse, ApiUsageResponse, MessageResponse

router = APIRouter()


class SettingsResponse(BaseModel):
    """Current application settings."""
    # Data directories
    data_dir: str
    db_path: str
    pdfs_path: str

    # Search parameters
    max_hops: int
    top_k: int
    min_citation_count: int

    # Web server
    web_host: str
    web_port: int

    # Citation key format
    citation_key_format: str

    # API key status (not the actual keys)
    has_ads_key: bool
    has_openai_key: bool
    has_anthropic_key: bool
    
    # Selected models
    openai_model: str
    anthropic_model: str

    # Author names for "my papers" detection
    my_author_names: str


class AuthorNamesRequest(BaseModel):
    """Request to update author names."""
    author_names: str

class ModelsRequest(BaseModel):
    """Request to update LLM models."""
    openai_model: str
    anthropic_model: str


class ApiKeysRequest(BaseModel):
    """Request to update API keys."""
    ads_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """Get current application settings."""
    return SettingsResponse(
        data_dir=str(settings.data_dir),
        db_path=str(settings.db_path),
        pdfs_path=str(settings.pdfs_path),
        max_hops=settings.max_hops,
        top_k=settings.top_k,
        min_citation_count=settings.min_citation_count,
        web_host=settings.web_host,
        web_port=settings.web_port,
        citation_key_format=settings.citation_key_format,
        has_ads_key=bool(settings.ads_api_key),
        has_openai_key=bool(settings.openai_api_key),
        has_anthropic_key=bool(settings.anthropic_api_key),
        openai_model=settings.openai_model,
        anthropic_model=settings.anthropic_model,
        my_author_names=settings.my_author_names,
    )


@router.get("/author-names")
async def get_author_names():
    """Get configured author names for 'my papers' detection."""
    return {
        "author_names": settings.my_author_names,
        "parsed_names": settings.get_my_author_names(),
    }


@router.put("/author-names", response_model=MessageResponse)
async def update_author_names(request: AuthorNamesRequest):
    """Update author names for 'my papers' detection.

    Names should be semicolon-separated, e.g., "Pan, K.-C.; Pan, Kuo-Chuan; Pan, K."
    """
    try:
        settings.save_my_author_names(request.author_names)
        return MessageResponse(
            message=f"Author names updated successfully",
            success=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save author names: {str(e)}")


@router.put("/models", response_model=MessageResponse)
async def update_models(request: ModelsRequest):
    """Update LLM model selection."""
    try:
        settings.save_models(request.openai_model, request.anthropic_model)
        return MessageResponse(
            message=f"Model settings updated successfully",
            success=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save model settings: {str(e)}")


@router.put("/api-keys", response_model=MessageResponse)
async def update_api_keys(request: ApiKeysRequest):
    """Update API keys."""
    try:
        settings.save_api_keys(
            request.ads_api_key,
            request.openai_api_key,
            request.anthropic_api_key
        )
        return MessageResponse(
            message=f"API keys updated successfully",
            success=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save API keys: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    paper_repo: PaperRepository = Depends(get_paper_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    note_repo: NoteRepository = Depends(get_note_repo),
):
    """Get database statistics."""
    papers = paper_repo.get_all(limit=10000)

    return StatsResponse(
        total_papers=len(papers),
        total_projects=len(project_repo.get_all()),
        total_notes=note_repo.count(),
        papers_with_pdf=sum(1 for p in papers if p.pdf_path),
        papers_with_embedded_pdf=sum(1 for p in papers if p.pdf_embedded),
        my_papers_count=sum(1 for p in papers if p.is_my_paper),
        min_year=min((p.year for p in papers if p.year), default=None),
        max_year=max((p.year for p in papers if p.year), default=None),
    )


@router.get("/api-usage", response_model=ApiUsageResponse)
async def get_api_usage(
    api_usage_repo: ApiUsageRepository = Depends(get_api_usage_repo),
):
    """Get today's API usage statistics."""
    return ApiUsageResponse(
        date=date.today().isoformat(),
        ads_calls=api_usage_repo.get_ads_usage_today(),
        openai_calls=api_usage_repo.get_openai_usage_today(),
        anthropic_calls=api_usage_repo.get_anthropic_usage_today(),
    )


@router.get("/vector-stats")
async def get_vector_stats(
    vector_store=Depends(get_vector_store_dep),
):
    """Get vector store statistics."""
    try:
        return {
            "abstracts_count": vector_store.count(),
            "pdf_chunks_count": vector_store.pdf_count(),
            "pdf_papers_count": vector_store.pdf_paper_count(),
            "notes_count": vector_store.notes_count(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get vector stats: {str(e)}")


@router.post("/test-api-key/{service}")
async def test_api_key(
    service: str,
):
    """Test if an API key is valid."""
    if service == "ads":
        if not settings.ads_api_key:
            return {"valid": False, "message": "ADS API key not configured"}

        try:
            from src.core.ads_client import ADSClient
            client = ADSClient()
            # Try a simple search
            papers = client.search("test", limit=1)
            return {"valid": True, "message": "ADS API key is valid"}
        except Exception as e:
            return {"valid": False, "message": f"ADS API key test failed: {str(e)}"}

    elif service == "openai":
        if not settings.openai_api_key:
            return {"valid": False, "message": "OpenAI API key not configured"}

        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)
            # Try to list models
            client.models.list()
            return {"valid": True, "message": "OpenAI API key is valid"}
        except Exception as e:
            return {"valid": False, "message": f"OpenAI API key test failed: {str(e)}"}

    elif service == "anthropic":
        if not settings.anthropic_api_key:
            return {"valid": False, "message": "Anthropic API key not configured"}

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            # Try a simple message
            client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return {"valid": True, "message": "Anthropic API key is valid"}
        except Exception as e:
            return {"valid": False, "message": f"Anthropic API key test failed: {str(e)}"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")


@router.post("/clear-data", response_model=MessageResponse)
async def clear_data(
    paper_repo: PaperRepository = Depends(get_paper_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Clear all data (papers, projects, embeddings, PDFs, notes)."""
    try:
        # 1. Clear Papers (includes PDFs for papers, notes, embeddings, associations)
        papers_deleted = paper_repo.delete_all()
        
        # 2. Clear Projects
        projects_deleted = project_repo.delete_all()

        # 3. Clean up any remaining PDFs just in case (orphaned files)
        if settings.pdfs_path.exists():
             import shutil
             # Don't remove the dir itself, just contents
             for item in settings.pdfs_path.iterdir():
                 if item.is_file():
                     item.unlink()
                 elif item.is_dir():
                     shutil.rmtree(item)

        return MessageResponse(
            message=f"Cleared {papers_deleted} papers and {projects_deleted} projects",
            success=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")
