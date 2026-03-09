"""
Nova Multimodal Embeddings

Implements multimodal embeddings using Amazon Nova Multimodal Embeddings.
Supports text, images, and code in a unified embedding space.

This is a key differentiator for Pillar 3 (Codebase Intelligence):
- Index code files, README images, architecture diagrams together
- Answer questions that span multiple modalities
- Understand visual documentation alongside code
"""

import asyncio
import base64
import hashlib
import json
import logging
import mimetypes
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

import boto3
from botocore.config import Config

from src.core.config import settings

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """Types of content that can be embedded."""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    DOCUMENT = "document"


class ImageFormat(str, Enum):
    """Supported image formats."""
    PNG = "png"
    JPEG = "jpeg"
    GIF = "gif"
    WEBP = "webp"
    SVG = "svg"


@dataclass
class EmbeddingInput:
    """Input for embedding generation."""
    content: Union[str, bytes]
    content_type: ContentType
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For code
    language: Optional[str] = None
    file_path: Optional[str] = None
    
    # For images
    image_format: Optional[ImageFormat] = None
    alt_text: Optional[str] = None


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embedding: List[float]
    content_hash: str
    content_type: ContentType
    dimension: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SimilarityResult:
    """Result of similarity search."""
    content_hash: str
    score: float
    content_type: ContentType
    metadata: Dict[str, Any] = field(default_factory=dict)


class NovaMultimodalEmbeddings:
    """
    Client for Amazon Nova Multimodal Embeddings.
    
    Generates embeddings for:
    - Text content (documentation, comments)
    - Code files (any programming language)
    - Images (architecture diagrams, screenshots)
    - Documents (PDFs, markdown)
    
    All content types are embedded in the same vector space,
    enabling cross-modal similarity search.
    """
    
    def __init__(
        self,
        region: Optional[str] = None,
        model_id: Optional[str] = None,
    ):
        self.region = region or settings.aws_region
        self.model_id = model_id or settings.nova_embeddings_model_id
        
        # Configure AWS client
        config = Config(
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        self._client = boto3.client("bedrock-runtime", config=config)
        
        # Embedding dimension
        self.dimension = settings.embedding_dimension
        
        logger.info(f"NovaMultimodalEmbeddings initialized with model: {self.model_id}")
    
    def _compute_hash(self, content: Union[str, bytes]) -> str:
        """Compute content hash for deduplication."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()[:16]
    
    async def embed_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingResult:
        """
        Generate embedding for text content.
        
        Args:
            text: Text to embed
            metadata: Optional metadata
            
        Returns:
            EmbeddingResult with vector
        """
        return await self._embed(
            EmbeddingInput(
                content=text,
                content_type=ContentType.TEXT,
                metadata=metadata or {},
            )
        )
    
    async def embed_code(
        self,
        code: str,
        language: str,
        file_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingResult:
        """
        Generate embedding for code content.
        
        Args:
            code: Code content
            language: Programming language
            file_path: Optional file path
            metadata: Optional metadata
            
        Returns:
            EmbeddingResult with vector
        """
        # Enhance code with language context
        enhanced_content = f"```{language}\n{code}\n```"
        
        return await self._embed(
            EmbeddingInput(
                content=enhanced_content,
                content_type=ContentType.CODE,
                language=language,
                file_path=file_path,
                metadata=metadata or {},
            )
        )
    
    async def embed_image(
        self,
        image_data: bytes,
        image_format: ImageFormat,
        alt_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingResult:
        """
        Generate embedding for image content.
        
        Args:
            image_data: Raw image bytes
            image_format: Image format
            alt_text: Optional alt text description
            metadata: Optional metadata
            
        Returns:
            EmbeddingResult with vector
        """
        return await self._embed(
            EmbeddingInput(
                content=image_data,
                content_type=ContentType.IMAGE,
                image_format=image_format,
                alt_text=alt_text,
                metadata=metadata or {},
            )
        )
    
    async def embed_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingResult:
        """
        Generate embedding for a file.
        
        Automatically detects content type from file extension.
        
        Args:
            file_path: Path to file
            metadata: Optional metadata
            
        Returns:
            EmbeddingResult with vector
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Detect content type
        mime_type, _ = mimetypes.guess_type(file_path)
        extension = path.suffix.lower()
        
        # Read file content
        if mime_type and mime_type.startswith("image/"):
            # Image file
            with open(file_path, "rb") as f:
                content = f.read()
            
            format_map = {
                ".png": ImageFormat.PNG,
                ".jpg": ImageFormat.JPEG,
                ".jpeg": ImageFormat.JPEG,
                ".gif": ImageFormat.GIF,
                ".webp": ImageFormat.WEBP,
                ".svg": ImageFormat.SVG,
            }
            image_format = format_map.get(extension, ImageFormat.PNG)
            
            return await self.embed_image(
                image_data=content,
                image_format=image_format,
                metadata={**(metadata or {}), "file_path": file_path},
            )
        else:
            # Text/code file
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            # Detect language from extension
            language_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".jsx": "javascript",
                ".tsx": "typescript",
                ".java": "java",
                ".go": "go",
                ".rs": "rust",
                ".cpp": "cpp",
                ".c": "c",
                ".h": "c",
                ".hpp": "cpp",
                ".rb": "ruby",
                ".php": "php",
                ".swift": "swift",
                ".kt": "kotlin",
                ".scala": "scala",
                ".cs": "csharp",
                ".md": "markdown",
                ".json": "json",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".toml": "toml",
                ".xml": "xml",
                ".html": "html",
                ".css": "css",
                ".sql": "sql",
                ".sh": "bash",
                ".bash": "bash",
            }
            
            language = language_map.get(extension)
            
            if language:
                return await self.embed_code(
                    code=content,
                    language=language,
                    file_path=file_path,
                    metadata=metadata,
                )
            else:
                return await self.embed_text(
                    text=content,
                    metadata={**(metadata or {}), "file_path": file_path},
                )
    
    async def _embed(self, input_data: EmbeddingInput) -> EmbeddingResult:
        """
        Generate embedding using Nova Multimodal Embeddings.
        
        Args:
            input_data: Input to embed
            
        Returns:
            EmbeddingResult with vector
        """
        try:
            # Build request based on content type
            if input_data.content_type == ContentType.IMAGE:
                # Image embedding
                request_body = self._build_image_request(input_data)
            else:
                # Text/code embedding
                request_body = self._build_text_request(input_data)
            
            # Call Nova Multimodal Embeddings
            response = await asyncio.to_thread(
                self._client.invoke_model,
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            embedding = response_body.get("embedding", [])
            
            # Compute content hash
            if isinstance(input_data.content, bytes):
                content_hash = self._compute_hash(input_data.content)
            else:
                content_hash = self._compute_hash(input_data.content)
            
            return EmbeddingResult(
                embedding=embedding,
                content_hash=content_hash,
                content_type=input_data.content_type,
                dimension=len(embedding),
                metadata={
                    **input_data.metadata,
                    "language": input_data.language,
                    "file_path": input_data.file_path,
                    "image_format": input_data.image_format.value if input_data.image_format else None,
                },
            )
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def _build_text_request(self, input_data: EmbeddingInput) -> Dict[str, Any]:
        """Build request for text/code embedding."""
        content = input_data.content
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="ignore")
        
        return {
            "inputText": content,
            "embeddingConfig": {
                "outputEmbeddingLength": self.dimension,
            }
        }
    
    def _build_image_request(self, input_data: EmbeddingInput) -> Dict[str, Any]:
        """Build request for image embedding."""
        image_data = input_data.content
        if isinstance(image_data, str):
            image_data = image_data.encode("utf-8")
        
        # Base64 encode image
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        
        # Determine media type
        media_type_map = {
            ImageFormat.PNG: "image/png",
            ImageFormat.JPEG: "image/jpeg",
            ImageFormat.GIF: "image/gif",
            ImageFormat.WEBP: "image/webp",
            ImageFormat.SVG: "image/svg+xml",
        }
        media_type = media_type_map.get(
            input_data.image_format,
            "image/png"
        )
        
        request = {
            "inputImage": {
                "source": {
                    "bytes": image_b64,
                },
                "format": media_type,
            },
            "embeddingConfig": {
                "outputEmbeddingLength": self.dimension,
            }
        }
        
        # Add alt text if provided
        if input_data.alt_text:
            request["inputText"] = input_data.alt_text
        
        return request
    
    async def embed_batch(
        self,
        inputs: List[EmbeddingInput],
        batch_size: int = 10,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple inputs.
        
        Args:
            inputs: List of inputs to embed
            batch_size: Number of concurrent requests
            
        Returns:
            List of EmbeddingResults
        """
        results = []
        
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [self._embed(inp) for inp in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch embedding failed: {result}")
                    # Return empty embedding for failed items
                    results.append(EmbeddingResult(
                        embedding=[],
                        content_hash="",
                        content_type=ContentType.TEXT,
                        dimension=0,
                    ))
                else:
                    results.append(result)
        
        return results


class VectorStore:
    """
    Simple in-memory vector store for embeddings.
    
    In production, this would use a proper vector database
    like Amazon OpenSearch or Pinecone.
    """
    
    def __init__(self):
        self._embeddings: Dict[str, EmbeddingResult] = {}
        self._vectors: List[Tuple[str, List[float]]] = []
        
        logger.info("VectorStore initialized")
    
    def add(self, result: EmbeddingResult) -> None:
        """Add an embedding to the store."""
        self._embeddings[result.content_hash] = result
        self._vectors.append((result.content_hash, result.embedding))
    
    def add_batch(self, results: List[EmbeddingResult]) -> None:
        """Add multiple embeddings to the store."""
        for result in results:
            if result.embedding:  # Skip empty embeddings
                self.add(result)
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        content_types: Optional[List[ContentType]] = None,
    ) -> List[SimilarityResult]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            content_types: Filter by content types
            
        Returns:
            List of SimilarityResults
        """
        if not self._vectors:
            return []
        
        # Compute similarities
        similarities = []
        
        for content_hash, embedding in self._vectors:
            result = self._embeddings.get(content_hash)
            
            if not result:
                continue
            
            # Filter by content type
            if content_types and result.content_type not in content_types:
                continue
            
            # Compute cosine similarity
            score = self._cosine_similarity(query_embedding, embedding)
            
            similarities.append(SimilarityResult(
                content_hash=content_hash,
                score=score,
                content_type=result.content_type,
                metadata=result.metadata,
            ))
        
        # Sort by score and return top_k
        similarities.sort(key=lambda x: x.score, reverse=True)
        return similarities[:top_k]
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get(self, content_hash: str) -> Optional[EmbeddingResult]:
        """Get an embedding by content hash."""
        return self._embeddings.get(content_hash)
    
    def remove(self, content_hash: str) -> bool:
        """Remove an embedding from the store."""
        if content_hash in self._embeddings:
            del self._embeddings[content_hash]
            self._vectors = [
                (h, v) for h, v in self._vectors
                if h != content_hash
            ]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all embeddings."""
        self._embeddings.clear()
        self._vectors.clear()
    
    def count(self) -> int:
        """Get number of embeddings."""
        return len(self._embeddings)
    
    def stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        type_counts = {}
        for result in self._embeddings.values():
            type_name = result.content_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            "total_embeddings": len(self._embeddings),
            "by_type": type_counts,
        }


class CodebaseIndexer:
    """
    Indexes a codebase using multimodal embeddings.
    
    Used by Pillar 3 (Codebase Intelligence) to:
    - Index all code files
    - Index documentation and images
    - Enable semantic search across the codebase
    """
    
    # File patterns to index
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
        ".cpp", ".c", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
        ".scala", ".cs", ".sh", ".bash",
    }
    
    DOC_EXTENSIONS = {
        ".md", ".txt", ".rst", ".adoc",
    }
    
    CONFIG_EXTENSIONS = {
        ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg",
    }
    
    IMAGE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    }
    
    # Patterns to exclude
    EXCLUDE_PATTERNS = {
        "__pycache__", "node_modules", ".git", ".venv", "venv",
        "dist", "build", ".next", ".cache", "coverage",
    }
    
    def __init__(
        self,
        embeddings: Optional[NovaMultimodalEmbeddings] = None,
        store: Optional[VectorStore] = None,
    ):
        self.embeddings = embeddings or NovaMultimodalEmbeddings()
        self.store = store or VectorStore()
        
        logger.info("CodebaseIndexer initialized")
    
    async def index_directory(
        self,
        directory: str,
        include_images: bool = True,
        include_docs: bool = True,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Index all files in a directory.
        
        Args:
            directory: Path to directory
            include_images: Whether to index images
            include_docs: Whether to index documentation
            exclude_patterns: Additional patterns to exclude
            
        Returns:
            Indexing statistics
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        exclude = self.EXCLUDE_PATTERNS.copy()
        if exclude_patterns:
            exclude.update(exclude_patterns)
        
        # Collect files to index
        files_to_index = []
        
        for file_path in directory.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip excluded patterns
            if any(pattern in str(file_path) for pattern in exclude):
                continue
            
            extension = file_path.suffix.lower()
            
            # Check if file should be indexed
            if extension in self.CODE_EXTENSIONS:
                files_to_index.append(str(file_path))
            elif include_docs and extension in self.DOC_EXTENSIONS:
                files_to_index.append(str(file_path))
            elif extension in self.CONFIG_EXTENSIONS:
                files_to_index.append(str(file_path))
            elif include_images and extension in self.IMAGE_EXTENSIONS:
                files_to_index.append(str(file_path))
        
        # Index files
        indexed = 0
        failed = 0
        
        for file_path in files_to_index:
            try:
                result = await self.embeddings.embed_file(file_path)
                self.store.add(result)
                indexed += 1
                logger.debug(f"Indexed: {file_path}")
            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")
                failed += 1
        
        return {
            "directory": str(directory),
            "files_found": len(files_to_index),
            "files_indexed": indexed,
            "files_failed": failed,
            "store_stats": self.store.stats(),
        }
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        content_types: Optional[List[ContentType]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search the indexed codebase.
        
        Args:
            query: Search query
            top_k: Number of results
            content_types: Filter by content types
            
        Returns:
            List of search results with metadata
        """
        # Generate query embedding
        query_result = await self.embeddings.embed_text(query)
        
        # Search store
        results = self.store.search(
            query_embedding=query_result.embedding,
            top_k=top_k,
            content_types=content_types,
        )
        
        # Enrich results with full metadata
        enriched = []
        for result in results:
            embedding_result = self.store.get(result.content_hash)
            if embedding_result:
                enriched.append({
                    "score": result.score,
                    "content_type": result.content_type.value,
                    "file_path": embedding_result.metadata.get("file_path"),
                    "language": embedding_result.metadata.get("language"),
                    "metadata": embedding_result.metadata,
                })
        
        return enriched
    
    async def search_similar_code(
        self,
        code: str,
        language: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find similar code in the codebase.
        
        Args:
            code: Code snippet
            language: Programming language
            top_k: Number of results
            
        Returns:
            List of similar code files
        """
        # Generate code embedding
        code_result = await self.embeddings.embed_code(code, language)
        
        # Search for similar code
        results = self.store.search(
            query_embedding=code_result.embedding,
            top_k=top_k,
            content_types=[ContentType.CODE],
        )
        
        return [
            {
                "score": r.score,
                "file_path": r.metadata.get("file_path"),
                "language": r.metadata.get("language"),
            }
            for r in results
        ]


# Global instances
_embeddings: Optional[NovaMultimodalEmbeddings] = None
_store: Optional[VectorStore] = None
_indexer: Optional[CodebaseIndexer] = None


def get_embeddings() -> NovaMultimodalEmbeddings:
    """Get or create the global embeddings instance."""
    global _embeddings
    if _embeddings is None:
        _embeddings = NovaMultimodalEmbeddings()
    return _embeddings


def get_vector_store() -> VectorStore:
    """Get or create the global vector store."""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def get_codebase_indexer() -> CodebaseIndexer:
    """Get or create the global codebase indexer."""
    global _indexer
    if _indexer is None:
        _indexer = CodebaseIndexer(get_embeddings(), get_vector_store())
    return _indexer
