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
    
    # Generate dynamic suggestions based on the checkpoint context and conversation
    suggestions = []
    prompt_lower = checkpoint.prompt.lower() if checkpoint.prompt else ""
    
    # Get recent conversation for context
    recent_context = ""
    if orchestrator and orchestrator.conversation_history:
        recent_context = " ".join([t.content.lower() for t in orchestrator.conversation_history[-3:]])
    
    # Suggest based on what's being asked - always 4 suggestions
    if "aria" in prompt_lower or "technical" in prompt_lower or "cto" in prompt_lower:
        suggestions = ["Yes, let's hear from Aria", "Skip to Felix (CFO)", "Skip to Nova (CMO)", "I have a question first"]
    elif "felix" in prompt_lower or "financial" in prompt_lower or "cfo" in prompt_lower:
        suggestions = ["Yes, bring in Felix", "Skip to Nova (CMO)", "Skip to Judge", "Go back to Aria"]
    elif "nova" in prompt_lower or "marketing" in prompt_lower or "cmo" in prompt_lower:
        suggestions = ["Yes, let's hear from Nova", "Skip to Judge", "Go back to Felix", "I have questions"]
    elif "judge" in prompt_lower or "investor" in prompt_lower:
        suggestions = ["Yes, give me the tough love", "I'm ready for feedback", "Go back to Nova", "Let me think about it"]
    elif "restaurant" in recent_context or "food" in recent_context:
        suggestions = ["Restaurant owners", "Food delivery services", "Diners/customers", "Move to next agent"]
    elif "saas" in recent_context or "software" in recent_context:
        suggestions = ["Small businesses", "Enterprise companies", "Startups", "Move to next agent"]
    elif "target" in prompt_lower or "audience" in prompt_lower or "who" in prompt_lower:
        suggestions = ["Small businesses", "Enterprise companies", "Consumers", "Move to next agent"]
    elif "problem" in prompt_lower or "solving" in prompt_lower:
        suggestions = ["Efficiency & automation", "Cost reduction", "Better user experience", "Move to next agent"]
    elif "stage" in prompt_lower or "far along" in prompt_lower:
        suggestions = ["Just an idea", "Have a prototype", "MVP ready", "Already launched"]
    elif "team" in prompt_lower or "building" in prompt_lower:
        suggestions = ["Solo founder", "Small team (2-3)", "Full team (4+)", "Looking for co-founders"]
    elif "funding" in prompt_lower or "capital" in prompt_lower:
        suggestions = ["Bootstrapping", "Pre-seed ($50-250k)", "Seed ($500k-2M)", "Series A ($2M+)"]
    else:
        # Default suggestions
        suggestions = ["Tell me more", "Move to next agent", "Let's continue", "I have a question"]
    
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
    Executes Pillar 2 with intelligent orchestration.
    
    This workflow is now fully conversational - no blocking HITL checkpoints.
    The AI proceeds autonomously while keeping the user informed.
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
    
    # Add any pillar 1 context to metadata
    if from_pillar == 1:
        context.metadata["from_pillar1"] = True
        context.metadata["pillar1_context"] = transition_context
    
    await stream_agent_log(sid, 'ORCHESTRATOR', f'🚀 Starting Engineering Workforce for: {user_input[:200]}...', 'action')
    await sio.emit('pipeline_update', {
        'current_stage': 'intake',
        'active_agent': 'ORCHESTRATOR',
        'progress_percent': 10,
        'stage_description': 'Understanding your requirements',
    }, to=sid)

    try:
        # Step 1: Planning (no blocking - proceed automatically)
        await sio.emit('pipeline_update', {
            'current_stage': 'planning',
            'active_agent': 'PLANNER',
            'progress_percent': 15,
            'stage_description': 'Designing architecture and specifications',
        }, to=sid)
        await stream_typing_indicator(sid, 'PLANNER', True)
        await stream_agent_log(sid, 'PLANNER', '📐 Creating architecture, database schema, and project structure...', 'thought')
        
        planner_response = await orch_agent.planner.execute(context)
        await stream_typing_indicator(sid, 'PLANNER', False)
        await stream_agent_log(sid, 'PLANNER', planner_response.content, 'result')
        
        context.metadata["engineering_spec"] = planner_response.metadata
        context.metadata["spec_text"] = planner_response.content
        
        # No HITL blocking - proceed directly to coding
        # User can still provide feedback via chat which will be handled conversationally
        await stream_agent_log(sid, 'ORCHESTRATOR', '✅ Architecture designed. Proceeding to code generation...', 'action')
        
        # Step 2: Coding
        await sio.emit('pipeline_update', {
            'current_stage': 'coding',
            'active_agent': 'CODER',
            'progress_percent': 30,
            'stage_description': 'Generating project files...',
        }, to=sid)
        await stream_typing_indicator(sid, 'CODER', True)
        await stream_agent_log(sid, 'CODER', '🔨 Building project structure and generating code...', 'thought')
        
        coder_response = await orch_agent.coder.execute(context)
        await stream_typing_indicator(sid, 'CODER', False)
        
        context.metadata["code_output"] = coder_response.metadata.get("code_output", {})
        
        # Stream files to frontend one by one for real-time preview
        try:
            import os
            project_dir = os.path.join(os.getcwd(), "output", "projects", sid)
            code_output = coder_response.metadata.get("code_output", {})
            all_files = {**code_output.get("files", {}), **code_output.get("tests", {}), **code_output.get("documentation", {})}
            
            if all_files:
                total_files = len(all_files)
                
                # Language mapping for syntax highlighting
                lang_map = {
                    'py': 'python', 'js': 'javascript', 'ts': 'typescript', 
                    'tsx': 'typescript', 'jsx': 'javascript', 'json': 'json',
                    'html': 'html', 'css': 'css', 'md': 'markdown', 'sql': 'sql',
                    'yaml': 'yaml', 'yml': 'yaml', 'sh': 'bash', 'txt': 'text'
                }
                
                # Stream each file individually with a small delay for visual effect
                for idx, (filepath, content) in enumerate(all_files.items()):
                    ext = filepath.split('.')[-1] if '.' in filepath else ''
                    language = lang_map.get(ext, 'text')
                    
                    # Calculate progress within coding stage (35% to 55%)
                    file_progress = 35 + int((idx / total_files) * 20)
                    
                    # Emit file streaming event
                    await sio.emit('file_streaming', {
                        'path': filepath,
                        'content': content,
                        'language': language,
                        'status': 'writing',
                        'index': idx,
                        'total': total_files,
                    }, to=sid)
                    
                    # Update pipeline progress
                    await sio.emit('pipeline_update', {
                        'current_stage': 'coding',
                        'active_agent': 'CODER',
                        'progress_percent': file_progress,
                        'stage_description': f'📝 Writing {filepath} ({idx + 1}/{total_files})',
                    }, to=sid)
                    
                    # Log each file creation
                    await stream_agent_log(sid, 'CODER', f'📄 Created: `{filepath}`', 'action')
                    
                    # Small delay for visual streaming effect
                    await asyncio.sleep(0.1)
                    
                    # Mark file as written
                    await sio.emit('file_streaming', {
                        'path': filepath,
                        'content': content,
                        'language': language,
                        'status': 'written',
                        'index': idx,
                        'total': total_files,
                    }, to=sid)
                
                # Save to filesystem
                saved_paths = save_project_files(project_dir, all_files)
                await stream_agent_log(sid, 'SYSTEM', f'💾 Saved {len(saved_paths)} files to `{project_dir}`', 'action')
                
                # Emit completion event - frontend can now start installation
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
                
                logger.info(f"Streamed {total_files} files to frontend for LivePreview")
                
                # Summary log
                await stream_agent_log(sid, 'CODER', f'✅ Generated {total_files} files: {", ".join(list(all_files.keys())[:5])}{"..." if total_files > 5 else ""}', 'result')
            else:
                await stream_agent_log(sid, 'CODER', '⚠️ No files were generated', 'error')
                
        except Exception as fs_err:
            logger.error(f"Failed to save project files: {fs_err}")
            await stream_agent_log(sid, 'SYSTEM', f'❌ Error saving files: {str(fs_err)}', 'error')
        
        # HITL Checkpoint: Review Code before Testing
        code_output = coder_response.metadata.get("code_output", {})
        files_created = list(code_output.get("files", {}).keys())
        
        coder_checkpoint = SmartCheckpoint(
            gate_type=HITLGateType.REVIEWER_FLAG,
            pillar=2,
            agent=AgentRole.CODER,
            prompt="Review the generated code before running tests",
            options=[HITLDecision.APPROVE, HITLDecision.REJECT, HITLDecision.MODIFY],
            context_summary=f'Created {len(files_created)} files including: {", ".join(files_created[:5])}{"..." if len(files_created) > 5 else ""}',
        )
        
        # CRITICAL: Register checkpoint BEFORE emitting to frontend
        hitl_handler.register_checkpoint(str(coder_checkpoint.id), coder_checkpoint)
        
        await sio.emit('hitl_checkpoint', {
            'id': str(coder_checkpoint.id),
            'gate_type': coder_checkpoint.gate_type.value,
            'pillar': 2,
            'agent': 'CODER',
            'prompt': f'💻 **Code Generation Complete**\n\nGenerated {len(files_created)} files. Review the code in the Files tab before proceeding to testing.',
            'options': ['approve', 'reject', 'modify'],
            'context_summary': f'Created {len(files_created)} files including: {", ".join(files_created[:5])}{"..." if len(files_created) > 5 else ""}',
            'agent_persona': AGENT_PERSONAS.get('CODER'),
            'allows_follow_up': True,
            'next_step_options': [
                {
                    'id': 'approve',
                    'label': '✅ Approve & Run Tests',
                    'description': 'Proceed to automated testing',
                    'action': 'approve',
                    'color': '#10b981',
                },
                {
                    'id': 'modify',
                    'label': '✏️ Request Changes',
                    'description': 'Ask for code modifications',
                    'action': 'modify',
                    'color': '#f59e0b',
                },
            ],
            'timestamp': datetime.utcnow().isoformat(),
        }, to=sid)
        
        # Wait for user decision - this BLOCKS until user responds
        coder_decision = await hitl_handler.present_checkpoint(coder_checkpoint)
        
        if coder_decision == HITLDecision.REJECT:
            await stream_agent_log(sid, 'SYSTEM', '❌ Code rejected. Pipeline stopped.', 'error')
            return
        
        # Handle MODIFY decision - loop back to CODER with user feedback
        if coder_decision == HITLDecision.MODIFY:
            # Get the user's modification request from the checkpoint
            user_feedback = hitl_handler.get_last_user_input() or "Please make the requested changes."
            
            await stream_agent_log(sid, 'SYSTEM', '✏️ Modification requested. Routing back to CODER...', 'action')
            
            # Update context with modification request
            context.metadata["modification_request"] = user_feedback
            context.metadata["is_modification"] = True
            
            # Re-run CODER with modification context
            await sio.emit('pipeline_update', {
                'current_stage': 'coding',
                'active_agent': 'CODER',
                'progress_percent': 45,
                'stage_description': 'Applying requested modifications',
            }, to=sid)
            await stream_typing_indicator(sid, 'CODER', True)
            await stream_agent_log(sid, 'CODER', f'📝 Applying modifications: {user_feedback}', 'thought')
            
            # Execute CODER again with modification context
            coder_response = await orch_agent.coder.execute(context)
            await stream_typing_indicator(sid, 'CODER', False)
            await stream_agent_log(sid, 'CODER', coder_response.content, 'result')
            
            # Update context with new code output
            context.metadata["code_output"] = coder_response.metadata.get("code_output", {})
            
            # Save updated files
            code_output = coder_response.metadata.get("code_output", {})
            if code_output.get("files"):
                try:
                    project_id = await save_project_files(code_output["files"])
                    await sio.emit('generated_files', {
                        'project_id': project_id,
                        'files': [
                            {'path': path, 'content': content, 'status': 'written'}
                            for path, content in code_output["files"].items()
                        ]
                    }, to=sid)
                    await stream_agent_log(sid, 'SYSTEM', f'💾 Updated {len(code_output["files"])} files', 'action')
                except Exception as fs_err:
                    logger.error(f"Failed to save updated files: {fs_err}")
            
            # Create another checkpoint for the modified code
            files_created = list(code_output.get("files", {}).keys())
            modified_checkpoint = SmartCheckpoint(
                gate_type=HITLGateType.REVIEWER_FLAG,
                pillar=2,
                agent=AgentRole.CODER,
                prompt="Review the modified code before running tests",
                options=[HITLDecision.APPROVE, HITLDecision.REJECT, HITLDecision.MODIFY],
                context_summary=f'Modified {len(files_created)} files based on your feedback',
            )
            
            hitl_handler.register_checkpoint(str(modified_checkpoint.id), modified_checkpoint)
            
            await sio.emit('hitl_checkpoint', {
                'id': str(modified_checkpoint.id),
                'gate_type': modified_checkpoint.gate_type.value,
                'pillar': 2,
                'agent': 'CODER',
                'prompt': f'💻 **Code Modified**\n\nApplied your requested changes to {len(files_created)} files. Review the updated code before proceeding.',
                'options': ['approve', 'reject', 'modify'],
                'context_summary': f'Modified files: {", ".join(files_created[:5])}{"..." if len(files_created) > 5 else ""}',
                'agent_persona': AGENT_PERSONAS.get('CODER'),
                'allows_follow_up': True,
                'next_step_options': [
                    {
                        'id': 'approve',
                        'label': '✅ Approve & Run Tests',
                        'description': 'Proceed to automated testing',
                        'action': 'approve',
                        'color': '#10b981',
                    },
                    {
                        'id': 'modify',
                        'label': '✏️ Request More Changes',
                        'description': 'Ask for additional modifications',
                        'action': 'modify',
                        'color': '#f59e0b',
                    },
                ],
                'timestamp': datetime.utcnow().isoformat(),
            }, to=sid)
            
            # Wait for decision on modified code
            modified_decision = await hitl_handler.present_checkpoint(modified_checkpoint)
            
            if modified_decision == HITLDecision.REJECT:
                await stream_agent_log(sid, 'SYSTEM', '❌ Modified code rejected. Pipeline stopped.', 'error')
                return
            
            # If still MODIFY, we could loop again, but for now proceed after one modification
            if modified_decision == HITLDecision.MODIFY:
                await stream_agent_log(sid, 'SYSTEM', '⚠️ Additional modifications requested. Please use the input field to describe changes, then approve when ready.', 'action')
        
        await stream_agent_log(sid, 'SYSTEM', '✅ Code approved. Proceeding to testing...', 'action')
        
        # Step 3: Testing
        await sio.emit('pipeline_update', {
            'current_stage': 'testing',
            'active_agent': 'TESTER',
            'progress_percent': 65,
            'stage_description': 'Validating implementation with tests',
        }, to=sid)
        await stream_typing_indicator(sid, 'TESTER', True)
        await stream_agent_log(sid, 'TESTER', '🧪 Running automated test suites...', 'thought')
        
        tester_response = await orch_agent.tester.execute(context)
        await stream_typing_indicator(sid, 'TESTER', False)
        await stream_agent_log(sid, 'TESTER', tester_response.content, 'result')
        
        context.metadata["test_output"] = tester_response.metadata
        
        # Step 4: Review
        await sio.emit('pipeline_update', {
            'current_stage': 'reviewing',
            'active_agent': 'REVIEWER',
            'progress_percent': 85,
            'stage_description': 'Performing final code review',
        }, to=sid)
        await stream_typing_indicator(sid, 'REVIEWER', True)
        await stream_agent_log(sid, 'REVIEWER', 'Checking for security and quality issues...', 'thought')
        
        reviewer_response = await orch_agent.reviewer.execute(context)
        await stream_typing_indicator(sid, 'REVIEWER', False)
        await stream_agent_log(sid, 'REVIEWER', reviewer_response.content, 'result')
        
        # Step 5: Finalization
        await sio.emit('pipeline_update', {
            'current_stage': 'complete',
            'active_agent': None,
            'progress_percent': 100,
            'stage_description': 'Engineering package complete!',
        }, to=sid)
        
        # Final deployment checkpoint
        await emit_next_steps_checkpoint(sid, orchestrator, pillar=2, brief_summary={})

    except Exception as e:
        logger.exception("Error in Pillar 2 pipeline")
        await stream_agent_log(sid, 'SYSTEM', f'❌ Error: {str(e)}', 'error')


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
