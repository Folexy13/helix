"""
REVIEWER Agent

Automatically reviews code and auto-fixes issues.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

REVIEWER_SYSTEM_PROMPT = """You are the REVIEWER agent for Helix's Engineering Workforce.

Your role is to AUTOMATICALLY review code and FIX issues - no questions asked.
You are a senior engineer who reviews AND fixes problems.

## Your Responsibilities:
1. **Review Code**: Check for security, performance, and quality issues
2. **Auto-Fix Issues**: Fix any issues you find automatically
3. **Report Summary**: Provide a brief summary of what was reviewed/fixed
4. **Approve**: If code is good, approve it

CRITICAL RULES:
- NEVER ask questions - just review and fix
- NEVER block the pipeline for minor issues
- AUTO-FIX all issues you find
- Only flag CRITICAL security issues that need human attention
- Be efficient - don't over-review

Output Format:
Provide a summary of the review, including:
- Files Reviewed
- Issues Found
- Issues Auto-Fixed
- Code Quality Score

End with a clear overall approval status."""


class ReviewerAgent(BaseAgent):
    """
    REVIEWER - Code review agent.
    
    Uses autonomous logic to review and approve code.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.REVIEWER,
            name="REVIEWER",
            description="Code Review Agent - Senior engineer review for quality and security",
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.HIGH,  # Deep thinking for thorough review
        )
        
        # Specialist agents now operate autonomously without tool-calling overhead.
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute REVIEWER's code review.
        
        Args:
            context: Agent execution context with code output
            
        Returns:
            AgentResponse with review report
        """
        logger.info(f"REVIEWER analyzing: {context.user_input[:100]}...")
        
        # Get the code output from CODER
        code_output = context.metadata.get("code_output", {})
        files = code_output.get("files", {})
        tests = code_output.get("tests", {})
        
        # Build the review prompt
        review_prompt = f"""Perform a comprehensive code review for the following code:

## Feature Description:
{context.user_input}

## Code Files:
{self._format_code_files(files)}

## Test Files:
{self._format_code_files(tests)}

## Engineering Specification:
{context.metadata.get('spec_text', 'No specification provided.')}

Please perform a thorough review and auto-fix any issues found."""

        try:
            # Invoke model
            # NOTE: use_tools=False to avoid "Model produced invalid sequence" errors
            response = await self.invoke_model(
                prompt=review_prompt,
                context=context,
                use_tools=False,
            )
            
            # Extract the review
            review_text = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            return self.format_response(
                content=review_text,
                reasoning=reasoning,
                metadata={
                    "total_issues": 0,
                    "approval_status": "APPROVED",
                },
            )
            
        except Exception as e:
            logger.error(f"REVIEWER execution error: {e}")
            return self.format_response(
                content="I encountered an error while reviewing the code.",
                success=False,
                error=str(e),
            )
    
    def _format_code_files(self, files: Dict[str, str]) -> str:
        """Format code files for the prompt."""
        if not files:
            return "No files provided."
        
        formatted = []
        for path, content in files.items():
            if len(content) > 2000:
                content = content[:2000] + "\n... (truncated)"
            formatted.append(f"### {path}\n```\n{content}\n```")
        
        return "\n\n".join(formatted)
    
    def get_voice_config(self) -> Dict[str, Any]:
        """Get Nova 2 Sonic voice configuration for REVIEWER."""
        return {
            "voice_id": "reviewer",
            "style": "authoritative",
            "pace": "deliberate",
            "tone": "constructive",
            "language": "en-US",
        }
