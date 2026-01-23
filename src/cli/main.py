"""Main CLI application for search-ads."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.ads_client import ADSClient, RateLimitExceeded
from src.core.config import settings, ensure_data_dirs
from src.core.latex_parser import (
    LaTeXParser,
    add_bibtex_entry,
    format_bibitem_from_paper,
)
from src.core.llm_client import LLMClient, LLMNotAvailable, RankedPaper, CitationType
from src.db.models import Paper
from src.db.repository import (
    PaperRepository,
    ProjectRepository,
    CitationRepository,
    ApiUsageRepository,
    get_db,
)

# Create Typer app
app = typer.Typer(
    name="search-ads",
    help="CLI tool for automating scientific paper citations using NASA ADS",
    add_completion=False,
)

# Sub-apps
pdf_app = typer.Typer(help="PDF management commands")
project_app = typer.Typer(help="Project management commands")
app.add_typer(pdf_app, name="pdf")
app.add_typer(project_app, name="project")

console = Console()


def _display_paper(paper: Paper, show_abstract: bool = True):
    """Display a paper in a nice format."""
    # Parse authors
    authors = "Unknown"
    if paper.authors:
        try:
            author_list = json.loads(paper.authors)
            if len(author_list) > 3:
                authors = f"{author_list[0]} et al."
            else:
                authors = ", ".join(author_list[:3])
        except json.JSONDecodeError:
            pass

    title = f"[bold]{paper.title}[/bold]"
    subtitle = f"{authors} ({paper.year})"
    citation_info = f"Citations: {paper.citation_count or 0}"

    content = f"{subtitle}\n{citation_info}\nBibcode: {paper.bibcode}"

    if show_abstract and paper.abstract:
        # Truncate abstract
        abstract = paper.abstract[:500] + "..." if len(paper.abstract) > 500 else paper.abstract
        content += f"\n\n[dim]{abstract}[/dim]"

    console.print(Panel(content, title=title, border_style="blue"))


@app.command()
def seed(
    identifier: str = typer.Argument(..., help="ADS URL or bibcode"),
    expand: bool = typer.Option(False, "--expand", "-e", help="Also fetch references and citations"),
    hops: int = typer.Option(1, "--hops", "-h", help="Number of hops for expansion"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Add to project"),
):
    """Seed the database with a paper from ADS."""
    ensure_data_dirs()

    ads_client = ADSClient()

    console.print(f"[blue]Fetching paper: {identifier}[/blue]")

    try:
        paper = ads_client.fetch_paper(identifier)

        if not paper:
            console.print("[red]Paper not found[/red]")
            raise typer.Exit(1)

        _display_paper(paper)

        # Add to project (use default if not specified)
        project_repo = ProjectRepository()
        target_project = project
        if not target_project:
            # Use default project
            default_proj = project_repo.get_or_create_default()
            target_project = default_proj.name
        else:
            # Create specified project if it doesn't exist
            if not project_repo.get(target_project):
                project_repo.create(target_project)

        project_repo.add_paper(target_project, paper.bibcode)
        console.print(f"[green]Added to project: {target_project}[/green]")

        # Expand if requested
        if expand:
            for hop in range(hops):
                console.print(f"\n[blue]Expanding (hop {hop + 1}/{hops})...[/blue]")

                refs = ads_client.fetch_references(paper.bibcode, limit=settings.refs_limit)
                console.print(f"  Fetched {len(refs)} references")

                cites = ads_client.fetch_citations(
                    paper.bibcode,
                    limit=settings.citations_limit,
                    min_citation_count=settings.min_citation_count,
                )
                console.print(f"  Fetched {len(cites)} citations")

        console.print("\n[green]Done![/green]")

    except RateLimitExceeded as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def expand(
    identifier: Optional[str] = typer.Argument(None, help="ADS URL or bibcode to expand"),
    all_papers: bool = typer.Option(False, "--all", help="Expand all papers in database"),
    hops: int = typer.Option(1, "--hops", "-h", help="Number of hops"),
    min_citations: int = typer.Option(0, "--min-citations", help="Minimum citation count filter"),
):
    """Expand the citation graph for a paper or all papers."""
    ensure_data_dirs()

    ads_client = ADSClient()
    paper_repo = PaperRepository()

    if all_papers:
        papers = paper_repo.get_all(limit=1000)
        console.print(f"[blue]Expanding {len(papers)} papers...[/blue]")
    elif identifier:
        bibcode = ADSClient.parse_bibcode_from_url(identifier) or identifier
        paper = paper_repo.get(bibcode)
        if not paper:
            paper = ads_client.fetch_paper(identifier)
        if not paper:
            console.print("[red]Paper not found[/red]")
            raise typer.Exit(1)
        papers = [paper]
    else:
        console.print("[red]Please provide a paper identifier or use --all[/red]")
        raise typer.Exit(1)

    try:
        for paper in papers:
            console.print(f"\n[blue]Expanding: {paper.bibcode}[/blue]")

            refs = ads_client.fetch_references(paper.bibcode, limit=settings.refs_limit)
            console.print(f"  References: {len(refs)}")

            cites = ads_client.fetch_citations(
                paper.bibcode,
                limit=settings.citations_limit,
                min_citation_count=min_citations,
            )
            console.print(f"  Citations: {len(cites)}")

        console.print("\n[green]Done![/green]")

    except RateLimitExceeded as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


def _display_ranked_paper(ranked: RankedPaper, index: int):
    """Display a ranked paper with relevance information."""
    paper = ranked.paper

    # Parse authors
    authors = "Unknown"
    if paper.authors:
        try:
            author_list = json.loads(paper.authors)
            if len(author_list) > 3:
                authors = f"{author_list[0]} et al."
            else:
                authors = ", ".join(author_list[:3])
        except json.JSONDecodeError:
            pass

    title = f"[bold]{paper.title}[/bold]"
    subtitle = f"{authors} ({paper.year})"

    # Relevance info
    score_color = "green" if ranked.relevance_score >= 0.7 else "yellow" if ranked.relevance_score >= 0.4 else "red"
    relevance = f"[{score_color}]Relevance: {ranked.relevance_score:.0%}[/{score_color}]"
    citation_type = f"[magenta]Type: {ranked.citation_type.value}[/magenta]"

    content = f"{subtitle}\n{relevance} | {citation_type}\nCitations: {paper.citation_count or 0} | Bibcode: {paper.bibcode}"

    if ranked.relevance_explanation:
        content += f"\n\n[cyan]Why cite:[/cyan] {ranked.relevance_explanation}"

    if paper.abstract:
        abstract = paper.abstract[:400] + "..." if len(paper.abstract) > 400 else paper.abstract
        content += f"\n\n[dim]{abstract}[/dim]"

    console.print(f"[bold cyan]{index}.[/bold cyan]")
    console.print(Panel(content, title=title, border_style="blue"))
    console.print()


def _search_local_database(keywords: list[str], limit: int = 50) -> list[Paper]:
    """Search the local database using keywords."""
    paper_repo = PaperRepository()
    results = []
    seen_bibcodes = set()

    # Search by each keyword in title and abstract
    for keyword in keywords:
        if len(keyword) < 3:  # Skip very short keywords
            continue
        # Search title and abstract
        matches = paper_repo.search_by_text(keyword, limit=limit)
        for paper in matches:
            if paper.bibcode not in seen_bibcodes:
                results.append(paper)
                seen_bibcodes.add(paper.bibcode)

    # Sort by citation count
    results.sort(key=lambda p: p.citation_count or 0, reverse=True)
    return results[:limit]


@app.command()
def find(
    context: str = typer.Option(..., "--context", "-c", help="Text context for the citation"),
    max_hops: int = typer.Option(2, "--max-hops", help="Maximum hops for graph expansion"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM-based analysis and ranking"),
    local_only: bool = typer.Option(False, "--local", "-l", help="Search local database only (no ADS API calls)"),
    num_refs: int = typer.Option(1, "--num-refs", "-n", help="Number of references needed (for \\cite{,} patterns)"),
):
    """Search for papers matching a context using LLM-powered analysis.

    Use --local to search only the local database (faster, no API calls).
    Use --num-refs to specify how many references are needed (e.g., 2 for \\cite{,}).
    """
    ensure_data_dirs()

    ads_client = ADSClient()
    paper_repo = PaperRepository()

    console.print(f"[blue]Searching for papers matching context...[/blue]")
    console.print(f"[dim]Context: {context[:100]}{'...' if len(context) > 100 else ''}[/dim]")
    if num_refs > 1:
        console.print(f"[cyan]Looking for {num_refs} references[/cyan]")
    console.print()

    try:
        papers = []
        analysis = None

        # Try LLM-powered analysis if available and not disabled
        if not no_llm:
            try:
                llm_client = LLMClient()

                # Step 1: Analyze context
                console.print("[blue]Analyzing context with LLM...[/blue]")
                analysis = llm_client.analyze_context(context)

                console.print(f"[green]Topic:[/green] {analysis.topic}")
                console.print(f"[green]Citation type needed:[/green] {analysis.citation_type.value}")
                console.print(f"[green]Search query:[/green] {analysis.search_query}")
                console.print(f"[dim]Reasoning: {analysis.reasoning}[/dim]\n")

            except LLMNotAvailable as e:
                console.print(f"[yellow]LLM not available: {e}[/yellow]")
                console.print("[yellow]Using basic keyword extraction...[/yellow]\n")

        # Step 2: Search for papers
        search_keywords = analysis.keywords if analysis else context.split()[:5]
        search_query = analysis.search_query if analysis else context

        if local_only:
            # Search local database only
            console.print("[blue]Searching local database...[/blue]")
            db_count = paper_repo.count()
            console.print(f"[dim]Database has {db_count} papers[/dim]")

            papers = _search_local_database(search_keywords, limit=top_k * 3)

            if not papers:
                console.print("[yellow]No papers found in local database[/yellow]")
                console.print("[dim]Try running without --local to search ADS, or seed more papers[/dim]")
                return
        else:
            # Search ADS (papers also get saved to local DB)
            console.print("[blue]Searching ADS...[/blue]")
            papers = ads_client.search(search_query, limit=top_k * 3)

            if not papers and analysis:
                # Fallback to keyword-based search
                console.print("[yellow]No results with extracted query, trying keywords...[/yellow]")
                keyword_query = " OR ".join(search_keywords[:3])
                papers = ads_client.search(keyword_query, limit=top_k * 3)

            if not papers:
                console.print("[yellow]No papers found[/yellow]")
                return

        # Step 3: Rank papers with LLM (if available)
        if not no_llm and analysis:
            try:
                llm_client = LLMClient()
                console.print(f"[blue]Ranking {len(papers)} papers by relevance...[/blue]\n")
                ranked_papers = llm_client.rank_papers(
                    papers, context, context_analysis=analysis, top_k=max(top_k, num_refs * 2)
                )

                # Show results
                display_count = max(top_k, num_refs)
                console.print(f"[green]Top {min(len(ranked_papers), display_count)} relevant papers:[/green]")
                if num_refs > 1:
                    console.print(f"[cyan](Select {num_refs} for your \\cite{{{',' * (num_refs - 1)}}} )[/cyan]\n")
                else:
                    console.print()

                for i, ranked in enumerate(ranked_papers[:display_count], 1):
                    _display_ranked_paper(ranked, i)

                return

            except Exception as e:
                console.print(f"[yellow]LLM ranking failed: {e}[/yellow]")

        # Fallback: display without ranking
        console.print(f"[green]Found {len(papers)} papers:[/green]\n")

        for i, paper in enumerate(papers[:top_k], 1):
            console.print(f"[bold cyan]{i}.[/bold cyan]")
            _display_paper(paper, show_abstract=True)
            console.print()

    except RateLimitExceeded as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def fill(
    bibcode: Optional[str] = typer.Option(None, "--bibcode", "-b", help="Paper bibcode to cite (single)"),
    bibcodes: Optional[str] = typer.Option(None, "--bibcodes", help="Comma-separated bibcodes for multiple refs (e.g., 'bib1,bib2')"),
    tex_file: Path = typer.Option(..., "--tex-file", "-t", help="LaTeX file to modify"),
    bib_file: Optional[Path] = typer.Option(None, "--bib-file", help="BibTeX file (auto-detected if not specified)"),
    line: int = typer.Option(..., "--line", "-l", help="Line number of the citation"),
    column: int = typer.Option(..., "--column", "-c", help="Column position of the citation"),
):
    """Fill an empty citation with one or more papers.

    For single reference: --bibcode "2023ApJ...XXX"
    For multiple refs:    --bibcodes "2023ApJ...XXX,2022MNRAS...YYY"
    """
    ensure_data_dirs()

    if not tex_file.exists():
        console.print(f"[red]File not found: {tex_file}[/red]")
        raise typer.Exit(1)

    # Parse bibcodes
    if bibcodes:
        bibcode_list = [b.strip() for b in bibcodes.split(",") if b.strip()]
    elif bibcode:
        bibcode_list = [bibcode]
    else:
        console.print("[red]Please provide --bibcode or --bibcodes[/red]")
        raise typer.Exit(1)

    ads_client = ADSClient()
    paper_repo = PaperRepository()

    # Parse LaTeX file
    parser = LaTeXParser(tex_file)
    bib_info = parser.get_bibliography_info()

    # Determine bib file
    if bib_file is None and bib_info.uses_bib_file:
        bib_file = tex_file.parent / bib_info.bib_file

    # Process each bibcode
    cite_keys = []
    papers_to_add = []

    for bcode in bibcode_list:
        # Get or fetch the paper
        paper = paper_repo.get(bcode)
        if not paper:
            console.print(f"[blue]Fetching paper from ADS: {bcode}...[/blue]")
            paper = ads_client.fetch_paper(bcode)
            if not paper:
                console.print(f"[red]Paper not found: {bcode}[/red]")
                raise typer.Exit(1)

        # Generate citation key
        cite_key = paper.generate_citation_key(
            format=settings.citation_key_format,
            lowercase=settings.citation_key_lowercase,
            max_length=settings.citation_key_max_length,
        )

        cite_keys.append(cite_key)
        papers_to_add.append((paper, cite_key))
        console.print(f"[green]Prepared: {cite_key}[/green] ({paper.title[:50]}...)")

    # Fill all citation keys at once
    console.print(f"\n[blue]Filling citation with: {', '.join(cite_keys)}[/blue]")

    try:
        # Fill each key one by one (the parser handles appending to existing keys)
        for cite_key in cite_keys:
            parser.fill_citation(line, column, cite_key)
        console.print(f"[green]Updated {tex_file}[/green]")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Add to bibliography
    for paper, cite_key in papers_to_add:
        if bib_file:
            # Get or generate BibTeX
            bibtex = paper.bibtex
            if not bibtex:
                bibtex = ads_client.generate_bibtex(paper.bibcode)
                if bibtex:
                    paper.bibtex = bibtex
                    paper_repo.add(paper)

            if bibtex:
                add_bibtex_entry(bib_file, bibtex)
                console.print(f"[green]Added BibTeX: {cite_key}[/green]")
            else:
                console.print(f"[yellow]Warning: Could not generate BibTeX for {cite_key}[/yellow]")
        else:
            # Add bibitem to tex file
            bibitem_text = format_bibitem_from_paper(paper)
            parser.add_bibitem(cite_key, bibitem_text)
            console.print(f"[green]Added \\bibitem: {cite_key}[/green]")

    console.print(f"\n[green]Done! Added {len(cite_keys)} reference(s)[/green]")


@app.command()
def status():
    """Show database and API usage status."""
    ensure_data_dirs()

    paper_repo = PaperRepository()
    project_repo = ProjectRepository()
    usage_repo = ApiUsageRepository()

    paper_count = paper_repo.count()
    projects = project_repo.get_all()
    ads_usage = usage_repo.get_ads_usage_today()
    openai_usage = usage_repo.get_openai_usage_today()
    anthropic_usage = usage_repo.get_anthropic_usage_today()

    table = Table(title="Search-ADS Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Papers in database", str(paper_count))
    table.add_row("Projects", str(len(projects)))
    table.add_row("ADS API calls today", f"{ads_usage} / 5000")
    table.add_row("OpenAI API calls today", str(openai_usage))
    table.add_row("Anthropic API calls today", str(anthropic_usage))
    table.add_row("Database location", str(settings.db_path))

    # Show LLM availability
    llm_status = []
    if settings.anthropic_api_key:
        llm_status.append("Claude")
    if settings.openai_api_key:
        llm_status.append("OpenAI")
    table.add_row("LLM backends available", ", ".join(llm_status) if llm_status else "[red]None[/red]")

    console.print(table)


@app.command()
def list_papers(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of papers to show"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
):
    """List papers in the database."""
    ensure_data_dirs()

    paper_repo = PaperRepository()
    papers = paper_repo.get_all(limit=limit, project=project)

    if not papers:
        console.print("[yellow]No papers found[/yellow]")
        return

    table = Table(title=f"Papers ({len(papers)})")
    table.add_column("Bibcode", style="cyan", no_wrap=True)
    table.add_column("Year", style="magenta")
    table.add_column("Title", style="white")
    table.add_column("Citations", style="green")

    for paper in papers:
        title = paper.title[:50] + "..." if len(paper.title) > 50 else paper.title
        table.add_row(
            paper.bibcode,
            str(paper.year) if paper.year else "-",
            title,
            str(paper.citation_count) if paper.citation_count else "-",
        )

    console.print(table)


@app.command(name="import")
def import_bib(
    bib_file: Path = typer.Option(..., "--bib-file", "-b", help="BibTeX file to import"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Add imported papers to project"),
):
    """Import papers from a BibTeX file."""
    ensure_data_dirs()

    if not bib_file.exists():
        console.print(f"[red]File not found: {bib_file}[/red]")
        raise typer.Exit(1)

    import re

    ads_client = ADSClient()
    paper_repo = PaperRepository()
    project_repo = ProjectRepository()

    content = bib_file.read_text()

    # Extract bibcodes or DOIs from entries
    # Pattern for @article{key, ...}
    entry_pattern = re.compile(r"@\w+\{([^,]+),", re.MULTILINE)
    entries = entry_pattern.findall(content)

    console.print(f"[blue]Found {len(entries)} entries in {bib_file}[/blue]")

    imported = 0
    for entry_key in entries:
        # Try to find bibcode in the entry
        # Look for adsurl or bibcode field
        entry_start = content.find(entry_key)
        entry_end = content.find("}", entry_start)
        if entry_end == -1:
            entry_end = len(content)

        entry_text = content[entry_start:entry_end]

        # Try to extract bibcode
        bibcode_match = re.search(r"bibcode\s*=\s*[{\"]([^}\"]+)", entry_text, re.IGNORECASE)
        if bibcode_match:
            bibcode = bibcode_match.group(1)
        else:
            # Try adsurl
            adsurl_match = re.search(r"adsurl\s*=\s*[{\"]([^}\"]+)", entry_text, re.IGNORECASE)
            if adsurl_match:
                bibcode = ADSClient.parse_bibcode_from_url(adsurl_match.group(1))
            else:
                console.print(f"  [yellow]Skipping {entry_key}: no bibcode found[/yellow]")
                continue

        if bibcode:
            try:
                paper = ads_client.fetch_paper(bibcode)
                if paper:
                    imported += 1
                    if project:
                        if not project_repo.get(project):
                            project_repo.create(project)
                        project_repo.add_paper(project, paper.bibcode)
                    console.print(f"  [green]Imported: {bibcode}[/green]")
            except RateLimitExceeded:
                console.print("[red]Rate limit reached, stopping import[/red]")
                break

    console.print(f"\n[green]Imported {imported} papers[/green]")


# Database management commands
db_app = typer.Typer(help="Database management commands")
app.add_typer(db_app, name="db")


@db_app.command("clear")
def db_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Clear all papers from the database."""
    ensure_data_dirs()

    paper_repo = PaperRepository()
    count = paper_repo.count()

    if count == 0:
        console.print("[yellow]Database is already empty[/yellow]")
        return

    if not force:
        confirm = typer.confirm(f"Delete all {count} papers from the database?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    deleted = paper_repo.delete_all()
    console.print(f"[green]Deleted {deleted} papers from the database[/green]")


# PDF commands
@pdf_app.command("download")
def pdf_download(bibcode: str = typer.Argument(..., help="Paper bibcode")):
    """Download PDF for a paper."""
    console.print("[yellow]PDF download not yet implemented (Phase 3)[/yellow]")


@pdf_app.command("embed")
def pdf_embed(bibcode: str = typer.Argument(..., help="Paper bibcode")):
    """Embed PDF content for full-text search."""
    console.print("[yellow]PDF embedding not yet implemented (Phase 3)[/yellow]")


# Project commands
@project_app.command("init")
def project_init(name: str = typer.Argument(..., help="Project name")):
    """Initialize a new project."""
    ensure_data_dirs()

    project_repo = ProjectRepository()

    if project_repo.get(name):
        console.print(f"[yellow]Project '{name}' already exists[/yellow]")
        return

    project_repo.create(name)
    console.print(f"[green]Created project: {name}[/green]")


@project_app.command("delete")
def project_delete(
    name: str = typer.Argument(..., help="Project name to delete"),
    delete_papers: bool = typer.Option(False, "--delete-papers", "-d", help="Also delete papers only in this project"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a project and optionally its papers."""
    ensure_data_dirs()

    project_repo = ProjectRepository()

    project = project_repo.get(name)
    if not project:
        console.print(f"[red]Project '{name}' not found[/red]")
        raise typer.Exit(1)

    # Get paper count
    paper_bibcodes = project_repo.get_project_papers(name)
    paper_count = len(paper_bibcodes)

    # Confirmation message
    if delete_papers:
        msg = f"Delete project '{name}' and its {paper_count} papers (papers in other projects will be kept)?"
    else:
        msg = f"Delete project '{name}'? ({paper_count} papers will be unassigned but kept in database)"

    if not force:
        confirm = typer.confirm(msg)
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    success, papers_deleted = project_repo.delete(name, delete_papers=delete_papers)

    if success:
        console.print(f"[green]Deleted project: {name}[/green]")
        if delete_papers:
            console.print(f"[green]Deleted {papers_deleted} papers (papers in other projects were kept)[/green]")
    else:
        console.print(f"[red]Failed to delete project '{name}'[/red]")
        raise typer.Exit(1)


@project_app.command("add-paper")
def project_add_paper(
    bibcode: str = typer.Argument(..., help="Paper bibcode to add"),
    project: str = typer.Option(..., "--project", "-p", help="Project name"),
):
    """Add an existing paper to a project."""
    ensure_data_dirs()

    paper_repo = PaperRepository()
    project_repo = ProjectRepository()

    # Check if paper exists
    paper = paper_repo.get(bibcode)
    if not paper:
        console.print(f"[red]Paper not found in database: {bibcode}[/red]")
        console.print("[dim]Use 'search-ads seed' to add the paper first[/dim]")
        raise typer.Exit(1)

    # Create project if it doesn't exist
    if not project_repo.get(project):
        project_repo.create(project)
        console.print(f"[blue]Created project: {project}[/blue]")

    # Check if already in project
    if project_repo.paper_in_project(bibcode, project):
        console.print(f"[yellow]Paper already in project '{project}'[/yellow]")
        return

    # Add paper to project
    project_repo.add_paper(project, bibcode)
    console.print(f"[green]Added '{paper.title[:50]}...' to project '{project}'[/green]")


@project_app.command("list")
def project_list(name: Optional[str] = typer.Argument(None, help="Project name to show papers for")):
    """List all projects or papers in a project."""
    ensure_data_dirs()

    project_repo = ProjectRepository()
    paper_repo = PaperRepository()

    if name:
        # Show papers in project
        papers = paper_repo.get_all(limit=100, project=name)
        if not papers:
            console.print(f"[yellow]No papers in project '{name}'[/yellow]")
            return

        console.print(f"[bold]Papers in project '{name}':[/bold]\n")
        for paper in papers:
            console.print(f"  - {paper.bibcode}: {paper.title[:60]}...")
    else:
        # List all projects
        projects = project_repo.get_all()
        if not projects:
            console.print("[yellow]No projects found[/yellow]")
            return

        table = Table(title="Projects")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")

        for proj in projects:
            table.add_row(proj.name, proj.description or "-")

        console.print(table)


if __name__ == "__main__":
    app()
