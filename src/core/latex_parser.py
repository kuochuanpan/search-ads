"""LaTeX parser for finding and filling citations."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class EmptyCitation:
    """Represents an empty citation in a LaTeX file."""

    line_number: int
    column: int
    cite_type: str  # cite, citep, citet, etc.
    context: str  # Surrounding text for context
    full_match: str  # The full \cite{} match
    existing_keys: list[str]  # Any existing keys in the citation


@dataclass
class BibliographyInfo:
    """Information about the bibliography setup in a LaTeX file."""

    uses_bib_file: bool
    bib_file: Optional[str] = None
    uses_bibitem: bool = False
    bibitem_location: Optional[int] = None  # Line number of thebibliography


class LaTeXParser:
    """Parser for LaTeX files to find and modify citations."""

    # Citation command patterns
    CITE_PATTERN = re.compile(
        r"\\(cite[pt]?|citep?|citet|citealt|citealp|citeauthor|citeyear|citeyearpar)"
        r"(?:\[[^\]]*\])?"  # Optional [] argument
        r"(?:\[[^\]]*\])?"  # Optional second [] argument
        r"\{([^}]*)\}",
        re.MULTILINE,
    )

    # Pattern for empty or partial citations
    EMPTY_CITE_PATTERN = re.compile(
        r"\\(cite[pt]?|citep?|citet|citealt|citealp|citeauthor|citeyear|citeyearpar)"
        r"(?:\[[^\]]*\])?"
        r"(?:\[[^\]]*\])?"
        r"\{(\s*(?:,\s*)*)\}",  # Empty or just commas
        re.MULTILINE,
    )

    # Pattern for bibliography file
    BIB_FILE_PATTERN = re.compile(r"\\bibliography\{([^}]+)\}")
    BIBRESOURCE_PATTERN = re.compile(r"\\addbibresource\{([^}]+)\}")

    # Pattern for \begin{thebibliography}
    THEBIB_PATTERN = re.compile(r"\\begin\{thebibliography\}")

    # Pattern for \end{document}
    END_DOC_PATTERN = re.compile(r"\\end\{document\}")

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self.content = self.file_path.read_text()
        self.lines = self.content.splitlines(keepends=True)

    def find_empty_citations(self) -> list[EmptyCitation]:
        """Find all empty citations in the file.

        Returns:
            List of EmptyCitation objects
        """
        empty_cites = []

        for match in self.EMPTY_CITE_PATTERN.finditer(self.content):
            # Calculate line number and column
            start = match.start()
            line_num = self.content[:start].count("\n") + 1
            line_start = self.content.rfind("\n", 0, start) + 1
            column = start - line_start + 1

            # Extract context (surrounding text)
            context = self._extract_context(start)

            empty_cites.append(
                EmptyCitation(
                    line_number=line_num,
                    column=column,
                    cite_type=match.group(1),
                    context=context,
                    full_match=match.group(0),
                    existing_keys=[],
                )
            )

        # Also find citations with partial keys (e.g., \cite{key1, })
        for match in self.CITE_PATTERN.finditer(self.content):
            keys_str = match.group(2)
            keys = [k.strip() for k in keys_str.split(",")]

            # Check if any key is empty
            if any(k == "" for k in keys):
                start = match.start()
                line_num = self.content[:start].count("\n") + 1
                line_start = self.content.rfind("\n", 0, start) + 1
                column = start - line_start + 1

                context = self._extract_context(start)
                existing = [k for k in keys if k]

                # Avoid duplicates with EMPTY_CITE_PATTERN
                if not any(ec.line_number == line_num and ec.column == column for ec in empty_cites):
                    empty_cites.append(
                        EmptyCitation(
                            line_number=line_num,
                            column=column,
                            cite_type=match.group(1),
                            context=context,
                            full_match=match.group(0),
                            existing_keys=existing,
                        )
                    )

        return empty_cites

    def _extract_context(self, position: int, window: int = 200) -> str:
        """Extract surrounding context for a citation.

        Args:
            position: Character position in content
            window: Number of characters to extract on each side

        Returns:
            Cleaned context string
        """
        start = max(0, position - window)
        end = min(len(self.content), position + window)

        context = self.content[start:end]

        # Clean up LaTeX commands for better LLM understanding
        # Remove common LaTeX commands but keep text
        context = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", context)
        context = re.sub(r"\\[a-zA-Z]+", "", context)
        context = re.sub(r"[{}]", "", context)
        context = re.sub(r"\s+", " ", context)

        return context.strip()

    def get_bibliography_info(self) -> BibliographyInfo:
        """Detect how bibliography is handled in this file.

        Returns:
            BibliographyInfo object
        """
        # Check for \bibliography{file}
        bib_match = self.BIB_FILE_PATTERN.search(self.content)
        if bib_match:
            bib_file = bib_match.group(1)
            if not bib_file.endswith(".bib"):
                bib_file += ".bib"
            return BibliographyInfo(uses_bib_file=True, bib_file=bib_file)

        # Check for biblatex \addbibresource
        bibres_match = self.BIBRESOURCE_PATTERN.search(self.content)
        if bibres_match:
            return BibliographyInfo(uses_bib_file=True, bib_file=bibres_match.group(1))

        # Check for thebibliography environment
        thebib_match = self.THEBIB_PATTERN.search(self.content)
        if thebib_match:
            line_num = self.content[: thebib_match.start()].count("\n") + 1
            return BibliographyInfo(
                uses_bib_file=False,
                uses_bibitem=True,
                bibitem_location=line_num,
            )

        # No bibliography found - will use bibitem at end
        return BibliographyInfo(uses_bib_file=False, uses_bibitem=True)

    def fill_citation(
        self,
        line: int,
        column: int,
        citation_key: str,
        save: bool = True,
    ) -> str:
        """Fill an empty citation with a key.

        Args:
            line: Line number (1-indexed)
            column: Column position (1-indexed)
            citation_key: The citation key to insert
            save: Whether to save the file

        Returns:
            The modified content
        """
        # Convert to 0-indexed
        line_idx = line - 1

        if line_idx < 0 or line_idx >= len(self.lines):
            raise ValueError(f"Invalid line number: {line}")

        line_content = self.lines[line_idx]

        # Find the citation at this position
        # Look for \cite{} pattern starting near column
        cite_match = None
        for match in self.CITE_PATTERN.finditer(line_content):
            if abs(match.start() - (column - 1)) < 5:  # Allow some tolerance
                cite_match = match
                break

        if not cite_match:
            # Try empty citation pattern
            for match in self.EMPTY_CITE_PATTERN.finditer(line_content):
                if abs(match.start() - (column - 1)) < 5:
                    cite_match = match
                    break

        if not cite_match:
            raise ValueError(f"No citation found at line {line}, column {column}")

        # Get existing keys
        existing_keys = cite_match.group(2) if len(cite_match.groups()) > 1 else ""
        keys = [k.strip() for k in existing_keys.split(",") if k.strip()]

        # Add new key
        keys.append(citation_key)
        new_keys = ", ".join(keys)

        # Construct new citation
        cite_type = cite_match.group(1)
        new_cite = f"\\{cite_type}{{{new_keys}}}"

        # Replace in line
        new_line = line_content[: cite_match.start()] + new_cite + line_content[cite_match.end() :]
        self.lines[line_idx] = new_line

        # Update content
        self.content = "".join(self.lines)

        if save:
            self.file_path.write_text(self.content)

        return self.content

    def add_bibitem(self, bibkey: str, bibitem_text: str, save: bool = True) -> str:
        """Add a \\bibitem entry to the file.

        Args:
            bibkey: The citation key
            bibitem_text: The full bibitem text (author, title, etc.)
            save: Whether to save the file

        Returns:
            The modified content
        """
        bib_info = self.get_bibliography_info()

        # Format the bibitem entry
        bibitem = f"\\bibitem{{{bibkey}}} {bibitem_text}\n"

        if bib_info.uses_bibitem and bib_info.bibitem_location:
            # Insert after \begin{thebibliography}
            # Find the end of the begin line
            line_idx = bib_info.bibitem_location - 1
            # Find where to insert (after any existing bibitems or after begin)
            insert_idx = line_idx + 1

            # Find the end of thebibliography
            for i in range(insert_idx, len(self.lines)):
                if "\\end{thebibliography}" in self.lines[i]:
                    # Insert before \end
                    self.lines.insert(i, bibitem)
                    break
            else:
                # No end found, insert at insert_idx
                self.lines.insert(insert_idx, bibitem)

        else:
            # No thebibliography - create one before \end{document}
            end_doc_match = self.END_DOC_PATTERN.search(self.content)
            if end_doc_match:
                end_line = self.content[: end_doc_match.start()].count("\n")

                # Create thebibliography environment
                bib_env = (
                    "\n\\begin{thebibliography}{99}\n"
                    + bibitem
                    + "\\end{thebibliography}\n\n"
                )
                self.lines.insert(end_line, bib_env)
            else:
                # No \end{document}, append at end
                self.lines.append(
                    "\n\\begin{thebibliography}{99}\n"
                    + bibitem
                    + "\\end{thebibliography}\n"
                )

        self.content = "".join(self.lines)

        if save:
            self.file_path.write_text(self.content)

        return self.content


def add_bibtex_entry(bib_file: Path, bibtex: str) -> bool:
    """Add a BibTeX entry to a .bib file.

    Args:
        bib_file: Path to the .bib file
        bibtex: The BibTeX entry to add

    Returns:
        True if successful
    """
    # Check if entry already exists (by checking for bibcode/key)
    key_match = re.search(r"@\w+\{([^,]+),", bibtex)
    if not key_match:
        return False

    key = key_match.group(1)

    if bib_file.exists():
        existing = bib_file.read_text()
        # Check if this key already exists
        if re.search(rf"@\w+\{{\s*{re.escape(key)}\s*,", existing):
            return True  # Already exists

        # Append to file
        with open(bib_file, "a") as f:
            f.write("\n" + bibtex + "\n")
    else:
        # Create new file
        bib_file.write_text(bibtex + "\n")

    return True


def format_bibitem_from_paper(paper) -> str:
    """Format a Paper object as a \\bibitem entry.

    Args:
        paper: Paper object

    Returns:
        Formatted bibitem text (without the \\bibitem{key} part)
    """
    import json

    parts = []

    # Authors
    if paper.authors:
        try:
            authors = json.loads(paper.authors)
            if len(authors) > 3:
                author_str = f"{authors[0]} et al."
            else:
                author_str = ", ".join(authors)
            parts.append(author_str)
        except json.JSONDecodeError:
            pass

    # Year
    if paper.year:
        parts.append(str(paper.year))

    # Title
    if paper.title:
        parts.append(f"``{paper.title}''")

    # Journal info
    journal_parts = []
    if paper.journal:
        journal_parts.append(paper.journal)
    if paper.volume:
        journal_parts.append(paper.volume)
    if paper.pages:
        journal_parts.append(paper.pages)

    if journal_parts:
        parts.append(", ".join(journal_parts))

    return ", ".join(parts) + "."
