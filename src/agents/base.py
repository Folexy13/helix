"""
Base Agent class for all Helix agents.

Provides common functionality for agent execution, tool use,
and integration with the Strands Agents SDK pattern.
"""

import logging
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar
from uuid import UUID, uuid4

from src.core.bedrock_client import BedrockClient, get_bedrock_client
from src.core.config import settings
from src.core.models import (
    AgentRole,
    Conversation,
    HITLCheckpoint,
    HITLDecision,
    HITLGateType,
    Message,
    MessageRole,
    ReasoningEffort,
    SessionState,
)

from src.utils.helpers import clean_content

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class AgentContext:
    """
    Context passed to agents during execution.
    
    Contains session state, conversation history, and any
    additional context needed for the agent to operate.
    """
    session_state: SessionState
    conversation: Conversation
    user_input: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # RAG context from Pillar 3 (if available)
    codebase_context: Optional[str] = None
    
    # Parent agent (for nested agent calls)
    parent_agent: Optional["BaseAgent"] = None
    
    # Tools available to this agent
    available_tools: List[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    """
    Response from an agent execution.
    
    Contains the output, any tool calls made, and metadata.
    """
    agent: AgentRole
    content: str
    reasoning: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    hitl_checkpoint: Optional[HITLCheckpoint] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    success: bool = True
    error: Optional[str] = None


class Tool:
    """
    Represents a tool that an agent can use.
    
    Tools are functions that agents can call to perform actions
    like web searches, file operations, or calling other agents.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
    
    def to_bedrock_format(self) -> Dict[str, Any]:
        """Convert tool to Bedrock tool format."""
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": self.parameters,
                        "required": list(self.parameters.keys()),
                    }
                }
            }
        }
    
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments."""
        return await self.handler(**kwargs)


class BaseAgent(ABC):
    """
    Abstract base class for all Helix agents.
    
    Provides common functionality for:
    - Interacting with Nova models via Bedrock
    - Managing conversation context
    - Tool registration and execution
    - HITL checkpoint creation
    - Agent-to-agent communication
    """
    
    def __init__(
        self,
        role: AgentRole,
        name: str,
        description: str,
        system_prompt: str,
        reasoning_effort: Optional[ReasoningEffort] = None,
        bedrock_client: Optional[BedrockClient] = None,
    ):
        """
        Initialize the agent.
        
        Args:
            role: The agent's role enum
            name: Human-readable name
            description: Description of the agent's purpose
            system_prompt: System prompt for the agent
            reasoning_effort: Extended thinking level (None = disabled)
            bedrock_client: Optional custom Bedrock client
        """
        self.role = role
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.reasoning_effort = reasoning_effort
        self.bedrock_client = bedrock_client or get_bedrock_client()
        
        # Registered tools
        self._tools: Dict[str, Tool] = {}
        
        # Register default tools
        self._register_default_tools()
        
        logger.info(f"Agent initialized: {self.name} ({self.role.value})")
    
    def _register_default_tools(self) -> None:
        """Register default tools available to all agents."""
        # NOTE: Disabled think tool as it causes "Model produced invalid sequence" errors
        # with Nova Lite. The model tries to use tools but generates invalid sequences.
        # For now, agents will work without tools.
        pass
    
    async def _think_handler(self, thought: str = "", **kwargs) -> str:
        """Handler for the think tool."""
        # Handle case where thought might be passed differently
        if not thought and kwargs:
            thought = str(kwargs.get('thought', kwargs.get('text', str(kwargs))))
        logger.debug(f"Agent {self.name} thinking: {thought[:100] if thought else 'empty'}...")
        return f"Thought recorded: {thought}"
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool for this agent."""
        self._tools[tool.name] = tool
        logger.debug(f"Tool registered for {self.name}: {tool.name}")
    
    def get_tools_for_bedrock(self) -> List[Dict[str, Any]]:
        """Get all tools in Bedrock format."""
        return [tool.to_bedrock_format() for tool in self._tools.values()]
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute the agent's main logic.
        
        This method must be implemented by each specific agent.
        
        Args:
            context: The execution context
            
        Returns:
            AgentResponse with the result
        """
        pass
    
    async def invoke_model(
        self,
        prompt: str,
        context: AgentContext,
        use_tools: bool = True,
        override_reasoning: Optional[ReasoningEffort] = None,
    ) -> Dict[str, Any]:
        """
        Invoke the Nova model with the given prompt.
        
        Args:
            prompt: The user prompt
            context: Agent context with conversation history
            use_tools: Whether to include tools in the request
            override_reasoning: Override the default reasoning effort
            
        Returns:
            Model response dictionary
        """
        # Build messages from conversation history
        messages = []
        for msg in context.conversation.messages[-settings.max_conversation_history:]:
            messages.append({
                "role": msg.role.value,
                "content": [{"text": msg.content}],
            })
        
        # Determine reasoning effort
        reasoning = override_reasoning or self.reasoning_effort
        
        # Nova 2 Lite supports extended thinking/reasoning
        # Always use Nova Lite - it handles both regular and reasoning requests
        model_id = settings.nova_lite_model_id
        
        # Get tools if enabled
        tools = self.get_tools_for_bedrock() if use_tools and self._tools else None
        
        # Invoke model
        response = await self.bedrock_client.generate_text(
            prompt=prompt,
            system_prompt=self.system_prompt,
            messages=messages,
            model_id=model_id,
            reasoning_effort=reasoning,
            tools=tools,
        )
        
        # Handle tool calls if present
        if response.get("tool_use"):
            response = await self._handle_tool_calls(response, context)
        
        # Clean response text
        if "text" in response:
            response["text"] = clean_content(response["text"])
        
        return response
    
    async def _handle_tool_calls(
        self,
        response: Dict[str, Any],
        context: AgentContext,
    ) -> Dict[str, Any]:
        """Handle tool calls from the model response."""
        tool_results = []
        
        for tool_call in response.get("tool_use", []):
            tool_name = tool_call.get("name")
            tool_input = tool_call.get("input", {})
            tool_id = tool_call.get("toolUseId")
            
            if tool_name in self._tools:
                try:
                    result = await self._tools[tool_name].execute(**tool_input)
                    tool_results.append({
                        "toolUseId": tool_id,
                        "content": [{"text": str(result)}],
                    })
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    tool_results.append({
                        "toolUseId": tool_id,
                        "content": [{"text": f"Error: {str(e)}"}],
                    })
            else:
                logger.warning(f"Unknown tool called: {tool_name}")
        
        # If we have tool results, continue the conversation
        if tool_results:
            # Add assistant message with tool use
            # Add tool results
            # Continue generation
            pass
        
        return response
    
    async def structured_extract(self, text: str, schema: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """
        Use the model to extract structured data from a text block.
        
        Args:
            text: The unstructured text to extract from
            schema: A dictionary describing the expected JSON keys and types
            context: Current agent context
            
        Returns:
            Dictionary with extracted data
        """
        prompt = f"""Extract the following structured information from the text below.
Return ONLY a valid JSON object matching this schema: {json.dumps(schema)}

TEXT TO ANALYZE:
{text}

JSON RESPONSE:"""

        try:
            response = await self.invoke_model(
                prompt=prompt,
                context=context,
                use_tools=False,
                override_reasoning=None # Extraction doesn't need deep thinking
            )
            
            # Find the JSON block in the response
            content = response.get("text", "{}")
            
            # Simple JSON extraction from text
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return json.loads(content)
        except Exception as e:
            logger.error(f"Structured extraction error: {e}")
            return {}

    def create_hitl_checkpoint(
        self,
        gate_type: HITLGateType,
        prompt: str,
        options: List[HITLDecision],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HITLCheckpoint:
        """
        Create a Human-in-the-Loop checkpoint.
        
        This pauses execution and waits for user input.
        
        Args:
            gate_type: Type of HITL gate
            prompt: Prompt to show the user
            options: Available decision options
            metadata: Additional metadata
            
        Returns:
            HITLCheckpoint object
        """
        checkpoint = HITLCheckpoint(
            gate_type=gate_type,
            pillar=self._get_pillar_number(),
            agent=self.role,
            prompt=prompt,
            options=options,
            metadata=metadata or {},
        )
        
        logger.info(f"HITL checkpoint created: {gate_type.value} by {self.name}")
        return checkpoint
    
    def _get_pillar_number(self) -> int:
        """Get the pillar number for this agent."""
        pillar1_roles = {AgentRole.ARIA, AgentRole.FELIX, AgentRole.NOVA, AgentRole.JUDGE, AgentRole.ROUTER}
        pillar2_roles = {AgentRole.PLANNER, AgentRole.CODER, AgentRole.TESTER, AgentRole.DOCS, AgentRole.REVIEWER, AgentRole.ORCHESTRATOR}
        pillar3_roles = {AgentRole.SAGE}
        
        if self.role in pillar1_roles:
            return 1
        elif self.role in pillar2_roles:
            return 2
        elif self.role in pillar3_roles:
            return 3
        return 0
    
    async def call_agent(
        self,
        agent: "BaseAgent",
        context: AgentContext,
        input_override: Optional[str] = None,
    ) -> AgentResponse:
        """
        Call another agent (agent-to-agent communication).
        
        This implements the Strands Agents `use_agent` pattern.
        
        Args:
            agent: The agent to call
            context: Current context (will be passed to child agent)
            input_override: Optional override for user input
            
        Returns:
            Response from the called agent
        """
        # Create child context
        child_context = AgentContext(
            session_state=context.session_state,
            conversation=context.conversation,
            user_input=input_override or context.user_input,
            metadata=context.metadata.copy(),
            codebase_context=context.codebase_context,
            parent_agent=self,
        )
        
        logger.info(f"Agent {self.name} calling agent {agent.name}")
        
        # Execute child agent
        response = await agent.execute(child_context)
        
        return response
    
    def format_response(
        self,
        content: str,
        reasoning: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        hitl_checkpoint: Optional[HITLCheckpoint] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> AgentResponse:
        """
        Format an agent response.
        
        Helper method to create consistent response objects.
        """
        return AgentResponse(
            agent=self.role,
            content=content,
            reasoning=reasoning,
            tool_calls=tool_calls or [],
            hitl_checkpoint=hitl_checkpoint,
            metadata=metadata or {},
            success=success,
            error=error,
        )
