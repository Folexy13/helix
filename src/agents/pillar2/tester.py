"""
TESTER Agent

Writes and validates tests for the generated code.

NOW ENHANCED WITH:
- Real code execution via CodeInterpreterTool
- Actual test validation (not simulated)
- Syntax checking before test execution
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort
from src.tools.advanced_tools import CodeInterpreterTool, get_tool_registry

logger = logging.getLogger(__name__)

TESTER_SYSTEM_PROMPT = """You are the TESTER agent for Helix's Engineering Workforce.

Your role is to CREATE comprehensive test suites AUTOMATICALLY. You don't ask questions - you write tests.

## IMPORTANT: WEBCONTAINER-COMPATIBLE TESTS
All tests must run in a WebContainer browser environment using Vitest.
- Use Vitest (NOT Jest) for all tests
- Use @testing-library/react for React component tests
- Tests run in jsdom environment
- NO backend/API tests - only frontend tests

Your Responsibilities:
1. Create Test Files: Write complete test suites for all frontend code
2. Unit Tests: Test individual components and hooks
3. Integration Tests: Test component interactions
4. Mock API calls using vi.mock() or MSW patterns

CRITICAL RULES:
- NEVER ask questions - just write tests
- ALWAYS provide complete test files
- ALWAYS use Vitest syntax (describe, it, expect, vi)
- ALWAYS use @testing-library/react for component tests
- Tests must be runnable in WebContainer (browser environment)

## OUTPUT FORMAT:
For each test file, use this EXACT format:

### File: src/__tests__/ComponentName.test.tsx
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ComponentName from '../components/ComponentName'

describe('ComponentName', () => {
  it('should render correctly', () => {
    render(<ComponentName />)
    expect(screen.getByText('Expected Text')).toBeInTheDocument()
  })
  
  it('should handle user interaction', async () => {
    render(<ComponentName />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByText('Updated Text')).toBeInTheDocument()
  })
})
```

## TESTING PATTERNS:

### Testing Components with State:
```tsx
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Counter from '../components/Counter'

describe('Counter', () => {
  it('increments count when button clicked', () => {
    render(<Counter />)
    const button = screen.getByRole('button', { name: /increment/i })
    fireEvent.click(button)
    expect(screen.getByText('Count: 1')).toBeInTheDocument()
  })
})
```

### Testing with Zustand Store:
```tsx
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { useStore } from '../store/store'
import MyComponent from '../components/MyComponent'

describe('MyComponent with Store', () => {
  beforeEach(() => {
    // Reset store before each test
    useStore.setState({ items: [] })
  })
  
  it('displays items from store', () => {
    useStore.setState({ items: [{ id: '1', name: 'Test Item' }] })
    render(<MyComponent />)
    expect(screen.getByText('Test Item')).toBeInTheDocument()
  })
})
```

### Mocking API Calls:
```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import * as mockApi from '../services/mockApi'
import DataComponent from '../components/DataComponent'

vi.mock('../services/mockApi')

describe('DataComponent', () => {
  it('displays fetched data', async () => {
    vi.mocked(mockApi.mockApi.get).mockResolvedValue({
      data: [{ id: '1', name: 'Test' }],
      success: true
    })
    
    render(<DataComponent />)
    await waitFor(() => {
      expect(screen.getByText('Test')).toBeInTheDocument()
    })
  })
})
```

Write COMPLETE tests that actually test the frontend code."""


class TesterAgent(BaseAgent):
    """
    TESTER - Test writing and validation agent.
    
    Uses CodeInterpreterTool to actually execute and validate tests.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.TESTER,
            name="TESTER",
            description="Test Agent - Writes and validates tests with real execution",
            system_prompt=TESTER_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.MEDIUM,
        )
        
        # Initialize code interpreter for real test execution
        self._code_interpreter = CodeInterpreterTool()
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute TESTER's test generation and validation.
        
        Args:
            context: Agent execution context with code output
            
        Returns:
            AgentResponse with generated tests
        """
        logger.info(f"TESTER creating tests for: {context.user_input[:100]}...")
        
        # Get the code output from CODER
        code_output = context.metadata.get("code_output", {})
        files = code_output.get("files", {})
        
        # Build the testing prompt
        testing_prompt = f"""Write comprehensive tests for the following code:

## Feature Description:
{context.user_input}

## Code to Test:
{self._format_code_files(files)}

## Engineering Specification:
{context.metadata.get('spec_text', 'No specification provided.')}

Please write:
1. Unit tests for each function/method
2. Integration tests for component interactions
3. Edge case tests for boundary conditions
4. Error handling tests

Follow the testing guidelines and provide complete, runnable test files."""

        try:
            # Invoke model
            # NOTE: use_tools=False to avoid "Model produced invalid sequence" errors
            response = await self.invoke_model(
                prompt=testing_prompt,
                context=context,
                use_tools=False,
            )
            
            # Extract the tests
            test_text = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse test output
            test_output = self._parse_test_output(test_text)
            
            # ACTUALLY RUN THE TESTS using CodeInterpreterTool
            test_results = await self._execute_tests(test_output)
            
            return self.format_response(
                content=test_text,
                reasoning=reasoning,
                metadata={
                    "test_files": list(test_output.keys()),
                    "test_count": test_results.get("total_tests", 0),
                    "tests_passed": test_results.get("passed", 0),
                    "tests_failed": test_results.get("failed", 0),
                    "coverage": test_results.get("coverage", "N/A"),
                    "test_output": test_output,
                    "execution_results": test_results.get("execution_results", []),
                    "real_execution": True,
                },
            )
            
        except Exception as e:
            logger.error(f"TESTER execution error: {e}")
            return self.format_response(
                content="I encountered an error while generating tests.",
                success=False,
                error=str(e),
            )
    
    def _format_code_files(self, files: Dict[str, str]) -> str:
        """Format code files for the prompt."""
        if not files:
            return "No code files provided."
        
        formatted = []
        for path, content in files.items():
            # Truncate very long files
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"
            formatted.append(f"### {path}\n```\n{content}\n```")
        
        return "\n\n".join(formatted)
    
    def _parse_test_output(self, test_text: str) -> Dict[str, str]:
        """Parse test text into test files."""
        import re
        
        tests = {}
        
        # Find test file blocks
        file_pattern = r'###\s*Test File:\s*([^\n]+)\n+```\w*\n(.*?)```'
        matches = re.findall(file_pattern, test_text, re.DOTALL)
        
        for path, content in matches:
            tests[path.strip()] = content.strip()
        
        # If no structured files found, try to extract any test code blocks
        if not tests:
            code_blocks = re.findall(r'```(\w+)?\n(.*?)```', test_text, re.DOTALL)
            for i, (lang, content) in enumerate(code_blocks):
                if 'test' in content.lower() or 'assert' in content.lower():
                    ext = ".py" if lang in ["python", "py", ""] else f".{lang}"
                    tests[f"test_generated_{i+1}{ext}"] = content.strip()
        
        return tests
    
    async def _execute_tests(self, test_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Actually execute the generated tests using CodeInterpreterTool.
        
        This is a key differentiator - we don't just generate tests,
        we actually run them and report real results.
        """
        execution_results = []
        total_tests = 0
        passed = 0
        failed = 0
        
        for file_path, test_code in test_files.items():
            # Determine language from file extension
            if file_path.endswith(".py"):
                language = "python"
            elif file_path.endswith((".js", ".ts")):
                language = "javascript"
            else:
                language = "python"  # Default
            
            try:
                # First validate syntax
                syntax_result = await self._code_interpreter.validate_syntax(
                    test_code, language
                )
                
                if not syntax_result.success:
                    execution_results.append({
                        "file": file_path,
                        "status": "syntax_error",
                        "error": syntax_result.output.get("stderr", "") if syntax_result.output else syntax_result.error,
                    })
                    failed += 1
                    continue
                
                # Run the tests
                test_result = await self._code_interpreter.run_tests(
                    test_code, language
                )
                
                # Parse test output
                if test_result.success:
                    output = test_result.output or {}
                    stdout = output.get("stdout", "")
                    
                    # Count tests from output (simplified parsing)
                    import re
                    passed_match = re.search(r'(\d+) passed', stdout)
                    failed_match = re.search(r'(\d+) failed', stdout)
                    
                    file_passed = int(passed_match.group(1)) if passed_match else 1
                    file_failed = int(failed_match.group(1)) if failed_match else 0
                    
                    passed += file_passed
                    failed += file_failed
                    total_tests += file_passed + file_failed
                    
                    execution_results.append({
                        "file": file_path,
                        "status": "passed" if file_failed == 0 else "partial",
                        "passed": file_passed,
                        "failed": file_failed,
                        "stdout": stdout[:500],  # Truncate
                        "execution_time": test_result.execution_time,
                    })
                else:
                    failed += 1
                    total_tests += 1
                    execution_results.append({
                        "file": file_path,
                        "status": "failed",
                        "error": test_result.error,
                        "stderr": test_result.output.get("stderr", "") if test_result.output else "",
                    })
                    
            except Exception as e:
                logger.error(f"Test execution error for {file_path}: {e}")
                execution_results.append({
                    "file": file_path,
                    "status": "error",
                    "error": str(e),
                })
                failed += 1
                total_tests += 1
        
        # Calculate coverage (simplified - would need actual coverage tool)
        coverage = f"{(passed / max(total_tests, 1)) * 100:.1f}%" if total_tests > 0 else "N/A"
        
        return {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "coverage": coverage,
            "execution_results": execution_results,
            "real_execution": True,
        }
    
    def get_voice_config(self) -> Dict[str, Any]:
        """Get Nova 2 Sonic voice configuration for TESTER."""
        return {
            "voice_id": "joanna",  # Clear, professional voice
            "style": "methodical",
            "pace": "clear",
            "tone": "precise",
            "language": "en-US",
        }
