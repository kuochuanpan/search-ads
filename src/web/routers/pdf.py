"""PDF API router."""

import subprocess
import sys
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from src.db.repository import PaperRepository
from src.web.dependencies import get_paper_repo, get_pdf_handler, get_vector_store_dep
from src.web.schemas.common import MessageResponse

router = APIRouter()


class PDFStatusResponse(BaseModel):
    """PDF status for a paper."""
    bibcode: str
    has_pdf: bool
    pdf_path: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_embedded: bool = False


class PDFStatsResponse(BaseModel):
    """Overall PDF statistics."""
    total_papers: int
    papers_with_pdf: int
    papers_with_embedded_pdf: int
    pdf_chunks_count: int


@router.get("/{bibcode}/status", response_model=PDFStatusResponse)
async def get_pdf_status(
    bibcode: str,
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Get PDF status for a paper."""
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    return PDFStatusResponse(
        bibcode=bibcode,
        has_pdf=paper.pdf_path is not None,
        pdf_path=paper.pdf_path,
        pdf_url=paper.pdf_url,
        pdf_embedded=paper.pdf_embedded,
    )


@router.post("/{bibcode}/download", response_model=MessageResponse)
async def download_pdf(
    bibcode: str,
    background_tasks: BackgroundTasks,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    pdf_handler=Depends(get_pdf_handler),
):
    """Download PDF for a paper."""
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    # Check if already downloaded
    if paper.pdf_path:
        return MessageResponse(message=f"PDF already downloaded: {paper.pdf_path}")

    try:
        # Download PDF synchronously for now
        pdf_path = pdf_handler.download(paper)
        if pdf_path:
            # Update paper with PDF path
            paper.pdf_path = str(pdf_path)
            paper_repo.add(paper)
            return MessageResponse(message=f"PDF downloaded successfully to {pdf_path}")
        else:
            raise HTTPException(status_code=404, detail="PDF not available for this paper")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/{bibcode}/embed", response_model=MessageResponse)
async def embed_pdf(
    bibcode: str,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    pdf_handler=Depends(get_pdf_handler),
    vector_store=Depends(get_vector_store_dep),
):
    """Embed PDF content for semantic search."""
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    if not paper.pdf_path:
        raise HTTPException(status_code=400, detail="PDF not downloaded. Download first.")

    if paper.pdf_embedded:
        return MessageResponse(message="PDF already embedded")

    try:
        # Parse PDF content
        pdf_text = pdf_handler.parse(paper.pdf_path)
        if not pdf_text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        # Embed in vector store
        vector_store.embed_pdf(bibcode, pdf_text, paper.title)

        # Update paper status
        paper.pdf_embedded = True
        paper_repo.add(paper, embed=False)

        return MessageResponse(message="PDF embedded successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@router.delete("/{bibcode}/embed", response_model=MessageResponse)
async def delete_pdf_embedding(
    bibcode: str,
    paper_repo: PaperRepository = Depends(get_paper_repo),
    vector_store=Depends(get_vector_store_dep),
):
    """Remove PDF embedding (un-embed)."""
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    if not paper.pdf_embedded:
        return MessageResponse(message="PDF is not embedded")

    try:
        # Remove embedding from vector store
        vector_store.delete_pdf(bibcode)

        # Update paper status
        paper.pdf_embedded = False
        paper_repo.add(paper, embed=False)

        return MessageResponse(message="PDF embedding removed successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove embedding: {str(e)}")


@router.get("/{bibcode}/open", response_model=MessageResponse)
async def open_pdf(
    bibcode: str,
    paper_repo: PaperRepository = Depends(get_paper_repo),
):
    """Get PDF path for opening in system viewer."""
    paper = paper_repo.get(bibcode)
    if not paper:
        raise HTTPException(status_code=404, detail=f"Paper not found: {bibcode}")

    if not paper.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not downloaded")

    # Try to open in system viewer
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", paper.pdf_path], check=True)
        elif sys.platform == "win32":  # Windows
            subprocess.run(["start", "", paper.pdf_path], shell=True, check=True)
        else:  # Linux
            subprocess.run(["xdg-open", paper.pdf_path], check=True)

        return MessageResponse(message=f"Opening PDF: {paper.pdf_path}")
    except Exception as e:
        # Still return the path even if opening fails
        return MessageResponse(message=f"PDF path: {paper.pdf_path}")


@router.get("/stats", response_model=PDFStatsResponse)
async def get_pdf_stats(
    paper_repo: PaperRepository = Depends(get_paper_repo),
    vector_store=Depends(get_vector_store_dep),
):
    """Get overall PDF statistics."""
    papers = paper_repo.get_all(limit=10000)

    total = len(papers)
    with_pdf = sum(1 for p in papers if p.pdf_path)
    embedded = sum(1 for p in papers if p.pdf_embedded)

    try:
        pdf_chunks = vector_store.pdf_count()
    except Exception:
        pdf_chunks = 0

    return PDFStatsResponse(
        total_papers=total,
        papers_with_pdf=with_pdf,
        papers_with_embedded_pdf=embedded,
        pdf_chunks_count=pdf_chunks,
    )
