"""
Amazon Bedrock client for interacting with Nova models.

Provides a unified interface for:
- Nova 2 Lite (text generation with extended thinking)
- Nova 2 Sonic (speech-to-speech)
- Nova Multimodal Embeddings
"""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import boto3
from botocore.config import Config

from src.core.config import settings
from src.core.models import NovaModel, ReasoningEffort

logger = logging.getLogger(__name__)


class BedrockClient:
    """
    Client for Amazon Bedrock Runtime API.
    
    Handles all interactions with Nova models including:
    - Text generation with Nova 2 Lite
    - Extended thinking for complex reasoning
    - Embeddings generation with Nova Multimodal Embeddings
    - Voice interactions with Nova 2 Sonic
    """
    
    def __init__(
        self,
        region: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """
        Initialize the Bedrock client.
        
        Args:
            region: AWS region (defaults to settings)
            endpoint_url: Custom endpoint URL (optional)
        """
        self.region = region or settings.aws_region
        self.endpoint_url = endpoint_url or settings.bedrock_endpoint_url
        
        # Configure boto3 client
        config = Config(
            region_name=self.region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        
        client_kwargs = {"config": config}
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
        
        # Create Bedrock Runtime client
        self._client = boto3.client("bedrock-runtime", **client_kwargs)
        
        logger.info(f"BedrockClient initialized for region: {self.region}")
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model_id: str = NovaModel.NOVA_LITE.value,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[ReasoningEffort] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate text using Nova 2 Lite.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            messages: Optional conversation history
            model_id: Model ID to use
            temperature: Sampling temperature (0-1)
            top_p: Top-p sampling parameter
            max_tokens: Maximum tokens to generate
            reasoning_effort: Extended thinking effort level
            tools: Optional tools for function calling
            
        Returns:
            Response dictionary with generated text and metadata
        """
        # Build messages array
        if messages is None:
            messages = []
        
        # Add user message
        messages.append({"role": "user", "content": [{"text": prompt}]})
        
        # Build request body
        request_body = {
            "messages": messages,
            "inferenceConfig": {
                "temperature": temperature or settings.default_temperature,
                "topP": top_p or settings.default_top_p,
                "maxTokens": max_tokens or settings.default_max_tokens,
            },
        }
        
        # Add system prompt if provided
        if system_prompt:
            request_body["system"] = [{"text": system_prompt}]
        
        # Add extended thinking if specified
        # Note: Extended thinking is only supported on Nova Pro models
        # Disabled for now as Nova Lite doesn't support it
        # if reasoning_effort and "nova-pro" in model_id:
        #     request_body["additionalModelRequestFields"] = {
        #         "reasoningConfig": {
        #             "type": "enabled",
        #             "maxReasoningEffort": reasoning_effort.value,
        #         }
        #     }
        
        # Add tools if specified
        if tools:
            request_body["toolConfig"] = {"tools": tools}
        
        try:
            response = self._client.converse(
                modelId=model_id,
                **request_body,
            )
            
            # Extract response content
            output = response.get("output", {})
            message = output.get("message", {})
            content = message.get("content", [])
            
            # Extract text from content blocks
            text_content = ""
            reasoning_content = ""
            tool_use = []
            
            for block in content:
                if "text" in block:
                    text_content += block["text"]
                elif "reasoningContent" in block:
                    reasoning_content = block["reasoningContent"].get("reasoningText", "")
                elif "toolUse" in block:
                    tool_use.append(block["toolUse"])
            
            return {
                "text": text_content,
                "reasoning": reasoning_content,
                "tool_use": tool_use,
                "stop_reason": response.get("stopReason"),
                "usage": response.get("usage", {}),
                "metrics": response.get("metrics", {}),
            }
            
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            raise
    
    async def generate_text_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model_id: str = NovaModel.NOVA_LITE.value,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[ReasoningEffort] = None,
    ) -> AsyncIterator[str]:
        """
        Stream text generation using Nova 2 Lite.
        
        Yields text chunks as they are generated.
        """
        # Build messages array
        if messages is None:
            messages = []
        
        messages.append({"role": "user", "content": [{"text": prompt}]})
        
        request_body = {
            "messages": messages,
            "inferenceConfig": {
                "temperature": temperature or settings.default_temperature,
                "topP": top_p or settings.default_top_p,
                "maxTokens": max_tokens or settings.default_max_tokens,
            },
        }
        
        if system_prompt:
            request_body["system"] = [{"text": system_prompt}]
        
        if reasoning_effort:
            request_body["additionalModelRequestFields"] = {
                "reasoningConfig": {
                    "type": "enabled",
                    "maxReasoningEffort": reasoning_effort.value,
                }
            }
        
        try:
            response = self._client.converse_stream(
                modelId=model_id,
                **request_body,
            )
            
            stream = response.get("stream")
            if stream:
                for event in stream:
                    if "contentBlockDelta" in event:
                        delta = event["contentBlockDelta"].get("delta", {})
                        if "text" in delta:
                            yield delta["text"]
                            
        except Exception as e:
            logger.error(f"Error streaming text: {e}")
            raise
    
    async def generate_embeddings(
        self,
        inputs: Union[str, List[str], bytes, List[bytes]],
        input_type: str = "text",
        model_id: str = NovaModel.NOVA_EMBEDDINGS.value,
    ) -> List[List[float]]:
        """
        Generate embeddings using Nova Multimodal Embeddings.
        
        Args:
            inputs: Text strings, image bytes, or mixed inputs
            input_type: Type of input ("text", "image", "document")
            model_id: Model ID to use
            
        Returns:
            List of embedding vectors
        """
        if isinstance(inputs, (str, bytes)):
            inputs = [inputs]
        
        embeddings = []
        
        for input_item in inputs:
            # Build input based on type
            if input_type == "text":
                input_body = {
                    "inputText": input_item if isinstance(input_item, str) else input_item.decode(),
                }
            elif input_type == "image":
                import base64
                input_body = {
                    "inputImage": base64.b64encode(input_item).decode() if isinstance(input_item, bytes) else input_item,
                }
            else:
                input_body = {"inputText": str(input_item)}
            
            try:
                response = self._client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(input_body),
                    contentType="application/json",
                    accept="application/json",
                )
                
                response_body = json.loads(response["body"].read())
                embedding = response_body.get("embedding", [])
                embeddings.append(embedding)
                
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                raise
        
        return embeddings
    
    async def invoke_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model_id: str = NovaModel.NOVA_LITE.value,
        reasoning_effort: Optional[ReasoningEffort] = None,
    ) -> Dict[str, Any]:
        """
        Invoke model with tool use capability.
        
        Used for agent-to-agent communication and external tool calls.
        """
        return await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
            model_id=model_id,
            reasoning_effort=reasoning_effort,
            tools=tools,
        )
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        try:
            # Use bedrock client (not runtime) for model info
            bedrock = boto3.client("bedrock", region_name=self.region)
            response = bedrock.get_foundation_model(modelIdentifier=model_id)
            return response.get("modelDetails", {})
        except Exception as e:
            logger.warning(f"Could not get model info for {model_id}: {e}")
            return {}


# Global client instance
_bedrock_client: Optional[BedrockClient] = None


def get_bedrock_client() -> BedrockClient:
    """Get or create the global Bedrock client instance."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClient()
    return _bedrock_client
