"""Vector store using ChromaDB for semantic search over paper abstracts."""

from pathlib import Path
from typing import Optional, Any

from chromadb import Documents, EmbeddingFunction, Embeddings

from src.core.config import settings
from src.db.models import Paper


class OllamaEmbeddingFunction(EmbeddingFunction):
    """Custom embedding function for Ollama."""

    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings for a list of documents."""
        import requests

        embeddings = []
        for text in input:
            try:
                response = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model_name, "prompt": text},
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
            except Exception as e:
                # In production, might want to retry or handle better
                print(f"Ollama embedding failed for text snippet: {e}")
                # Fallback to zero vector or raise? Raising is safer.
                raise ValueError(f"Ollama embedding failed: {e}")
        return embeddings


class GoogleGeminiEmbeddingFunction(EmbeddingFunction):
    """Custom embedding function for Gemini."""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def __call__(self, input: Documents) -> Embeddings:
        """Generate embeddings for a list of documents."""
        client = self._get_client()

        model = "text-embedding-004"

        try:
            result = client.models.embed_content(
                model=model,
                contents=input,
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
             raise ValueError(f"Gemini embedding failed: {e}")


class VectorStore:
    """ChromaDB-based vector store for paper embeddings.

    Uses configured provider (OpenAI, Gemini, Ollama) for generating embeddings.
    Stores embeddings in a persistent ChromaDB database.
    """

    ABSTRACTS_COLLECTION = "abstracts"
    PDF_COLLECTION = "pdf_contents"
    NOTES_COLLECTION = "notes"

    def __init__(self, persist_dir: Optional[Path] = None):
        """Initialize the vector store.

        Args:
            persist_dir: Directory for persistent storage. Defaults to settings.chroma_path.
        """
        self.persist_dir = persist_dir or settings.chroma_path
        self._client = None
        self._abstracts_collection = None
        self._pdf_collection = None
        self._notes_collection = None
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

    def reset_embedding_function(self):
        """Reset the cached embedding function so it picks up new provider settings.

        Call this after changing the embedding provider in settings, before
        re-embedding. Also resets cached collections since they hold a
        reference to the old embedding function.
        """
        self._embedding_function = None
        self._abstracts_collection = None
        self._pdf_collection = None
        self._notes_collection = None

    @property
    def embedding_function(self):
        """Get the embedding function based on configuration."""
        if self._embedding_function is None:
            provider = settings.embedding_provider
            
            if provider == "openai":
                if settings.openai_api_key:
                    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

                    self._embedding_function = OpenAIEmbeddingFunction(
                        api_key=settings.openai_api_key,
                        model_name="text-embedding-3-small",
                    )
                else:
                    # Fallback or error?
                     raise ValueError("OpenAI API key not set for embeddings")

            elif provider == "gemini":
                if settings.gemini_api_key:
                    self._embedding_function = GoogleGeminiEmbeddingFunction(
                        api_key=settings.gemini_api_key,
                        model_name="models/text-embedding-004"
                    )
                else:
                    raise ValueError("Gemini API key not set for embeddings")
            
            elif provider == "ollama":
                self._embedding_function = OllamaEmbeddingFunction(
                    base_url=settings.ollama_base_url,
                    model_name=settings.ollama_embedding_model
                )
            
            else:
                 # Fallback to default embedding function (sentence-transformers)
                from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
                self._embedding_function = DefaultEmbeddingFunction()
                
        return self._embedding_function

    def _get_or_create_collection(self, name: str, description: str):
        """Get or create a collection, handling embedding function conflicts.

        If a collection already exists with a different embedding function,
        delete it and recreate to avoid conflicts. This means re-indexing is needed.
        """
        try:
            # Try to get or create with our current embedding function
            return self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_function,
                metadata={"description": description},
            )
        except ValueError as e:
            # Embedding function conflict - collection exists with different embedding
            if "embedding function" in str(e).lower():
                # Delete the old collection and create fresh with new embedding
                self.client.delete_collection(name=name)
                return self.client.create_collection(
                    name=name,
                    embedding_function=self.embedding_function,
                    metadata={"description": description},
                )
            raise

    @property
    def abstracts_collection(self):
        """Get or create the abstracts collection."""
        if self._abstracts_collection is None:
            self._abstracts_collection = self._get_or_create_collection(
                name=self.ABSTRACTS_COLLECTION,
                description="Paper abstracts for semantic search",
            )
        return self._abstracts_collection

    @property
    def pdf_collection(self):
        """Get or create the PDF contents collection."""
        if self._pdf_collection is None:
            self._pdf_collection = self._get_or_create_collection(
                name=self.PDF_COLLECTION,
                description="PDF full-text content for semantic search",
            )
        return self._pdf_collection

    @property
    def notes_collection(self):
        """Get or create the notes collection."""
        if self._notes_collection is None:
            self._notes_collection = self._get_or_create_collection(
                name=self.NOTES_COLLECTION,
                description="User notes for semantic search",
            )
        return self._notes_collection

    def embed_paper(self, paper: Paper, note_content: Optional[str] = None) -> bool:
        """Embed a paper's abstract into the vector store.

        Args:
            paper: Paper to embed
            note_content: Optional content of user notes to include in embedding

        Returns:
            True if successful, False if no abstract or already embedded
        """
        if not paper.abstract:
            # Even if no abstract, if we have a note or it's my paper, we might want to embed?
            # For now, keep requirement for abstract to ensure quality, but maybe relax later.
            # actually if we have a note, we definitely want to search it.
            # Let's allow embedding if abstract OR note exists.
            if not note_content:
                 return False
        
        # We overwrite existing embedding to update metadata/content
        # So we don't check for existence anymore, we just upsert.

        # Prepare authors string
        authors_str = ""
        import json
        if paper.authors:
            try:
                authors_list = json.loads(paper.authors)
                authors_str = ", ".join(authors_list)
            except:
                pass

        # Prepare document text
        # Format:
        # Title: ...
        # Authors: ...
        # My Paper: Yes/No
        # Abstract: ...
        # Notes: ...
        
        parts = [
            f"Title: {paper.title}",
            f"Authors: {authors_str}" if authors_str else "",
            f"My Paper: {'Yes' if paper.is_my_paper else 'No'}",
            f"Abstract: {paper.abstract[:2500] + '... (truncated)' if paper.abstract and len(paper.abstract) > 2500 else (paper.abstract or '')}",
            f"Notes: {note_content}" if note_content else ""
        ]
        
        doc_text = "\n\n".join([p for p in parts if p])
        
        # Check total length and truncate if needed (especially for Ollama)
        # Author lists can be massive (e.g. LIGO papers), so we truncate the author part
        # in the source string if it's too long, to avoid context limit errors.
        if len(authors_str) > 500:
             authors_truncated = authors_str[:500] + "... (+ many more)"
             parts[1] = f"Authors: {authors_truncated}"
             doc_text = "\n\n".join([p for p in parts if p])

        # Prepare metadata
        # Truncate string fields to satisfy Chroma limits
        metadata = {
            "bibcode": paper.bibcode,
            "title": paper.title[:1000] if paper.title else "",
            "year": paper.year or 0,
            "citation_count": paper.citation_count or 0,
            "first_author": paper.first_author[:100],
            "is_my_paper": paper.is_my_paper,
            "has_note": bool(note_content),
            "authors": authors_str[:1000] if authors_str else "", 
        }

        # Add to collection (upsert)
        try:
            self.abstracts_collection.upsert(
                ids=[paper.bibcode],
                documents=[doc_text],
                metadatas=[metadata],
            )
        except Exception as e:
            # Check for dimension mismatch (InvalidArgumentError from Chroma)
            if "dimension" in str(e).lower() and "expecting" in str(e).lower():
                print(f"Dimension mismatch detected. Clearing abstracts collection to rebuild with current provider.")
                self.client.delete_collection(self.ABSTRACTS_COLLECTION)
                self._abstracts_collection = None # Force re-creation
                
                # Retry once
                self.abstracts_collection.upsert(
                    ids=[paper.bibcode],
                    documents=[doc_text],
                    metadatas=[metadata],
                )
            else:
                raise e

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
            # Truncate abstract if too long to avoid context limit errors (especially for Ollama)
            # 5000 chars is roughly 1000-1500 tokens, which should be safe for most models
            # but let's be conservative with 2500 chars for the combo of title + abstract
            documents = []
            for p in batch:
                abstract = p.abstract or ""
                if len(abstract) > 2500:
                    abstract = abstract[:2500] + "... (truncated)"
                documents.append(f"{p.title}\n\n{abstract}")
            metadatas = [
                {
                    "bibcode": p.bibcode,
                    "title": p.title[:1000] if p.title else "",
                    "year": p.year or 0,
                    "citation_count": p.citation_count or 0,
                    "first_author": p.first_author[:100],
                }
                for p in batch
            ]

            try:
                self.abstracts_collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
                embedded += len(batch)
            except Exception as e:
                if "dimension" in str(e).lower() and "expecting" in str(e).lower():
                    print("Dimension mismatch detected. Clearing abstracts collection to rebuild with current provider.")
                    self.client.delete_collection(self.ABSTRACTS_COLLECTION)
                    self._abstracts_collection = None

                    # Retry once
                    self.abstracts_collection.add(
                        ids=ids,
                        documents=documents,
                        metadatas=metadatas,
                    )
                    embedded += len(batch)
                else:
                    # Batch failed — fall back to embedding one paper at a time
                    # so a single bad paper doesn't block the rest.
                    for j, paper in enumerate(batch):
                        try:
                            self.abstracts_collection.add(
                                ids=[ids[j]],
                                documents=[documents[j]],
                                metadatas=[metadatas[j]],
                            )
                            embedded += 1
                        except Exception as inner_e:
                            print(f"Skipping {paper.bibcode}: {inner_e}")

        return embedded

    def search(
        self,
        query: str,
        n_results: int = 10,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        min_citations: Optional[int] = None,
    ) -> list[dict]:
        """Search for papers by semantic similarity.

        Args:
            query: Search query text
            n_results: Maximum number of results to return
            min_year: Optional minimum publication year filter
            max_year: Optional maximum publication year filter
            min_citations: Optional minimum citation count filter

        Returns:
            List of dicts with bibcode, distance, and metadata
        """
        # Build where clause for filtering
        where = None
        where_clauses = []

        if min_year:
            where_clauses.append({"year": {"$gte": min_year}})
        if max_year:
            where_clauses.append({"year": {"$lte": max_year}})
        if min_citations:
            where_clauses.append({"citation_count": {"$gte": min_citations}})

        if len(where_clauses) == 1:
            where = where_clauses[0]
        elif len(where_clauses) > 1:
            where = {"$and": where_clauses}

        # Query the collection
        try:
            results = self.abstracts_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            if "dimension" in str(e).lower() and "expecting" in str(e).lower():
                print("Embedding dimension mismatch. Run 'search-ads db embed --force' to rebuild.")
                return []
            raise

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
        try:
            self.pdf_collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as e:
             if "dimension" in str(e).lower() and "expecting" in str(e).lower():
                print(f"Dimension mismatch detected. Clearing PDF collection to rebuild.")
                self.client.delete_collection(self.PDF_COLLECTION)
                self._pdf_collection = None
                
                # Retry once
                self.pdf_collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
             else:
                raise e

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
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        min_citations: Optional[int] = None,
    ) -> list[dict]:
        """Search PDF contents by semantic similarity.

        Args:
            query: Search query text
            n_results: Maximum number of results to return
            bibcode: Optional filter to specific paper
            min_year: Optional minimum publication year filter
            max_year: Optional maximum publication year filter
            min_citations: Optional minimum citation count filter

        Returns:
            List of dicts with bibcode, chunk_index, distance, and document
        """
        where = {"bibcode": bibcode} if bibcode else None

        try:
            results = self.pdf_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            if "dimension" in str(e).lower() and "expecting" in str(e).lower():
                print("Embedding dimension mismatch. Run 'search-ads db embed --force' to rebuild.")
                return []
            raise

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

    # Note embedding methods

    def embed_note(self, note) -> bool:
        """Embed a note into the vector store.

        Args:
            note: Note object to embed

        Returns:
            True if successful
        """
        # Use bibcode as ID since we have one note per paper
        note_id = f"note_{note.bibcode}"

        # Remove existing embedding for this note
        existing = self.notes_collection.get(ids=[note_id])
        if existing["ids"]:
            self.notes_collection.delete(ids=[note_id])

        # Prepare metadata
        metadata = {
            "bibcode": note.bibcode,
            "note_id": note.id,
        }

        # Add to collection
        try:
            self.notes_collection.add(
                ids=[note_id],
                documents=[note.content],
                metadatas=[metadata],
            )
        except Exception as e:
             if "dimension" in str(e).lower() and "expecting" in str(e).lower():
                print(f"Dimension mismatch detected. Clearing notes collection to rebuild.")
                self.client.delete_collection(self.NOTES_COLLECTION)
                self._notes_collection = None
                
                # Retry once
                self.notes_collection.add(
                    ids=[note_id],
                    documents=[note.content],
                    metadatas=[metadata],
                )
             else:
                raise e

        return True

    def search_notes(
        self,
        query: str,
        n_results: int = 10,
    ) -> list[dict]:
        """Search notes by semantic similarity.

        Args:
            query: Search query text
            n_results: Maximum number of results to return

        Returns:
            List of dicts with bibcode, distance, and content
        """
        try:
            results = self.notes_collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            if "dimension" in str(e).lower() and "expecting" in str(e).lower():
                print("Embedding dimension mismatch. Run 'search-ads db embed --force' to rebuild.")
                return []
            raise

        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, note_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                formatted.append(
                    {
                        "note_id": note_id,
                        "bibcode": metadata.get("bibcode", ""),
                        "distance": results["distances"][0][i] if results["distances"] else None,
                        "content": results["documents"][0][i] if results["documents"] else "",
                    }
                )

        return formatted

    def delete_note(self, bibcode: str) -> bool:
        """Remove a note from the vector store.

        Args:
            bibcode: Paper bibcode

        Returns:
            True if deleted, False if not found
        """
        note_id = f"note_{bibcode}"
        existing = self.notes_collection.get(ids=[note_id])
        if existing["ids"]:
            self.notes_collection.delete(ids=[note_id])
            return True
        return False

    def notes_count(self) -> int:
        """Get the number of embedded notes."""
        return self.notes_collection.count()

    def is_note_embedded(self, bibcode: str) -> bool:
        """Check if a note is already embedded."""
        note_id = f"note_{bibcode}"
        existing = self.notes_collection.get(ids=[note_id])
        return bool(existing["ids"])

    def clear_notes(self) -> int:
        """Clear all note embeddings.

        Returns:
            Number of notes deleted
        """
        count = self.notes_count()
        if count > 0:
            self.client.delete_collection(self.NOTES_COLLECTION)
            self._notes_collection = None
        return count


# Global vector store instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
