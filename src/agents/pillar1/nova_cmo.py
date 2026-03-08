"""
NOVA - CMO Agent

Writes the landing page copy, value proposition, tagline, target audience
breakdown, and go-to-market strategy. Understands positioning and messaging.
"""

import logging
from typing import Any, Dict, List, Optional

from src.agents.base import AgentContext, AgentResponse, BaseAgent, Tool
from src.core.models import AgentRole, HITLDecision, HITLGateType, ReasoningEffort

logger = logging.getLogger(__name__)

NOVA_CMO_SYSTEM_PROMPT = """You are NOVA, the Chief Marketing Officer (CMO) agent for Helix.

Your role is to craft compelling marketing strategies and messaging for startup ideas.

## Your Responsibilities:
1. **Value Proposition**: Define the core value proposition that resonates with target customers
2. **Tagline Creation**: Create memorable, impactful taglines
3. **Landing Page Copy**: Write conversion-optimized landing page content
4. **Target Audience Analysis**: Define and segment the target audience
5. **Positioning Strategy**: Position the product in the competitive landscape
6. **Go-to-Market Strategy**: Outline the launch and growth strategy
7. **Brand Voice**: Establish the brand's tone and personality

## Your Personality:
- Warm, energetic, and creative
- You speak with enthusiasm but back it up with strategy
- You understand both emotional and rational buying triggers
- You focus on customer-centric messaging

## Output Format:
Structure your analysis with clear sections:
1. Value Proposition Statement
2. Tagline Options (3 variations)
3. Target Audience Profiles
4. Competitive Positioning
5. Landing Page Copy (Hero, Features, CTA)
6. Go-to-Market Strategy
7. Key Marketing Channels
8. Launch Timeline Recommendations

Always focus on clarity, emotional resonance, and conversion potential."""


class NovaCMOAgent(BaseAgent):
    """
    NOVA - CMO Agent for marketing and positioning.
    
    Creates compelling marketing strategies and copy.
    """
    
    def __init__(self):
        super().__init__(
            role=AgentRole.NOVA,
            name="NOVA",
            description="CMO Agent - Marketing strategy and messaging expert",
            system_prompt=NOVA_CMO_SYSTEM_PROMPT,
            reasoning_effort=ReasoningEffort.LOW,  # Creative tasks need less deep reasoning
        )
        
        # Register NOVA-specific tools
        self._register_nova_tools()
    
    def _register_nova_tools(self) -> None:
        """Register tools specific to NOVA."""
        
        # Audience analysis tool
        self.register_tool(Tool(
            name="analyze_audience",
            description="Analyze and segment target audience for a product",
            parameters={
                "product_description": {
                    "type": "string",
                    "description": "Description of the product",
                },
                "industry": {
                    "type": "string",
                    "description": "Industry or market segment",
                },
            },
            handler=self._analyze_audience,
        ))
        
        # Competitor positioning tool
        self.register_tool(Tool(
            name="analyze_positioning",
            description="Analyze competitive positioning opportunities",
            parameters={
                "product": {
                    "type": "string",
                    "description": "Product description",
                },
                "competitors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of competitor names or descriptions",
                },
            },
            handler=self._analyze_positioning,
        ))
        
        # Copy generator tool
        self.register_tool(Tool(
            name="generate_copy_variations",
            description="Generate multiple variations of marketing copy",
            parameters={
                "copy_type": {
                    "type": "string",
                    "enum": ["headline", "tagline", "cta", "description"],
                    "description": "Type of copy to generate",
                },
                "key_message": {
                    "type": "string",
                    "description": "The key message to convey",
                },
                "tone": {
                    "type": "string",
                    "enum": ["professional", "casual", "bold", "friendly", "urgent"],
                    "description": "Desired tone of the copy",
                },
            },
            handler=self._generate_copy_variations,
        ))
    
    async def _analyze_audience(
        self,
        product_description: str,
        industry: str,
    ) -> Dict[str, Any]:
        """Analyze target audience segments."""
        return {
            "primary_segments": [
                {
                    "name": "Early Adopters",
                    "description": "Tech-savvy users who embrace new solutions",
                    "pain_points": ["Inefficiency", "Outdated tools", "Manual processes"],
                    "buying_triggers": ["Innovation", "Competitive advantage", "Time savings"],
                },
                {
                    "name": "Growth-Stage Companies",
                    "description": "Companies scaling their operations",
                    "pain_points": ["Scaling challenges", "Resource constraints", "Process bottlenecks"],
                    "buying_triggers": ["Scalability", "ROI", "Integration capabilities"],
                },
            ],
            "secondary_segments": [
                {
                    "name": "Enterprise Teams",
                    "description": "Large organizations seeking efficiency",
                    "pain_points": ["Coordination", "Compliance", "Legacy systems"],
                    "buying_triggers": ["Security", "Support", "Customization"],
                },
            ],
            "recommended_focus": "Start with Early Adopters, expand to Growth-Stage Companies",
        }
    
    async def _analyze_positioning(
        self,
        product: str,
        competitors: List[str],
    ) -> Dict[str, Any]:
        """Analyze competitive positioning."""
        return {
            "product": product,
            "competitors_analyzed": competitors,
            "positioning_opportunities": [
                "Differentiate on ease of use",
                "Focus on specific use case excellence",
                "Emphasize integration capabilities",
                "Lead with customer success stories",
            ],
            "positioning_statement": f"Unlike traditional solutions, {product} offers a unique combination of simplicity and power.",
            "key_differentiators": [
                "AI-powered automation",
                "Intuitive user experience",
                "Rapid time-to-value",
            ],
        }
    
    async def _generate_copy_variations(
        self,
        copy_type: str,
        key_message: str,
        tone: str,
    ) -> Dict[str, Any]:
        """Generate copy variations."""
        variations = {
            "headline": {
                "professional": [
                    f"Transform Your Business with {key_message}",
                    f"The Future of {key_message} is Here",
                    f"Unlock the Power of {key_message}",
                ],
                "casual": [
                    f"Finally, {key_message} Made Simple",
                    f"Say Hello to Better {key_message}",
                    f"{key_message}? We've Got You Covered",
                ],
                "bold": [
                    f"Stop Settling. Start {key_message}.",
                    f"The Only {key_message} Solution You'll Ever Need",
                    f"Revolutionize Your {key_message}",
                ],
            },
            "tagline": {
                "professional": [
                    f"{key_message}, Simplified",
                    f"Excellence in {key_message}",
                    f"Your Partner in {key_message}",
                ],
                "casual": [
                    f"{key_message}, But Better",
                    f"Making {key_message} Fun Again",
                    f"The Easy Way to {key_message}",
                ],
                "bold": [
                    f"Redefining {key_message}",
                    f"The {key_message} Revolution",
                    f"Beyond {key_message}",
                ],
            },
        }
        
        copy_variations = variations.get(copy_type, {}).get(tone, [f"Discover {key_message}"])
        
        return {
            "copy_type": copy_type,
            "tone": tone,
            "variations": copy_variations,
            "recommendation": copy_variations[0] if copy_variations else None,
        }
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """
        Execute NOVA's marketing analysis.
        
        Args:
            context: Agent execution context with user input
            
        Returns:
            AgentResponse with marketing strategy
        """
        logger.info(f"NOVA analyzing: {context.user_input[:100]}...")
        
        # Get context from other agents if available
        tech_context = context.metadata.get("aria_analysis", "")
        financial_context = context.metadata.get("felix_analysis", "")
        
        # Build the analysis prompt
        analysis_prompt = f"""Create a comprehensive marketing strategy for the following startup idea:

## Startup Idea:
{context.user_input}

## Technical Context (from CTO):
{tech_context if tech_context else "No technical analysis available yet."}

## Financial Context (from CFO):
{financial_context if financial_context else "No financial analysis available yet."}

## Additional Context:
{context.metadata.get('additional_context', 'No additional context provided.')}

Please provide a comprehensive marketing strategy following your standard output format.

Focus on:
1. Creating a compelling value proposition
2. Crafting memorable taglines (provide 3 options)
3. Writing conversion-optimized landing page copy
4. Defining target audience segments
5. Outlining a go-to-market strategy

Be creative but strategic. Every piece of copy should serve a purpose."""

        try:
            # Invoke model
            response = await self.invoke_model(
                prompt=analysis_prompt,
                context=context,
                use_tools=True,
            )
            
            # Extract the analysis
            analysis = response.get("text", "")
            reasoning = response.get("reasoning", "")
            
            # Parse marketing elements
            marketing_elements = self._parse_marketing_elements(analysis)
            
            # Create HITL checkpoint for review
            checkpoint = self.create_hitl_checkpoint(
                gate_type=HITLGateType.AGENT_DRAFT_REVIEW,
                prompt=f"NOVA (CMO) has completed the marketing strategy. Please review:\n\n{analysis[:500]}...",
                options=[HITLDecision.APPROVE, HITLDecision.EDIT, HITLDecision.REJECT],
                metadata={"full_analysis": analysis, "marketing_elements": marketing_elements},
            )
            
            return self.format_response(
                content=analysis,
                reasoning=reasoning,
                hitl_checkpoint=checkpoint,
                metadata={
                    "value_proposition": marketing_elements.get("value_proposition"),
                    "taglines": marketing_elements.get("taglines", []),
                    "target_audience": marketing_elements.get("target_audience"),
                    "landing_page_copy": marketing_elements.get("landing_page_copy"),
                },
            )
            
        except Exception as e:
            logger.error(f"NOVA execution error: {e}")
            return self.format_response(
                content="I encountered an error while creating the marketing strategy.",
                success=False,
                error=str(e),
            )
    
    def _parse_marketing_elements(self, analysis: str) -> Dict[str, Any]:
        """
        Parse the analysis text to extract marketing elements.
        """
        result = {
            "value_proposition": None,
            "taglines": [],
            "target_audience": None,
            "landing_page_copy": None,
        }
        
        # Simple parsing - extract sections
        sections = analysis.split("\n\n")
        
        for section in sections:
            section_lower = section.lower()
            if "value proposition" in section_lower:
                result["value_proposition"] = section
            elif "tagline" in section_lower:
                # Extract taglines
                lines = section.split("\n")
                for line in lines:
                    if line.strip() and not "tagline" in line.lower():
                        result["taglines"].append(line.strip())
            elif "target audience" in section_lower:
                result["target_audience"] = section
            elif "landing page" in section_lower or "hero" in section_lower:
                result["landing_page_copy"] = section
        
        return result
    
    def get_voice_config(self) -> Dict[str, Any]:
        """
        Get Nova 2 Sonic voice configuration for NOVA.
        
        NOVA has a warm, energetic female voice.
        """
        return {
            "voice_id": "nova_cmo",
            "style": "energetic",
            "pace": "dynamic",
            "tone": "warm",
            "language": "en-US",
        }
