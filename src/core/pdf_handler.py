"""PDF download and parsing utilities."""

import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from src.core.config import settings
from src.db.models import Paper


class PDFDownloadError(Exception):
    """Raised when PDF download fails."""

    pass


class PDFParseError(Exception):
    """Raised when PDF parsing fails."""

    pass


class PDFHandler:
    """Handler for downloading and parsing PDFs."""

    # User agent to avoid being blocked
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, pdf_dir: Optional[Path] = None):
        """Initialize the PDF handler.

        Args:
            pdf_dir: Directory to store downloaded PDFs. Defaults to settings.pdfs_path.
        """
        self.pdf_dir = pdf_dir or settings.pdfs_path
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def get_pdf_path(self, bibcode: str) -> Path:
        """Get the local path for a paper's PDF.

        Args:
            bibcode: Paper bibcode

        Returns:
            Path to the PDF file
        """
        # Sanitize bibcode for filename (replace special chars)
        safe_name = re.sub(r"[^\w\-.]", "_", bibcode)
        return self.pdf_dir / f"{safe_name}.pdf"

    def is_downloaded(self, bibcode: str) -> bool:
        """Check if a PDF is already downloaded.

        Args:
            bibcode: Paper bibcode

        Returns:
            True if PDF exists locally
        """
        return self.get_pdf_path(bibcode).exists()

    def download(self, paper: Paper, force: bool = False) -> Path:
        """Download a paper's PDF.

        Args:
            paper: Paper object with pdf_url
            force: Re-download even if already exists

        Returns:
            Path to the downloaded PDF

        Raises:
            PDFDownloadError: If download fails
        """
        pdf_path = self.get_pdf_path(paper.bibcode)

        if pdf_path.exists() and not force:
            return pdf_path

        if not paper.pdf_url:
            raise PDFDownloadError(f"No PDF URL available for {paper.bibcode}")

        # Strategy: Try primary URL (ADS/Journal) first, then fallback to arXiv if available
        # We construct the ADS Link Gateway URL dynamically to ensure we always try the journal first,
        # even if the stored paper.pdf_url points to arXiv (legacy data).
        ads_url = f"https://ui.adsabs.harvard.edu/link_gateway/{paper.bibcode}/PUB_PDF"
        
        urls_to_try = [(ads_url, "Journal/ADS")]
        
        # Add stored URL if it's different (e.g. might be a direct link we found before)
        if paper.pdf_url and paper.pdf_url != ads_url and "arxiv.org" not in paper.pdf_url:
             urls_to_try.append((paper.pdf_url, "Stored URL"))

        if paper.arxiv_id:
            urls_to_try.append((f"https://arxiv.org/pdf/{paper.arxiv_id}.pdf", "arXiv"))

        headers = {"User-Agent": self.USER_AGENT}
        last_error = None

        for url, source in urls_to_try:
            # Handle arXiv URLs - ensure we get the PDF
            if "arxiv.org" in url and not url.endswith(".pdf"):
                # Convert abstract URL to PDF URL
                if "/abs/" in url:
                    url = url.replace("/abs/", "/pdf/") + ".pdf"
                elif not url.endswith(".pdf"):
                    url = url + ".pdf"

            try:
                print(f"Attempting download from {source}: {url}")
                response = requests.get(url, headers=headers, timeout=60, stream=True)
                response.raise_for_status()

                # Check if we got a PDF
                content_type = response.headers.get("Content-Type", "").lower()
                if "pdf" not in content_type and not url.endswith(".pdf"):
                    # This happens with paywalls (returns HTML)
                    msg = f"{source} returned non-PDF content ({content_type})"
                    print(msg)
                    last_error = msg
                    continue

                # Save the PDF to a temporary path first
                temp_path = pdf_path.with_suffix(".tmp")
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Verify it's a valid PDF
                if temp_path.stat().st_size < 1000:
                    temp_path.unlink()
                    last_error = "Downloaded file too small"
                    continue

                # Quick check for PDF magic bytes
                with open(temp_path, "rb") as f:
                    header = f.read(8)
                    if not header.startswith(b"%PDF"):
                        temp_path.unlink()
                        last_error = "Downloaded file is not a valid PDF header"
                        continue

                # Success! Rename to final path
                temp_path.rename(pdf_path)
                return pdf_path

            except Exception as e:
                last_error = str(e)
                print(f"Failed to download from {source}: {e}")
                continue

        # If we get here, all attempts failed
        if pdf_path.exists():
            pdf_path.unlink()
            
        raise PDFDownloadError(f"Failed to download PDF. Last error: {last_error}")

    def parse(self, pdf_path: Path) -> str:
        """Extract text from a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text content

        Raises:
            PDFParseError: If parsing fails
        """
        if not pdf_path.exists():
            raise PDFParseError(f"PDF file not found: {pdf_path}")

        try:
            import fitz  # PyMuPDF

            text_parts = []

            with fitz.open(pdf_path) as doc:
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    if text.strip():
                        text_parts.append(text)

            if not text_parts:
                raise PDFParseError("No text extracted from PDF")

            full_text = "\n\n".join(text_parts)

            # Clean up the text
            full_text = self._clean_text(full_text)

            return full_text

        except ImportError:
            raise PDFParseError("PyMuPDF (fitz) not installed. Run: pip install pymupdf")
        except Exception as e:
            raise PDFParseError(f"Failed to parse PDF: {e}")

    def _clean_text(self, text: str) -> str:
        """Clean extracted PDF text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        # Remove page headers/footers patterns (common in papers)
        # These are heuristic and may need adjustment
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Skip likely page numbers
            if re.match(r"^\s*\d+\s*$", line):
                continue
            # Skip very short lines that are likely headers
            if len(line.strip()) < 3:
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def download_and_parse(self, paper: Paper, force: bool = False) -> tuple[Path, str]:
        """Download and parse a paper's PDF in one step.

        Args:
            paper: Paper object
            force: Re-download even if exists

        Returns:
            Tuple of (pdf_path, extracted_text)
        """
        pdf_path = self.download(paper, force=force)
        text = self.parse(pdf_path)
        return pdf_path, text

    def delete(self, bibcode: str) -> bool:
        """Delete a downloaded PDF.

        Args:
            bibcode: Paper bibcode

        Returns:
            True if deleted, False if not found
        """
        pdf_path = self.get_pdf_path(bibcode)
        if pdf_path.exists():
            pdf_path.unlink()
            return True
        return False

    def get_storage_stats(self) -> dict:
        """Get statistics about PDF storage.

        Returns:
            Dict with count and total_size_mb
        """
        pdfs = list(self.pdf_dir.glob("*.pdf"))
        total_size = sum(p.stat().st_size for p in pdfs)

        return {
            "count": len(pdfs),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
