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
    
    async def index_repository(
        self,
        repo_path: str,
        exclude_patterns: Optional[List[str]] = None,
    ) -> CodebaseIndex:
        """
        Index a repository for SAGE to understand.
        
        This should be called before asking questions about a codebase.
        """
        logger.info(f"SAGE indexing repository: {repo_path}")
        
        # Index the repository
        index = await self.indexer.index_repository(
            repo_path,
            exclude_patterns=set(exclude_patterns) if exclude_patterns else None,
        )
        
        # Build the RAG index
        self.rag.build_index()
        
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
        
        # Check if we have an indexed codebase
        if not self._indexed_repos:
            # Check if there's a repo path in context
            repo_path = context.metadata.get("repository_path")
            if repo_path:
                await self.index_repository(repo_path)
            else:
                return self.format_response(
                    content="I don't have a codebase indexed yet. Please connect a repository first.",
                    metadata={"needs_indexing": True},
                )
        
        # Retrieve relevant context
        results = await self.rag.retrieve(context.user_input)
        
        # Check if we found relevant code
        if not results or all(r.score < 0.3 for r in results):
            # Low confidence - escalate to user (HITL Gate 3.3)
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.UNCERTAINTY_ESCALATION,
                prompt=f"""I'm not confident I found the right code for your question:

**Your Question:** {context.user_input}

I found some potentially related code, but the relevance scores are low.
Could you:
1. Rephrase your question with more specific terms?
2. Mention specific file names or function names?
3. Provide more context about what you're looking for?""",
                options=[HITLDecision.APPROVE],  # User provides clarification
                metadata={"low_confidence": True, "best_score": results[0].score if results else 0},
            )
            
            return self.format_response(
                content="I need some clarification to give you an accurate answer.",
                hitl_checkpoint=checkpoint,
                metadata={"confidence": "low"},
            )
        
        # Format context for the prompt
        code_context = self.rag.format_context_for_prompt(results)
        
        # Build the answer prompt
        answer_prompt = f"""Answer the following question about the codebase:

## Question:
{context.user_input}

## Relevant Code from the Codebase:
{code_context}

Please provide a comprehensive answer that:
1. Directly addresses the question
2. References specific files and line numbers
3. Shows relevant code snippets
4. Explains the reasoning and context
5. Suggests related areas to explore

If you're uncertain about any part, say so clearly."""

        try:
            # Invoke model with code context
            response = await self.invoke_model(
                prompt=answer_prompt,
                context=context,
                use_tools=True,
            )
            
            answer = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            return self.format_response(
                content=answer,
                reasoning=reasoning,
                metadata={
                    "confidence": "high" if results[0].score > 0.7 else "medium",
                    "sources": [
                        {"file": r.chunk.file_path, "score": r.score}
                        for r in results[:5]
                    ],
                    "index_stats": self.rag.get_index_stats(),
                },
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
