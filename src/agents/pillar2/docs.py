"""
DOCS Agent

Writes comprehensive documentation for the generated code.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

DOCS_SYSTEM_PROMPT = """You are the DOCS agent for Helix's Engineering Workforce.

Your role is to CREATE COMPLETE DOCUMENTATION automatically - no questions asked.

Your Responsibilities:
1. README.md: Complete project README with setup instructions
2. API Documentation: Full API reference with examples
3. Architecture Docs: System architecture documentation
4. Deployment Guide: How to deploy to production

CRITICAL RULES:
- NEVER ask questions - just write documentation
- ALWAYS provide complete, professional documentation
- ALWAYS include setup instructions that actually work
- ALWAYS include environment variable documentation

Output Format:
For each documentation file, provide the file path and complete content.
Include: README.md, docs/api.md, docs/deployment.md

Documentation Standards:
- Python: Google-style docstrings
- JavaScript/TypeScript: JSDoc comments
- Markdown for README and guides

Write COMPLETE, PROFESSIONAL documentation that helps users get started immediately."""


class DocsAgent(BaseAgent):
    """
    DOCS - Documentation agent.
    
    Creates comprehensive documentation for code.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.DOCS,
            name="DOCS",
            description="Documentation Agent - Creates comprehensive documentation",
            system_prompt=DOCS_SYSTEM_PROMPT,
            reasoning_effort=None,  # Documentation doesn't need extended thinking
        )
        
        # Specialist agents now operate autonomously without tool-calling overhead.
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute DOCS's documentation generation.
        
        Args:
            context: Agent execution context with code output
            
        Returns:
            AgentResponse with generated documentation
        """
        logger.info(f"DOCS creating documentation for: {context.user_input[:100]}...")
        
        # Get the code output from CODER
        code_output = context.metadata.get("code_output", {})
        files = code_output.get("files", {})
        tests = code_output.get("tests", {})
        
        # Build the documentation prompt
        docs_prompt = f"""Create comprehensive documentation for the following code:

## Feature Description:
{context.user_input}

## Code Files:
{self._format_code_files(files)}

## Test Files:
{self._format_code_files(tests)}

## Engineering Specification:
{context.metadata.get('spec_text', 'No specification provided.')}

Please create:
1. Inline comments for complex code sections
2. Docstrings for all functions and classes
3. README.md with installation and usage instructions
4. Any additional documentation needed

Follow the documentation guidelines and standards."""

        try:
            # Invoke model
            # NOTE: use_tools=False to avoid "Model produced invalid sequence" errors
            response = await self.invoke_model(
                prompt=docs_prompt,
                context=context,
                use_tools=False,
            )
            
            # Extract the documentation
            docs_text = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse documentation output
            docs_output = self._parse_docs_output(docs_text)
            
            return self.format_response(
                content=docs_text,
                reasoning=reasoning,
                metadata={
                    "documentation_files": list(docs_output.keys()),
                    "has_readme": "README.md" in docs_output,
                    "docs_output": docs_output,
                },
            )
            
        except Exception as e:
            logger.error(f"DOCS execution error: {e}")
            return self.format_response(
                content="I encountered an error while generating documentation.",
                success=False,
                error=str(e),
            )
    
    def _format_code_files(self, files: Dict[str, str]) -> str:
        """Format code files for the prompt."""
        if not files:
            return "No files provided."
        
        formatted = []
        for path, content in files.items():
            # Truncate very long files
            if len(content) > 1500:
                content = content[:1500] + "\n... (truncated)"
            formatted.append(f"### {path}\n```\n{content}\n```")
        
        return "\n\n".join(formatted)
    
    def _parse_docs_output(self, docs_text: str) -> Dict[str, str]:
        """Parse documentation text into files."""
        import re
        
        docs = {}
        
        # Find any documentation files in markdown blocks
        file_pattern = r'####?\s*([^\n]+\.(?:md|rst|txt))\s*\n+```(?:\w+)?\n(.*?)```'
        matches = re.findall(file_pattern, docs_text, re.DOTALL)
        
        for filename, content in matches:
            filename = filename.strip()
            docs[filename] = content.strip()
        
        # If no structured files found, try to extract any markdown blocks
        if not docs:
            md_blocks = re.findall(r'```markdown\n(.*?)```', docs_text, re.DOTALL)
            if md_blocks:
                docs["README.md"] = md_blocks[0].strip()
        
        return docs
    
    def get_voice_config(self) -> Dict[str, Any]:
        """Get Nova 2 Sonic voice configuration for DOCS."""
        return {
            "voice_id": "docs",
            "style": "clear",
            "pace": "measured",
            "tone": "helpful",
            "language": "en-US",
        }
