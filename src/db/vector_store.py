"""Vector store using ChromaDB for semantic search over paper abstracts."""

from pathlib import Path
from typing import Optional

from src.core.config import settings
from src.db.models import Paper


class VectorStore:
    """ChromaDB-based vector store for paper embeddings.

    Uses OpenAI's text-embedding-3-small model for generating embeddings.
    Stores embeddings in a persistent ChromaDB database.
    """

    ABSTRACTS_COLLECTION = "abstracts"
    PDF_COLLECTION = "pdf_contents"

    def __init__(self, persist_dir: Optional[Path] = None):
        """Initialize the vector store.

        Args:
            persist_dir: Directory for persistent storage. Defaults to settings.chroma_path.
        """
        self.persist_dir = persist_dir or settings.chroma_path
        self._client = None
        self._abstracts_collection = None
        self._pdf_collection = None
        self._embedding_function = None

    @property
    def client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.persist_dir.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    @property
    def embedding_function(self):
        """Get the embedding function (OpenAI or fallback)."""
        if self._embedding_function is None:
            if settings.openai_api_key:
                from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

                self._embedding_function = OpenAIEmbeddingFunction(
                    api_key=settings.openai_api_key,
                    model_name="text-embedding-3-small",
                )
            else:
                # Fallback to default embedding function (sentence-transformers)
                from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

                self._embedding_function = DefaultEmbeddingFunction()
        return self._embedding_function

    @property
    def abstracts_collection(self):
        """Get or create the abstracts collection."""
        if self._abstracts_collection is None:
            self._abstracts_collection = self.client.get_or_create_collection(
                name=self.ABSTRACTS_COLLECTION,
                embedding_function=self.embedding_function,
                metadata={"description": "Paper abstracts for semantic search"},
            )
        return self._abstracts_collection

    @property
    def pdf_collection(self):
        """Get or create the PDF contents collection."""
        if self._pdf_collection is None:
            self._pdf_collection = self.client.get_or_create_collection(
                name=self.PDF_COLLECTION,
                embedding_function=self.embedding_function,
                metadata={"description": "PDF full-text content for semantic search"},
            )
        return self._pdf_collection

    def embed_paper(self, paper: Paper) -> bool:
        """Embed a paper's abstract into the vector store.

        Args:
            paper: Paper to embed

        Returns:
            True if successful, False if no abstract or already embedded
        """
        if not paper.abstract:
            return False

        # Check if already embedded
        existing = self.abstracts_collection.get(ids=[paper.bibcode])
        if existing["ids"]:
            return True  # Already embedded

        # Prepare document text (title + abstract for better context)
        doc_text = f"{paper.title}\n\n{paper.abstract}"

        # Prepare metadata
        metadata = {
            "bibcode": paper.bibcode,
            "title": paper.title,
            "year": paper.year or 0,
            "citation_count": paper.citation_count or 0,
            "first_author": paper.first_author,
        }

        # Add to collection
        self.abstracts_collection.add(
            ids=[paper.bibcode],
            documents=[doc_text],
            metadatas=[metadata],
        )

        return True

    def embed_papers(self, papers: list[Paper], batch_size: int = 100) -> int:
        """Embed multiple papers in batches.

        Args:
            papers: List of papers to embed
            batch_size: Number of papers to embed at once

        Returns:
            Number of papers successfully embedded
        """
        embedded = 0

        # Filter papers with abstracts and not already embedded
        papers_to_embed = []
        for paper in papers:
            if paper.abstract:
                existing = self.abstracts_collection.get(ids=[paper.bibcode])
                if not existing["ids"]:
                    papers_to_embed.append(paper)

        # Process in batches
        for i in range(0, len(papers_to_embed), batch_size):
            batch = papers_to_embed[i : i + batch_size]

            ids = [p.bibcode for p in batch]
            documents = [f"{p.title}\n\n{p.abstract}" for p in batch]
            metadatas = [
                {
                    "bibcode": p.bibcode,
                    "title": p.title,
                    "year": p.year or 0,
                    "citation_count": p.citation_count or 0,
                    "first_author": p.first_author,
                }
                for p in batch
            ]

            self.abstracts_collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

            embedded += len(batch)

        return embedded

    def search(
        self,
        query: str,
        n_results: int = 10,
        min_year: Optional[int] = None,
        min_citations: Optional[int] = None,
    ) -> list[dict]:
        """Search for papers by semantic similarity.

        Args:
            query: Search query text
            n_results: Maximum number of results to return
            min_year: Optional minimum publication year filter
            min_citations: Optional minimum citation count filter

        Returns:
            List of dicts with bibcode, distance, and metadata
        """
        # Build where clause for filtering
        where = None
        where_clauses = []

        if min_year:
            where_clauses.append({"year": {"$gte": min_year}})
        if min_citations:
            where_clauses.append({"citation_count": {"$gte": min_citations}})

        if len(where_clauses) == 1:
            where = where_clauses[0]
        elif len(where_clauses) > 1:
            where = {"$and": where_clauses}

        # Query the collection
        results = self.abstracts_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, bibcode in enumerate(results["ids"][0]):
                formatted.append(
                    {
                        "bibcode": bibcode,
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "document": results["documents"][0][i] if results["documents"] else "",
                    }
                )

        return formatted

    def delete_paper(self, bibcode: str) -> bool:
        """Remove a paper from the vector store.

        Args:
            bibcode: Paper bibcode to remove

        Returns:
            True if deleted, False if not found
        """
        existing = self.abstracts_collection.get(ids=[bibcode])
        if existing["ids"]:
            self.abstracts_collection.delete(ids=[bibcode])
            return True
        return False

    def count(self) -> int:
        """Get the number of embedded papers."""
        return self.abstracts_collection.count()

    def is_embedded(self, bibcode: str) -> bool:
        """Check if a paper is already embedded."""
        existing = self.abstracts_collection.get(ids=[bibcode])
        return bool(existing["ids"])

    def clear(self) -> int:
        """Clear all embeddings from the abstracts collection.

        Returns:
            Number of items deleted
        """
        count = self.count()
        self.client.delete_collection(self.ABSTRACTS_COLLECTION)
        self._abstracts_collection = None  # Force recreation
        return count

    # PDF embedding methods

    def embed_pdf(
        self,
        bibcode: str,
        pdf_text: str,
        title: str = "",
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
    ) -> int:
        """Embed PDF content into the vector store.

        Splits the PDF text into chunks for better retrieval.

        Args:
            bibcode: Paper bibcode
            pdf_text: Extracted PDF text
            title: Paper title (prepended to chunks for context)
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks

        Returns:
            Number of chunks embedded
        """
        # Remove existing chunks for this paper
        self.delete_pdf(bibcode)

        # Split into chunks
        chunks = self._split_text(pdf_text, chunk_size, chunk_overlap)

        if not chunks:
            return 0

        # Prepare data for embedding
        ids = [f"{bibcode}_chunk_{i}" for i in range(len(chunks))]
        documents = [f"{title}\n\n{chunk}" if title else chunk for chunk in chunks]
        metadatas = [
            {
                "bibcode": bibcode,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        # Add to collection
        self.pdf_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        return len(chunks)

    def _split_text(
        self, text: str, chunk_size: int, overlap: int
    ) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to split
            chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end (.!?) followed by space
                for i in range(end, max(start + chunk_size // 2, start), -1):
                    if text[i - 1] in ".!?" and (i >= len(text) or text[i].isspace()):
                        end = i
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    def search_pdf(
        self,
        query: str,
        n_results: int = 10,
        bibcode: Optional[str] = None,
    ) -> list[dict]:
        """Search PDF contents by semantic similarity.

        Args:
            query: Search query text
            n_results: Maximum number of results to return
            bibcode: Optional filter to specific paper

        Returns:
            List of dicts with bibcode, chunk_index, distance, and document
        """
        where = {"bibcode": bibcode} if bibcode else None

        results = self.pdf_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                formatted.append(
                    {
                        "chunk_id": chunk_id,
                        "bibcode": metadata.get("bibcode", ""),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "document": results["documents"][0][i] if results["documents"] else "",
                    }
                )

        return formatted

    def delete_pdf(self, bibcode: str) -> int:
        """Remove all PDF chunks for a paper.

        Args:
            bibcode: Paper bibcode

        Returns:
            Number of chunks deleted
        """
        # Find all chunks for this bibcode
        results = self.pdf_collection.get(
            where={"bibcode": bibcode},
            include=[],
        )

        if results["ids"]:
            self.pdf_collection.delete(ids=results["ids"])
            return len(results["ids"])

        return 0

    def pdf_count(self) -> int:
        """Get the total number of PDF chunks embedded."""
        return self.pdf_collection.count()

    def pdf_paper_count(self) -> int:
        """Get the number of unique papers with embedded PDFs."""
        # Get all unique bibcodes
        results = self.pdf_collection.get(include=["metadatas"])
        if not results["metadatas"]:
            return 0

        bibcodes = set(m.get("bibcode") for m in results["metadatas"] if m)
        return len(bibcodes)

    def is_pdf_embedded(self, bibcode: str) -> bool:
        """Check if a paper's PDF is embedded."""
        results = self.pdf_collection.get(
            where={"bibcode": bibcode},
            limit=1,
            include=[],
        )
        return bool(results["ids"])

    def clear_pdfs(self) -> int:
        """Clear all PDF embeddings.

        Returns:
            Number of chunks deleted
        """
        count = self.pdf_count()
        if count > 0:
            self.client.delete_collection(self.PDF_COLLECTION)
            self._pdf_collection = None
        return count


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
