"""
Pillar 3: Codebase Intelligence

Ask Your Codebase - indexes the entire codebase using Nova Multimodal Embeddings
and enables natural language conversations about the code.

Components:
- SAGE: The codebase intelligence agent
- RAG: Retrieval-Augmented Generation with Nova Multimodal Embeddings
- Indexer: Codebase indexing and chunking
"""

from src.agents.pillar3.sage import SageAgent
from src.agents.pillar3.rag import CodebaseRAG
from src.agents.pillar3.indexer import CodebaseIndexer

__all__ = [
    "SageAgent",
    "CodebaseRAG",
    "CodebaseIndexer",
]
