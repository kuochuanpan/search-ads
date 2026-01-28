"""Import API router."""

from typing import Optional, List
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.db.repository import PaperRepository, ProjectRepository, CitationRepository
from src.web.dependencies import get_paper_repo, get_project_repo, get_ads_client, get_pdf_handler, get_vector_store_dep, get_citation_repo
from src.web.schemas.paper import PaperRead
from src.web.schemas.common import MessageResponse

router = APIRouter()


class ImportFromADSRequest(BaseModel):
    """Request to import a paper from ADS."""
    identifier: str  # bibcode, ADS URL, DOI, or arXiv ID
    project: Optional[str] = None
    expand_references: bool = False
    expand_citations: bool = False
    max_hops: int = 1
    download_pdf: bool = False


class ImportFromADSResponse(BaseModel):
    """Response from importing a paper."""
    success: bool
    bibcode: Optional[str] = None
    title: Optional[str] = None
    message: str
    papers_added: int = 1


class BatchImportRequest(BaseModel):
    """Request to import multiple papers."""
    identifiers: List[str]  # List of bibcodes, DOIs, or arXiv IDs
    project: Optional[str] = None


class BatchImportResponse(BaseModel):
    """Response from batch import."""
    success: bool
    imported: int
    failed: int
    errors: List[str] = []


@router.post("/ads", response_model=ImportFromADSResponse)
async def import_from_ads(
    request: ImportFromADSRequest,
    ads_client=Depends(get_ads_client),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Import a paper from ADS by URL, bibcode, DOI, or arXiv ID."""
    try:
        # Parse identifier to get bibcode
        bibcode = ads_client.parse_bibcode_from_url(request.identifier)
        if not bibcode:
            raise HTTPException(status_code=400, detail=f"Could not parse identifier: {request.identifier}")

        # Fetch paper from ADS
        paper = ads_client.fetch_paper(bibcode)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper not found in ADS: {bibcode}")

        # Add to database
        paper_repo.add(paper)

        # Add to project if specified
        if request.project:
            # Ensure project exists
            project = project_repo.get(request.project)
            if not project:
                project_repo.create(request.project)
            project_repo.add_paper(request.project, paper.bibcode)

        papers_added = 1

        # Expand references if requested
        if request.expand_references:
            refs = ads_client.fetch_references(bibcode, limit=50)
            for ref in refs:
                paper_repo.add(ref)
                if request.project:
                    project_repo.add_paper(request.project, ref.bibcode)
            papers_added += len(refs)

        # Expand citations if requested
        if request.expand_citations:
            cites = ads_client.fetch_citations(bibcode, limit=50)
            for cite in cites:
                paper_repo.add(cite)
                if request.project:
                    project_repo.add_paper(request.project, cite.bibcode)
            papers_added += len(cites)

        return ImportFromADSResponse(
            success=True,
            bibcode=paper.bibcode,
            title=paper.title,
            message=f"Successfully imported {papers_added} paper(s)",
            papers_added=papers_added,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/ads/stream")
async def import_from_ads_stream(
    request: ImportFromADSRequest,
    ads_client=Depends(get_ads_client),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    citation_repo: CitationRepository = Depends(get_citation_repo),
    pdf_handler=Depends(get_pdf_handler),
    vector_store=Depends(get_vector_store_dep),
):
    """Import a paper from ADS with streaming progress (useful for recursive imports)."""

    async def event_generator():
        try:
            yield json.dumps({
                "type": "progress",
                "message": f"Resolving identifier: {request.identifier}..."
            }) + "\n"
            await asyncio.sleep(0.01)

            # Parse identifier to get bibcode
            bibcode = ads_client.parse_bibcode_from_url(request.identifier)
            if not bibcode:
                yield json.dumps({"type": "error", "message": f"Could not parse identifier: {request.identifier}"}) + "\n"
                return

            yield json.dumps({
                "type": "progress",
                "message": f"Fetching metadata for {bibcode}..."
            }) + "\n"

            # Fetch paper from ADS
            paper = ads_client.fetch_paper(bibcode)
            if not paper:
                yield json.dumps({"type": "error", "message": f"Paper not found in ADS: {bibcode}"}) + "\n"
                return

            # Add to database (skip embedding for now, we'll do it at the end or separately)
            # Actually for the main paper we can embed immediately or add to batch
            # Let's add to batch to consistent
            paper_repo.add(paper, embed=False)
            
            papers_to_embed = [paper]

            # Add to project if specified
            if request.project:
                project = project_repo.get(request.project)
                if not project:
                    project_repo.create(request.project)
                project_repo.add_paper(request.project, paper.bibcode)

            papers_added = 1
            yield json.dumps({
                "type": "log",
                "level": "success",
                "message": f"Imported: {paper.title[:50]}..."
            }) + "\n"

            # Download PDF if requested
            if request.download_pdf:
                yield json.dumps({
                    "type": "progress",
                    "message": f"Downloading PDF for {bibcode}..."
                }) + "\n"
                await asyncio.sleep(0.01)

                try:
                    pdf_path = pdf_handler.download(paper)
                    if pdf_path:
                        paper.pdf_path = str(pdf_path)
                        paper_repo.add(paper, embed=False) # Update path without re-embedding yet
                        yield json.dumps({
                            "type": "log",
                            "level": "success",
                            "message": f"PDF downloaded: {pdf_path}"
                        }) + "\n"
                    else:
                        yield json.dumps({
                            "type": "log",
                            "level": "info",
                            "message": "PDF not available for this paper"
                        }) + "\n"
                except Exception as pdf_err:
                    yield json.dumps({
                        "type": "log",
                        "level": "info",
                        "message": f"Could not download PDF: {str(pdf_err)}"
                    }) + "\n"

            # Expand references if requested
            if request.expand_references:
                yield json.dumps({
                    "type": "progress",
                    "message": "Fetching references..."
                }) + "\n"
                
                # We can't easily stream the internal 'fetch_references' of ads_client if it's atomic.
                # But we can report when it's done or if we modify ads_client.
                # For now, we'll just await it but maybe we can improve ads_client later.
                # Assuming fetch_references returns a list.
                refs = ads_client.fetch_references(bibcode, limit=50, save=False)
                
                for i, ref in enumerate(refs):
                    paper_repo.add(ref, embed=False)
                    citation_repo.add(citing_bibcode=bibcode, cited_bibcode=ref.bibcode)
                    papers_to_embed.append(ref)
                    if request.project:
                        project_repo.add_paper(request.project, ref.bibcode)
                    
                    if i % 10 == 0:
                        yield json.dumps({
                            "type": "progress",
                            "message": f"Processing references ({i+1}/{len(refs)})..."
                        }) + "\n"
                        await asyncio.sleep(0)
                        
                papers_added += len(refs)
                if refs:
                    yield json.dumps({
                        "type": "log",
                        "level": "info",
                        "message": f"Added {len(refs)} references"
                    }) + "\n"

            # Expand citations if requested
            if request.expand_citations:
                yield json.dumps({
                    "type": "progress",
                    "message": "Fetching citations..."
                }) + "\n"
                
                cites = ads_client.fetch_citations(bibcode, limit=50, save=False)
                
                for i, cite in enumerate(cites):
                    paper_repo.add(cite, embed=False)
                    citation_repo.add(citing_bibcode=cite.bibcode, cited_bibcode=bibcode)
                    papers_to_embed.append(cite)
                    if request.project:
                        project_repo.add_paper(request.project, cite.bibcode)
                    
                    if i % 10 == 0:
                        yield json.dumps({
                            "type": "progress",
                            "message": f"Processing citations ({i+1}/{len(cites)})..."
                        }) + "\n"
                        await asyncio.sleep(0)

                papers_added += len(cites)
                if cites:
                    yield json.dumps({
                        "type": "log",
                        "level": "info",
                        "message": f"Added {len(cites)} citations"
                    }) + "\n"

            yield json.dumps({
                "type": "result",
                "data": {
                    "success": True,
                    "bibcode": paper.bibcode,
                    "title": paper.title,
                    "message": f"Successfully imported {papers_added} paper(s)",
                    "papers_added": papers_added,
                }
            }) + "\n"

            # Batch embed all collected papers
            if papers_to_embed:
                yield json.dumps({
                    "type": "progress",
                    "message": f"Generating embeddings for {len(papers_to_embed)} papers..."
                }) + "\n"
                await asyncio.sleep(0.01)
                
                # Run embedding in thread pool to avoid blocking asyncio loop too much
                # (though ChromaDB might be partly blocking anyway)
                try:
                    await asyncio.to_thread(vector_store.embed_papers, papers_to_embed)
                    yield json.dumps({
                        "type": "log",
                        "level": "success",
                        "message": f"Embedded {len(papers_to_embed)} papers"
                    }) + "\n"
                except Exception as e:
                     yield json.dumps({
                        "type": "log",
                        "level": "warning",
                        "message": f"Embedding failed: {str(e)}"
                    }) + "\n"

        except Exception as e:
            yield json.dumps({
                "type": "error",
                "message": f"Import failed: {str(e)}"
            }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.post("/batch", response_model=BatchImportResponse)
async def batch_import(
    request: BatchImportRequest,
    ads_client=Depends(get_ads_client),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Import multiple papers by identifiers."""
    imported = 0
    failed = 0
    errors = []

    # Ensure project exists if specified
    if request.project:
        project = project_repo.get(request.project)
        if not project:
            project_repo.create(request.project)

    for identifier in request.identifiers:
        try:
            bibcode = ads_client.parse_bibcode_from_url(identifier)
            if not bibcode:
                failed += 1
                errors.append(f"Could not parse: {identifier}")
                continue

            paper = ads_client.fetch_paper(bibcode)
            if not paper:
                failed += 1
                errors.append(f"Not found: {identifier}")
                continue

            paper_repo.add(paper)

            if request.project:
                project_repo.add_paper(request.project, paper.bibcode)

            imported += 1

        except Exception as e:
            failed += 1
            errors.append(f"Error importing {identifier}: {str(e)}")

    return BatchImportResponse(
        success=failed == 0,
        imported=imported,
        failed=failed,
        errors=errors,
    )


@router.post("/batch/stream")
async def batch_import_stream(
    request: BatchImportRequest,
    ads_client=Depends(get_ads_client),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Import multiple papers by identifiers with streaming progress."""
    
    async def event_generator():
        imported = 0
        failed = 0
        errors = []
        total = len(request.identifiers)

        # Ensure project exists if specified
        if request.project:
            try:
                project = project_repo.get(request.project)
                if not project:
                    project_repo.create(request.project)
            except Exception as e:
                yield json.dumps({
                    "type": "error",
                    "message": f"Failed to access project: {str(e)}"
                }) + "\n"
                return

        for i, identifier in enumerate(request.identifiers):
            try:
                # Notify start of item
                yield json.dumps({
                    "type": "progress",
                    "current": i + 1,
                    "total": total,
                    "message": f"Processing {identifier}...",
                    "imported": imported,
                    "failed": failed
                }) + "\n"

                # Small delay to allow UI to update (and prevent blocking event loop too much)
                await asyncio.sleep(0.01)

                bibcode = ads_client.parse_bibcode_from_url(identifier)
                if not bibcode:
                    failed += 1
                    error_msg = f"Could not parse: {identifier}"
                    errors.append(error_msg)
                    yield json.dumps({
                        "type": "log",
                        "level": "error",
                        "message": error_msg
                    }) + "\n"
                    continue

                paper = ads_client.fetch_paper(bibcode)
                if not paper:
                    failed += 1
                    error_msg = f"Not found: {identifier}"
                    errors.append(error_msg)
                    yield json.dumps({
                        "type": "log",
                        "level": "error",
                        "message": error_msg
                    }) + "\n"
                    continue

                paper_repo.add(paper)

                if request.project:
                    project_repo.add_paper(request.project, paper.bibcode)

                imported += 1
                yield json.dumps({
                    "type": "log",
                    "level": "success",
                    "message": f"Imported: {paper.title[:50]}..."
                }) + "\n"

            except Exception as e:
                failed += 1
                error_msg = f"Error importing {identifier}: {str(e)}"
                errors.append(error_msg)
                yield json.dumps({
                    "type": "log",
                    "level": "error",
                    "message": error_msg
                }) + "\n"

        # Final result
        yield json.dumps({
            "type": "result",
            "data": {
                "success": failed == 0,
                "imported": imported,
                "failed": failed,
                "errors": errors,
            }
        }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.post("/bibtex", response_model=BatchImportResponse)
async def import_bibtex(
    bibtex_content: str = Form(...),
    project: Optional[str] = Form(default=None),
    fetch_from_ads: bool = Form(default=True),
    ads_client=Depends(get_ads_client),
    paper_repo: PaperRepository = Depends(get_paper_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """Import papers from BibTeX content."""
    import re

    # Simple BibTeX parsing to extract bibcodes
    # Look for patterns like: 2024ApJ...123...45P or doi or arxiv
    bibcode_pattern = r'\d{4}[A-Za-z&.]+\.\d+[A-Za-z.]*\d*[A-Za-z]?'
    doi_pattern = r'doi\s*=\s*[{"]?([^}"\s,]+)'
    arxiv_pattern = r'eprint\s*=\s*[{"]?(\d+\.\d+)'

    identifiers = []

    # Try to find bibcodes first
    bibcodes = re.findall(bibcode_pattern, bibtex_content)
    identifiers.extend(bibcodes)

    # Also look for DOIs and arXiv IDs if no bibcodes found
    if not identifiers:
        dois = re.findall(doi_pattern, bibtex_content, re.IGNORECASE)
        identifiers.extend(dois)

        arxiv_ids = re.findall(arxiv_pattern, bibtex_content, re.IGNORECASE)
        identifiers.extend(arxiv_ids)

    if not identifiers:
        return BatchImportResponse(
            success=False,
            imported=0,
            failed=0,
            errors=["No valid identifiers found in BibTeX content"],
        )

    # Ensure project exists if specified
    if project:
        existing_project = project_repo.get(project)
        if not existing_project:
            project_repo.create(project)

    imported = 0
    failed = 0
    errors = []

    for identifier in identifiers:
        try:
            if fetch_from_ads:
                bibcode = ads_client.parse_bibcode_from_url(identifier)
                if bibcode:
                    paper = ads_client.fetch_paper(bibcode)
                    if paper:
                        paper_repo.add(paper)
                        if project:
                            project_repo.add_paper(project, paper.bibcode)
                        imported += 1
                        continue

            failed += 1
            errors.append(f"Could not fetch: {identifier}")

        except Exception as e:
            failed += 1
            errors.append(f"Error: {identifier}: {str(e)}")

    return BatchImportResponse(
        success=failed == 0,
        imported=imported,
        failed=failed,
        errors=errors,
    )
