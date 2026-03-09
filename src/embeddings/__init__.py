"""
Embeddings Module

Provides multimodal embeddings using Amazon Nova Multimodal Embeddings:
- Text embeddings
- Code embeddings
- Image embeddings
- Unified vector space for cross-modal search
"""

from src.embeddings.multimodal import (
    NovaMultimodalEmbeddings,
    VectorStore,
    CodebaseIndexer,
    ContentType,
    ImageFormat,
    EmbeddingInput,
    EmbeddingResult,
    SimilarityResult,
    get_embeddings,
    get_vector_store,
    get_codebase_indexer,
)

__all__ = [
    "NovaMultimodalEmbeddings",
    "VectorStore",
    "CodebaseIndexer",
    "ContentType",
    "ImageFormat",
    "EmbeddingInput",
    "EmbeddingResult",
    "SimilarityResult",
    "get_embeddings",
    "get_vector_store",
    "get_codebase_indexer",
]
