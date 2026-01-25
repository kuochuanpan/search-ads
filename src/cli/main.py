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
    NoteRepository,
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

# Template for .env file
ENV_TEMPLATE = """# Search-ADS Configuration
# Get your ADS API key from: https://ui.adsabs.harvard.edu/user/settings/token
ADS_API_KEY=

# OpenAI API key for embeddings and LLM features (optional)
# Get your key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Anthropic API key for Claude LLM features (optional)
# Get your key from: https://console.anthropic.com/
#ANTHROPIC_API_KEY=

# Author name(s) for auto-detecting "my papers" (semicolon-separated, optional)
# Example: MY_AUTHOR_NAMES="Pan, K.-C.; Pan, Kuo-Chuan; Pan, K."
#MY_AUTHOR_NAMES=
"""


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing .env file"),
):
    """Initialize search-ads configuration.

    Creates the data directory and a template .env file for API keys.
    The configuration is stored in ~/.search-ads/
    """
    config_dir = settings.data_dir
    env_file = config_dir / ".env"

    # Create directory
    config_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]Created directory:[/green] {config_dir}")

    # Create .env file
    if env_file.exists() and not force:
        console.print(f"[yellow]Config file already exists:[/yellow] {env_file}")
        console.print("[dim]Use --force to overwrite[/dim]")
    else:
        env_file.write_text(ENV_TEMPLATE)
        console.print(f"[green]Created config file:[/green] {env_file}")

    # Show next steps
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  1. Edit {env_file}")
    console.print("  2. Add your ADS API key (required)")
    console.print("     Get it from: https://ui.adsabs.harvard.edu/user/settings/token")
    console.print("  3. Optionally add OpenAI key for semantic search")
    console.print("\n[dim]Then run: search-ads seed <paper-url> to add your first paper[/dim]")


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

                # Add references to project
                for ref in refs:
                    project_repo.add_paper(target_project, ref.bibcode)

                cites = ads_client.fetch_citations(
                    paper.bibcode,
                    limit=settings.citations_limit,
                    min_citation_count=settings.min_citation_count,
                )
                console.print(f"  Fetched {len(cites)} citations")

                # Add citations to project
                for cite in cites:
                    project_repo.add_paper(target_project, cite.bibcode)

                console.print(f"  Added {len(refs) + len(cites)} papers to project: {target_project}")

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


def _search_local_database(
    query: str,
    keywords: list[str],
    limit: int = 50,
    use_vector: bool = True,
) -> list[Paper]:
    """Search the local database using vector similarity or keywords.

    Also searches user notes and includes papers with matching notes.

    Args:
        query: Full search query for vector search
        keywords: Keywords for fallback text search
        limit: Maximum results to return
        use_vector: Whether to use vector search (falls back to text if unavailable)

    Returns:
        List of matching papers
    """
    from src.db.vector_store import get_vector_store

    paper_repo = PaperRepository(auto_embed=False)
    note_repo = NoteRepository(auto_embed=False)

    seen_bibcodes = set()
    papers = []

    # Try vector search first
    if use_vector:
        try:
            vector_store = get_vector_store()
            vector_count = vector_store.count()
            notes_count = vector_store.notes_count()

            if vector_count > 0 or notes_count > 0:
                status_parts = []
                if vector_count > 0:
                    status_parts.append(f"{vector_count} papers")
                if notes_count > 0:
                    status_parts.append(f"{notes_count} notes")
                console.print(f"[dim]Using vector search ({', '.join(status_parts)} embedded)[/dim]")

                # Search abstracts
                if vector_count > 0:
                    results = vector_store.search(query, n_results=limit)
                    for result in results:
                        bibcode = result["bibcode"]
                        if bibcode not in seen_bibcodes:
                            paper = paper_repo.get(bibcode)
                            if paper:
                                papers.append(paper)
                                seen_bibcodes.add(bibcode)

                # Search notes
                if notes_count > 0:
                    note_results = vector_store.search_notes(query, n_results=limit)
                    for result in note_results:
                        bibcode = result["bibcode"]
                        if bibcode not in seen_bibcodes:
                            paper = paper_repo.get(bibcode)
                            if paper:
                                papers.append(paper)
                                seen_bibcodes.add(bibcode)

                if papers:
                    return papers[:limit]

                console.print("[yellow]No vector results, falling back to text search[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Vector search unavailable: {e}[/yellow]")
            console.print("[yellow]Falling back to text search[/yellow]")

    # Fallback to keyword-based text search
    console.print("[dim]Using keyword text search[/dim]")

    # Search by each keyword in title and abstract
    for keyword in keywords:
        if len(keyword) < 3:  # Skip very short keywords
            continue
        # Search title and abstract
        matches = paper_repo.search_by_text(keyword, limit=limit)
        for paper in matches:
            if paper.bibcode not in seen_bibcodes:
                papers.append(paper)
                seen_bibcodes.add(paper.bibcode)

        # Search notes
        note_matches = note_repo.search_by_text(keyword, limit=limit)
        for note in note_matches:
            if note.bibcode not in seen_bibcodes:
                paper = paper_repo.get(note.bibcode)
                if paper:
                    papers.append(paper)
                    seen_bibcodes.add(note.bibcode)

    # Sort by citation count
    papers.sort(key=lambda p: p.citation_count or 0, reverse=True)
    return papers[:limit]


@app.command()
def find(
    context: str = typer.Option(..., "--context", "-c", help="Text context for the citation"),
    author: Optional[str] = typer.Option(None, "--author", "-a", help="Filter by author name"),
    year: Optional[str] = typer.Option(None, "--year", "-y", help="Filter by year (e.g., 2020, 2018-2022)"),
    max_hops: int = typer.Option(2, "--max-hops", help="Maximum hops for graph expansion"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM-based analysis and ranking"),
    local_only: bool = typer.Option(False, "--local", "-l", help="Search local database only (no ADS API calls)"),
    num_refs: int = typer.Option(1, "--num-refs", "-n", help="Number of references needed (for \\cite{,} patterns)"),
):
    """Search for papers matching a context using LLM-powered analysis.

    Use --local to search only the local database (faster, no API calls).
    Use --num-refs to specify how many references are needed (e.g., 2 for \\cite{,}).
    Use --author to filter by author name (e.g., --author "Pan").
    Use --year to filter by year (e.g., --year 2020 or --year 2018-2022).
    """
    ensure_data_dirs()

    ads_client = ADSClient()
    paper_repo = PaperRepository()

    # Parse year filter
    year_range = None
    if year:
        if "-" in year:
            parts = year.split("-")
            year_range = (int(parts[0]), int(parts[1]))
        else:
            year_range = (int(year), int(year))

    console.print(f"[blue]Searching for papers matching context...[/blue]")
    console.print(f"[dim]Context: {context[:100]}{'...' if len(context) > 100 else ''}[/dim]")
    if author:
        console.print(f"[dim]Author filter: {author}[/dim]")
    if year_range:
        if year_range[0] == year_range[1]:
            console.print(f"[dim]Year filter: {year_range[0]}[/dim]")
        else:
            console.print(f"[dim]Year filter: {year_range[0]}-{year_range[1]}[/dim]")
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

            papers = _search_local_database(
                query=search_query,
                keywords=search_keywords,
                limit=top_k * 10,  # Get more to filter
                use_vector=True,
            )

            # Apply author and year filters to local results
            if papers and (author or year_range):
                filtered = []
                for p in papers:
                    # Author filter
                    if author:
                        if not p.authors or author.lower() not in p.authors.lower():
                            continue
                    # Year filter
                    if year_range:
                        if not p.year or not (year_range[0] <= p.year <= year_range[1]):
                            continue
                    filtered.append(p)
                papers = filtered[:top_k * 3]  # Limit after filtering

            if not papers:
                console.print("[yellow]No papers found in local database[/yellow]")
                console.print("[dim]Try running without --local to search ADS, or seed more papers[/dim]")
                console.print("[dim]Or run 'search-ads db embed' to embed existing papers for vector search[/dim]")
                return
        else:
            # Search ADS (papers also get saved to local DB)
            console.print("[blue]Searching ADS...[/blue]")

            # Build query with author filter
            ads_query = search_query
            if author:
                ads_query = f"({ads_query}) AND author:\"{author}\""

            papers = ads_client.search(ads_query, limit=top_k * 3, year_range=year_range)

            if not papers and analysis:
                # Fallback to keyword-based search
                console.print("[yellow]No results with extracted query, trying keywords...[/yellow]")
                keyword_query = " OR ".join(search_keywords[:3])
                if author:
                    keyword_query = f"({keyword_query}) AND author:\"{author}\""
                papers = ads_client.search(keyword_query, limit=top_k * 3, year_range=year_range)

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
def get(
    identifier: str = typer.Argument(..., help="Paper bibcode or ADS URL"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Output format: bibtex, bibitem, or all (default)"),
    fetch: bool = typer.Option(False, "--fetch", help="Fetch from ADS if not in local database"),
):
    """Get citation information for a paper (cite key, bibitem, bibtex).

    Returns plain text output suitable for use with Claude Code skill.
    The cite key is the bibcode for consistency with ADS.

    Examples:
        search-ads get 2021ApJ...914..140P
        search-ads get 2021ApJ...914..140P --format bibtex
        search-ads get 2021ApJ...914..140P --format bibitem
    """
    ensure_data_dirs()

    from src.core.ads_client import ADSClient

    # Parse bibcode from URL if needed
    bibcode = ADSClient.parse_bibcode_from_url(identifier) or identifier

    paper_repo = PaperRepository(auto_embed=False)
    paper = paper_repo.get(bibcode)

    if not paper and fetch:
        console.print(f"[blue]Fetching from ADS: {bibcode}[/blue]", err=True)
        ads_client = ADSClient()
        try:
            paper = ads_client.fetch_paper(bibcode)
        except RateLimitExceeded as e:
            console.print(f"[red]{e}[/red]", err=True)
            raise typer.Exit(1)

    if not paper:
        console.print(f"[red]Paper not found: {bibcode}[/red]", err=True)
        if not fetch:
            console.print("[dim]Use --fetch to retrieve from ADS[/dim]", err=True)
        raise typer.Exit(1)

    ads_client = ADSClient()

    # Get or generate bibtex
    bibtex = paper.bibtex
    if not bibtex:
        bibtex = ads_client.generate_bibtex(bibcode)
        if bibtex:
            paper.bibtex = bibtex
            paper_repo.add(paper, embed=False)

    # Get or generate aastex bibitem
    bibitem_aastex = paper.bibitem_aastex
    if not bibitem_aastex:
        bibitem_aastex = ads_client.generate_aastex(bibcode)
        if bibitem_aastex:
            paper.bibitem_aastex = bibitem_aastex
            paper_repo.add(paper, embed=False)

    # Output based on format
    if format == "bibtex":
        if bibtex:
            console.print(bibtex)
        else:
            console.print("[red]BibTeX not available[/red]", err=True)
            raise typer.Exit(1)
    elif format == "bibitem":
        if bibitem_aastex:
            console.print(bibitem_aastex)
        else:
            console.print("[red]Bibitem not available[/red]", err=True)
            raise typer.Exit(1)
    else:
        # Output all information
        console.print(f"Cite key: {bibcode}\n")

        if bibitem_aastex:
            console.print("Bibitem (aastex):")
            console.print(bibitem_aastex)
            console.print()

        if bibtex:
            console.print("BibTeX:")
            console.print(bibtex)


@app.command()
def show(
    identifier: str = typer.Argument(..., help="Paper bibcode or ADS URL"),
    fetch: bool = typer.Option(False, "--fetch", "-f", help="Fetch from ADS if not in local database"),
):
    """Show detailed information about a paper."""
    ensure_data_dirs()

    from src.core.ads_client import ADSClient

    # Parse bibcode from URL if needed
    bibcode = ADSClient.parse_bibcode_from_url(identifier) or identifier

    paper_repo = PaperRepository(auto_embed=False)
    paper = paper_repo.get(bibcode)

    if not paper and fetch:
        console.print(f"[blue]Fetching from ADS: {bibcode}[/blue]")
        ads_client = ADSClient()
        try:
            paper = ads_client.fetch_paper(bibcode)
        except RateLimitExceeded as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)

    if not paper:
        console.print(f"[red]Paper not found: {bibcode}[/red]")
        if not fetch:
            console.print("[dim]Use --fetch to retrieve from ADS[/dim]")
        raise typer.Exit(1)

    # Display detailed information
    table = Table(title=f"Paper Details", show_header=False, box=None)
    table.add_column("Field", style="cyan", width=15)
    table.add_column("Value", style="white")

    table.add_row("Bibcode", paper.bibcode)
    table.add_row("Title", paper.title)

    # Format authors
    if paper.authors:
        try:
            author_list = json.loads(paper.authors)
            if len(author_list) > 5:
                authors_str = ", ".join(author_list[:5]) + f" (+{len(author_list) - 5} more)"
            else:
                authors_str = ", ".join(author_list)
            table.add_row("Authors", authors_str)
        except json.JSONDecodeError:
            table.add_row("Authors", paper.authors)

    table.add_row("Year", str(paper.year) if paper.year else "-")
    table.add_row("Journal", paper.journal or "-")

    if paper.volume:
        table.add_row("Volume", paper.volume)
    if paper.pages:
        table.add_row("Pages", paper.pages)

    table.add_row("Citations", str(paper.citation_count) if paper.citation_count else "0")

    if paper.doi:
        table.add_row("DOI", paper.doi)
    if paper.arxiv_id:
        table.add_row("arXiv", paper.arxiv_id)

    # URLs
    ads_url = f"https://ui.adsabs.harvard.edu/abs/{paper.bibcode}/abstract"
    table.add_row("ADS URL", ads_url)

    if paper.pdf_url:
        table.add_row("PDF URL", paper.pdf_url)

    # Citation key (always use bibcode for consistency with ADS)
    table.add_row("Citation Key", paper.bibcode)

    # My paper status
    if paper.is_my_paper:
        table.add_row("My Paper", "[green]Yes[/green]")

    console.print(table)

    # Abstract in a separate panel
    if paper.abstract:
        console.print()
        console.print(Panel(paper.abstract, title="Abstract", border_style="blue"))

    # Show user note if available
    note_repo = NoteRepository(auto_embed=False)
    user_note = note_repo.get(paper.bibcode)
    if user_note:
        console.print()
        console.print(Panel(user_note.content, title="Note", border_style="cyan"))

    # Show AASTeX bibitem if available
    if paper.bibitem_aastex:
        console.print()
        console.print(Panel(paper.bibitem_aastex, title="Bibitem (AASTeX)", border_style="magenta"))

    # Show BibTeX if available
    if paper.bibtex:
        console.print()
        console.print(Panel(paper.bibtex, title="BibTeX", border_style="green"))


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
    total_count = paper_repo.count()
    papers = paper_repo.get_all(limit=limit, project=project)

    if not papers:
        console.print("[yellow]No papers found[/yellow]")
        return

    table = Table(title=f"Papers ({len(papers)}/{total_count})")
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

    paper_repo = PaperRepository(auto_embed=False)
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


@db_app.command("embed")
def db_embed(
    force: bool = typer.Option(False, "--force", "-f", help="Re-embed all papers (even if already embedded)"),
):
    """Embed all papers in the vector store for semantic search.

    This creates vector embeddings of paper abstracts using OpenAI's
    text-embedding-3-small model, enabling semantic similarity search.
    """
    ensure_data_dirs()

    from src.db.vector_store import get_vector_store

    paper_repo = PaperRepository(auto_embed=False)
    vector_store = get_vector_store()

    # Get all papers
    papers = paper_repo.get_all(limit=10000)

    if not papers:
        console.print("[yellow]No papers in database to embed[/yellow]")
        return

    console.print(f"[blue]Found {len(papers)} papers in database[/blue]")

    # Check current embedding count
    current_count = vector_store.count()
    console.print(f"[dim]Currently {current_count} papers embedded[/dim]")

    if force and current_count > 0:
        console.print("[yellow]Clearing existing embeddings...[/yellow]")
        vector_store.clear()

    # Filter papers with abstracts
    papers_with_abstracts = [p for p in papers if p.abstract]
    console.print(f"[dim]{len(papers_with_abstracts)} papers have abstracts[/dim]")

    if not papers_with_abstracts:
        console.print("[yellow]No papers with abstracts to embed[/yellow]")
        return

    console.print("[blue]Embedding papers...[/blue]")

    try:
        embedded = vector_store.embed_papers(papers_with_abstracts)
        console.print(f"[green]Successfully embedded {embedded} papers[/green]")

        final_count = vector_store.count()
        console.print(f"[dim]Total papers in vector store: {final_count}[/dim]")

    except Exception as e:
        console.print(f"[red]Error during embedding: {e}[/red]")
        raise typer.Exit(1)


@db_app.command("update")
def db_update(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Update only papers in this project"),
    older_than: Optional[int] = typer.Option(None, "--older-than", help="Update papers not updated in N days"),
    batch_size: int = typer.Option(50, "--batch-size", help="Papers per API call (max 50)"),
):
    """Update citation counts for papers in the database.

    Uses batch queries to minimize API calls. Only updates papers where
    the citation count has changed.
    """
    ensure_data_dirs()

    from datetime import datetime, timedelta

    ads_client = ADSClient()
    paper_repo = PaperRepository(auto_embed=False)

    # Get papers to update
    papers = paper_repo.get_all(limit=10000, project=project)

    if not papers:
        console.print("[yellow]No papers to update[/yellow]")
        return

    # Filter by age if specified
    if older_than:
        cutoff = datetime.utcnow() - timedelta(days=older_than)
        papers = [p for p in papers if p.updated_at < cutoff]

    if not papers:
        console.print("[yellow]No papers need updating[/yellow]")
        return

    console.print(f"[blue]Updating {len(papers)} papers...[/blue]")

    # Get bibcodes
    bibcodes = [p.bibcode for p in papers]

    # Batch update
    try:
        updates = ads_client.batch_update_papers(bibcodes, batch_size=batch_size)
    except RateLimitExceeded as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    # Apply updates
    updated_count = 0
    for paper in papers:
        if paper.bibcode in updates:
            new_citation_count = updates[paper.bibcode].get("citation_count")
            if new_citation_count is not None and new_citation_count != paper.citation_count:
                old_count = paper.citation_count or 0
                paper.citation_count = new_citation_count
                paper.updated_at = datetime.utcnow()
                paper_repo.add(paper, embed=False)
                updated_count += 1

                if new_citation_count > old_count:
                    console.print(f"  {paper.bibcode}: {old_count} -> {new_citation_count} (+{new_citation_count - old_count})")

    console.print(f"\n[green]Updated {updated_count} papers with changed citation counts[/green]")
    console.print(f"[dim]API calls used: {(len(bibcodes) + batch_size - 1) // batch_size}[/dim]")


@db_app.command("status")
def db_status():
    """Show detailed database and vector store status."""
    ensure_data_dirs()

    from src.db.vector_store import get_vector_store

    paper_repo = PaperRepository(auto_embed=False)

    table = Table(title="Database Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Paper stats
    total_papers = paper_repo.count()
    papers = paper_repo.get_all(limit=10000)
    papers_with_abstracts = len([p for p in papers if p.abstract])

    table.add_row("Total papers", str(total_papers))
    table.add_row("Papers with abstracts", str(papers_with_abstracts))

    # Vector store stats
    try:
        vector_store = get_vector_store()
        embedded_count = vector_store.count()
        table.add_row("Embedded in vector store", str(embedded_count))

        if papers_with_abstracts > 0:
            coverage = (embedded_count / papers_with_abstracts) * 100
            table.add_row("Embedding coverage", f"{coverage:.1f}%")
    except Exception as e:
        table.add_row("Vector store", f"[red]Error: {e}[/red]")

    # Paths
    table.add_row("Database path", str(settings.db_path))
    table.add_row("Vector store path", str(settings.chroma_path))

    console.print(table)


# PDF commands
@pdf_app.command("download")
def pdf_download(
    bibcode: str = typer.Argument(..., help="Paper bibcode"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-download even if exists"),
):
    """Download PDF for a paper from arXiv or ADS."""
    ensure_data_dirs()

    from src.core.pdf_handler import PDFHandler, PDFDownloadError

    paper_repo = PaperRepository(auto_embed=False)
    pdf_handler = PDFHandler()

    # Get paper from database
    paper = paper_repo.get(bibcode)
    if not paper:
        console.print(f"[red]Paper not found in database: {bibcode}[/red]")
        console.print("[dim]Use 'search-ads seed' to add the paper first[/dim]")
        raise typer.Exit(1)

    if pdf_handler.is_downloaded(bibcode) and not force:
        pdf_path = pdf_handler.get_pdf_path(bibcode)
        console.print(f"[yellow]PDF already downloaded: {pdf_path}[/yellow]")
        console.print("[dim]Use --force to re-download[/dim]")
        return

    console.print(f"[blue]Downloading PDF for: {paper.title[:60]}...[/blue]")

    if paper.pdf_url:
        console.print(f"[dim]URL: {paper.pdf_url}[/dim]")

    try:
        pdf_path = pdf_handler.download(paper, force=force)
        console.print(f"[green]Downloaded: {pdf_path}[/green]")

        # Update paper record with local path
        paper.pdf_path = str(pdf_path)
        paper_repo.add(paper, embed=False)

    except PDFDownloadError as e:
        console.print(f"[red]Download failed: {e}[/red]")
        raise typer.Exit(1)


@pdf_app.command("embed")
def pdf_embed(
    bibcode: str = typer.Argument(..., help="Paper bibcode"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-embed even if already embedded"),
):
    """Embed PDF content for full-text search.

    Downloads the PDF if not already downloaded, then extracts text
    and creates vector embeddings for semantic search.
    """
    ensure_data_dirs()

    from src.core.pdf_handler import PDFHandler, PDFDownloadError, PDFParseError
    from src.db.vector_store import get_vector_store

    paper_repo = PaperRepository(auto_embed=False)
    pdf_handler = PDFHandler()
    vector_store = get_vector_store()

    # Get paper from database
    paper = paper_repo.get(bibcode)
    if not paper:
        console.print(f"[red]Paper not found in database: {bibcode}[/red]")
        raise typer.Exit(1)

    # Check if already embedded
    if vector_store.is_pdf_embedded(bibcode) and not force:
        console.print(f"[yellow]PDF already embedded for: {bibcode}[/yellow]")
        console.print("[dim]Use --force to re-embed[/dim]")
        return

    console.print(f"[blue]Processing: {paper.title[:60]}...[/blue]")

    # Download if needed
    if not pdf_handler.is_downloaded(bibcode):
        console.print("[blue]Downloading PDF...[/blue]")
        try:
            pdf_path = pdf_handler.download(paper)
            paper.pdf_path = str(pdf_path)
            paper_repo.add(paper, embed=False)
        except PDFDownloadError as e:
            console.print(f"[red]Download failed: {e}[/red]")
            raise typer.Exit(1)
    else:
        pdf_path = pdf_handler.get_pdf_path(bibcode)

    # Parse PDF
    console.print("[blue]Extracting text...[/blue]")
    try:
        pdf_text = pdf_handler.parse(pdf_path)
        console.print(f"[dim]Extracted {len(pdf_text):,} characters[/dim]")
    except PDFParseError as e:
        console.print(f"[red]Parse failed: {e}[/red]")
        raise typer.Exit(1)

    # Embed in vector store
    console.print("[blue]Creating embeddings...[/blue]")
    try:
        num_chunks = vector_store.embed_pdf(bibcode, pdf_text, title=paper.title)
        console.print(f"[green]Embedded {num_chunks} chunks for {bibcode}[/green]")

        # Update paper record
        paper.pdf_embedded = True
        paper_repo.add(paper, embed=False)

    except Exception as e:
        console.print(f"[red]Embedding failed: {e}[/red]")
        raise typer.Exit(1)


@pdf_app.command("status")
def pdf_status():
    """Show PDF download and embedding status."""
    ensure_data_dirs()

    from src.core.pdf_handler import PDFHandler
    from src.db.vector_store import get_vector_store

    paper_repo = PaperRepository(auto_embed=False)
    pdf_handler = PDFHandler()
    vector_store = get_vector_store()

    # Get stats
    storage_stats = pdf_handler.get_storage_stats()
    pdf_papers = vector_store.pdf_paper_count()
    pdf_chunks = vector_store.pdf_count()

    table = Table(title="PDF Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("PDFs downloaded", str(storage_stats["count"]))
    table.add_row("Storage used", f"{storage_stats['total_size_mb']} MB")
    table.add_row("Papers with embedded PDFs", str(pdf_papers))
    table.add_row("Total PDF chunks", str(pdf_chunks))
    table.add_row("PDF directory", str(settings.pdfs_path))

    console.print(table)


@pdf_app.command("search")
def pdf_search(
    query: str = typer.Argument(..., help="Search query"),
    bibcode: Optional[str] = typer.Option(None, "--bibcode", "-b", help="Limit to specific paper"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results"),
):
    """Search through embedded PDF content."""
    ensure_data_dirs()

    from src.db.vector_store import get_vector_store

    vector_store = get_vector_store()
    paper_repo = PaperRepository(auto_embed=False)

    if vector_store.pdf_count() == 0:
        console.print("[yellow]No PDFs embedded yet[/yellow]")
        console.print("[dim]Use 'search-ads pdf embed <bibcode>' to embed PDFs[/dim]")
        return

    console.print(f"[blue]Searching PDF content for: {query}[/blue]\n")

    results = vector_store.search_pdf(query, n_results=top_k, bibcode=bibcode)

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    for i, result in enumerate(results, 1):
        paper = paper_repo.get(result["bibcode"])
        title = paper.title if paper else result["bibcode"]

        console.print(f"[bold cyan]{i}.[/bold cyan] [bold]{title[:70]}...[/bold]")
        console.print(f"   [dim]Bibcode: {result['bibcode']} | Chunk {result['chunk_index'] + 1}[/dim]")

        # Show snippet
        snippet = result["document"][:300] + "..." if len(result["document"]) > 300 else result["document"]
        console.print(f"   {snippet}\n")


@pdf_app.command("list")
def pdf_list():
    """List all downloaded PDFs."""
    ensure_data_dirs()

    from src.core.pdf_handler import PDFHandler
    from src.db.vector_store import get_vector_store

    paper_repo = PaperRepository(auto_embed=False)
    pdf_handler = PDFHandler()
    vector_store = get_vector_store()

    pdf_files = list(pdf_handler.pdf_dir.glob("*.pdf"))

    if not pdf_files:
        console.print("[yellow]No PDFs downloaded[/yellow]")
        return

    table = Table(title=f"Downloaded PDFs ({len(pdf_files)})")
    table.add_column("Bibcode", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Size", style="green")
    table.add_column("Embedded", style="magenta")

    for pdf_path in sorted(pdf_files):
        # Extract bibcode from filename
        bibcode = pdf_path.stem.replace("_", ".")

        paper = paper_repo.get(bibcode)
        title = paper.title[:40] + "..." if paper and len(paper.title) > 40 else (paper.title if paper else "-")

        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        size_str = f"{size_mb:.1f} MB"

        is_embedded = vector_store.is_pdf_embedded(bibcode)
        embedded_str = "[green]Yes[/green]" if is_embedded else "[dim]No[/dim]"

        table.add_row(bibcode, title, size_str, embedded_str)

    console.print(table)


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


@app.command()
def mine(
    bibcode: Optional[str] = typer.Argument(None, help="Paper bibcode to mark/unmark"),
    unmark: bool = typer.Option(False, "--unmark", "-u", help="Unmark as my paper"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all my papers"),
):
    """Mark papers as yours (authored by you).

    Mark a paper as yours:
        search-ads mine 2023ApJ...XXX

    Unmark a paper:
        search-ads mine 2023ApJ...XXX --unmark

    List all your papers:
        search-ads mine --list

    Configure auto-detection by setting MY_AUTHOR_NAMES in ~/.search-ads/.env:
        MY_AUTHOR_NAMES="Pan, K.-C.; Pan, Kuo-Chuan; Pan, K."

    Or use the Web UI: click the user icon in the top right to edit author names.
    """
    ensure_data_dirs()

    from src.core.config import settings

    paper_repo = PaperRepository(auto_embed=False)

    if list_all:
        # List all my papers
        my_papers = paper_repo.get_my_papers(limit=100)
        if not my_papers:
            console.print("[yellow]No papers marked as yours[/yellow]")
            if not settings.my_author_names:
                console.print("[dim]Tip: Set MY_AUTHOR_NAMES env var for auto-detection[/dim]")
            return

        table = Table(title=f"My Papers ({len(my_papers)})")
        table.add_column("Bibcode", style="cyan", no_wrap=True)
        table.add_column("Year", style="magenta")
        table.add_column("Title", style="white")
        table.add_column("Citations", style="green")

        for paper in my_papers:
            title = paper.title[:50] + "..." if len(paper.title) > 50 else paper.title
            table.add_row(
                paper.bibcode,
                str(paper.year) if paper.year else "-",
                title,
                str(paper.citation_count) if paper.citation_count else "-",
            )

        console.print(table)
        return

    if not bibcode:
        console.print("[red]Please provide a bibcode or use --list[/red]")
        raise typer.Exit(1)

    # Parse bibcode from URL if needed
    from src.core.ads_client import ADSClient
    bibcode = ADSClient.parse_bibcode_from_url(bibcode) or bibcode

    # Verify paper exists
    paper = paper_repo.get(bibcode)
    if not paper:
        console.print(f"[red]Paper not found in database: {bibcode}[/red]")
        console.print("[dim]Use 'search-ads seed' to add the paper first[/dim]")
        raise typer.Exit(1)

    if unmark:
        paper_repo.set_my_paper(bibcode, False)
        console.print(f"[green]Unmarked as your paper: {bibcode}[/green]")
    else:
        paper_repo.set_my_paper(bibcode, True)
        console.print(f"[green]Marked as your paper: {bibcode}[/green]")
        console.print(f"[dim]{paper.title}[/dim]")


@app.command()
def note(
    bibcode: str = typer.Argument(..., help="Paper bibcode"),
    add: Optional[str] = typer.Option(None, "--add", "-a", help="Add/append a note to this paper"),
    delete: bool = typer.Option(False, "--delete", "-d", help="Delete the note for this paper"),
):
    """Manage notes for papers.

    Add a note:
        search-ads note 2023ApJ...XXX --add "This paper describes..."

    If a note already exists, --add will append to it.

    Delete a note:
        search-ads note 2023ApJ...XXX --delete

    View a note (no flags):
        search-ads note 2023ApJ...XXX
    """
    ensure_data_dirs()

    from src.core.ads_client import ADSClient

    # Parse bibcode from URL if needed
    bibcode = ADSClient.parse_bibcode_from_url(bibcode) or bibcode

    paper_repo = PaperRepository(auto_embed=False)
    note_repo = NoteRepository()

    # Verify paper exists
    paper = paper_repo.get(bibcode)
    if not paper:
        console.print(f"[red]Paper not found in database: {bibcode}[/red]")
        console.print("[dim]Use 'search-ads seed' to add the paper first[/dim]")
        raise typer.Exit(1)

    if delete:
        # Delete note
        if note_repo.delete(bibcode):
            console.print(f"[green]Deleted note for: {bibcode}[/green]")
        else:
            console.print(f"[yellow]No note found for: {bibcode}[/yellow]")
        return

    if add:
        # Add/append note
        note_obj = note_repo.add(bibcode, add)
        existing = note_repo.get(bibcode)
        if existing and "\n\n" in existing.content:
            console.print(f"[green]Appended note for: {bibcode}[/green]")
        else:
            console.print(f"[green]Added note for: {bibcode}[/green]")

        console.print(Panel(note_obj.content, title=f"Note for {bibcode}", border_style="cyan"))
        return

    # View note (no flags)
    existing_note = note_repo.get(bibcode)
    if existing_note:
        console.print(f"[bold]{paper.title}[/bold]")
        console.print(f"[dim]{bibcode}[/dim]\n")
        console.print(Panel(existing_note.content, title="Note", border_style="cyan"))
    else:
        console.print(f"[yellow]No note for: {bibcode}[/yellow]")
        console.print(f"[dim]Use --add to create a note[/dim]")


@app.command()
def web(
    host: str = typer.Option(settings.web_host, "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(settings.web_port, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload for development"),
):
    """Start the web UI server.

    The web UI provides a browser-based interface for managing your paper library,
    searching papers, and visualizing citation networks.

    Examples:
        search-ads web                    # Start on default port 9527
        search-ads web --port 8080        # Start on port 8080
        search-ads web --reload           # Start with auto-reload for development
    """
    ensure_data_dirs()

    import uvicorn

    console.print(f"[bold green]Starting Search-ADS Web UI[/bold green]")
    console.print(f"[blue]Server: http://{host}:{port}[/blue]")
    console.print(f"[dim]Press Ctrl+C to stop[/dim]\n")

    uvicorn.run(
        "src.web.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
