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

    # Citation key format (default to bibcode for consistency with ADS)
    citation_key_format: Literal["author_year", "author_year_title", "bibcode"] = "bibcode"
    citation_key_lowercase: bool = True
    citation_key_max_length: int = 30

    # Author name(s) for auto-detecting "my papers"
    # Comma-separated list of name variations (e.g., "Pan, K.,Pan, Ke-Jung")
    my_author_names: str = Field(default="", alias="MY_AUTHOR_NAMES")

    def get_my_author_names(self) -> list[str]:
        """Get list of author name variations for matching."""
        if not self.my_author_names:
            return []
        return [name.strip() for name in self.my_author_names.split(",") if name.strip()]

    def is_my_paper_by_author(self, authors_json: str | None) -> bool:
        """Check if a paper is authored by me based on author list."""
        if not authors_json or not self.my_author_names:
            return False

        import json
        try:
            authors = json.loads(authors_json)
        except json.JSONDecodeError:
            return False

        my_names = self.get_my_author_names()
        for author in authors:
            author_lower = author.lower()
            for my_name in my_names:
                if my_name.lower() in author_lower:
                    return True
        return False


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
