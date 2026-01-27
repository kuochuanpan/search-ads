"""Configuration management for search-ads."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(Path.home() / ".search-ads" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    ads_api_key: str = Field(default="", alias="ADS_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # Data directories
    data_dir: Path = Field(default=Path.home() / ".search-ads")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "papers.db"

    @property
    def chroma_path(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def pdfs_path(self) -> Path:
        return self.data_dir / "pdfs"

    # Search parameters
    max_hops: int = Field(default=2, ge=0, le=5)
    top_k: int = Field(default=10, ge=1, le=50)
    expand_top_k: int = Field(default=5, ge=1, le=20)
    refs_limit: int = Field(default=50, ge=1, le=100)
    citations_limit: int = Field(default=50, ge=1, le=100)
    min_citation_count: int = Field(default=0, ge=0)

    # Default project
    default_project: str = Field(default="default")

    # Web UI server settings
    web_host: str = Field(default="127.0.0.1", alias="WEB_HOST")
    web_port: int = Field(default=9527, alias="WEB_PORT")

    # Citation key format (default to bibcode for consistency with ADS)
    citation_key_format: Literal["author_year", "author_year_title", "bibcode"] = "bibcode"
    citation_key_lowercase: bool = True
    citation_key_max_length: int = 30

    # Author name(s) for auto-detecting "my papers"
    # Semicolon-separated list of name variations (e.g., "Pan, K.; Pan, Ke-Jung")
    my_author_names: str = Field(default="", alias="MY_AUTHOR_NAMES")

    def get_my_author_names(self) -> list[str]:
        """Get list of author name variations for matching."""
        if not self.my_author_names:
            return []
        # Support both semicolon and comma separators for backwards compatibility
        # Prefer semicolon since author names contain commas
        if ";" in self.my_author_names:
            return [name.strip() for name in self.my_author_names.split(";") if name.strip()]
        return [name.strip() for name in self.my_author_names.split(",") if name.strip()]

    def is_my_paper_by_author(self, authors_json: str | None) -> bool:
        """Check if a paper is authored by me based on author list.

        Uses normalized matching to handle variations in author names:
        - Case insensitive comparison
        - Exact match on normalized names (e.g., "Pan, K.-C." matches "Pan, K.-C.")
        - Also checks if my name starts with or matches the paper author
          (handles "Pan, K." matching "Pan, Kuo-Chuan")
        """
        if not authors_json or not self.my_author_names:
            return False

        import json
        import re
        try:
            authors = json.loads(authors_json)
        except json.JSONDecodeError:
            return False

        my_names = self.get_my_author_names()

        def normalize_name(name: str) -> str:
            """Normalize author name for comparison."""
            # Lowercase and strip whitespace
            name = name.lower().strip()
            # Normalize multiple spaces to single space
            name = re.sub(r'\s+', ' ', name)
            return name

        def get_last_name(name: str) -> str:
            """Extract last name (part before comma)."""
            if ',' in name:
                return name.split(',')[0].strip()
            return name.split()[0] if name.split() else name

        def names_match(paper_author: str, my_name: str) -> bool:
            """Check if an author name matches one of my name variations."""
            paper_norm = normalize_name(paper_author)
            my_norm = normalize_name(my_name)

            # Exact match
            if paper_norm == my_norm:
                return True

            # Check if last names match first
            paper_last = get_last_name(paper_norm)
            my_last = get_last_name(my_norm)

            if paper_last != my_last:
                return False

            # Last names match, now check first name/initial
            # "Pan, K." should match "Pan, Kuo-Chuan" or "Pan, K.-C."
            # "Pan, Kuo-Chuan" should match "Pan, K."

            # Extract first name parts (everything after comma)
            paper_first = paper_norm.split(',')[1].strip() if ',' in paper_norm else ""
            my_first = my_norm.split(',')[1].strip() if ',' in my_norm else ""

            if not paper_first or not my_first:
                # If one has no first name, consider it a match if last names match
                return True

            # Check if one is abbreviation of the other
            # Get first initial from each
            paper_initial = paper_first[0] if paper_first else ""
            my_initial = my_first[0] if my_first else ""

            # If initials match, consider it a potential match
            if paper_initial == my_initial:
                return True

            return False

        for author in authors:
            for my_name in my_names:
                if names_match(author, my_name):
                    return True
        return False

    def set_my_author_names(self, names: str) -> None:
        """Update the author names setting (runtime only, does not persist)."""
        self.my_author_names = names

    def save_my_author_names(self, names: str) -> bool:
        """Save author names to the .env file."""
        import re
        env_path = self.data_dir / ".env"

        # Update the in-memory setting
        self.my_author_names = names

        # Read existing .env file
        if env_path.exists():
            content = env_path.read_text()
        else:
            content = ""

        # Update or add MY_AUTHOR_NAMES line
        new_line = f'MY_AUTHOR_NAMES="{names}"'

        if 'MY_AUTHOR_NAMES=' in content:
            # Replace existing line
            content = re.sub(
                r'^MY_AUTHOR_NAMES=.*$',
                new_line,
                content,
                flags=re.MULTILINE
            )
        else:
            # Add new line
            if content and not content.endswith('\n'):
                content += '\n'
            content += f'\n# Author name(s) for auto-detecting "my papers" (semicolon-separated)\n'
            content += f'{new_line}\n'

        env_path.write_text(content)
        return True


class ProjectConfig:
    """Project-specific configuration loaded from .search-ads.yaml."""

    def __init__(
        self,
        name: str = "default",
        prefer_project_papers: bool = True,
        include_all_papers: bool = True,
        seeds: list[str] | None = None,
    ):
        self.name = name
        self.prefer_project_papers = prefer_project_papers
        self.include_all_papers = include_all_papers
        self.seeds = seeds or []

    @classmethod
    def load_from_yaml(cls, path: Path) -> "ProjectConfig":
        """Load project config from a YAML file."""
        import yaml

        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        project = data.get("project", {})
        search = data.get("search", {})

        return cls(
            name=project.get("name", "default"),
            prefer_project_papers=search.get("prefer_project_papers", True),
            include_all_papers=search.get("include_all_papers", True),
            seeds=data.get("seeds", []),
        )


# Global settings instance
settings = Settings()


def ensure_data_dirs():
    """Ensure all data directories exist."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    settings.pdfs_path.mkdir(parents=True, exist_ok=True)
