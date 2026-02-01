"""Settings API router."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.core.config import settings
from src.core.llm_client import normalize_gemini_model_name
from src.db.repository import PaperRepository, ProjectRepository, NoteRepository, ApiUsageRepository
from src.web.dependencies import (
    get_paper_repo,
    get_project_repo,
    get_note_repo,
    get_api_usage_repo,
    get_vector_store_dep,
)
from src.web.schemas.common import StatsResponse, ApiUsageResponse, MessageResponse as BaseMessageResponse

router = APIRouter()

class MessageResponse(BaseMessageResponse):
    """Extend message response."""
    pass

class SettingsResponse(BaseModel):
    """Current application settings."""
    version: str
    # Data directories
    data_dir: str
    db_path: str
    pdfs_path: str
    
    # Providers
    llm_provider: str
    embedding_provider: str

    # Search parameters
    max_hops: int
    top_k: int
    min_citation_count: int

    # Web server
    web_host: str
    web_port: int

    # Citation key format
    citation_key_format: str

    # API key status
    has_ads_key: bool
    has_openai_key: bool
    has_anthropic_key: bool
    has_gemini_key: bool
    
    # Models
    openai_model: str
    anthropic_model: str
    gemini_model: str
    ollama_model: str
    ollama_embedding_model: str
    
    # Ollama
    ollama_base_url: str

    # Author names
    my_author_names: str


class AuthorNamesRequest(BaseModel):
    """Request to update author names."""
    author_names: str

class ModelsRequest(BaseModel):
    """Request to update LLM providers and models."""
    llm_provider: str
    embedding_provider: str
    openai_model: str
    anthropic_model: str
    gemini_model: str
    ollama_model: str
    ollama_embedding_model: str
    ollama_base_url: str


class ApiKeysRequest(BaseModel):
    """Request to update API keys."""
    ads_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None


def reindex_database(vector_store, paper_repo, notes_repo):
    """Background task to re-index the vector database."""
    print("Starting background re-indexing...")
    try:
        # 1. Clear existing data
        vector_store.clear()
        vector_store.clear_pdfs()
        vector_store.clear_notes()

        # 2. Reset cached embedding function so it picks up the new provider
        vector_store.reset_embedding_function()

        # 3. Embed all abstracts (batching is handled inside embed_papers)
        papers = paper_repo.get_all(limit=10000) # Safety limit, or iterate?
        print(f"Re-indexing {len(papers)} papers...")
        count = vector_store.embed_papers(papers, batch_size=50)
        print(f"Embeddings generated: {count}")
        
        # 3. Embed all PDFs (this is slow, do strictly necessary ones?)
        # For now, we only embed PDFs that were previously embedded (has pdf_embedded=True)
        papers_with_pdf = [p for p in papers if p.pdf_embedded and p.pdf_path]
        print(f"Re-indexing {len(papers_with_pdf)} PDFs...")
        
        pdf_count = 0
        import fitz # PyMuPDF
        from pathlib import Path
        
        for paper in papers_with_pdf:
            try:
                path = Path(paper.pdf_path)
                if path.exists():
                     with fitz.open(path) as doc:
                        text = ""
                        for page in doc:
                            text += page.get_text()
                        
                        if text:
                            vector_store.embed_pdf(
                                bibcode=paper.bibcode,
                                pdf_text=text,
                                title=paper.title
                            )
                            pdf_count += 1
            except Exception as e:
                print(f"Failed to re-embed PDF for {paper.bibcode}: {e}")
        
        print(f"PDFs re-indexed: {pdf_count}")
        
        # 4. Embed all notes
        notes = notes_repo.get_all()
        print(f"Re-indexing {len(notes)} notes...")
        for note in notes:
            vector_store.embed_note(note)
            
        print("Re-indexing complete.")
        
    except Exception as e:
        print(f"Re-indexing failed: {e}")


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """Get current application settings."""
    return SettingsResponse(
        version=settings.version,
        data_dir=str(settings.data_dir),
        db_path=str(settings.db_path),
        pdfs_path=str(settings.pdfs_path),
        llm_provider=settings.llm_provider,
        embedding_provider=settings.embedding_provider,
        max_hops=settings.max_hops,
        top_k=settings.top_k,
        min_citation_count=settings.min_citation_count,
        web_host=settings.web_host,
        web_port=settings.web_port,
        citation_key_format=settings.citation_key_format,
        has_ads_key=bool(settings.ads_api_key),
        has_openai_key=bool(settings.openai_api_key),
        has_anthropic_key=bool(settings.anthropic_api_key),
        has_gemini_key=bool(settings.gemini_api_key),
        openai_model=settings.openai_model,
        anthropic_model=settings.anthropic_model,
        gemini_model=settings.gemini_model,
        ollama_model=settings.ollama_model,
        ollama_embedding_model=settings.ollama_embedding_model,
        ollama_base_url=settings.ollama_base_url,
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
    """Update author names."""
    try:
        settings.save_my_author_names(request.author_names)
        return MessageResponse(
            message=f"Author names updated successfully",
            success=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save author names: {str(e)}")


@router.put("/models", response_model=MessageResponse)
async def update_models(
    request: ModelsRequest, 
    background_tasks: BackgroundTasks,
    vector_store=Depends(get_vector_store_dep),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    note_repo: NoteRepository = Depends(get_note_repo),
):
    """Update user configuration (Providers & Models).
    
    Triggers re-indexing if embedding provider changes.
    """
    try:
        # Check if embedding provider changed
        embedding_changed = (
            request.embedding_provider != settings.embedding_provider or
            (request.embedding_provider == "ollama" and request.ollama_embedding_model != settings.ollama_embedding_model)
        )
        
        settings.save_models(
            llm_provider=request.llm_provider,
            embedding_provider=request.embedding_provider,
            openai_model=request.openai_model,
            anthropic_model=request.anthropic_model,
            gemini_model=request.gemini_model,
            ollama_model=request.ollama_model,
            ollama_embedding_model=request.ollama_embedding_model,
            ollama_base_url=request.ollama_base_url
        )
        
        msg = "Settings updated successfully"
        if embedding_changed:
            msg += ". Re-indexing started in background."
            # Trigger background task
            # Use a wrapper to pass dependencies without needing active session (repos handle their own sessions)
            # Actually repos passed here depend on active session?
            # get_paper_repo -> dependencies.py -> get_db -> session yield.
            # Passing yielding dependencies to background task is bad. 
            # We should instantiate fresh repos inside the task or pass the DB factory.
            
            # Repos in dependencies.py use 'db' which is Request scope session OR a global get_db().
            # Let's import fresh repos in the helper or rely on them creating their own sessions if invoked without db arg.
            # PaperRepository.__init__(db: Optional[Database] = None). If None, it calls get_db().
            
            # However, get_db() -> Database instance.
            # The repos create a session using `with self.db.get_session()`.
            # So passing new instances of repositories is safe.
            
            new_paper_repo = PaperRepository() # Uses default global DB
            new_note_repo = NoteRepository()
            
            background_tasks.add_task(reindex_database, vector_store, new_paper_repo, new_note_repo)
            
        return MessageResponse(
            message=msg,
            success=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")


@router.put("/api-keys", response_model=MessageResponse)
async def update_api_keys(request: ApiKeysRequest):
    """Update API keys."""
    try:
        settings.save_api_keys(
            request.ads_api_key,
            request.openai_api_key,
            request.anthropic_api_key,
            request.gemini_api_key
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
        gemini_calls=api_usage_repo.get_gemini_usage_today(),
        ollama_calls=api_usage_repo.get_ollama_usage_today(),
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
            client.search("test", limit=1)
            return {"valid": True, "message": "ADS API key is valid"}
        except Exception as e:
            return {"valid": False, "message": f"ADS API key test failed: {str(e)}"}

    elif service == "openai":
        if not settings.openai_api_key:
            return {"valid": False, "message": "OpenAI API key not configured"}
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)
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
            client.messages.create(
                model=settings.anthropic_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return {"valid": True, "message": "Anthropic API key is valid"}
        except Exception as e:
            return {"valid": False, "message": f"Anthropic API key test failed: {str(e)}"}
            
    elif service == "gemini":
        if not settings.gemini_api_key:
             return {"valid": False, "message": "Gemini API key not configured"}
        try:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            client.models.generate_content(
                model=normalize_gemini_model_name(settings.gemini_model),
                contents="Hi",
            )
            return {"valid": True, "message": "Gemini API key is valid"}
        except Exception as e:
            return {"valid": False, "message": f"Gemini API key test failed: {str(e)}"}
            
    elif service == "ollama":
        try:
            import requests
            resp = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                 return {"valid": True, "message": "Ollama connection successful"}
            else:
                 return {"valid": False, "message": f"Ollama returned {resp.status_code}"}
        except Exception as e:
            return {"valid": False, "message": f"Ollama connection failed: {str(e)}"}

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


@router.get("/models/{provider}")
async def get_models(
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None
):
    """Get available models for a provider via settings or provided credentials."""
    models = []
    
    # Use provided key or fallback to settings
    key_to_use = api_key
    
    if provider == "openai":
        if not key_to_use:
            key_to_use = settings.openai_api_key
            
        if not key_to_use:
            raise HTTPException(status_code=400, detail="OpenAI API key not configured")
            
        try:
            import openai
            client = openai.OpenAI(api_key=key_to_use)
            response = client.models.list()
            # Filter for GPT and newer o1/o3 models
            # Exclude likely non-chat models if possible, but keeping it broad is safer for "missing" models complaint
            models = sorted([
                m.id for m in response.data 
                if ("gpt" in m.id or "o1-" in m.id or "o3-" in m.id) 
                and "audio" not in m.id 
                and "tts" not in m.id 
                and "realtime" not in m.id
            ])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch OpenAI models: {str(e)}")

    elif provider == "anthropic":
        if not key_to_use:
             key_to_use = settings.anthropic_api_key
             
        if not key_to_use:
             raise HTTPException(status_code=400, detail="Anthropic API key not configured")
             
        # Anthropic doesn't have a public models list endpoint easily accessible in all versions yet, 
        # but we can try to return common ones or see if library supports it.
        # As of recent versions, it's not a standard list call like OpenAI.
        # We will return a curated list of known valid models.
        models = [
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-haiku-20241022",
        ]

    elif provider == "gemini":
        if not key_to_use:
            key_to_use = settings.gemini_api_key
            
        if not key_to_use:
            raise HTTPException(status_code=400, detail="Gemini API key not configured")
            
        try:
            from google import genai
            client = genai.Client(api_key=key_to_use)
            response = client.models.list()
            models = []
            for m in response:
                name_lower = m.name.lower()
                # Include gemini, gemma, learnlm, and potential future names
                # Removing the supported_generation_methods check as it might be missing or 'unknown' for preview models
                if any(x in name_lower for x in ["gemini", "gemma", "learnlm", "paalm", "text-bison", "chat-bison"]):
                     # Remove 'models/' prefix
                     model_id = m.name.replace("models/", "")
                     models.append(model_id)
            models = sorted(models)
        except Exception as e:
             print(f"Gemini fetch error: {e}")
             raise HTTPException(status_code=500, detail=f"Failed to fetch Gemini models: {str(e)}")

    elif provider == "ollama":
        url_to_use = base_url if base_url else settings.ollama_base_url
        if not url_to_use:
             url_to_use = "http://localhost:11434"
             
        try:
            import requests
            # Remove trailing slash
            url_to_use = url_to_use.rstrip("/")
            resp = requests.get(f"{url_to_use}/api/tags", timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                # Debug print
                print(f"Ollama response: {data}")
                # Some versions might return just a list of strings? No, officially it's a list of objects.
                # But let's be safe.
                raw_models = data.get("models", [])
                models = []
                for m in raw_models:
                    if isinstance(m, dict):
                        models.append(m.get("name"))
                    elif isinstance(m, str):
                        models.append(m)
                models = sorted(models)
            else:
                 raise HTTPException(status_code=500, detail=f"Ollama returned {resp.status_code}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch Ollama models: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    return {"models": models}
