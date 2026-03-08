"""
Codebase Indexer

Indexes codebases using Nova Multimodal Embeddings for RAG.
Handles code files, documentation, images, and diagrams.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from src.core.bedrock_client import BedrockClient, get_bedrock_client
from src.core.config import settings
from src.core.models import CodebaseIndex

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """A chunk of code or documentation for indexing."""
    id: UUID = field(default_factory=uuid4)
    file_path: str = ""
    content: str = ""
    start_line: int = 0
    end_line: int = 0
    language: str = ""
    chunk_type: str = "code"  # code, docstring, comment, markdown, image
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CodebaseIndexer:
    """
    Indexes codebases for RAG using Nova Multimodal Embeddings.
    
    Supports:
    - Code files (Python, JavaScript, TypeScript, etc.)
    - Documentation (Markdown, RST, etc.)
    - Images (architecture diagrams, screenshots)
    - Configuration files
    """
    
    # File extensions to index
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
        ".cpp", ".c", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
        ".kt", ".scala", ".r", ".sql", ".sh", ".bash", ".zsh",
    }
    
    DOC_EXTENSIONS = {
        ".md", ".rst", ".txt", ".adoc", ".org",
    }
    
    CONFIG_EXTENSIONS = {
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
        ".xml", ".properties",
    }
    
    IMAGE_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
    }
    
    # Files/directories to ignore
    IGNORE_PATTERNS = {
        ".git", ".svn", ".hg", "__pycache__", "node_modules",
        ".venv", "venv", "env", ".env", "dist", "build",
        ".idea", ".vscode", ".DS_Store", "*.pyc", "*.pyo",
        "*.egg-info", ".pytest_cache", ".mypy_cache",
    }
    
    def __init__(
        self,
        bedrock_client: Optional[BedrockClient] = None,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        """
        Initialize the indexer.
        
        Args:
            bedrock_client: Bedrock client for embeddings
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.bedrock_client = bedrock_client or get_bedrock_client()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        # Index storage
        self._chunks: List[CodeChunk] = []
        self._file_index: Dict[str, List[UUID]] = {}  # file_path -> chunk_ids
        
        logger.info("CodebaseIndexer initialized")
    
    async def index_repository(
        self,
        repo_path: str,
        exclude_patterns: Optional[Set[str]] = None,
    ) -> CodebaseIndex:
        """
        Index an entire repository.
        
        Args:
            repo_path: Path to the repository
            exclude_patterns: Additional patterns to exclude
            
        Returns:
            CodebaseIndex with indexing information
        """
        logger.info(f"Indexing repository: {repo_path}")
        
        repo_path = Path(repo_path)
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        
        # Combine ignore patterns
        ignore = self.IGNORE_PATTERNS.copy()
        if exclude_patterns:
            ignore.update(exclude_patterns)
        
        # Collect files to index
        files_to_index = []
        excluded_files = []
        
        for file_path in repo_path.rglob("*"):
            if file_path.is_file():
                # Check if should be ignored
                if self._should_ignore(file_path, ignore):
                    excluded_files.append(str(file_path.relative_to(repo_path)))
                    continue
                
                # Check if supported extension
                if self._is_supported_file(file_path):
                    files_to_index.append(file_path)
        
        logger.info(f"Found {len(files_to_index)} files to index")
        
        # Index each file
        total_chunks = 0
        indexed_files = []
        
        for file_path in files_to_index:
            try:
                chunks = await self._index_file(file_path, repo_path)
                total_chunks += len(chunks)
                indexed_files.append(str(file_path.relative_to(repo_path)))
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
        
        # Create index record
        index = CodebaseIndex(
            repository_url=str(repo_path),
            indexed_files=indexed_files,
            excluded_files=excluded_files,
            total_chunks=total_chunks,
            last_indexed_at=datetime.utcnow(),
        )
        
        logger.info(f"Indexing complete: {len(indexed_files)} files, {total_chunks} chunks")
        
        return index
    
    async def _index_file(
        self,
        file_path: Path,
        repo_root: Path,
    ) -> List[CodeChunk]:
        """Index a single file."""
        relative_path = str(file_path.relative_to(repo_root))
        extension = file_path.suffix.lower()
        
        # Determine file type and indexing strategy
        if extension in self.IMAGE_EXTENSIONS:
            return await self._index_image(file_path, relative_path)
        elif extension in self.CODE_EXTENSIONS:
            return await self._index_code(file_path, relative_path)
        elif extension in self.DOC_EXTENSIONS:
            return await self._index_documentation(file_path, relative_path)
        elif extension in self.CONFIG_EXTENSIONS:
            return await self._index_config(file_path, relative_path)
        else:
            return []
    
    async def _index_code(
        self,
        file_path: Path,
        relative_path: str,
    ) -> List[CodeChunk]:
        """Index a code file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(f"Could not decode {file_path}")
            return []
        
        # Detect language
        language = self._detect_language(file_path)
        
        # Split into chunks
        chunks = self._chunk_code(content, relative_path, language)
        
        # Generate embeddings for each chunk
        for chunk in chunks:
            embedding = await self._generate_embedding(chunk.content)
            chunk.embedding = embedding
            self._chunks.append(chunk)
        
        # Update file index
        self._file_index[relative_path] = [c.id for c in chunks]
        
        return chunks
    
    async def _index_documentation(
        self,
        file_path: Path,
        relative_path: str,
    ) -> List[CodeChunk]:
        """Index a documentation file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return []
        
        # Split into chunks
        chunks = self._chunk_text(content, relative_path, "markdown")
        
        # Generate embeddings
        for chunk in chunks:
            embedding = await self._generate_embedding(chunk.content)
            chunk.embedding = embedding
            self._chunks.append(chunk)
        
        self._file_index[relative_path] = [c.id for c in chunks]
        
        return chunks
    
    async def _index_config(
        self,
        file_path: Path,
        relative_path: str,
    ) -> List[CodeChunk]:
        """Index a configuration file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return []
        
        # Config files are usually small, index as single chunk
        chunk = CodeChunk(
            file_path=relative_path,
            content=content,
            start_line=1,
            end_line=content.count("\n") + 1,
            language=file_path.suffix.lstrip("."),
            chunk_type="config",
        )
        
        embedding = await self._generate_embedding(content)
        chunk.embedding = embedding
        self._chunks.append(chunk)
        
        self._file_index[relative_path] = [chunk.id]
        
        return [chunk]
    
    async def _index_image(
        self,
        file_path: Path,
        relative_path: str,
    ) -> List[CodeChunk]:
        """
        Index an image file using Nova Multimodal Embeddings.
        
        This allows SAGE to understand architecture diagrams and screenshots.
        """
        try:
            image_bytes = file_path.read_bytes()
        except Exception as e:
            logger.warning(f"Could not read image {file_path}: {e}")
            return []
        
        # Generate embedding for image
        embedding = await self._generate_image_embedding(image_bytes)
        
        chunk = CodeChunk(
            file_path=relative_path,
            content=f"[Image: {relative_path}]",
            chunk_type="image",
            embedding=embedding,
            metadata={"size_bytes": len(image_bytes)},
        )
        
        self._chunks.append(chunk)
        self._file_index[relative_path] = [chunk.id]
        
        return [chunk]
    
    def _chunk_code(
        self,
        content: str,
        file_path: str,
        language: str,
    ) -> List[CodeChunk]:
        """Split code into semantic chunks."""
        chunks = []
        lines = content.split("\n")
        
        current_chunk = []
        current_start = 1
        current_size = 0
        
        for i, line in enumerate(lines, 1):
            current_chunk.append(line)
            current_size += len(line) + 1
            
            # Check if we should create a new chunk
            should_split = False
            
            # Split on function/class definitions
            if language == "python":
                if line.strip().startswith(("def ", "class ", "async def ")):
                    if current_size > self.chunk_size // 2:
                        should_split = True
            
            # Split on size
            if current_size >= self.chunk_size:
                should_split = True
            
            if should_split and current_chunk:
                chunk_content = "\n".join(current_chunk)
                chunks.append(CodeChunk(
                    file_path=file_path,
                    content=chunk_content,
                    start_line=current_start,
                    end_line=i,
                    language=language,
                    chunk_type="code",
                ))
                
                # Keep overlap
                overlap_lines = int(self.chunk_overlap / 50)  # Approximate lines
                current_chunk = current_chunk[-overlap_lines:] if overlap_lines > 0 else []
                current_start = max(1, i - overlap_lines + 1)
                current_size = sum(len(l) + 1 for l in current_chunk)
        
        # Add remaining content
        if current_chunk:
            chunk_content = "\n".join(current_chunk)
            chunks.append(CodeChunk(
                file_path=file_path,
                content=chunk_content,
                start_line=current_start,
                end_line=len(lines),
                language=language,
                chunk_type="code",
            ))
        
        return chunks
    
    def _chunk_text(
        self,
        content: str,
        file_path: str,
        doc_type: str,
    ) -> List[CodeChunk]:
        """Split text into chunks."""
        chunks = []
        
        # Split on paragraphs or headers
        sections = content.split("\n\n")
        
        current_chunk = []
        current_size = 0
        
        for section in sections:
            section_size = len(section)
            
            if current_size + section_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_content = "\n\n".join(current_chunk)
                chunks.append(CodeChunk(
                    file_path=file_path,
                    content=chunk_content,
                    chunk_type="documentation",
                    language=doc_type,
                ))
                current_chunk = []
                current_size = 0
            
            current_chunk.append(section)
            current_size += section_size
        
        # Add remaining
        if current_chunk:
            chunk_content = "\n\n".join(current_chunk)
            chunks.append(CodeChunk(
                file_path=file_path,
                content=chunk_content,
                chunk_type="documentation",
                language=doc_type,
            ))
        
        return chunks
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Nova Multimodal Embeddings."""
        try:
            embeddings = await self.bedrock_client.generate_embeddings(
                inputs=text,
                input_type="text",
            )
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []
    
    async def _generate_image_embedding(self, image_bytes: bytes) -> List[float]:
        """Generate embedding for image using Nova Multimodal Embeddings."""
        try:
            embeddings = await self.bedrock_client.generate_embeddings(
                inputs=image_bytes,
                input_type="image",
            )
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error(f"Failed to generate image embedding: {e}")
            return []
    
    def _should_ignore(self, file_path: Path, ignore_patterns: Set[str]) -> bool:
        """Check if file should be ignored."""
        path_str = str(file_path)
        
        for pattern in ignore_patterns:
            if pattern in path_str:
                return True
            if file_path.match(pattern):
                return True
        
        return False
    
    def _is_supported_file(self, file_path: Path) -> bool:
        """Check if file type is supported."""
        extension = file_path.suffix.lower()
        return extension in (
            self.CODE_EXTENSIONS |
            self.DOC_EXTENSIONS |
            self.CONFIG_EXTENSIONS |
            self.IMAGE_EXTENSIONS
        )
    
    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        extension_map = {
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
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".sql": "sql",
            ".sh": "bash",
        }
        return extension_map.get(file_path.suffix.lower(), "unknown")
    
    def get_chunks(self) -> List[CodeChunk]:
        """Get all indexed chunks."""
        return self._chunks
    
    def get_chunks_for_file(self, file_path: str) -> List[CodeChunk]:
        """Get chunks for a specific file."""
        chunk_ids = self._file_index.get(file_path, [])
        return [c for c in self._chunks if c.id in chunk_ids]
    
    def clear_index(self) -> None:
        """Clear the index."""
        self._chunks = []
        self._file_index = {}
