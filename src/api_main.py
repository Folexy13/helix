"""
API Module

FastAPI application providing the backend for the Helix frontend dashboard.
Includes Socket.IO for real-time bidirectional communication.

Enhanced with:
- Intelligent HITL with follow-up questions
- Smart agent handoffs with context awareness
- Bidirectional conversation support
- Real-time agent status streaming
- Nova 2 Sonic voice interactions
- Nova Act GitHub automation
- Advanced tools (web grounding, code interpreter, extended thinking)
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
import uvicorn

from src.core.models import SessionState, HITLDecision, AgentRole, HITLGateType
from src.core.orchestration import (
    IntelligentOrchestrator,
    SmartCheckpoint,
    AgentHandoff,
    HandoffReason,
    ConversationTurn,
)
from src.hitl.handlers import APIHITLHandler
from src.hitl.checkpoint_manager import CheckpointManager
from src.agents.pillar2.orchestrator import OrchestratorAgent
from src.agents.pillar1.router import RouterAgent
from src.agents.pillar3.sage import SageAgent
from src.agents.base import AgentContext, AgentResponse
from src.utils.helpers import save_project_files

# Import new modules
from src.api.voice_endpoints import router as voice_router
from src.api.github_oauth import router as github_router
from src.automation import get_github_automation
from src.tools import get_tool_registry
from src.embeddings import get_codebase_indexer
from src.core.redis_storage import get_storage, close_storage

logger = logging.getLogger(__name__)

# --- Setup FastAPI ---
app = FastAPI(
    title="Helix API",
    version="0.3.0",
    description="""
    Helix - Intelligence That Spirals Forward
    
    AI-powered platform with:
    - Pillar 1: Founding Team (AI Startup Co-Founder)
    - Pillar 2: Engineering Workforce (Autonomous Coding Agents)
    - Pillar 3: Codebase Intelligence (Ask Your Codebase)
    
    Powered by Amazon Nova 2 Lite, Nova 2 Sonic, Nova Act, and Nova Multimodal Embeddings.
    """
)

# Include routers
app.include_router(voice_router)
app.include_router(github_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Setup Socket.IO ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

# Global State
active_sessions: Dict[str, SessionState] = {}
hitl_handlers: Dict[str, APIHITLHandler] = {}
orchestrators: Dict[str, IntelligentOrchestrator] = {}
conversation_contexts: Dict[str, Dict[str, Any]] = {}


# --- Agent Personas for UI with Nova 2 Sonic Voice IDs ---
AGENT_PERSONAS = {
    "ROUTER": {
        "name": "ROUTER",
        "title": "Team Coordinator",
        "avatar": "🎯",
        "color": "#f97316",
        "voice": "neutral",
        "voice_id": "ivy",  # Nova 2 Sonic voice
        "speaking_rate": 1.0,
        "description": "Orchestrates the founding team analysis"
    },
    "ARIA": {
        "name": "ARIA",
        "title": "Chief Technology Officer",
        "avatar": "🔧",
        "color": "#3b82f6",
        "voice": "technical",
        "voice_id": "tiffany",  # Calm, precise female voice
        "speaking_rate": 0.95,
        "description": "Technical feasibility and architecture expert"
    },
    "FELIX": {
        "name": "FELIX",
        "title": "Chief Financial Officer",
        "avatar": "💰",
        "color": "#22c55e",
        "voice": "analytical",
        "voice_id": "matthew",  # Measured, confident male voice
        "speaking_rate": 0.9,
        "tools": ["web_search"],  # Web grounding for live pricing
        "description": "Financial projections and cost analysis with live data"
    },
    "NOVA": {
        "name": "NOVA",
        "title": "Chief Marketing Officer",
        "avatar": "📣",
        "color": "#ec4899",
        "voice": "creative",
        "voice_id": "aurora",  # Warm, energetic female voice
        "speaking_rate": 1.05,
        "description": "Marketing strategy and positioning"
    },
    "JUDGE": {
        "name": "JUDGE",
        "title": "Investor Advisor",
        "avatar": "⚖️",
        "color": "#8b5cf6",
        "voice": "critical",
        "description": "Investment evaluation and fundability"
    },
    "ORCHESTRATOR": {
        "name": "ORCHESTRATOR",
        "title": "Engineering Lead",
        "avatar": "🎛️",
        "color": "#f97316",
        "voice": "neutral",
        "description": "Coordinates the engineering workforce"
    },
    "PLANNER": {
        "name": "PLANNER",
        "title": "Technical Architect",
        "avatar": "📋",
        "color": "#06b6d4",
        "voice": "methodical",
        "description": "Creates engineering specifications"
    },
    "CODER": {
        "name": "CODER",
        "title": "Senior Developer",
        "avatar": "💻",
        "color": "#10b981",
        "voice": "technical",
        "description": "Implements features and writes code"
    },
    "TESTER": {
        "name": "TESTER",
        "title": "QA Engineer",
        "avatar": "🧪",
        "color": "#f59e0b",
        "voice": "thorough",
        "description": "Creates and validates tests"
    },
    "DOCS": {
        "name": "DOCS",
        "title": "Technical Writer",
        "avatar": "📚",
        "color": "#6366f1",
        "voice": "clear",
        "description": "Generates documentation"
    },
    "REVIEWER": {
        "name": "REVIEWER",
        "title": "Code Reviewer",
        "avatar": "🔍",
        "color": "#ef4444",
        "voice": "critical",
        "description": "Reviews code quality and security"
    },
    "SAGE": {
        "name": "SAGE",
        "title": "Codebase Oracle",
        "avatar": "🧙",
        "color": "#8b5cf6",
        "voice": "wise",
        "description": "Answers questions about your codebase"
    },
    "SYSTEM": {
        "name": "SYSTEM",
        "title": "Helix System",
        "avatar": "⚡",
        "color": "#64748b",
        "voice": "neutral",
        "description": "System notifications"
    },
}


# --- Socket.IO Events ---

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")
    # Send agent personas on connect
    await sio.emit('agent_personas', AGENT_PERSONAS, to=sid)


@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")
    # Cleanup session data
    active_sessions.pop(sid, None)
    hitl_handlers.pop(sid, None)
    orchestrators.pop(sid, None)
    conversation_contexts.pop(sid, None)


@sio.event
async def start_pipeline(sid, data):
    """Triggered by frontend to start a new pipeline."""
    logger.info(f"Received start_pipeline event from {sid}: {data}")
    pillar = data.get('pillar')
    user_input = data.get('input')
    context = data.get('context')  # Context from previous pillar transition
    
    logger.info(f"Starting pipeline for Pillar {pillar} via Socket {sid}")
    
    # Check if we have existing session state (for pillar transitions)
    existing_session = active_sessions.get(sid)
    existing_orchestrator = orchestrators.get(sid)
    
    # Create or reuse Session State
    if existing_session and context and context.get('from_pillar'):
        # Pillar transition - preserve context
        session_state = existing_session
        logger.info(f"Pillar transition from {context.get('from_pillar')} to {pillar}")
    else:
        # New session
        session_state = SessionState()
    
    checkpoint_manager = CheckpointManager(session_state)
    hitl_handler = APIHITLHandler(checkpoint_manager)
    
    # Reuse or create orchestrator
    if existing_orchestrator and context:
        intelligent_orchestrator = existing_orchestrator
        # Add transition context to conversation
        if context.get('summary'):
            intelligent_orchestrator.add_conversation_turn(
                "system",
                f"[Context from Pillar {context.get('from_pillar')}]: {context.get('summary')}"
            )
    else:
        intelligent_orchestrator = IntelligentOrchestrator(session_state)
    
    # Store globally for this connection
    active_sessions[sid] = session_state
    hitl_handlers[sid] = hitl_handler
    orchestrators[sid] = intelligent_orchestrator
    conversation_contexts[sid] = {
        "pillar": pillar, 
        "started_at": datetime.utcnow().isoformat(),
        "from_pillar": context.get('from_pillar') if context else None,
        "transition_context": context.get('summary') if context else None,
    }

    # Wire up intelligent orchestrator callbacks
    def on_handoff(handoff: AgentHandoff):
        asyncio.create_task(emit_agent_handoff(sid, handoff))
    
    intelligent_orchestrator.on_handoff(on_handoff)

    # Wire up CheckpointManager to emit Socket.IO events
    def on_checkpoint_created(checkpoint):
        logger.info(f"Emitting hitl_checkpoint to {sid}: {checkpoint.id}")
        asyncio.create_task(emit_smart_checkpoint(sid, checkpoint, intelligent_orchestrator))
        
    checkpoint_manager.on_checkpoint_created(on_checkpoint_created)

    if pillar == 1:
        asyncio.create_task(run_pillar1_workflow(sid, session_state, hitl_handler, intelligent_orchestrator, user_input))
    elif pillar == 2:
        asyncio.create_task(run_pillar2_workflow(sid, session_state, hitl_handler, intelligent_orchestrator, user_input))
    elif pillar == 3:
        repo_path = data.get('repo')
        # Validate repo_path to prevent corrupted data
        if repo_path:
            # Sanitize: repo_path should be a clean path, not contain log output
            if any(x in str(repo_path) for x in ['INFO:', 'ERROR:', 'websocket', '[accepted]', 'connection']):
                logger.warning(f"Received corrupted repo_path, ignoring: {repo_path[:100]}...")
                repo_path = None
            elif len(str(repo_path)) > 500:
                logger.warning(f"repo_path too long, ignoring: {repo_path[:100]}...")
                repo_path = None
        asyncio.create_task(run_pillar3_workflow(sid, session_state, hitl_handler, intelligent_orchestrator, user_input, repo_path))
    else:
        await sio.emit('agent_log', {'agent': 'SYSTEM', 'message': f'Pillar {pillar} not recognized.', 'type': 'error'}, to=sid)


@sio.event
async def hitl_decision(sid, data):
    """Received from frontend when user makes a HITL decision."""
    checkpoint_id = data.get('checkpoint_id')
    decision_str = data.get('decision')
    user_input = data.get('user_input', '')
    field_responses = data.get('field_responses', {})
    
    logger.info(f"Received HITL decision {decision_str} for {checkpoint_id}")
    
    handler = hitl_handlers.get(sid)
    orchestrator = orchestrators.get(sid)
    
    if handler and orchestrator:
        try:
            decision_enum = HITLDecision(decision_str.lower())
            
            # Add to conversation history
            orchestrator.add_conversation_turn(
                speaker="user",
                content=user_input or f"Decision: {decision_str}",
                metadata={"decision": decision_str, "field_responses": field_responses}
            )
            
            # Resolve the checkpoint
            handler.resolve_external(checkpoint_id, decision_enum, user_input)
            
            # Emit resolution with context
            await sio.emit('hitl_resolved', {
                'checkpoint_id': checkpoint_id,
                'decision': decision_str,
                'has_follow_up': False,  # Will be set by workflow if needed
                'context_summary': orchestrator._generate_context_summary()
            }, to=sid)
            
        except ValueError:
            logger.error(f"Invalid decision received: {decision_str}")
            await sio.emit('error', {'message': f'Invalid decision: {decision_str}'}, to=sid)


@sio.event
async def user_message(sid, data):
    """Handle free-form user messages during pipeline execution."""
    message = data.get('message', '')
    target_agent = data.get('target_agent')
    
    orchestrator = orchestrators.get(sid)
    if orchestrator:
        # Add to conversation
        turn = orchestrator.add_conversation_turn(
            speaker="user",
            content=message,
        )
        
        # Emit acknowledgment
        await sio.emit('message_received', {
            'message_id': str(turn.timestamp),
            'intent': turn.intent.value if turn.intent else 'unknown',
        }, to=sid)
        
        # If there's a target agent, route the message
        if target_agent:
            await stream_agent_log(
                sid, 
                target_agent.upper(), 
                f"Received your message. Processing...", 
                'thought'
            )


@sio.event
async def request_clarification(sid, data):
    """User requests clarification from an agent."""
    agent = data.get('agent', 'SYSTEM')
    question = data.get('question', '')
    
    orchestrator = orchestrators.get(sid)
    if orchestrator:
        orchestrator.add_conversation_turn(
            speaker="user",
            content=f"Question for {agent}: {question}",
        )
        
        await stream_agent_log(
            sid,
            agent.upper(),
            f"Let me address your question: {question}",
            'thought'
        )
        
        # In a full implementation, this would trigger the agent to respond
        # For now, emit a placeholder
        await asyncio.sleep(1)
        await stream_agent_log(
            sid,
            agent.upper(),
            "I'll incorporate this into my analysis. Please continue with the current checkpoint.",
            'action'
        )


@sio.event
async def pillar_transition(sid, data):
    """Handle intelligent pillar transitions with context passing."""
    from_pillar = data.get('from_pillar')
    to_pillar = data.get('to_pillar')
    context = data.get('context', {})
    
    logger.info(f"Pillar transition: {from_pillar} -> {to_pillar}")
    
    orchestrator = orchestrators.get(sid)
    session_state = active_sessions.get(sid)
    
    if orchestrator and session_state:
        # Generate context summary from current pillar's conversation
        context_summary = orchestrator._generate_context_summary() if orchestrator else ""
        
        # Get key insights from the conversation
        recent_results = [
            turn.content[:300] for turn in orchestrator.conversation_history[-10:]
            if turn.speaker != "user"
        ]
        
        # Emit transition acknowledgment
        await sio.emit('pillar_transition_ready', {
            'from_pillar': from_pillar,
            'to_pillar': to_pillar,
            'context_summary': context_summary,
            'key_insights': recent_results[-3:] if recent_results else [],
            'user_intent': context.get('userIntent', 'Continue workflow'),
        }, to=sid)
        
        # Update conversation context
        conversation_contexts[sid] = {
            **conversation_contexts.get(sid, {}),
            'pillar': to_pillar,
            'from_pillar': from_pillar,
            'transition_context': context_summary,
        }
        
        await stream_agent_log(
            sid,
            'SYSTEM',
            f"Transitioning to {'Founding Team' if to_pillar == 1 else 'Engineering Workforce' if to_pillar == 2 else 'Knowledge Base'}. Context has been preserved.",
            'action'
        )


async def generate_smart_suggestions(checkpoint, orchestrator: IntelligentOrchestrator) -> List[str]:
    """
    Generate context-aware suggestions based on the conversation.
    Uses simple keyword matching for reliability - LLM generation was causing issues.
    """
    prompt_text = checkpoint.prompt.lower() if checkpoint.prompt else ""
    agent_name = checkpoint.agent.value.upper() if hasattr(checkpoint, 'agent') and checkpoint.agent else "ROUTER"
    
    # Build conversation context
    recent_context = ""
    if orchestrator and orchestrator.conversation_history:
        recent_context = " ".join([t.content.lower() for t in orchestrator.conversation_history[-3:]])
    
    # Determine the workflow stage
    pillar1_agent_order = ["ARIA", "FELIX", "NOVA", "JUDGE"]
    current_agent_idx = pillar1_agent_order.index(agent_name) if agent_name in pillar1_agent_order else -1
    next_agent = pillar1_agent_order[current_agent_idx + 1] if current_agent_idx >= 0 and current_agent_idx < len(pillar1_agent_order) - 1 else None
    
    # Generate suggestions based on context - ORDER MATTERS (most specific first)
    suggestions = []
    
    # ═══════════════════════════════════════════════════════════════════════
    # PILLAR 1 - Founding Team Agent Handoffs
    # ═══════════════════════════════════════════════════════════════════════
    if "ready to hear from aria" in prompt_text or ("aria" in prompt_text and "cto" in prompt_text):
        suggestions = ["Yes, let's hear from Aria", "Skip to Felix (CFO)", "Skip to Nova (CMO)", "I have a question first"]
    elif "pass the baton to felix" in prompt_text or ("felix" in prompt_text and "cfo" in prompt_text):
        suggestions = ["Yes, bring in Felix", "Skip to Nova (CMO)", "Skip to Judge", "Go back to Aria"]
    elif "bring in nova" in prompt_text or ("nova" in prompt_text and "cmo" in prompt_text):
        suggestions = ["Yes, let's hear from Nova", "Skip to Judge", "Go back to Felix", "I have questions"]
    elif "ready for the tough love" in prompt_text or ("judge" in prompt_text and "investor" in prompt_text):
        suggestions = ["Yes, give me the tough love", "I'm ready for feedback", "Go back to Nova", "Let me think about it"]
    elif "what would you like to do next" in prompt_text or "full team's perspective" in prompt_text:
        suggestions = ["Move to Pillar 2 (Build)", "Ask Aria a follow-up", "Ask Felix a follow-up", "Save this analysis"]
    
    # ═══════════════════════════════════════════════════════════════════════
    # PILLAR 2 - Engineering Workforce Agent Handoffs
    # ═══════════════════════════════════════════════════════════════════════
    # Intake - Ready to start building
    elif "ready to start building" in prompt_text or ("planner" in prompt_text and "architecture" in prompt_text):
        suggestions = ["Yes, let's start!", "I want to add more details", "What will you build exactly?", "How long will this take?"]
    # After Planner - offer Coder
    elif "pass the baton to the coder" in prompt_text or ("coder" in prompt_text and "implement" in prompt_text):
        suggestions = ["Yes, start coding!", "I want to change something", "Explain this more", "Skip to testing"]
    # After Coder - offer Tester
    elif "bring in the tester" in prompt_text or ("tester" in prompt_text and "test" in prompt_text):
        suggestions = ["Yes, run tests", "I want to modify the code", "Skip to documentation", "Skip to review"]
    # After Tester - offer Docs
    elif "bring in docs" in prompt_text or ("docs" in prompt_text and "documentation" in prompt_text):
        suggestions = ["Yes, generate docs", "Skip to review", "Go back to code", "I have questions"]
    # After Docs - offer Reviewer
    elif "ready for the review" in prompt_text or ("reviewer" in prompt_text and "quality" in prompt_text):
        suggestions = ["Yes, review it", "Go back to code", "I want changes first", "Skip review"]
    # Engineering complete
    elif "engineering complete" in prompt_text or "you've heard from" in prompt_text:
        suggestions = ["Create GitHub PR", "Download ZIP", "Move to Pillar 3", "Ask a question"]
    
    # Pillar 2 - Code review/modification prompts
    elif "files created" in prompt_text or "implementation" in prompt_text:
        suggestions = ["Looks good, continue", "Make changes", "Regenerate", "Go back to planning"]
    
    # 2. Funding/capital questions (check before team since funding questions may mention "seeking")
    elif any(word in prompt_text for word in ["funding", "capital", "investment", "money", "budget", "pre-seed", "seed", "series"]):
        suggestions = ["Bootstrapping for now", "Pre-seed ($50-250k)", "Seed ($500k-2M)", "Not sure yet"]
    
    # 3. Timeline/milestone questions
    elif any(word in prompt_text for word in ["timeline", "milestone", "deadline", "when", "schedule", "launch"]):
        suggestions = ["2-4 weeks", "1-2 months", "3-6 months", "Still figuring it out"]
    
    # 4. Team/leadership questions (expanded keywords)
    elif any(word in prompt_text for word in ["team", "building", "leading", "founder", "co-founder", "developer", "who is", "who's"]):
        suggestions = ["Solo founder", "Small team (2-3)", "Full team (4+)", "Looking for co-founders"]
    
    # 5. Stage/progress questions
    elif any(word in prompt_text for word in ["stage", "far along", "progress", "prototype", "mvp", "idea stage", "built"]):
        suggestions = ["Just an idea", "Have a prototype", "MVP ready", "Already launched"]
    
    # 6. Target market/audience questions
    elif any(word in prompt_text for word in ["target", "audience", "customer", "market", "who are", "for whom"]):
        # Check context for specific industries
        if "shoe" in recent_context or "footwear" in recent_context:
            suggestions = ["Athletes and runners", "Fashion-conscious consumers", "Budget shoppers", "Mass market"]
        elif "restaurant" in recent_context or "food" in recent_context:
            suggestions = ["Restaurant owners", "Food delivery services", "Diners/customers", "Let's continue"]
        elif "saas" in recent_context or "software" in recent_context:
            suggestions = ["Small businesses", "Enterprise companies", "Startups", "Let's continue"]
        else:
            suggestions = ["Small businesses", "Enterprise companies", "Consumers", "Let's continue"]
    
    # 7. Problem/solution questions
    elif any(word in prompt_text for word in ["problem", "solving", "challenge", "pain point", "issue"]):
        if "shoe" in recent_context or "footwear" in recent_context:
            suggestions = ["Finding the right fit", "High prices", "Limited styles", "Quality issues"]
        else:
            suggestions = ["Efficiency & automation", "Cost reduction", "Better user experience", "Let's continue"]
    
    # 8. Custom/handmade vs mass production
    elif any(word in prompt_text for word in ["custom", "handmade", "mass-producing", "production", "manufacturing"]):
        suggestions = ["Custom/handmade", "Mass production", "Both", "Not sure yet"]
    
    # 9. Default fallback with next agent if available
    elif next_agent:
        suggestions = [f"Yes, bring in {next_agent}", "Tell me more", "I have a question", f"Skip to {pillar1_agent_order[-1]}"]
    else:
        suggestions = ["Tell me more", "Let's continue", "I have a question", "Sounds good"]
    
    return suggestions


async def emit_smart_checkpoint(sid: str, checkpoint, orchestrator: IntelligentOrchestrator):
    """
    Emit an enhanced HITL checkpoint with smart features.
    
    IMPORTANT: This function also registers the checkpoint with the HITL handler
    to ensure proper blocking behavior when present_checkpoint is called.
    """
    # Register checkpoint with handler BEFORE emitting to frontend
    handler = hitl_handlers.get(sid)
    if handler:
        handler.register_checkpoint(str(checkpoint.id), checkpoint)
        logger.info(f"emit_smart_checkpoint: Registered checkpoint {checkpoint.id} with handler")
    
    # Generate truly dynamic suggestions using LLM
    suggestions = await generate_smart_suggestions(checkpoint, orchestrator)
    
    # Get conversation context
    context_summary = orchestrator._generate_context_summary() if orchestrator else ""
    
    # Turn off processing indicator when emitting checkpoint
    await sio.emit('pipeline_update', {
        'current_stage': 'waiting_for_input',
        'active_agent': checkpoint.agent.value.upper(),
        'progress_percent': 50,
        'stage_description': 'Waiting for your response...',
    }, to=sid)
    
    await sio.emit('hitl_checkpoint', {
        'id': str(checkpoint.id),
        'gate_type': checkpoint.gate_type.value,
        'pillar': checkpoint.pillar,
        'agent': checkpoint.agent.value,
        'prompt': checkpoint.prompt,
        'options': [opt.value for opt in checkpoint.options],
        # Enhanced fields
        'questions': [],  # No parsed questions - use natural conversation
        'suggestions': suggestions,
        'context_summary': context_summary,
        'conversation_history': [
            {"speaker": t.speaker, "content": t.content[:200]}
            for t in orchestrator.conversation_history[-5:]
        ] if orchestrator else [],
        'agent_persona': AGENT_PERSONAS.get(checkpoint.agent.value.upper(), AGENT_PERSONAS['SYSTEM']),
        'allows_follow_up': True,
        'timestamp': datetime.utcnow().isoformat(),
    }, to=sid)


async def emit_agent_handoff(sid: str, handoff: AgentHandoff):
    """Emit agent handoff event to frontend."""
    await sio.emit('agent_handoff', {
        'from_agent': handoff.from_agent.value,
        'to_agent': handoff.to_agent.value,
        'reason': handoff.reason.value,
        'from_persona': AGENT_PERSONAS.get(handoff.from_agent.value.upper()),
        'to_persona': AGENT_PERSONAS.get(handoff.to_agent.value.upper()),
        'timestamp': handoff.timestamp.isoformat(),
    }, to=sid)


async def stream_agent_log(sid: str, agent: str, message: str, log_type: str = 'result'):
    """Stream agent log with persona information."""
    persona = AGENT_PERSONAS.get(agent.upper(), AGENT_PERSONAS['SYSTEM'])
    
    await sio.emit('agent_log', {
        'agent': agent,
        'message': message,
        'type': log_type,
        'timestamp': datetime.utcnow().isoformat(),
        'persona': persona,
    }, to=sid)


async def stream_typing_indicator(sid: str, agent: str, is_typing: bool):
    """Stream typing indicator for an agent."""
    await sio.emit('agent_typing', {
        'agent': agent,
        'is_typing': is_typing,
        'persona': AGENT_PERSONAS.get(agent.upper()),
    }, to=sid)


async def emit_next_steps_checkpoint(
    sid: str,
    orchestrator: IntelligentOrchestrator,
    pillar: int,
    brief_summary: dict
):
    """
    Emit a smart next-steps checkpoint that offers intelligent options.
    
    This is the key to making the system feel smart - instead of just saying
    "you can now proceed", we ask the user what they want to do next.
    """
    from uuid import uuid4
    
    if pillar == 1:
        # After Pillar 1 (Founding Team) completion
        prompt = f"""## 🎉 Your Startup Brief is Complete!

The Founding Team has finished analyzing your idea. Here's what we found:

**Idea:** {brief_summary.get('idea', 'Your startup concept')}...
**Overall Feasibility:** {brief_summary.get('feasibility_score', 'Evaluated')}/10

### What would you like to do next?

I can help you with any of these options:

1. **🚀 Start Building** - Transfer this brief to the Engineering Workforce (Pillar 2) and begin implementing your MVP
2. **✏️ Refine the Brief** - Go back and adjust specific sections or ask follow-up questions to any agent
3. **💾 Save & Exit** - Save this brief for later and come back when you're ready

Which path would you like to take?"""

        options = ['build', 'refine', 'save']
        
        await sio.emit('hitl_checkpoint', {
            'id': str(uuid4()),
            'gate_type': 'next_steps',
            'pillar': pillar,
            'agent': 'router',
            'prompt': prompt,
            'options': options,
            'questions': [],
            'suggestions': [
                "Start with the authentication module",
                "Build a landing page first",
                "Create the database schema",
            ],
            'context_summary': "Startup Brief analysis complete. Ready for next steps.",
            'conversation_history': [
                {"speaker": t.speaker, "content": t.content[:200]}
                for t in orchestrator.conversation_history[-3:]
            ] if orchestrator else [],
            'agent_persona': AGENT_PERSONAS.get('ROUTER'),
            'allows_follow_up': True,
            'is_next_steps': True,  # Special flag for frontend
            'next_step_options': [
                {
                    'id': 'build',
                    'label': '🚀 Start Building',
                    'description': 'Transfer to Engineering Workforce',
                    'action': 'navigate_pillar2',
                    'color': '#22c55e',
                },
                {
                    'id': 'refine',
                    'label': '✏️ Refine Brief',
                    'description': 'Adjust sections or ask questions',
                    'action': 'restart_pillar1',
                    'color': '#3b82f6',
                },
                {
                    'id': 'save',
                    'label': '💾 Save & Exit',
                    'description': 'Save for later',
                    'action': 'save_and_exit',
                    'color': '#64748b',
                },
            ],
            'timestamp': datetime.utcnow().isoformat(),
        }, to=sid)
        
    elif pillar == 2:
        # After Pillar 2 (Engineering) completion
        prompt = f"""## 🎉 Engineering Package Complete!

The Engineering Workforce has finished building your feature.

### What would you like to do next?

1. **🔀 Create GitHub PR** - Use Nova Act to create a pull request with all the generated code
2. **🔍 Review Changes** - Go through the code, tests, and documentation in detail
3. **✏️ Request Changes** - Ask for modifications before creating the PR

Which would you prefer?"""

        options = ['create_pr', 'review', 'modify']
        
        await sio.emit('hitl_checkpoint', {
            'id': str(uuid4()),
            'gate_type': 'next_steps',
            'pillar': pillar,
            'agent': 'orchestrator',
            'prompt': prompt,
            'options': options,
            'questions': [],
            'suggestions': [],
            'context_summary': "Engineering package ready for deployment.",
            'conversation_history': [],
            'agent_persona': AGENT_PERSONAS.get('ORCHESTRATOR'),
            'allows_follow_up': True,
            'is_next_steps': True,
            'next_step_options': [
                {
                    'id': 'create_pr',
                    'label': '🔀 Create GitHub PR',
                    'description': 'Deploy via Nova Act',
                    'action': 'create_pr',
                    'color': '#8b5cf6',
                },
                {
                    'id': 'review',
                    'label': '🔍 Review Changes',
                    'description': 'Inspect code in detail',
                    'action': 'review_code',
                    'color': '#06b6d4',
                },
                {
                    'id': 'modify',
                    'label': '✏️ Request Changes',
                    'description': 'Ask for modifications',
                    'action': 'request_changes',
                    'color': '#f59e0b',
                },
            ],
            'timestamp': datetime.utcnow().isoformat(),
        }, to=sid)


async def run_pillar1_workflow(
    sid: str,
    session_state: SessionState,
    hitl_handler: APIHITLHandler,
    orchestrator: IntelligentOrchestrator,
    user_input: str
):
    """
    Executes Pillar 1 with conversational agent handoffs.
    
    Each agent has a full conversation with the user, and the user must
    approve before moving to the next agent. No automatic agent chaining.
    """
    router = RouterAgent()
    
    # Add initial user input to conversation
    orchestrator.add_conversation_turn("user", user_input)
    
    context = AgentContext(
        session_state=session_state,
        conversation=session_state.pillar1_conversation,
        user_input=user_input,
    )
    
    await sio.emit('pipeline_update', {
        'current_stage': 'intake',
        'active_agent': 'ROUTER',
        'progress_percent': 10,
        'stage_description': 'Starting conversation',
    }, to=sid)

    try:
        # Conversational loop - Router manages the flow
        iteration = 0
        max_iterations = 50  # Allow many back-and-forth exchanges
        
        while iteration < max_iterations:
            iteration += 1
            
            # Determine which agent is active based on workflow stage
            workflow_stage = context.metadata.get("workflow_stage", "intake")
            active_agent = "ROUTER"
            if "aria" in workflow_stage:
                active_agent = "ARIA"
            elif "felix" in workflow_stage:
                active_agent = "FELIX"
            elif "nova" in workflow_stage:
                active_agent = "NOVA"
            elif "judge" in workflow_stage:
                active_agent = "JUDGE"
            
            # Execute router (which may delegate to specialists)
            await stream_typing_indicator(sid, active_agent, True)
            response = await router.execute(context)
            await stream_typing_indicator(sid, active_agent, False)
            
            # Determine the speaker for the response
            response_stage = context.metadata.get("workflow_stage", "intake")
            speaker = "ROUTER"
            if "aria_active" in response_stage or "felix_pending" in response_stage:
                speaker = "ARIA"
            elif "felix_active" in response_stage or "nova_pending" in response_stage:
                speaker = "FELIX"
            elif "nova_active" in response_stage or "judge_pending" in response_stage:
                speaker = "NOVA"
            elif "judge_active" in response_stage or "complete" in response_stage:
                speaker = "JUDGE"
            
            # Stream the response
            if response.content:
                await stream_agent_log(sid, speaker, response.content, 'result')
                orchestrator.add_conversation_turn(speaker.lower(), response.content)
            
            # Update pipeline with current agent
            await sio.emit('pipeline_update', {
                'current_stage': response_stage,
                'active_agent': speaker,
                'progress_percent': min(20 + iteration * 10, 95),
                'stage_description': f'{speaker} is speaking...',
            }, to=sid)
            
            # Check if there's a checkpoint (question for user)
            if response.hitl_checkpoint and not response.hitl_checkpoint.is_resolved:
                checkpoint = response.hitl_checkpoint
                
                # Emit checkpoint for user to respond
                await emit_smart_checkpoint(sid, checkpoint, orchestrator)
                
                # Wait for user response
                decision = await hitl_handler.present_checkpoint(checkpoint)
                user_response = hitl_handler.get_last_user_input()
                
                # Add user response to context
                orchestrator.add_conversation_turn("user", user_response or f"Decision: {decision.value}")
                context.user_input = user_response or ""
                context.metadata["last_user_response"] = user_response
                
                # CRITICAL: Record intake answers so the router tracks progress
                # This prevents the router from asking the same questions repeatedly
                if workflow_stage == "intake" and user_response:
                    router.record_intake_answer(context, user_response)
                
            elif response.metadata.get("workflow_complete"):
                # Router signals workflow is done
                break
            else:
                # No checkpoint and not complete - wait for more user input
                break
        
        # Final completion
        await sio.emit('pipeline_update', {
            'current_stage': 'complete',
            'active_agent': None,
            'progress_percent': 100,
            'stage_description': 'Conversation complete!',
        }, to=sid)
        
        # Emit next-steps checkpoint
        await emit_next_steps_checkpoint(sid, orchestrator, pillar=1, brief_summary={
            'idea': user_input[:100],
            'feasibility_score': response.metadata.get('feasibility_score', 'N/A'),
        })

    except Exception as e:
        logger.exception("Error in Pillar 1 pipeline")
        await stream_agent_log(sid, 'SYSTEM', f'❌ Error: {str(e)}', 'error')


async def run_pillar2_workflow(
    sid: str, 
    session_state: SessionState, 
    hitl_handler: APIHITLHandler,
    orchestrator: IntelligentOrchestrator,
    user_input: str
):
    """
    Executes Pillar 2 with conversational agent handoffs (like Pillar 1).
    
    Each agent has a full conversation with the user, and the user must
    approve before moving to the next agent. No automatic agent chaining.
    """
    orch_agent = OrchestratorAgent()
    
    # Check if we have context from pillar 1 transition
    ctx = conversation_contexts.get(sid, {})
    from_pillar = ctx.get('from_pillar')
    transition_context = ctx.get('transition_context')
    
    # If transitioning from pillar 1, incorporate the context
    if from_pillar == 1 and transition_context:
        enhanced_input = f"""Based on the startup analysis from the Founding Team:

{transition_context}

User's request: {user_input}

Build a complete, production-ready frontend application that addresses this startup idea."""
        orchestrator.add_conversation_turn("system", f"[Context from Founding Team]: {transition_context[:500]}...")
    else:
        enhanced_input = user_input
    
    orchestrator.add_conversation_turn("user", user_input)
    
    context = AgentContext(
        session_state=session_state,
        conversation=session_state.pillar2_conversation,
        user_input=enhanced_input,
    )
    
    # CRITICAL: Store the original request so it doesn't get overwritten
    context.metadata["original_request"] = user_input
    
    # Add any pillar 1 context to metadata
    if from_pillar == 1:
        context.metadata["from_pillar1"] = True
        context.metadata["pillar1_context"] = transition_context
    
    await stream_agent_log(sid, 'ORCHESTRATOR', f'🚀 Starting Engineering Workforce for: {user_input[:200]}...', 'action')
    await sio.emit('pipeline_update', {
        'current_stage': 'intake',
        'active_agent': 'ORCHESTRATOR',
        'progress_percent': 10,
        'stage_description': 'Starting conversation',
    }, to=sid)

    try:
        # Conversational loop - Orchestrator manages the flow (like Pillar 1)
        iteration = 0
        max_iterations = 50  # Allow many back-and-forth exchanges
        
        while iteration < max_iterations:
            iteration += 1
            
            # Determine which agent is active based on workflow stage
            workflow_stage = context.metadata.get("workflow_stage", "intake")
            active_agent = "ORCHESTRATOR"
            if "planner" in workflow_stage:
                active_agent = "PLANNER"
            elif "coder" in workflow_stage:
                active_agent = "CODER"
            elif "tester" in workflow_stage:
                active_agent = "TESTER"
            elif "docs" in workflow_stage:
                active_agent = "DOCS"
            elif "reviewer" in workflow_stage:
                active_agent = "REVIEWER"
            
            # Show "thinking" message like Pillar 1 does
            thinking_messages = {
                "ORCHESTRATOR": "🤔 Understanding your request...",
                "PLANNER": "📐 Designing the architecture and features...",
                "CODER": "💻 Writing the code for your application...",
                "TESTER": "🧪 Running automated tests...",
                "DOCS": "📝 Generating documentation...",
                "REVIEWER": "🔍 Reviewing code quality and security...",
            }
            await stream_agent_log(sid, active_agent, thinking_messages.get(active_agent, "Processing..."), 'thought')
            
            # Execute orchestrator (which may delegate to specialists)
            await stream_typing_indicator(sid, active_agent, True)
            response = await orch_agent.execute(context)
            await stream_typing_indicator(sid, active_agent, False)
            
            # Determine the speaker for the response
            response_stage = context.metadata.get("workflow_stage", "intake")
            speaker = "ORCHESTRATOR"
            if "planner_active" in response_stage or "coder_pending" in response_stage:
                speaker = "PLANNER"
            elif "coder_active" in response_stage or "tester_pending" in response_stage:
                speaker = "CODER"
            elif "tester_active" in response_stage or "docs_pending" in response_stage:
                speaker = "TESTER"
            elif "docs_active" in response_stage or "reviewer_pending" in response_stage:
                speaker = "DOCS"
            elif "reviewer_active" in response_stage or "complete" in response_stage:
                speaker = "REVIEWER"
            
            # Stream the response
            if response.content:
                await stream_agent_log(sid, speaker, response.content, 'result')
                orchestrator.add_conversation_turn(speaker.lower(), response.content)
            
            # Update pipeline with current agent
            progress_map = {
                "intake": 10, "planner_pending": 15, "planner_active": 20,
                "coder_pending": 30, "coder_active": 40,
                "tester_pending": 55, "tester_active": 65,
                "docs_pending": 75, "docs_active": 80,
                "reviewer_pending": 85, "reviewer_active": 90,
                "complete": 100
            }
            progress = progress_map.get(response_stage, min(20 + iteration * 5, 95))
            
            await sio.emit('pipeline_update', {
                'current_stage': response_stage,
                'active_agent': speaker,
                'progress_percent': progress,
                'stage_description': f'{speaker} is speaking...',
            }, to=sid)
            
            # Handle code output - stream files to frontend
            code_output = response.metadata.get("code_output", {})
            if code_output and code_output.get("files"):
                await _stream_generated_files(sid, code_output)
            
            # Check if there's a checkpoint (question for user)
            if response.hitl_checkpoint and not response.hitl_checkpoint.is_resolved:
                checkpoint = response.hitl_checkpoint
                
                # Emit checkpoint for user to respond
                await emit_smart_checkpoint(sid, checkpoint, orchestrator)
                
                # Wait for user response
                decision = await hitl_handler.present_checkpoint(checkpoint)
                user_response = hitl_handler.get_last_user_input()
                
                # Add user response to context
                orchestrator.add_conversation_turn("user", user_response or f"Decision: {decision.value}")
                context.user_input = user_response or ""
                context.metadata["last_user_response"] = user_response
                
                # Record intake answers so the orchestrator tracks progress
                if workflow_stage == "intake" and user_response:
                    orch_agent.record_intake_answer(context, user_response)
                
            elif response.metadata.get("workflow_complete"):
                # Orchestrator signals workflow is done
                break
            else:
                # No checkpoint and not complete - wait for more user input
                break
        
        # Final completion
        await sio.emit('pipeline_update', {
            'current_stage': 'complete',
            'active_agent': None,
            'progress_percent': 100,
            'stage_description': 'Engineering complete!',
        }, to=sid)
        
        # Emit next-steps checkpoint
        await emit_next_steps_checkpoint(sid, orchestrator, pillar=2, brief_summary={
            'feature': user_input[:100],
        })

    except Exception as e:
        logger.exception("Error in Pillar 2 pipeline")
        await stream_agent_log(sid, 'SYSTEM', f'❌ Error: {str(e)}', 'error')


async def _stream_generated_files(sid: str, code_output: dict):
    """Helper function to stream generated files to frontend."""
    import os
    
    all_files = {
        **code_output.get("files", {}), 
        **code_output.get("tests", {}), 
        **code_output.get("documentation", {})
    }
    
    if not all_files:
        return
    
    total_files = len(all_files)
    
    # Language mapping for syntax highlighting
    lang_map = {
        'py': 'python', 'js': 'javascript', 'ts': 'typescript', 
        'tsx': 'typescript', 'jsx': 'javascript', 'json': 'json',
        'html': 'html', 'css': 'css', 'md': 'markdown', 'sql': 'sql',
        'yaml': 'yaml', 'yml': 'yaml', 'sh': 'bash', 'txt': 'text'
    }
    
    # Stream each file individually
    for idx, (filepath, content) in enumerate(all_files.items()):
        ext = filepath.split('.')[-1] if '.' in filepath else ''
        language = lang_map.get(ext, 'text')
        
        # Emit file streaming event
        await sio.emit('file_streaming', {
            'path': filepath,
            'content': content,
            'language': language,
            'status': 'written',
            'index': idx,
            'total': total_files,
        }, to=sid)
        
        # Small delay for visual streaming effect
        await asyncio.sleep(0.05)
    
    # Save to filesystem
    try:
        project_dir = os.path.join(os.getcwd(), "output", "projects", sid)
        saved_paths = save_project_files(project_dir, all_files)
        await stream_agent_log(sid, 'SYSTEM', f'💾 Saved {len(saved_paths)} files', 'action')
    except Exception as fs_err:
        logger.error(f"Failed to save project files: {fs_err}")
    
    # Emit completion event
    project_type = 'react' if any('tsx' in f or 'jsx' in f for f in all_files.keys()) else 'node'
    await sio.emit('files_complete', {
        'total_files': total_files,
        'project_type': project_type,
        'ready_for_install': True,
    }, to=sid)
    
    # Also emit batch for compatibility
    generated_files = [
        {'path': fp, 'content': ct, 'language': lang_map.get(fp.split('.')[-1] if '.' in fp else '', 'text')}
        for fp, ct in all_files.items()
    ]
    await sio.emit('generated_files', {
        'files': generated_files,
        'project_type': project_type
    }, to=sid)


async def run_pillar3_workflow(
    sid: str,
    session_state: SessionState,
    hitl_handler: APIHITLHandler,
    orchestrator: IntelligentOrchestrator,
    user_input: str,
    repo_path: Optional[str] = None
):
    """Executes Pillar 3 with intelligent orchestration."""
    sage = SageAgent()
    
    orchestrator.add_conversation_turn("user", user_input)
    
    # Create progress callback for real-time updates
    async def progress_callback(stage: str, message: str, progress: int):
        await sio.emit('pipeline_update', {
            'current_stage': stage,
            'active_agent': 'SAGE',
            'progress_percent': progress,
            'stage_description': message,
        }, to=sid)
        await stream_agent_log(sid, 'SAGE', message, 'thought')
    
    context = AgentContext(
        session_state=session_state,
        conversation=session_state.pillar3_conversation,
        user_input=user_input,
        metadata={
            "repository_path": repo_path,
            "progress_callback": progress_callback,
        } if repo_path else {}
    )
    
    await stream_agent_log(sid, 'SAGE', f'Consulting the Codebase Oracle: {user_input}', 'action')
    
    # Initial progress update
    if repo_path:
        await sio.emit('pipeline_update', {
            'current_stage': 'cloning',
            'active_agent': 'SAGE',
            'progress_percent': 5,
            'stage_description': f'Connecting to repository: {repo_path}',
        }, to=sid)
        await stream_agent_log(sid, 'SAGE', f'🔗 Connecting to repository: {repo_path}', 'thought')
    else:
        await sio.emit('pipeline_update', {
            'current_stage': 'indexing',
            'active_agent': 'SAGE',
            'progress_percent': 20,
            'stage_description': 'Analyzing codebase structure',
        }, to=sid)

    try:
        await stream_typing_indicator(sid, 'SAGE', True)
        
        response = await sage.execute(context)
        await stream_typing_indicator(sid, 'SAGE', False)
        
        orchestrator.add_conversation_turn("sage", response.content)
        
        iteration = 0
        max_iterations = 10
        
        while response.hitl_checkpoint and not response.hitl_checkpoint.is_resolved and iteration < max_iterations:
            iteration += 1
            checkpoint = response.hitl_checkpoint
            
            await emit_smart_checkpoint(sid, checkpoint, orchestrator)
            
            # Wait for user decision - this BLOCKS until user responds
            decision = await hitl_handler.present_checkpoint(checkpoint)
            
            # Get user input from handler (stored before cleanup)
            user_response = hitl_handler.get_last_user_input()
            orchestrator.add_conversation_turn("user", user_response or f"Decision: {decision.value}")
            
            await sio.emit('pipeline_update', {
                'current_stage': 'retrieval',
                'active_agent': 'SAGE',
                'progress_percent': 60,
                'stage_description': 'Retrieving relevant context',
            }, to=sid)
            
            await stream_typing_indicator(sid, 'SAGE', True)
            await stream_agent_log(sid, 'SAGE', 'Searching embeddings and retrieving relevant context blocks...', 'thought')
            
            response = await sage.execute(context)
            await stream_typing_indicator(sid, 'SAGE', False)
            
            orchestrator.add_conversation_turn("sage", response.content)
        
        await sio.emit('pipeline_update', {
            'current_stage': 'complete',
            'active_agent': None,
            'progress_percent': 100,
            'stage_description': 'Analysis complete!',
        }, to=sid)
        
        await stream_agent_log(sid, 'SAGE', response.content, 'result')
        await stream_agent_log(
            sid, 
            'SYSTEM', 
            '✅ Codebase analysis complete! Ask follow-up questions anytime.', 
            'action'
        )

    except Exception as e:
        logger.exception("Error in Pillar 3 pipeline")
        await stream_agent_log(sid, 'SYSTEM', f'❌ Error: {str(e)}', 'error')


# --- REST API Endpoints ---

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Helix API...")
    # Initialize Redis storage (will use in-memory if Redis unavailable)
    try:
        storage = await get_storage()
        logger.info("Storage backend initialized successfully")
    except Exception as e:
        logger.warning(f"Storage initialization warning: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Helix API...")
    # Close Redis connection
    await close_storage()
    logger.info("Storage connection closed")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.3.0"}


@app.get("/api/agents")
async def get_agents():
    """Get all agent personas."""
    return AGENT_PERSONAS


@app.get("/api/session/{sid}")
async def get_session(sid: str):
    """Get session state."""
    session = active_sessions.get(sid)
    if not session:
        return {"error": "Session not found"}
    
    return {
        "id": str(session.id),
        "active_pillar": session.active_pillar,
        "checkpoints_count": len(session.checkpoints),
        "pending_count": len(session.pending_checkpoints),
    }


# To run: uvicorn src.api:socket_app --reload --host 0.0.0.0 --port 8000
