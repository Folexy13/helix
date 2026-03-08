"""
CODER Agent

Writes the actual code based on the approved plan. Uses Nova Multimodal
Embeddings RAG (from Pillar 3) to understand the existing codebase and
write code that matches its patterns, style, and conventions.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, CodeOutput, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

CODER_SYSTEM_PROMPT = """You are the CODER agent for Helix's Engineering Workforce.

Your role is to BUILD THE ENTIRE PROJECT autonomously - like Kilo Code agent.
You don't ask questions, you just build.

## Your Responsibilities:
1. **Create Project Structure**: Set up the entire project directory structure
2. **Install Dependencies**: Generate package.json/requirements.txt with all deps
3. **Write All Code**: Implement every file needed for the project
4. **Configuration Files**: Create all config files (env, docker, etc.)
5. **Database Setup**: Create migrations, seeds, schema files
6. **API Implementation**: Build complete REST/GraphQL APIs

## CRITICAL RULES:
- NEVER ask questions - just build
- ALWAYS provide COMPLETE files - no placeholders
- ALWAYS include package.json/requirements.txt
- ALWAYS include .env.example
- ALWAYS include README.md with setup instructions
- ALWAYS include Dockerfile if applicable
- Build EVERYTHING the project needs to run

## Output Format:
For EVERY file in the project:

```
### 📁 File: [path/to/file.ext]

\`\`\`language
[COMPLETE file content - no placeholders]
\`\`\`
```

## Project Setup Files (ALWAYS include):

### package.json (for Node.js projects)
\`\`\`json
{
  "name": "project-name",
  "version": "1.0.0",
  "scripts": {
    "dev": "...",
    "build": "...",
    "start": "...",
    "test": "..."
  },
  "dependencies": { ... },
  "devDependencies": { ... }
}
\`\`\`

### requirements.txt (for Python projects)
\`\`\`
flask==2.3.0
sqlalchemy==2.0.0
...
\`\`\`

### .env.example
\`\`\`
DATABASE_URL=postgresql://user:pass@localhost:5432/db
JWT_SECRET=your-secret-here
...
\`\`\`

### Dockerfile
\`\`\`dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
\`\`\`

### docker-compose.yml
\`\`\`yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
  db:
    image: postgres:15
    ...
\`\`\`

## Code Quality:
- Write production-ready code
- Include proper error handling
- Add input validation
- Use TypeScript/type hints
- Follow best practices
- Make it actually work!

REMEMBER: You are building a COMPLETE, RUNNABLE project. Not a skeleton."""


class CoderAgent(BaseAgent):
    """
    CODER - Code implementation agent.
    
    Writes production-ready code based on approved specs.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.CODER,
            name="CODER",
            description="Code Implementation Agent - Writes production-ready code",
            system_prompt=CODER_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        
        # Register CODER-specific tools
        self._register_coder_tools()
    
    def _register_coder_tools(self) -> None:
        """Register tools specific to CODER."""
        
        # File write tool
        self.register_tool(Tool(
            name="file_write",
            description="Write content to a file",
            parameters={
                "path": {
                    "type": "string",
                    "description": "Path to the file",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write",
                },
            },
            handler=self._file_write,
        ))
        
        # File read tool
        self.register_tool(Tool(
            name="file_read",
            description="Read content from a file",
            parameters={
                "path": {
                    "type": "string",
                    "description": "Path to the file",
                },
            },
            handler=self._file_read,
        ))
        
        # Code search tool
        self.register_tool(Tool(
            name="search_codebase",
            description="Search the codebase for patterns or references",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File pattern to search (e.g., *.py)",
                },
            },
            handler=self._search_codebase,
        ))
    
    async def _file_write(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file."""
        # In production, this would actually write to the filesystem
        return {
            "path": path,
            "status": "written",
            "bytes": len(content),
        }
    
    async def _file_read(self, path: str) -> Dict[str, Any]:
        """Read content from a file."""
        # In production, this would read from the filesystem
        return {
            "path": path,
            "content": "# File content would be here",
            "status": "read",
        }
    
    async def _search_codebase(self, query: str, file_pattern: str) -> Dict[str, Any]:
        """Search the codebase."""
        # In production, this would search the actual codebase
        return {
            "query": query,
            "pattern": file_pattern,
            "results": [],
            "total_matches": 0,
        }
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute CODER's code implementation.
        
        Args:
            context: Agent execution context with engineering spec
            
        Returns:
            AgentResponse with generated code
        """
        logger.info(f"CODER implementing: {context.user_input[:100]}...")
        
        # Get the engineering spec from context
        engineering_spec = context.metadata.get("engineering_spec", {})
        tasks = engineering_spec.get("tasks", [])
        
        # Get codebase context from Pillar 3 RAG
        codebase_context = context.codebase_context or ""
        
        # Build the coding prompt
        coding_prompt = f"""Implement the following feature based on the approved engineering specification:

## Feature Request:
{context.user_input}

## Engineering Specification:
{context.metadata.get('spec_text', 'No specification provided.')}

## Tasks to Implement:
{self._format_tasks(tasks)}

## Codebase Context:
{codebase_context if codebase_context else "No existing codebase context. Create new files as needed."}

## Additional Context:
{context.metadata.get('additional_context', 'No additional context provided.')}

Please implement all the required code following your guidelines.

For each file:
1. Provide the complete file path
2. Write the complete, production-ready code
3. Include proper error handling
4. Add appropriate comments and docstrings
5. Follow the existing code style if context is provided

Remember: Provide COMPLETE code, never use placeholders."""

        try:
            # Invoke model
            response = await self.invoke_model(
                prompt=coding_prompt,
                context=context,
                use_tools=True,
            )
            
            # Extract the code
            code_text = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse into structured output
            code_output = self._parse_code_output(code_text)
            
            # Create HITL checkpoint for mid-task interruption (Gate 2.3)
            # This allows the user to interrupt and provide feedback
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.MID_TASK_INTERRUPT,
                prompt=f"""CODER has generated the following code:

**Files Created/Modified:** {len(code_output.files)}
{chr(10).join(f'- {f}' for f in list(code_output.files.keys())[:5])}

Would you like to:
- **Approve**: Continue to testing
- **Edit**: Modify the generated code
- **Reject**: Regenerate with different approach""",
                options=[HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
                metadata={"code_output": code_output.model_dump()},
            )
            
            return self.format_response(
                content=code_text,
                reasoning=reasoning,
                hitl_checkpoint=checkpoint,
                metadata={
                    "files_created": list(code_output.files.keys()),
                    "file_count": len(code_output.files),
                    "code_output": code_output.model_dump(),
                },
            )
            
        except Exception as e:
            logger.error(f"CODER execution error: {e}")
            return self.format_response(
                content="I encountered an error while generating the code.",
                success=False,
                error=str(e),
            )
    
    def _format_tasks(self, tasks: List[Dict[str, Any]]) -> str:
        """Format tasks for the prompt."""
        if not tasks:
            return "No specific tasks defined."
        
        formatted = []
        for i, task in enumerate(tasks, 1):
            name = task.get("name", f"Task {i}")
            desc = task.get("description", "No description")
            formatted.append(f"{i}. **{name}**: {desc}")
        
        return "\n".join(formatted)
    
    def _parse_code_output(self, code_text: str) -> CodeOutput:
        """
        Parse the code text into a structured CodeOutput.
        """
        files = {}
        tests = {}
        documentation = {}
        
        import re
        
        # Find file blocks
        # Pattern: ### File: path/to/file.ext followed by code block
        file_pattern = r'###\s*File:\s*([^\n]+)\n+```\w*\n(.*?)```'
        matches = re.findall(file_pattern, code_text, re.DOTALL)
        
        for path, content in matches:
            path = path.strip()
            content = content.strip()
            
            # Categorize by file type
            if 'test' in path.lower() or path.startswith('tests/'):
                tests[path] = content
            elif path.endswith('.md') or 'readme' in path.lower():
                documentation[path] = content
            else:
                files[path] = content
        
        # If no structured files found, try to extract any code blocks
        if not files and not tests:
            code_blocks = re.findall(r'```(\w+)?\n(.*?)```', code_text, re.DOTALL)
            for i, (lang, content) in enumerate(code_blocks):
                ext = self._get_extension(lang)
                files[f"generated_file_{i+1}{ext}"] = content.strip()
        
        return CodeOutput(
            files=files,
            tests=tests,
            documentation=documentation,
        )
    
    def _get_extension(self, language: str) -> str:
        """Get file extension for a language."""
        extensions = {
            "python": ".py",
            "py": ".py",
            "javascript": ".js",
            "js": ".js",
            "typescript": ".ts",
            "ts": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "cpp": ".cpp",
            "c": ".c",
            "html": ".html",
            "css": ".css",
            "json": ".json",
            "yaml": ".yaml",
            "yml": ".yml",
            "sql": ".sql",
            "sh": ".sh",
            "bash": ".sh",
        }
        return extensions.get(language.lower() if language else "", ".txt")
    
    def get_voice_config(self) -> Dict[str, Any]:
        """Get Nova 2 Sonic voice configuration for CODER."""
        return {
            "voice_id": "coder",
            "style": "technical",
            "pace": "steady",
            "tone": "focused",
            "language": "en-US",
        }
