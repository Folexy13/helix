"""
DOCS Agent

Writes inline comments, function docstrings, README updates, and changelog entries.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

DOCS_SYSTEM_PROMPT = """You are the DOCS agent for Helix's Engineering Workforce.

Your role is to CREATE COMPLETE DOCUMENTATION automatically - no questions asked.

## Your Responsibilities:
1. **README.md**: Complete project README with setup instructions
2. **API Documentation**: Full API reference with examples
3. **Architecture Docs**: System architecture documentation
4. **User Guide**: How to use the application
5. **Developer Guide**: How to contribute/extend
6. **Deployment Guide**: How to deploy to production

## CRITICAL RULES:
- NEVER ask questions - just write documentation
- ALWAYS provide complete, professional documentation
- ALWAYS include setup instructions that actually work
- ALWAYS include API examples with curl/fetch
- ALWAYS include environment variable documentation

## Output Format:

### 📚 Documentation Package

#### 📁 README.md
\`\`\`markdown
# Project Name

Brief description of what this project does.

## 🚀 Quick Start

\`\`\`bash
# Clone the repository
git clone https://github.com/user/project.git
cd project

# Install dependencies
npm install

# Set up environment
cp .env.example .env
# Edit .env with your values

# Run development server
npm run dev
\`\`\`

## 📋 Features

- Feature 1: Description
- Feature 2: Description
- Feature 3: Description

## 🏗️ Architecture

[Brief architecture overview]

## 📖 API Reference

See [API Documentation](./docs/api.md)

## 🧪 Testing

\`\`\`bash
npm test
npm run test:coverage
\`\`\`

## 🚢 Deployment

See [Deployment Guide](./docs/deployment.md)

## 📄 License

MIT
\`\`\`

#### 📁 docs/api.md
\`\`\`markdown
# API Reference

## Authentication

### POST /api/auth/login
Login with email and password.

**Request:**
\`\`\`bash
curl -X POST http://localhost:3000/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "user@example.com", "password": "secret"}'
\`\`\`

**Response:**
\`\`\`json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": { "id": 1, "email": "user@example.com" }
}
\`\`\`

[... more endpoints ...]
\`\`\`

#### 📁 docs/deployment.md
\`\`\`markdown
# Deployment Guide

## Docker Deployment

\`\`\`bash
docker-compose up -d
\`\`\`

## Manual Deployment

1. Build the project: \`npm run build\`
2. Set environment variables
3. Start the server: \`npm start\`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL connection string | Yes |
| JWT_SECRET | Secret for JWT signing | Yes |
| PORT | Server port (default: 3000) | No |
\`\`\`

#### 📁 docs/architecture.md
\`\`\`markdown
# Architecture

## System Overview

[Mermaid diagram]

## Components

### Frontend
- React/Next.js application
- State management with Zustand

### Backend
- Node.js/Express API
- PostgreSQL database

### Infrastructure
- Docker containers
- Nginx reverse proxy
\`\`\`

REMEMBER: Write COMPLETE, PROFESSIONAL documentation that helps users get started immediately.

## Documentation Standards:
- Python: Google-style or NumPy-style docstrings
- JavaScript/TypeScript: JSDoc comments
- Markdown for README and guides
- Keep it maintainable and up-to-date"""


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
        
        # Register DOCS-specific tools
        self._register_docs_tools()
    
    def _register_docs_tools(self) -> None:
        """Register tools specific to DOCS."""
        
        # Generate docstring tool
        self.register_tool(Tool(
            name="generate_docstring",
            description="Generate a docstring for a function or class",
            parameters={
                "code": {
                    "type": "string",
                    "description": "The code to document",
                },
                "style": {
                    "type": "string",
                    "enum": ["google", "numpy", "sphinx", "jsdoc"],
                    "description": "Documentation style",
                },
            },
            handler=self._generate_docstring,
        ))
        
        # Generate README tool
        self.register_tool(Tool(
            name="generate_readme",
            description="Generate README documentation",
            parameters={
                "project_name": {
                    "type": "string",
                    "description": "Name of the project",
                },
                "description": {
                    "type": "string",
                    "description": "Project description",
                },
                "features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of features",
                },
            },
            handler=self._generate_readme,
        ))
        
        # Generate changelog entry tool
        self.register_tool(Tool(
            name="generate_changelog",
            description="Generate a changelog entry",
            parameters={
                "version": {
                    "type": "string",
                    "description": "Version number",
                },
                "changes": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of changes",
                },
            },
            handler=self._generate_changelog,
        ))
    
    async def _generate_docstring(self, code: str, style: str) -> Dict[str, Any]:
        """Generate a docstring for code."""
        return {
            "style": style,
            "docstring": '"""Generated docstring."""',
            "status": "generated",
        }
    
    async def _generate_readme(
        self,
        project_name: str,
        description: str,
        features: List[str],
    ) -> Dict[str, Any]:
        """Generate README content."""
        features_md = "\n".join(f"- {f}" for f in features)
        
        readme = f"""# {project_name}

{description}

## Features

{features_md}

## Installation

```bash
pip install {project_name.lower().replace(' ', '-')}
```

## Usage

```python
# Example usage
```

## License

MIT
"""
        return {
            "readme": readme,
            "status": "generated",
        }
    
    async def _generate_changelog(
        self,
        version: str,
        changes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate changelog entry."""
        from datetime import datetime
        
        date = datetime.now().strftime("%Y-%m-%d")
        
        changelog = f"""## [{version}] - {date}

### Added
- New feature implementation

### Changed
- Updated functionality

### Fixed
- Bug fixes
"""
        return {
            "changelog": changelog,
            "version": version,
            "status": "generated",
        }
    
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
4. CHANGELOG.md entry for this feature
5. Any additional documentation needed

Follow the documentation guidelines and standards."""

        try:
            # Invoke model
            response = await self.invoke_model(
                prompt=docs_prompt,
                context=context,
                use_tools=True,
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
                    "has_changelog": "CHANGELOG.md" in docs_output,
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
        
        # Find README section
        readme_match = re.search(
            r'####?\s*README\.md\s*\n+```(?:markdown)?\n(.*?)```',
            docs_text,
            re.DOTALL | re.IGNORECASE
        )
        if readme_match:
            docs["README.md"] = readme_match.group(1).strip()
        
        # Find CHANGELOG section
        changelog_match = re.search(
            r'####?\s*CHANGELOG\.md\s*\n+```(?:markdown)?\n(.*?)```',
            docs_text,
            re.DOTALL | re.IGNORECASE
        )
        if changelog_match:
            docs["CHANGELOG.md"] = changelog_match.group(1).strip()
        
        # Find any other documentation files
        file_pattern = r'####?\s*([^\n]+\.(?:md|rst|txt))\s*\n+```(?:\w+)?\n(.*?)```'
        matches = re.findall(file_pattern, docs_text, re.DOTALL)
        
        for filename, content in matches:
            filename = filename.strip()
            if filename not in docs:
                docs[filename] = content.strip()
        
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
