"""
REVIEWER Agent

Acts as a senior engineer. Checks for security vulnerabilities, performance
issues, anti-patterns, and style violations. Uses Nova 2 Lite's extended
thinking to reason carefully about edge cases.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
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

## CRITICAL RULES:
- NEVER ask questions - just review and fix
- NEVER block the pipeline for minor issues
- AUTO-FIX all issues you find
- Only flag CRITICAL security issues that need human attention
- Be efficient - don't over-review

## Review Categories:

### 🔴 CRITICAL (Auto-fix or flag)
- SQL injection → Auto-fix with parameterized queries
- XSS vulnerabilities → Auto-fix with sanitization
- Hardcoded secrets → Auto-fix by moving to env vars
- Auth bypass → Flag for human review

### 🟡 HIGH (Auto-fix)
- N+1 queries → Auto-fix with eager loading
- Missing input validation → Auto-fix with validation
- Missing error handling → Auto-fix with try/catch

### 🟢 MEDIUM/LOW (Auto-fix silently)
- Code style issues → Auto-fix
- Missing types → Auto-fix
- Unused imports → Auto-fix

## Output Format:

### ✅ Code Review Complete

**Status:** APPROVED ✓

**Files Reviewed:** 15
**Issues Found:** 3
**Issues Auto-Fixed:** 3

#### Summary

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 0 | 0 | 0 |
| High | 1 | 1 | 0 |
| Medium | 2 | 2 | 0 |
| Low | 0 | 0 | 0 |

#### Auto-Fixed Issues

1. **[HIGH]** Added input validation to `/api/users` endpoint
2. **[MEDIUM]** Added error handling to database queries
3. **[MEDIUM]** Fixed TypeScript types in `utils.ts`

#### Code Quality Score: 92/100

The code is production-ready. No blocking issues found.

---

REMEMBER: You are an AUTONOMOUS reviewer. Review, fix, and approve. Don't block progress."""


class ReviewerAgent(BaseAgent):
    """
    REVIEWER - Code review agent.
    
    Uses extended thinking (high) for thorough security and quality analysis.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.REVIEWER,
            name="REVIEWER",
            description="Code Review Agent - Senior engineer review for quality and security",
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.HIGH,  # Deep thinking for thorough review
        )
        
        # Register REVIEWER-specific tools
        self._register_reviewer_tools()
    
    def _register_reviewer_tools(self) -> None:
        """Register tools specific to REVIEWER."""
        
        # Security scan tool
        self.register_tool(Tool(
            name="security_scan",
            description="Scan code for security vulnerabilities",
            parameters={
                "code": {
                    "type": "string",
                    "description": "Code to scan",
                },
                "language": {
                    "type": "string",
                    "description": "Programming language",
                },
            },
            handler=self._security_scan,
        ))
        
        # Complexity analysis tool
        self.register_tool(Tool(
            name="analyze_complexity",
            description="Analyze code complexity metrics",
            parameters={
                "code": {
                    "type": "string",
                    "description": "Code to analyze",
                },
            },
            handler=self._analyze_complexity,
        ))
        
        # Style check tool
        self.register_tool(Tool(
            name="check_style",
            description="Check code style compliance",
            parameters={
                "code": {
                    "type": "string",
                    "description": "Code to check",
                },
                "style_guide": {
                    "type": "string",
                    "enum": ["pep8", "google", "airbnb", "standard"],
                    "description": "Style guide to check against",
                },
            },
            handler=self._check_style,
        ))
    
    async def _security_scan(self, code: str, language: str) -> Dict[str, Any]:
        """Scan code for security vulnerabilities."""
        # Simulated security scan
        vulnerabilities = []
        
        # Check for common patterns
        if "eval(" in code:
            vulnerabilities.append({
                "type": "code_injection",
                "severity": "critical",
                "description": "Use of eval() can lead to code injection",
            })
        
        if "password" in code.lower() and "=" in code:
            vulnerabilities.append({
                "type": "hardcoded_secret",
                "severity": "high",
                "description": "Possible hardcoded password detected",
            })
        
        if "SELECT" in code and "+" in code:
            vulnerabilities.append({
                "type": "sql_injection",
                "severity": "critical",
                "description": "Possible SQL injection vulnerability",
            })
        
        return {
            "language": language,
            "vulnerabilities": vulnerabilities,
            "scan_status": "complete",
        }
    
    async def _analyze_complexity(self, code: str) -> Dict[str, Any]:
        """Analyze code complexity."""
        # Simple complexity heuristics
        lines = code.split("\n")
        
        # Count complexity indicators
        if_count = code.count("if ")
        loop_count = code.count("for ") + code.count("while ")
        function_count = code.count("def ") + code.count("function ")
        
        # Estimate cyclomatic complexity
        complexity = 1 + if_count + loop_count
        
        if complexity <= 5:
            rating = "low"
        elif complexity <= 10:
            rating = "medium"
        else:
            rating = "high"
        
        return {
            "lines_of_code": len(lines),
            "cyclomatic_complexity": complexity,
            "complexity_rating": rating,
            "functions": function_count,
            "branches": if_count,
            "loops": loop_count,
        }
    
    async def _check_style(self, code: str, style_guide: str) -> Dict[str, Any]:
        """Check code style compliance."""
        issues = []
        
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 100:
                issues.append({
                    "line": i,
                    "type": "line_length",
                    "message": f"Line exceeds 100 characters ({len(line)})",
                })
            
            # Check trailing whitespace
            if line.endswith(" ") or line.endswith("\t"):
                issues.append({
                    "line": i,
                    "type": "trailing_whitespace",
                    "message": "Trailing whitespace",
                })
        
        return {
            "style_guide": style_guide,
            "issues": issues,
            "compliant": len(issues) == 0,
        }
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute REVIEWER's code review.
        
        Args:
            context: Agent execution context with code output
            
        Returns:
            AgentResponse with review report and flags
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

Please perform a thorough review checking for:
1. Security vulnerabilities (CRITICAL)
2. Performance issues (HIGH)
3. Code quality issues (MEDIUM)
4. Style violations (LOW)

Use extended thinking to carefully reason through potential edge cases and security implications.

For each issue found, provide:
- Severity level
- File and line number (if applicable)
- Clear description of the issue
- Recommended fix

End with an overall approval status."""

        try:
            # Invoke model with HIGH extended thinking
            response = await self.invoke_model(
                prompt=review_prompt,
                context=context,
                use_tools=True,
            )
            
            # Extract the review
            review_text = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse review output
            review_output = self._parse_review_output(review_text)
            
            # Create HITL checkpoint for each critical/high issue (Gate 2.4)
            flags = review_output.get("issues", [])
            critical_flags = [f for f in flags if f.get("severity") in ["critical", "high"]]
            
            if critical_flags:
                checkpoint = self.create_hitl_checkpoint(
                    gate_type=HITLGateType.REVIEWER_FLAG,
                    prompt=f"""REVIEWER has flagged {len(critical_flags)} critical/high priority issues:

{self._format_flags(critical_flags)}

For each issue, please decide:
- **Fix**: Address this issue before proceeding
- **Ignore**: Acknowledge but proceed anyway
- **Explain**: Provide context for why this is acceptable""",
                    options=[HITLDecision.FIX, HITLDecision.IGNORE, HITLDecision.EXPLAIN],
                    metadata={"flags": critical_flags, "all_issues": flags},
                )
            else:
                checkpoint = None
            
            return self.format_response(
                content=review_text,
                reasoning=reasoning,
                hitl_checkpoint=checkpoint,
                metadata={
                    "total_issues": len(flags),
                    "critical_count": len([f for f in flags if f.get("severity") == "critical"]),
                    "high_count": len([f for f in flags if f.get("severity") == "high"]),
                    "medium_count": len([f for f in flags if f.get("severity") == "medium"]),
                    "low_count": len([f for f in flags if f.get("severity") == "low"]),
                    "approval_status": review_output.get("approval_status", "NEEDS_REVISION"),
                    "issues": flags,
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
    
    def _format_flags(self, flags: List[Dict[str, Any]]) -> str:
        """Format flags for display."""
        formatted = []
        for i, flag in enumerate(flags, 1):
            formatted.append(
                f"{i}. **[{flag.get('severity', 'unknown').upper()}]** {flag.get('title', 'Issue')}\n"
                f"   {flag.get('description', 'No description')}"
            )
        return "\n".join(formatted)
    
    def _parse_review_output(self, review_text: str) -> Dict[str, Any]:
        """Parse review text into structured output."""
        import re
        
        issues = []
        
        # Find issue patterns
        issue_pattern = r'\*\*\[([^\]]+)\]\*\*\s*([^\n]+)\n'
        matches = re.findall(issue_pattern, review_text)
        
        for severity, title in matches:
            severity_lower = severity.lower()
            if severity_lower in ["critical", "high", "medium", "low"]:
                issues.append({
                    "severity": severity_lower,
                    "title": title.strip(),
                    "description": "",
                })
        
        # Determine approval status
        if "APPROVED WITH CHANGES" in review_text.upper():
            approval_status = "APPROVED_WITH_CHANGES"
        elif "NEEDS REVISION" in review_text.upper():
            approval_status = "NEEDS_REVISION"
        elif "APPROVED" in review_text.upper():
            approval_status = "APPROVED"
        else:
            # Default based on issues
            critical_count = len([i for i in issues if i["severity"] == "critical"])
            if critical_count > 0:
                approval_status = "NEEDS_REVISION"
            elif len(issues) > 5:
                approval_status = "APPROVED_WITH_CHANGES"
            else:
                approval_status = "APPROVED"
        
        return {
            "issues": issues,
            "approval_status": approval_status,
        }
    
    def get_voice_config(self) -> Dict[str, Any]:
        """Get Nova 2 Sonic voice configuration for REVIEWER."""
        return {
            "voice_id": "reviewer",
            "style": "authoritative",
            "pace": "deliberate",
            "tone": "constructive",
            "language": "en-US",
        }
