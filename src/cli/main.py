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


@app.command()
def find(
    context: str = typer.Option(..., "--context", "-c", help="Text context for the citation"),
    max_hops: int = typer.Option(2, "--max-hops", help="Maximum hops for graph expansion"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
):
    """Search for papers matching a context."""
    ensure_data_dirs()

    ads_client = ADSClient()

    console.print(f"[blue]Searching for papers matching context...[/blue]")
    console.print(f"[dim]Context: {context[:100]}...[/dim]\n")

    try:
        # For Phase 1, do a simple keyword search
        # Phase 2 will add LLM-based keyword extraction and ranking
        papers = ads_client.search(context, limit=top_k)

        if not papers:
            console.print("[yellow]No papers found[/yellow]")
            return

        console.print(f"[green]Found {len(papers)} papers:[/green]\n")

        for i, paper in enumerate(papers, 1):
            console.print(f"[bold cyan]{i}.[/bold cyan]")
            _display_paper(paper, show_abstract=True)
            console.print()

    except RateLimitExceeded as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)


@app.command()
def fill(
    bibcode: str = typer.Option(..., "--bibcode", "-b", help="Paper bibcode to cite"),
    tex_file: Path = typer.Option(..., "--tex-file", "-t", help="LaTeX file to modify"),
    bib_file: Optional[Path] = typer.Option(None, "--bib-file", help="BibTeX file (auto-detected if not specified)"),
    line: int = typer.Option(..., "--line", "-l", help="Line number of the citation"),
    column: int = typer.Option(..., "--column", "-c", help="Column position of the citation"),
):
    """Fill an empty citation with a paper."""
    ensure_data_dirs()

    if not tex_file.exists():
        console.print(f"[red]File not found: {tex_file}[/red]")
        raise typer.Exit(1)

    ads_client = ADSClient()
    paper_repo = PaperRepository()

    # Get or fetch the paper
    paper = paper_repo.get(bibcode)
    if not paper:
        console.print(f"[blue]Fetching paper from ADS...[/blue]")
        paper = ads_client.fetch_paper(bibcode)
        if not paper:
            console.print(f"[red]Paper not found: {bibcode}[/red]")
            raise typer.Exit(1)

    # Generate citation key
    cite_key = paper.generate_citation_key(
        format=settings.citation_key_format,
        lowercase=settings.citation_key_lowercase,
        max_length=settings.citation_key_max_length,
    )

    # Parse LaTeX file
    parser = LaTeXParser(tex_file)
    bib_info = parser.get_bibliography_info()

    # Determine bib file
    if bib_file is None and bib_info.uses_bib_file:
        bib_file = tex_file.parent / bib_info.bib_file

    console.print(f"[blue]Filling citation with: {cite_key}[/blue]")

    # Fill the citation in the tex file
    try:
        parser.fill_citation(line, column, cite_key)
        console.print(f"[green]Updated {tex_file}[/green]")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Add to bibliography
    if bib_file:
        # Get or generate BibTeX
        bibtex = paper.bibtex
        if not bibtex:
            bibtex = ads_client.generate_bibtex(bibcode)
            if bibtex:
                paper.bibtex = bibtex
                paper_repo.add(paper)

        if bibtex:
            add_bibtex_entry(bib_file, bibtex)
            console.print(f"[green]Added BibTeX entry to {bib_file}[/green]")
        else:
            console.print("[yellow]Warning: Could not generate BibTeX[/yellow]")
    else:
        # Add bibitem to tex file
        bibitem_text = format_bibitem_from_paper(paper)
        parser.add_bibitem(cite_key, bibitem_text)
        console.print(f"[green]Added \\bibitem to {tex_file}[/green]")

    console.print("\n[green]Done![/green]")


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

    table = Table(title="Search-ADS Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Papers in database", str(paper_count))
    table.add_row("Projects", str(len(projects)))
    table.add_row("ADS API calls today", f"{ads_usage} / 5000")
    table.add_row("Database location", str(settings.db_path))

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
