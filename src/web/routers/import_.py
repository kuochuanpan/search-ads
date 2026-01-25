"""Import API router."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from src.db.repository import PaperRepository, ProjectRepository
from src.web.dependencies import get_paper_repo, get_project_repo, get_ads_client
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
