"""
Codebase RAG (Retrieval-Augmented Generation)

Uses Nova Multimodal Embeddings for semantic search across the codebase.
Supports text, code, and image queries in a unified embedding space.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.agents.pillar3.indexer import CodeChunk, CodebaseIndexer
from src.core.bedrock_client import BedrockClient, get_bedrock_client
from src.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from RAG retrieval."""
    chunk: CodeChunk
    score: float
    context: str


class CodebaseRAG:
    """
    RAG system for codebase intelligence.
    
    Uses Nova Multimodal Embeddings to enable:
    - Semantic code search
    - Cross-modal queries (text to code, image to code)
    - Context-aware code understanding
    """
    
    def __init__(
        self,
        indexer: Optional[CodebaseIndexer] = None,
        bedrock_client: Optional[BedrockClient] = None,
        top_k: int = None,
    ):
        """
        Initialize the RAG system.
        
        Args:
            indexer: Codebase indexer with embedded chunks
            bedrock_client: Bedrock client for embeddings
            top_k: Number of results to retrieve
        """
        self.indexer = indexer or CodebaseIndexer()
        self.bedrock_client = bedrock_client or get_bedrock_client()
        self.top_k = top_k or settings.top_k_results
        
        # Vector store (using numpy for simplicity)
        # In production, use FAISS or a vector database
        self._embeddings: Optional[np.ndarray] = None
        self._chunk_ids: List[str] = []
        
        logger.info("CodebaseRAG initialized")
    
    def build_index(self) -> None:
        """Build the vector index from indexed chunks."""
        chunks = self.indexer.get_chunks()
        
        if not chunks:
            logger.warning("No chunks to index")
            return
        
        # Filter chunks with embeddings
        valid_chunks = [c for c in chunks if c.embedding]
        
        if not valid_chunks:
            logger.warning("No chunks with embeddings")
            return
        
        # Build embedding matrix
        embeddings = [c.embedding for c in valid_chunks]
        self._embeddings = np.array(embeddings)
        self._chunk_ids = [str(c.id) for c in valid_chunks]
        
        # Normalize for cosine similarity
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        self._embeddings = self._embeddings / (norms + 1e-10)
        
        logger.info(f"Built index with {len(valid_chunks)} vectors")
    
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_type: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant code chunks for a query.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            filter_type: Filter by chunk type (code, documentation, image)
            
        Returns:
            List of retrieval results with scores
        """
        if self._embeddings is None or len(self._embeddings) == 0:
            logger.warning("Index not built, returning empty results")
            return []
        
        k = top_k or self.top_k
        
        # Generate query embedding
        query_embedding = await self._embed_query(query)
        if not query_embedding:
            return []
        
        # Normalize query embedding
        query_vec = np.array(query_embedding)
        query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        
        # Compute cosine similarity
        similarities = np.dot(self._embeddings, query_vec)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:k * 2]  # Get extra for filtering
        
        # Build results
        results = []
        chunks = self.indexer.get_chunks()
        chunk_map = {str(c.id): c for c in chunks}
        
        for idx in top_indices:
            if len(results) >= k:
                break
            
            chunk_id = self._chunk_ids[idx]
            chunk = chunk_map.get(chunk_id)
            
            if not chunk:
                continue
            
            # Apply type filter
            if filter_type and chunk.chunk_type != filter_type:
                continue
            
            score = float(similarities[idx])
            context = self._build_context(chunk)
            
            results.append(RetrievalResult(
                chunk=chunk,
                score=score,
                context=context,
            ))
        
        return results
    
    async def retrieve_with_image(
        self,
        image_bytes: bytes,
        top_k: Optional[int] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve code chunks relevant to an image query.
        
        This enables queries like "What code relates to this error screenshot?"
        """
        if self._embeddings is None:
            return []
        
        k = top_k or self.top_k
        
        # Generate image embedding
        try:
            embeddings = await self.bedrock_client.generate_embeddings(
                inputs=image_bytes,
                input_type="image",
            )
            image_embedding = embeddings[0] if embeddings else None
        except Exception as e:
            logger.error(f"Failed to embed image: {e}")
            return []
        
        if not image_embedding:
            return []
        
        # Normalize
        image_vec = np.array(image_embedding)
        image_vec = image_vec / (np.linalg.norm(image_vec) + 1e-10)
        
        # Compute similarity
        similarities = np.dot(self._embeddings, image_vec)
        top_indices = np.argsort(similarities)[::-1][:k]
        
        # Build results
        results = []
        chunks = self.indexer.get_chunks()
        chunk_map = {str(c.id): c for c in chunks}
        
        for idx in top_indices:
            chunk_id = self._chunk_ids[idx]
            chunk = chunk_map.get(chunk_id)
            
            if chunk:
                results.append(RetrievalResult(
                    chunk=chunk,
                    score=float(similarities[idx]),
                    context=self._build_context(chunk),
                ))
        
        return results
    
    async def retrieve_for_file(
        self,
        file_path: str,
        query: str,
    ) -> List[RetrievalResult]:
        """Retrieve chunks from a specific file relevant to a query."""
        # Get chunks for the file
        file_chunks = self.indexer.get_chunks_for_file(file_path)
        
        if not file_chunks:
            return []
        
        # Generate query embedding
        query_embedding = await self._embed_query(query)
        if not query_embedding:
            return []
        
        query_vec = np.array(query_embedding)
        query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        
        # Score each chunk
        results = []
        for chunk in file_chunks:
            if not chunk.embedding:
                continue
            
            chunk_vec = np.array(chunk.embedding)
            chunk_vec = chunk_vec / (np.linalg.norm(chunk_vec) + 1e-10)
            
            score = float(np.dot(query_vec, chunk_vec))
            
            results.append(RetrievalResult(
                chunk=chunk,
                score=score,
                context=self._build_context(chunk),
            ))
        
        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        
        return results[:self.top_k]
    
    async def _embed_query(self, query: str) -> Optional[List[float]]:
        """Generate embedding for a query."""
        try:
            embeddings = await self.bedrock_client.generate_embeddings(
                inputs=query,
                input_type="text",
            )
            return embeddings[0] if embeddings else None
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return None
    
    def _build_context(self, chunk: CodeChunk) -> str:
        """Build context string for a chunk."""
        context_parts = [
            f"File: {chunk.file_path}",
        ]
        
        if chunk.start_line and chunk.end_line:
            context_parts.append(f"Lines: {chunk.start_line}-{chunk.end_line}")
        
        if chunk.language:
            context_parts.append(f"Language: {chunk.language}")
        
        context_parts.append(f"Type: {chunk.chunk_type}")
        context_parts.append("")
        context_parts.append(chunk.content)
        
        return "\n".join(context_parts)
    
    def format_context_for_prompt(
        self,
        results: List[RetrievalResult],
        max_tokens: int = 4000,
    ) -> str:
        """
        Format retrieval results for inclusion in a prompt.
        
        Args:
            results: Retrieval results
            max_tokens: Maximum tokens for context
            
        Returns:
            Formatted context string
        """
        if not results:
            return "No relevant code found in the codebase."
        
        context_parts = ["## Relevant Code from Codebase\n"]
        current_length = 0
        
        for i, result in enumerate(results, 1):
            chunk_context = f"""
### Result {i} (Relevance: {result.score:.2f})
**File:** `{result.chunk.file_path}`
**Lines:** {result.chunk.start_line}-{result.chunk.end_line}
**Type:** {result.chunk.chunk_type}

```{result.chunk.language}
{result.chunk.content}
```
"""
            # Rough token estimate (4 chars per token)
            chunk_tokens = len(chunk_context) // 4
            
            if current_length + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_context)
            current_length += chunk_tokens
        
        return "\n".join(context_parts)
    
    def get_file_summary(self, file_path: str) -> Dict[str, Any]:
        """Get a summary of a file's indexed content."""
        chunks = self.indexer.get_chunks_for_file(file_path)
        
        if not chunks:
            return {"file": file_path, "indexed": False}
        
        return {
            "file": file_path,
            "indexed": True,
            "chunks": len(chunks),
            "lines": max(c.end_line for c in chunks if c.end_line) if chunks else 0,
            "types": list(set(c.chunk_type for c in chunks)),
            "language": chunks[0].language if chunks else "unknown",
        }
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        chunks = self.indexer.get_chunks()
        
        if not chunks:
            return {"indexed": False, "chunks": 0}
        
        # Count by type
        type_counts = {}
        language_counts = {}
        
        for chunk in chunks:
            type_counts[chunk.chunk_type] = type_counts.get(chunk.chunk_type, 0) + 1
            if chunk.language:
                language_counts[chunk.language] = language_counts.get(chunk.language, 0) + 1
        
        return {
            "indexed": True,
            "total_chunks": len(chunks),
            "chunks_with_embeddings": len([c for c in chunks if c.embedding]),
            "files": len(set(c.file_path for c in chunks)),
            "by_type": type_counts,
            "by_language": language_counts,
        }
