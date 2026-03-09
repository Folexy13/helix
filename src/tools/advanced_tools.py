"""
Advanced Tools for Helix Agents

Implements specialized tools that leverage Nova 2 Lite's built-in capabilities:
- Web Grounding: Real-time web search for live data (FELIX/CFO)
- Code Interpreter: Execute and validate code (TESTER)
- Think Tool: Extended reasoning for complex analysis (REVIEWER, PLANNER)

These tools are critical differentiators for the hackathon.
"""

import asyncio
import json
import logging
import subprocess
import sys
import tempfile
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

import boto3
from botocore.config import Config

from src.core.config import settings

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories of tools."""
    WEB_GROUNDING = "web_grounding"
    CODE_INTERPRETER = "code_interpreter"
    REASONING = "reasoning"
    FILE_OPERATIONS = "file_operations"
    AGENT_COMMUNICATION = "agent_communication"


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    tool_name: str
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# WEB GROUNDING TOOL (for FELIX/CFO)
# =============================================================================

class WebGroundingTool:
    """
    Web Grounding Tool using Nova 2 Lite's built-in web search.
    
    Used by FELIX (CFO) to fetch real-time pricing data:
    - AWS service pricing
    - SaaS tool costs
    - API pricing
    - Market data
    """
    
    def __init__(self):
        config = Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        self._client = boto3.client("bedrock-runtime", config=config)
        
        logger.info("WebGroundingTool initialized")
    
    def get_tool_spec(self) -> Dict[str, Any]:
        """Get the tool specification for Bedrock."""
        return {
            "toolSpec": {
                "name": "web_search",
                "description": """Search the web for real-time information. 
                Use this to find current pricing, market data, statistics, 
                and other live information that may change over time.
                Returns relevant search results with sources.""",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["pricing", "market_data", "statistics", "general"],
                                "description": "Category of information to search for"
                            },
                            "recency": {
                                "type": "string",
                                "enum": ["day", "week", "month", "year"],
                                "description": "How recent the information should be"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        }
    
    async def execute(
        self,
        query: str,
        category: str = "general",
        recency: str = "month",
    ) -> ToolResult:
        """
        Execute a web search using Nova 2 Lite's web grounding.
        
        Args:
            query: Search query
            category: Type of information
            recency: How recent results should be
            
        Returns:
            ToolResult with search results
        """
        start_time = datetime.utcnow()
        
        try:
            # Build request with web grounding enabled
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": f"""Search the web for: {query}
                                
Category: {category}
Recency: Within the last {recency}

Provide accurate, up-to-date information with sources.
For pricing data, include specific numbers and dates.
Format the response as structured data."""
                            }
                        ]
                    }
                ],
                "inferenceConfig": {
                    "temperature": 0.1,  # Low temperature for factual data
                    "maxTokens": 2000,
                },
                # Enable web grounding
                "additionalModelRequestFields": {
                    "webGrounding": {
                        "enabled": True,
                        "searchConfig": {
                            "recency": recency,
                        }
                    }
                }
            }
            
            # Execute search
            response = await asyncio.to_thread(
                self._client.converse,
                modelId=settings.nova_lite_model_id,
                **request_body,
            )
            
            # Extract results
            output = response.get("output", {})
            message = output.get("message", {})
            content = message.get("content", [])
            
            text_content = ""
            sources = []
            
            for block in content:
                if "text" in block:
                    text_content += block["text"]
                elif "webGroundingResults" in block:
                    sources = block["webGroundingResults"].get("sources", [])
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ToolResult(
                success=True,
                tool_name="web_search",
                output={
                    "query": query,
                    "results": text_content,
                    "sources": sources,
                },
                execution_time=execution_time,
                metadata={
                    "category": category,
                    "recency": recency,
                }
            )
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ToolResult(
                success=False,
                tool_name="web_search",
                output=None,
                error=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )
    
    async def get_aws_pricing(self, service: str, region: str = "us-east-1") -> ToolResult:
        """Get current AWS service pricing."""
        query = f"AWS {service} pricing {region} current rates per hour month"
        return await self.execute(query, category="pricing", recency="week")
    
    async def get_saas_pricing(self, product: str) -> ToolResult:
        """Get SaaS product pricing."""
        query = f"{product} pricing plans cost per user month enterprise"
        return await self.execute(query, category="pricing", recency="month")
    
    async def get_api_pricing(self, api_name: str) -> ToolResult:
        """Get API pricing information."""
        query = f"{api_name} API pricing cost per request call"
        return await self.execute(query, category="pricing", recency="month")
    
    async def get_market_data(self, topic: str) -> ToolResult:
        """Get market data and statistics."""
        query = f"{topic} market size statistics trends 2024 2025"
        return await self.execute(query, category="market_data", recency="month")


# =============================================================================
# CODE INTERPRETER TOOL (for TESTER)
# =============================================================================

class CodeInterpreterTool:
    """
    Code Interpreter Tool using Nova 2 Lite's code execution.
    
    Used by TESTER to:
    - Execute test suites
    - Validate code syntax
    - Run code snippets
    - Check for runtime errors
    """
    
    SUPPORTED_LANGUAGES = ["python", "javascript", "typescript", "bash"]
    
    def __init__(self):
        config = Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        self._client = boto3.client("bedrock-runtime", config=config)
        
        # Sandbox configuration
        self._timeout = 30  # seconds
        self._max_output_size = 10000  # characters
        
        logger.info("CodeInterpreterTool initialized")
    
    def get_tool_spec(self) -> Dict[str, Any]:
        """Get the tool specification for Bedrock."""
        return {
            "toolSpec": {
                "name": "code_interpreter",
                "description": """Execute code and return the results.
                Supports Python, JavaScript, TypeScript, and Bash.
                Use this to run tests, validate code, and check for errors.
                Returns stdout, stderr, and exit code.""",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "The code to execute"
                            },
                            "language": {
                                "type": "string",
                                "enum": ["python", "javascript", "typescript", "bash"],
                                "description": "Programming language"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Execution timeout in seconds (max 30)"
                            }
                        },
                        "required": ["code", "language"]
                    }
                }
            }
        }
    
    async def execute(
        self,
        code: str,
        language: str,
        timeout: int = 30,
    ) -> ToolResult:
        """
        Execute code in a sandboxed environment.
        
        Args:
            code: Code to execute
            language: Programming language
            timeout: Execution timeout
            
        Returns:
            ToolResult with execution output
        """
        start_time = datetime.utcnow()
        
        if language not in self.SUPPORTED_LANGUAGES:
            return ToolResult(
                success=False,
                tool_name="code_interpreter",
                output=None,
                error=f"Unsupported language: {language}",
            )
        
        timeout = min(timeout, self._timeout)
        
        try:
            # Execute locally in sandbox
            result = await self._execute_local(code, language, timeout)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ToolResult(
                success=result["exit_code"] == 0,
                tool_name="code_interpreter",
                output={
                    "stdout": result["stdout"][:self._max_output_size],
                    "stderr": result["stderr"][:self._max_output_size],
                    "exit_code": result["exit_code"],
                },
                execution_time=execution_time,
                metadata={
                    "language": language,
                    "timeout": timeout,
                }
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                tool_name="code_interpreter",
                output=None,
                error=f"Execution timed out after {timeout} seconds",
                execution_time=timeout,
            )
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return ToolResult(
                success=False,
                tool_name="code_interpreter",
                output=None,
                error=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )
    
    async def _execute_local(
        self,
        code: str,
        language: str,
        timeout: int,
    ) -> Dict[str, Any]:
        """Execute code locally in a subprocess."""
        
        # Create temp file
        suffix = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "bash": ".sh",
        }[language]
        
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            delete=False,
        ) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Build command
            if language == "python":
                cmd = [sys.executable, temp_path]
            elif language == "javascript":
                cmd = ["node", temp_path]
            elif language == "typescript":
                cmd = ["npx", "ts-node", temp_path]
            elif language == "bash":
                cmd = ["bash", temp_path]
            else:
                raise ValueError(f"Unknown language: {language}")
            
            # Execute with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                raise
            
            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": process.returncode,
            }
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
    
    async def run_tests(
        self,
        test_code: str,
        language: str = "python",
    ) -> ToolResult:
        """Run a test suite and return results."""
        
        if language == "python":
            # Wrap in pytest runner
            wrapped_code = f"""
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# Test code
{test_code}

# Run tests
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["-v", __file__]))
"""
        else:
            wrapped_code = test_code
        
        return await self.execute(wrapped_code, language)
    
    async def validate_syntax(
        self,
        code: str,
        language: str,
    ) -> ToolResult:
        """Validate code syntax without executing."""
        
        if language == "python":
            validation_code = f"""
import ast
import sys

code = '''{code}'''

try:
    ast.parse(code)
    print("Syntax OK")
    sys.exit(0)
except SyntaxError as e:
    print(f"Syntax Error: {{e}}")
    sys.exit(1)
"""
            return await self.execute(validation_code, "python")
        
        # For other languages, try to compile/parse
        return await self.execute(code, language)


# =============================================================================
# EXTENDED THINKING TOOL (for PLANNER, REVIEWER)
# =============================================================================

class ExtendedThinkingTool:
    """
    Extended Thinking Tool using Nova Pro's reasoning capabilities.
    
    Used by PLANNER and REVIEWER for:
    - Complex problem decomposition
    - Multi-step reasoning
    - Edge case analysis
    - Security vulnerability detection
    """
    
    def __init__(self):
        config = Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        self._client = boto3.client("bedrock-runtime", config=config)
        
        logger.info("ExtendedThinkingTool initialized")
    
    def get_tool_spec(self) -> Dict[str, Any]:
        """Get the tool specification for Bedrock."""
        return {
            "toolSpec": {
                "name": "think",
                "description": """Engage in extended thinking for complex reasoning.
                Use this for multi-step analysis, problem decomposition,
                edge case identification, and deep technical analysis.
                Returns both the reasoning process and conclusions.""",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "problem": {
                                "type": "string",
                                "description": "The problem or question to analyze"
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context for the analysis"
                            },
                            "effort": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "Reasoning effort level"
                            }
                        },
                        "required": ["problem"]
                    }
                }
            }
        }
    
    async def execute(
        self,
        problem: str,
        context: str = "",
        effort: str = "medium",
    ) -> ToolResult:
        """
        Execute extended thinking analysis.
        
        Args:
            problem: Problem to analyze
            context: Additional context
            effort: Reasoning effort level
            
        Returns:
            ToolResult with reasoning and conclusions
        """
        start_time = datetime.utcnow()
        
        try:
            # Build request with extended thinking
            system_prompt = """You are an expert analyst with deep technical knowledge.
            
When analyzing problems:
1. Break down the problem into components
2. Consider multiple perspectives
3. Identify edge cases and potential issues
4. Reason through each step carefully
5. Provide clear, actionable conclusions

Show your reasoning process explicitly."""

            user_prompt = f"""Problem: {problem}

{f"Context: {context}" if context else ""}

Analyze this thoroughly and provide:
1. Problem breakdown
2. Key considerations
3. Potential issues or edge cases
4. Recommendations
5. Confidence level in your analysis"""

            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": user_prompt}]
                    }
                ],
                "system": [{"text": system_prompt}],
                "inferenceConfig": {
                    "temperature": 0.3,
                    "maxTokens": 4000,
                },
                # Enable extended thinking (Nova Pro only)
                "additionalModelRequestFields": {
                    "reasoningConfig": {
                        "type": "enabled",
                        "maxReasoningEffort": effort,
                    }
                }
            }
            
            # Use Nova Pro for extended thinking
            model_id = "amazon.nova-pro-v1:0"
            
            response = await asyncio.to_thread(
                self._client.converse,
                modelId=model_id,
                **request_body,
            )
            
            # Extract results
            output = response.get("output", {})
            message = output.get("message", {})
            content = message.get("content", [])
            
            text_content = ""
            reasoning_content = ""
            
            for block in content:
                if "text" in block:
                    text_content += block["text"]
                elif "reasoningContent" in block:
                    reasoning_content = block["reasoningContent"].get("reasoningText", "")
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return ToolResult(
                success=True,
                tool_name="think",
                output={
                    "reasoning": reasoning_content,
                    "conclusions": text_content,
                },
                execution_time=execution_time,
                metadata={
                    "effort": effort,
                    "model": model_id,
                }
            )
            
        except Exception as e:
            logger.error(f"Extended thinking failed: {e}")
            return ToolResult(
                success=False,
                tool_name="think",
                output=None,
                error=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )
    
    async def analyze_security(self, code: str, language: str) -> ToolResult:
        """Analyze code for security vulnerabilities."""
        problem = f"""Analyze this {language} code for security vulnerabilities:

```{language}
{code}
```

Look for:
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication/authorization issues
- Data exposure risks
- Insecure configurations
- Cryptographic weaknesses
- Input validation issues"""
        
        return await self.execute(problem, effort="high")
    
    async def decompose_task(self, task: str, constraints: str = "") -> ToolResult:
        """Decompose a complex task into subtasks."""
        problem = f"""Decompose this software engineering task into subtasks:

Task: {task}

{f"Constraints: {constraints}" if constraints else ""}

Provide:
1. Ordered list of subtasks
2. Dependencies between subtasks
3. Estimated complexity for each
4. Potential blockers or risks"""
        
        return await self.execute(problem, effort="medium")
    
    async def review_architecture(self, architecture: str) -> ToolResult:
        """Review a system architecture."""
        problem = f"""Review this system architecture:

{architecture}

Analyze:
1. Scalability considerations
2. Single points of failure
3. Security boundaries
4. Performance bottlenecks
5. Maintainability concerns
6. Cost implications"""
        
        return await self.execute(problem, effort="high")


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolRegistry:
    """
    Registry of all available tools.
    
    Provides a unified interface for tool discovery and execution.
    """
    
    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._initialize_tools()
        
        logger.info(f"ToolRegistry initialized with {len(self._tools)} tools")
    
    def _initialize_tools(self) -> None:
        """Initialize all available tools."""
        self._tools = {
            "web_search": WebGroundingTool(),
            "code_interpreter": CodeInterpreterTool(),
            "think": ExtendedThinkingTool(),
        }
    
    def get_tool(self, name: str) -> Optional[Any]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_tool_specs(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get tool specifications for Bedrock."""
        if tool_names is None:
            tool_names = list(self._tools.keys())
        
        specs = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool and hasattr(tool, "get_tool_spec"):
                specs.append(tool.get_tool_spec())
        
        return specs
    
    async def execute_tool(
        self,
        name: str,
        **kwargs,
    ) -> ToolResult:
        """Execute a tool by name."""
        tool = self._tools.get(name)
        
        if not tool:
            return ToolResult(
                success=False,
                tool_name=name,
                output=None,
                error=f"Unknown tool: {name}",
            )
        
        if not hasattr(tool, "execute"):
            return ToolResult(
                success=False,
                tool_name=name,
                output=None,
                error=f"Tool {name} does not support execution",
            )
        
        return await tool.execute(**kwargs)
    
    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self._tools.keys())


# Global registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
