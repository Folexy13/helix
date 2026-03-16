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
        
        # Validate endpoint URL if provided
        if self.endpoint_url:
            if not self.endpoint_url.startswith("https://"):
                logger.warning(f"Invalid endpoint URL format: {self.endpoint_url}. Using default endpoint.")
                self.endpoint_url = None
        
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
        model_id: Optional[str] = None,
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
        # Use config model ID if not specified
        if model_id is None:
            model_id = settings.nova_lite_model_id
        
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
        
        # NOTE: Extended thinking/reasoning is not currently supported via additionalModelRequestFields
        # for Nova models in the Converse API. The reasoning_effort parameter is accepted but not used.
        # Future versions may support this feature.
        
        # Add tools if specified
        if tools:
            request_body["toolConfig"] = {"tools": tools}
        
        import asyncio
        
        try:
            # Run synchronous boto3 call in thread pool to avoid blocking
            def _converse():
                return self._client.converse(
                    modelId=model_id,
                    **request_body,
                )
            
            response = await asyncio.to_thread(_converse)
            
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
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reasoning_effort: Optional[ReasoningEffort] = None,
    ) -> AsyncIterator[str]:
        """
        Stream text generation using Nova 2 Lite.
        
        Yields text chunks as they are generated.
        """
        # Use config model ID if not specified
        if model_id is None:
            model_id = settings.nova_lite_model_id
        
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
        
        # NOTE: Extended thinking/reasoning is not currently supported via additionalModelRequestFields
        # for Nova models in the Converse API. The reasoning_effort parameter is accepted but not used.
        
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
        model_id: Optional[str] = None,
    ) -> List[List[float]]:
        """
        Generate embeddings using Titan Text Embeddings.
        
        Args:
            inputs: Text strings (image embeddings not supported with Titan text model)
            input_type: Type of input ("text" only for Titan text model)
            model_id: Model ID to use
            
        Returns:
            List of embedding vectors
        """
        import asyncio
        
        # Use config model ID if not specified
        if model_id is None:
            model_id = settings.nova_embeddings_model_id
        
        # Titan text embedding model only supports text
        if input_type == "image":
            logger.warning("Image embeddings not supported with Titan text embedding model")
            return []
        
        if isinstance(inputs, (str, bytes)):
            inputs = [inputs]
        
        embeddings = []
        
        for input_item in inputs:
            # Build input for Titan text embedding model
            if isinstance(input_item, bytes):
                input_item = input_item.decode('utf-8', errors='ignore')
            
            input_body = {
                "inputText": str(input_item),
            }
            
            try:
                # Run synchronous boto3 call in thread pool to avoid blocking
                def _invoke():
                    return self._client.invoke_model(
                        modelId=model_id,
                        body=json.dumps(input_body),
                        contentType="application/json",
                        accept="application/json",
                    )
                
                response = await asyncio.to_thread(_invoke)
                
                response_body = json.loads(response["body"].read())
                embedding = response_body.get("embedding", [])
                embeddings.append(embedding)
                
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                # Return empty embedding instead of raising to allow indexing to continue
                embeddings.append([])
        
        return embeddings
    
    async def invoke_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model_id: str = NovaModel.NOVA_PRO.value,
        reasoning_effort: Optional[ReasoningEffort] = None,
    ) -> Dict[str, Any]:
        """
        Invoke model with tool use capability.
        
        Uses Nova Pro by default for better reasoning in tool-use scenarios.
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
