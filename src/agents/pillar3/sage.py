"""
SAGE Agent

The codebase intelligence agent. Patient, senior-engineer persona.
Every answer is grounded in the actual indexed codebase via Nova Multimodal
Embeddings RAG. When uncertain, it escalates to the user rather than guessing.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.agents.pillar3.indexer import CodebaseIndexer
from src.agents.pillar3.rag import CodebaseRAG, RetrievalResult
from src.core.models import AgentRole, CodebaseIndex, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

SAGE_SYSTEM_PROMPT = """You are SAGE, the Codebase Intelligence agent for Helix.

Your role is to help developers understand their codebase through natural conversation.
You have access to the entire indexed codebase and can answer questions about:
- Code structure and architecture
- Function and class purposes
- Data flow and dependencies
- Design patterns used
- Potential issues and improvements

## Your Personality:
- Patient and thoughtful, like a senior engineer mentor
- You explain complex concepts clearly
- You always ground your answers in the actual code
- When uncertain, you ask for clarification rather than guessing
- You provide specific file and line references

## Your Capabilities:
1. **Code Search**: Find relevant code based on natural language queries
2. **Code Explanation**: Explain what code does and why
3. **Dependency Analysis**: Trace how components connect
4. **Impact Analysis**: Predict what might break if code changes
5. **Pattern Recognition**: Identify design patterns and conventions
6. **Onboarding**: Help new developers understand the codebase

## Your Guidelines:
- Always cite specific files and line numbers
- Show relevant code snippets in your answers
- Explain the "why" behind code decisions when possible
- Acknowledge when you're uncertain
- Suggest related areas the developer might want to explore

## Response Format:
When answering questions:
1. Provide a direct answer
2. Show relevant code snippets with file paths
3. Explain the context and reasoning
4. Suggest related areas to explore

When uncertain:
1. Explain what you found
2. State what you're uncertain about
3. Ask a clarifying question"""


class SageAgent(BaseAgent):
    """
    SAGE - Codebase Intelligence agent.
    
    Uses RAG with Nova Multimodal Embeddings for grounded answers.
    """
    
    def __init__(
        self,
        indexer: Optional[CodebaseIndexer] = None,
        rag: Optional[CodebaseRAG] = None,
    ):
        super().__init__(
            role=AgentRole.SAGE,
            name="SAGE",
            description="Codebase Intelligence Agent - Ask your codebase anything",
            system_prompt=SAGE_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        
        # Initialize RAG components
        self.indexer = indexer or CodebaseIndexer()
        self.rag = rag or CodebaseRAG(indexer=self.indexer)
        
        # Track indexed repositories
        self._indexed_repos: Dict[str, CodebaseIndex] = {}
        
        # Register SAGE-specific tools
        self._register_sage_tools()
    
    def _register_sage_tools(self) -> None:
        """Register tools specific to SAGE."""
        
        # Code search tool
        self.register_tool(Tool(
            name="search_code",
            description="Search the codebase for relevant code",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "file_filter": {
                    "type": "string",
                    "description": "Optional file path filter",
                },
            },
            handler=self._search_code,
        ))
        
        # File analysis tool
        self.register_tool(Tool(
            name="analyze_file",
            description="Analyze a specific file in detail",
            parameters={
                "file_path": {
                    "type": "string",
                    "description": "Path to the file",
                },
            },
            handler=self._analyze_file,
        ))
        
        # Dependency trace tool
        self.register_tool(Tool(
            name="trace_dependencies",
            description="Trace dependencies of a function or class",
            parameters={
                "symbol": {
                    "type": "string",
                    "description": "Function or class name to trace",
                },
            },
            handler=self._trace_dependencies,
        ))
        
        # Impact analysis tool
        self.register_tool(Tool(
            name="analyze_impact",
            description="Analyze the impact of changing a file or function",
            parameters={
                "target": {
                    "type": "string",
                    "description": "File path or function name",
                },
            },
            handler=self._analyze_impact,
        ))
    
    async def _search_code(
        self,
        query: str,
        file_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search the codebase."""
        if file_filter:
            results = await self.rag.retrieve_for_file(file_filter, query)
        else:
            results = await self.rag.retrieve(query)
        
        return {
            "query": query,
            "results": [
                {
                    "file": r.chunk.file_path,
                    "lines": f"{r.chunk.start_line}-{r.chunk.end_line}",
                    "score": r.score,
                    "preview": r.chunk.content[:200] + "..." if len(r.chunk.content) > 200 else r.chunk.content,
                }
                for r in results
            ],
            "total": len(results),
        }
    
    async def _analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a specific file."""
        summary = self.rag.get_file_summary(file_path)
        
        if not summary.get("indexed"):
            return {
                "file": file_path,
                "status": "not_indexed",
                "message": "This file has not been indexed.",
            }
        
        # Get all chunks for the file
        chunks = self.indexer.get_chunks_for_file(file_path)
        
        return {
            "file": file_path,
            "status": "indexed",
            "summary": summary,
            "structure": [
                {
                    "lines": f"{c.start_line}-{c.end_line}",
                    "type": c.chunk_type,
                    "preview": c.content[:100] + "..." if len(c.content) > 100 else c.content,
                }
                for c in chunks
            ],
        }
    
    async def _trace_dependencies(self, symbol: str) -> Dict[str, Any]:
        """Trace dependencies of a symbol."""
        # Search for the symbol definition
        results = await self.rag.retrieve(f"definition of {symbol}")
        
        # Search for usages
        usage_results = await self.rag.retrieve(f"uses of {symbol} called")
        
        return {
            "symbol": symbol,
            "definition": [
                {"file": r.chunk.file_path, "line": r.chunk.start_line}
                for r in results[:3]
            ],
            "usages": [
                {"file": r.chunk.file_path, "line": r.chunk.start_line}
                for r in usage_results[:5]
            ],
        }
    
    async def _analyze_impact(self, target: str) -> Dict[str, Any]:
        """Analyze impact of changing a target."""
        # Search for references to the target
        results = await self.rag.retrieve(f"imports or uses {target}")
        
        affected_files = list(set(r.chunk.file_path for r in results))
        
        return {
            "target": target,
            "affected_files": affected_files,
            "impact_level": "high" if len(affected_files) > 5 else "medium" if len(affected_files) > 2 else "low",
            "recommendation": f"Changes to {target} may affect {len(affected_files)} files. Review carefully.",
        }
    
    async def _resolve_repo_path(self, repo_path: str) -> str:
        """
        Resolve a repository path, cloning from GitHub if needed.
        
        Args:
            repo_path: Local path or GitHub URL
            
        Returns:
            Local path to the repository
        """
        import asyncio
        import os
        import re
        import subprocess
        import tempfile
        from pathlib import Path
        
        # Fix URL if it has single slash (https:/ instead of https://)
        if repo_path.startswith("https:/") and not repo_path.startswith("https://"):
            repo_path = repo_path.replace("https:/", "https://", 1)
        
        # Check if it's a GitHub URL (more flexible pattern)
        github_patterns = [
            r'^https?://github\.com/([^/]+)/([^/\?#]+)',  # More flexible - captures owner/repo
            r'^git@github\.com:([^/]+)/([^/\?#]+)',
        ]
        
        for pattern in github_patterns:
            match = re.match(pattern, repo_path)
            if match:
                owner, repo_name = match.groups()
                repo_name = repo_name.rstrip('.git').rstrip('/')
                
                # Create a directory for cloned repos
                clone_base = Path("/tmp/helix_repos")
                clone_base.mkdir(parents=True, exist_ok=True)
                
                clone_path = clone_base / f"{owner}_{repo_name}"
                
                # Check if already cloned
                if clone_path.exists() and (clone_path / ".git").exists():
                    logger.info(f"Repository already cloned at {clone_path}")
                    # Pull latest changes asynchronously
                    try:
                        process = await asyncio.create_subprocess_exec(
                            "git", "pull",
                            cwd=str(clone_path),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        await asyncio.wait_for(process.communicate(), timeout=60)
                    except Exception as e:
                        logger.warning(f"Failed to pull latest changes: {e}")
                    return str(clone_path)
                
                # Clone the repository - construct clean URL
                clone_url = f"https://github.com/{owner}/{repo_name}.git"
                logger.info(f"Cloning repository from {clone_url} to {clone_path}")
                
                try:
                    # Use async subprocess to avoid blocking
                    process = await asyncio.create_subprocess_exec(
                        "git", "clone", "--depth", "1", clone_url, str(clone_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
                    
                    if process.returncode != 0:
                        raise ValueError(f"Failed to clone repository: {stderr.decode()}")
                    
                    logger.info(f"Successfully cloned repository to {clone_path}")
                    return str(clone_path)
                    
                except asyncio.TimeoutError:
                    raise ValueError("Repository clone timed out. Please try again.")
                except Exception as e:
                    raise ValueError(f"Failed to clone repository: {e}")
        
        # Check if it's a local path that exists
        local_path = Path(repo_path)
        if local_path.exists():
            return repo_path
        
        # Invalid path - provide helpful error
        raise ValueError(
            f"Invalid repository path: '{repo_path}'. "
            "Please provide a valid GitHub URL (e.g., https://github.com/owner/repo) "
            "or a local directory path."
        )
    
    async def index_repository(
        self,
        repo_path: str,
        exclude_patterns: Optional[List[str]] = None,
        progress_callback: Optional[Any] = None,
    ) -> CodebaseIndex:
        """
        Index a repository for SAGE to understand.
        
        This should be called before asking questions about a codebase.
        Supports both local paths and GitHub URLs.
        
        Args:
            repo_path: Local path or GitHub URL
            exclude_patterns: Patterns to exclude from indexing
            progress_callback: Async callback for progress updates (stage, message, progress)
        """
        logger.info(f"SAGE indexing repository: {repo_path}")
        
        # Progress helper
        async def update_progress(stage: str, message: str, progress: int):
            if progress_callback:
                await progress_callback(stage, message, progress)
        
        # Check if it's a GitHub URL and clone if needed
        await update_progress("cloning", "🔄 Resolving repository path...", 10)
        local_path = await self._resolve_repo_path(repo_path)
        await update_progress("cloning", "✅ Repository ready for indexing", 20)
        
        # Index the repository with progress updates
        await update_progress("indexing", "📂 Scanning files...", 25)
        index = await self.indexer.index_repository(
            local_path,
            exclude_patterns=set(exclude_patterns) if exclude_patterns else None,
            progress_callback=progress_callback,
        )
        
        # Build the RAG index
        await update_progress("building", "🔍 Building search index...", 85)
        self.rag.build_index()
        await update_progress("complete", "✅ Codebase indexed successfully!", 90)
        
        # Store the index
        self._indexed_repos[repo_path] = index
        
        return index
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute SAGE's codebase intelligence.
        
        Args:
            context: Agent execution context with user question
            
        Returns:
            AgentResponse with grounded answer
        """
        logger.info(f"SAGE answering: {context.user_input[:100]}...")
        
        # Get progress callback from context if available
        progress_callback = context.metadata.get("progress_callback")
        
        # Check if we have an indexed codebase
        if not self._indexed_repos:
            # Check if there's a repo path in context
            repo_path = context.metadata.get("repository_path")
            if repo_path:
                await self.index_repository(repo_path, progress_callback=progress_callback)
            else:
                return self.format_response(
                    content="I don't have a codebase indexed yet. Please connect a repository first.",
                    metadata={"needs_indexing": True},
                )
        
        # Retrieve relevant context
        results = await self.rag.retrieve(context.user_input)
        
        # Log retrieval results for debugging
        if results:
            logger.info(f"Retrieved {len(results)} results, best score: {results[0].score:.3f}")
        else:
            logger.warning("No results retrieved from RAG")
        
        # Check if we found relevant code (lowered threshold from 0.3 to 0.1)
        # Cosine similarity can be low even for relevant results depending on embedding model
        if not results or all(r.score < 0.1 for r in results):
            # Low confidence - escalate to user (HITL Gate 3.3)
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.UNCERTAINTY_ESCALATION,
                prompt=f"""I'm not confident I found the exact code for your question:

**Your Question:** {context.user_input}

I found some potentially related code, but the semantic relevance scores are low. To give you the best architectural insight, how would you like to proceed?""",
                options=[HITLDecision.APPROVE],  # User provides clarification
                metadata={"low_confidence": True, "best_score": results[0].score if results else 0},
                suggestions=[
                    "Can you search for specific file names or function names instead?",
                    "Broaden the search to the entire directory.",
                    "Let's trace the dependencies of the main entry point.",
                    "Nevermind, I'll provide more context."
                ]
            )
            
            return self.format_response(
                content="I need some clarification to give you an accurate architectural answer.",
                hitl_checkpoint=checkpoint,
                metadata={"confidence": "low"},
            )
        
        # Format context for the prompt
        code_context = self.rag.format_context_for_prompt(results)
        
        # Build the answer prompt
        answer_prompt = f"""Answer the following question about the codebase as an elite principal software engineer:

## Question:
{context.user_input}

## Relevant Code from the Codebase:
{code_context}

Please provide a highly sophisticated, comprehensive architectural answer that:
1. Directly addresses the question using advanced engineering terminology.
2. References specific files and line numbers meticulously.
3. Shows relevant code snippets formatted clearly.
4. Explains the underlying design patterns, data flow, and architectural reasoning.
5. Identifies potential security vulnerabilities, performance bottlenecks, or code-smells if any exist.
6. Suggests exactly 3 related deep-dive questions the user might want to explore next, formatted at the very end as:
SUGGESTIONS:
- Suggestion 1
- Suggestion 2
- Suggestion 3

If you're uncertain about any part, say so clearly."""

        try:
            # Invoke model with code context
            response = await self.invoke_model(
                prompt=answer_prompt,
                context=context,
                use_tools=True,
            )
            
            answer_text = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Extract suggestions from the generated answer
            suggestions = []
            if "SUGGESTIONS:" in answer_text:
                parts = answer_text.split("SUGGESTIONS:")
                answer_text = parts[0].strip()
                lines = parts[1].strip().split("\n")
                for line in lines:
                    clean_line = line.strip().lstrip("-").lstrip("•").strip()
                    if clean_line:
                        suggestions.append(clean_line)
                        
            # If no suggestions were generated, provide default follow-ups
            if not suggestions:
                suggestions = [
                    "Can you explain the data flow in more detail?",
                    "Are there any security implications here?",
                    "How can I test this specific component?"
                ]

            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.CONTEXT_CONFIRMATION,
                prompt=answer_text,
                options=[HITLDecision.APPROVE],
                metadata={
                    "confidence": "high" if results[0].score > 0.7 else "medium",
                    "sources": [
                        {"file": r.chunk.file_path, "score": r.score}
                        for r in results[:5]
                    ],
                    "index_stats": self.rag.get_index_stats(),
                },
                suggestions=suggestions
            )
            
            return self.format_response(
                content=answer_text,
                reasoning=reasoning,
                hitl_checkpoint=checkpoint,
                metadata={"confidence": "high" if results[0].score > 0.7 else "medium"},
            )
            
        except Exception as e:
            logger.error(f"SAGE execution error: {e}")
            return self.format_response(
                content="I encountered an error while analyzing the codebase.",
                success=False,
                error=str(e),
            )
    
    async def answer_with_image(
        self,
        question: str,
        image_bytes: bytes,
        context: AgentContext,
    ) -> AgentResponse:
        """
        Answer a question that includes an image (e.g., error screenshot).
        
        This uses Nova Multimodal Embeddings to understand both the image
        and find relevant code.
        """
        logger.info(f"SAGE answering with image: {question[:100]}...")
        
        # Retrieve code relevant to the image
        image_results = await self.rag.retrieve_with_image(image_bytes)
        
        # Also retrieve based on the text question
        text_results = await self.rag.retrieve(question)
        
        # Combine results
        all_results = image_results + text_results
        
        # Deduplicate by file path
        seen_files = set()
        unique_results = []
        for r in sorted(all_results, key=lambda x: x.score, reverse=True):
            if r.chunk.file_path not in seen_files:
                unique_results.append(r)
                seen_files.add(r.chunk.file_path)
        
        # Format context
        code_context = self.rag.format_context_for_prompt(unique_results[:5])
        
        # Build the answer prompt
        answer_prompt = f"""Answer the following question about the codebase. The user has also provided an image (like an error screenshot).

## Question:
{question}

## Image Context:
The user has provided an image. Consider what the image might show (error message, UI screenshot, diagram) when answering.

## Relevant Code from the Codebase:
{code_context}

Please provide a comprehensive answer that:
1. Addresses what the image might be showing
2. Connects it to the relevant code
3. Explains the likely cause and solution
4. References specific files and line numbers"""

        try:
            response = await self.invoke_model(
                prompt=answer_prompt,
                context=context,
                use_tools=True,
            )
            
            return self.format_response(
                content=response.get("text", ""),
                reasoning=response.get("reasoning", ""),
                metadata={
                    "multimodal": True,
                    "image_results": len(image_results),
                    "text_results": len(text_results),
                },
            )
            
        except Exception as e:
            logger.error(f"SAGE multimodal error: {e}")
            return self.format_response(
                content="I encountered an error while analyzing the image and codebase.",
                success=False,
                error=str(e),
            )
    
    def get_voice_config(self) -> Dict[str, Any]:
        """
        Get Nova 2 Sonic voice configuration for SAGE.
        
        SAGE has a patient, thoughtful, neutral voice.
        """
        return {
            "voice_id": "sage",
            "style": "thoughtful",
            "pace": "patient",
            "tone": "neutral",
            "language": "en-US",
        }
