"""
CODER Agent

Writes the actual code based on the approved plan. Uses Nova Multimodal
Embeddings RAG (from Pillar 3) to understand the existing codebase.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.core.models import AgentRole, CodeOutput, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

CODER_SYSTEM_PROMPT = """You are the CODER agent for Helix's Engineering Workforce.

Your role is to BUILD THE ENTIRE PROJECT autonomously. You don't ask questions, you just build.

## Your Responsibilities:
1. **Create Project Structure**: Set up the entire project directory structure
2. **Install Dependencies**: Generate package.json or requirements.txt with all deps
3. **Write All Code**: Implement every file needed for the project
4. **Configuration Files**: Create all config files (env, docker, etc.)
5. **API Implementation**: Build complete REST APIs

## CRITICAL RULES:
- NEVER ask questions - just build
- ALWAYS provide COMPLETE files - no placeholders like "// TODO" or "// implement here"
- ALWAYS include package.json or requirements.txt with REAL versions
- ALWAYS include .env.example with actual variable names
- Build EVERYTHING the project needs to run
- Use REAL file paths (e.g., src/components/Button.tsx, NOT generated_file_1.tsx)

## **CRITICAL OUTPUT FORMAT - YOU MUST FOLLOW THIS EXACTLY:**

For EACH file, use this EXACT format with the file path on its own line:

### File: path/to/filename.ext
```language
// complete file content here - NO PLACEHOLDERS
```

## REQUIRED FILES FOR A REACT/VITE PROJECT:

### File: package.json
```json
{
  "name": "project-name",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

### File: vite.config.ts
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true
  }
})
```

### File: index.html
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App Name</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### File: src/main.tsx
```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

### File: src/App.tsx
```tsx
import React from 'react'
// Import your components here

export default function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Your app content */}
    </div>
  )
}
```

### File: src/index.css
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### File: tailwind.config.js
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### File: postcss.config.js
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

### File: tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### File: .env.example
```
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=MyApp
```

## FOR BACKEND (Node.js/Express):

### File: backend/package.json
```json
{
  "name": "backend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "express": "^4.18.0",
    "cors": "^2.8.5",
    "dotenv": "^16.3.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.0",
    "@types/cors": "^2.8.0",
    "typescript": "^5.3.0",
    "tsx": "^4.7.0"
  }
}
```

### File: backend/src/index.ts
```typescript
import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'

dotenv.config()

const app = express()
const PORT = process.env.PORT || 8000

app.use(cors())
app.use(express.json())

// Routes here

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`)
})
```

## FOR TESTS:

### File: tests/App.test.tsx
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../src/App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
    expect(document.body).toBeTruthy()
  })
})
```

## Code Quality Requirements:
- Write production-ready code with proper error handling
- Include input validation
- Use TypeScript with proper types
- Follow React best practices (hooks, functional components)
- Use Tailwind CSS for styling
- Include loading states and error boundaries

You are building a COMPLETE, RUNNABLE project. Not a skeleton or placeholder."""


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
        
        # Specialist agents now operate autonomously without tool-calling overhead.
    
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
{codebase_context if codebase_context else "No existing codebase context. Create a new project from scratch."}

## Additional Context:
{context.metadata.get('additional_context', 'No additional context provided.')}

---

## IMPORTANT INSTRUCTIONS:

1. **Create a COMPLETE project structure** with all necessary files
2. **Use the EXACT format** for each file:
   ```
   ### File: path/to/file.ext
   ```language
   // complete code
   ```
   ```

3. **Required files for a React project:**
   - package.json (with real dependency versions)
   - vite.config.ts
   - index.html
   - src/main.tsx
   - src/App.tsx
   - src/index.css (with Tailwind imports)
   - tailwind.config.js
   - postcss.config.js
   - tsconfig.json
   - .env.example

4. **For each component**, create a separate file in src/components/

5. **NO PLACEHOLDERS** - Write complete, working code

6. **Include proper TypeScript types** for all components and functions

Now generate ALL the files needed for this project:"""

        try:
            # Invoke model
            # NOTE: use_tools=False to avoid "Model produced invalid sequence" errors
            response = await self.invoke_model(
                prompt=coding_prompt,
                context=context,
                use_tools=False,
            )
            
            # Extract the code
            code_text = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse into structured output
            code_output = self._parse_code_output(code_text)
            
            # Log what was generated
            logger.info(f"CODER generated {len(code_output.files)} source files, {len(code_output.tests)} test files")
            for path in code_output.files.keys():
                logger.info(f"  - {path}")
            
            return self.format_response(
                content=code_text,
                reasoning=reasoning,
                metadata={
                    "files_created": list(code_output.files.keys()),
                    "tests_created": list(code_output.tests.keys()),
                    "docs_created": list(code_output.documentation.keys()),
                    "file_count": len(code_output.files),
                    "test_count": len(code_output.tests),
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
            return "No specific tasks defined. Build a complete project based on the feature request."
        
        formatted = []
        for i, task in enumerate(tasks, 1):
            name = task.get("name", f"Task {i}")
            desc = task.get("description", "No description")
            formatted.append(f"{i}. **{name}**: {desc}")
        
        return "\n".join(formatted)
    
    def _parse_code_output(self, code_text: str) -> CodeOutput:
        """
        Parse the code text into a structured CodeOutput.
        
        Improved parsing to handle various formats and avoid generic file names.
        """
        files = {}
        tests = {}
        documentation = {}
        
        # Pattern 1: ### File: path/to/file.ext followed by code block
        file_pattern = r'###\s*File:\s*([^\n`]+)\n+```(\w*)\n(.*?)```'
        matches = re.findall(file_pattern, code_text, re.DOTALL)
        
        for path, lang, content in matches:
            path = path.strip()
            content = content.strip()
            
            # Skip empty content
            if not content:
                continue
            
            # Categorize by file type
            if 'test' in path.lower() or path.startswith('tests/') or path.startswith('__tests__/'):
                tests[path] = content
            elif path.endswith('.md') or 'readme' in path.lower() or 'docs/' in path.lower():
                documentation[path] = content
            else:
                files[path] = content
        
        # Pattern 2: **path/to/file.ext** or `path/to/file.ext` followed by code block
        if not files:
            alt_pattern = r'(?:\*\*|`)([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)(?:\*\*|`)\s*\n+```(\w*)\n(.*?)```'
            alt_matches = re.findall(alt_pattern, code_text, re.DOTALL)
            
            for path, lang, content in alt_matches:
                path = path.strip()
                content = content.strip()
                
                if not content:
                    continue
                
                if 'test' in path.lower():
                    tests[path] = content
                elif path.endswith('.md'):
                    documentation[path] = content
                else:
                    files[path] = content
        
        # Pattern 3: Numbered files like "1. package.json" followed by code block
        if not files:
            numbered_pattern = r'\d+\.\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)\s*\n+```(\w*)\n(.*?)```'
            numbered_matches = re.findall(numbered_pattern, code_text, re.DOTALL)
            
            for path, lang, content in numbered_matches:
                path = path.strip()
                content = content.strip()
                
                if not content:
                    continue
                
                if 'test' in path.lower():
                    tests[path] = content
                elif path.endswith('.md'):
                    documentation[path] = content
                else:
                    files[path] = content
        
        # Last resort: Extract code blocks and try to infer file names from content
        if not files:
            code_blocks = re.findall(r'```(\w+)?\n(.*?)```', code_text, re.DOTALL)
            
            for i, (lang, content) in enumerate(code_blocks):
                content = content.strip()
                if not content:
                    continue
                
                # Try to infer file name from content
                path = self._infer_file_path(lang, content, i)
                
                if 'test' in path.lower():
                    tests[path] = content
                elif path.endswith('.md'):
                    documentation[path] = content
                else:
                    files[path] = content
        
        return CodeOutput(
            files=files,
            tests=tests,
            documentation=documentation,
        )
    
    def _infer_file_path(self, language: str, content: str, index: int) -> str:
        """
        Infer a meaningful file path from the content and language.
        """
        lang = language.lower() if language else ""
        
        # Check for package.json
        if '"name"' in content and '"version"' in content and '"dependencies"' in content:
            return "package.json"
        
        # Check for vite.config
        if 'defineConfig' in content and 'vite' in content.lower():
            return "vite.config.ts"
        
        # Check for tailwind.config
        if 'tailwind' in content.lower() and 'content' in content:
            return "tailwind.config.js"
        
        # Check for postcss.config
        if 'postcss' in content.lower() or 'autoprefixer' in content:
            return "postcss.config.js"
        
        # Check for tsconfig
        if '"compilerOptions"' in content:
            return "tsconfig.json"
        
        # Check for HTML
        if '<!DOCTYPE html>' in content or '<html' in content:
            return "index.html"
        
        # Check for React main entry
        if 'createRoot' in content and 'render' in content:
            return "src/main.tsx"
        
        # Check for React App component
        if 'export default function App' in content or 'function App()' in content:
            return "src/App.tsx"
        
        # Check for CSS with Tailwind
        if '@tailwind' in content:
            return "src/index.css"
        
        # Check for Express server
        if 'express' in content and 'listen' in content:
            return "backend/src/index.ts"
        
        # Check for React component
        if 'export default function' in content or 'export function' in content:
            # Try to extract component name
            match = re.search(r'(?:export default function|export function)\s+(\w+)', content)
            if match:
                component_name = match.group(1)
                if component_name != 'App':
                    return f"src/components/{component_name}.tsx"
        
        # Default based on language
        ext = self._get_extension(lang)
        return f"src/generated_{index + 1}{ext}"
    
    def _get_extension(self, language: str) -> str:
        """Get file extension for a language."""
        extensions = {
            "python": ".py",
            "py": ".py",
            "javascript": ".js",
            "js": ".js",
            "typescript": ".ts",
            "ts": ".ts",
            "tsx": ".tsx",
            "jsx": ".jsx",
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
