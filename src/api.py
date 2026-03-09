"""
API Module

FastAPI application providing the backend for the Helix frontend dashboard.
Includes Socket.IO for real-time bidirectional communication.

Enhanced with:
- Intelligent HITL with follow-up questions
- Smart agent handoffs with context awareness
- Bidirectional conversation support
- Real-time agent status streaming
"""

import asyncio
import logging
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

logger = logging.getLogger(__name__)

# --- Setup FastAPI ---
app = FastAPI(title="Helix API", version="0.2.0")

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


# --- Agent Personas for UI ---
AGENT_PERSONAS = {
    "ROUTER": {
        "name": "ROUTER",
        "title": "Team Coordinator",
        "avatar": "🎯",
        "color": "#f97316",
        "voice": "neutral",
        "description": "Orchestrates the founding team analysis"
    },
    "ARIA": {
        "name": "ARIA",
        "title": "Chief Technology Officer",
        "avatar": "🔧",
        "color": "#3b82f6",
        "voice": "technical",
        "description": "Technical feasibility and architecture expert"
    },
    "FELIX": {
        "name": "FELIX",
        "title": "Chief Financial Officer",
        "avatar": "💰",
        "color": "#22c55e",
        "voice": "analytical",
        "description": "Financial projections and cost analysis"
    },
    "NOVA": {
        "name": "NOVA",
        "title": "Chief Marketing Officer",
        "avatar": "📣",
        "color": "#ec4899",
        "voice": "creative",
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
    
    logger.info(f"Starting pipeline for Pillar {pillar} via Socket {sid}")
    
    # Create Session State
    session_state = SessionState()
    checkpoint_manager = CheckpointManager(session_state)
    hitl_handler = APIHITLHandler(checkpoint_manager)
    intelligent_orchestrator = IntelligentOrchestrator(session_state)
    
    # Store globally for this connection
    active_sessions[sid] = session_state
    hitl_handlers[sid] = hitl_handler
    orchestrators[sid] = intelligent_orchestrator
    conversation_contexts[sid] = {"pillar": pillar, "started_at": datetime.utcnow().isoformat()}

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


async def emit_smart_checkpoint(sid: str, checkpoint, orchestrator: IntelligentOrchestrator):
    """Emit an enhanced HITL checkpoint with smart features."""
    # Generate smart suggestions based on context
    suggestions = []
    if checkpoint.gate_type == HITLGateType.IDEA_CLARIFICATION:
        suggestions = [
            "Focus on B2B SaaS market",
            "Target enterprise customers",
            "Start with MVP approach",
            "Consider freemium model",
        ]
    elif checkpoint.gate_type == HITLGateType.SPEC_APPROVAL:
        suggestions = [
            "Add more acceptance criteria",
            "Break down into smaller tasks",
            "Request complexity estimates",
        ]
    
    # Parse questions from prompt if present
    questions = []
    prompt_lines = checkpoint.prompt.split('\n')
    for i, line in enumerate(prompt_lines):
        if line.strip().startswith('-'):
            questions.append({
                "id": f"q_{i}",
                "text": line.strip()[1:].strip(),
                "type": "text",
                "required": True,
                "placeholder": "Your answer...",
            })
    
    # Get conversation context
    context_summary = orchestrator._generate_context_summary() if orchestrator else ""
    
    await sio.emit('hitl_checkpoint', {
        'id': str(checkpoint.id),
        'gate_type': checkpoint.gate_type.value,
        'pillar': checkpoint.pillar,
        'agent': checkpoint.agent.value,
        'prompt': checkpoint.prompt,
        'options': [opt.value for opt in checkpoint.options],
        # Enhanced fields
        'questions': questions,
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
    """Executes Pillar 1 with intelligent orchestration."""
    router = RouterAgent()
    
    # Add initial user input to conversation
    orchestrator.add_conversation_turn("user", user_input)
    
    context = AgentContext(
        session_state=session_state,
        conversation=session_state.pillar1_conversation,
        user_input=user_input,
    )
    
    await stream_agent_log(sid, 'ROUTER', f'Initializing Founding Team for idea: {user_input}', 'action')
    await sio.emit('pipeline_update', {
        'current_stage': 'intake',
        'active_agent': 'ROUTER',
        'progress_percent': 10,
        'stage_description': 'Gathering initial information about your idea',
    }, to=sid)

    try:
        # Step 1: Initial execution (Clarification)
        await stream_typing_indicator(sid, 'ROUTER', True)
        await stream_agent_log(sid, 'ROUTER', 'Analyzing your idea and preparing clarifying questions...', 'thought')
        
        response = await router.execute(context)
        await stream_typing_indicator(sid, 'ROUTER', False)
        
        # Add agent response to conversation
        orchestrator.add_conversation_turn("router", response.content)
        
        iteration = 0
        max_iterations = 10
        
        while response.hitl_checkpoint and not response.hitl_checkpoint.is_resolved and iteration < max_iterations:
            iteration += 1
            checkpoint = response.hitl_checkpoint
            
            # Emit enhanced checkpoint
            await emit_smart_checkpoint(sid, checkpoint, orchestrator)
            
            # Wait for user decision
            decision = await hitl_handler.present_checkpoint(checkpoint)
            
            # Get user input from handler
            user_response = hitl_handler._pending.get(str(checkpoint.id), {}).get('input', '')
            
            # Add to conversation
            orchestrator.add_conversation_turn("user", user_response or f"Decision: {decision.value}")
            
            # Record in context
            context.metadata[f"resolved_{checkpoint.gate_type.value}"] = True
            
            if checkpoint.gate_type.value == "gate_1_1":
                context.metadata["clarification_complete"] = True
                context.metadata["user_clarifications"] = user_response
            
            # Update pipeline with agent progression
            await sio.emit('pipeline_update', {
                'current_stage': 'analyzing',
                'active_agent': 'ROUTER',
                'progress_percent': 30,
                'stage_description': 'Coordinating specialist analysis',
            }, to=sid)
            
            # Show handoffs to specialists
            specialists = [
                ('ARIA', 'Evaluating technical architecture and complexity...', 40),
                ('FELIX', 'Projecting financial requirements and runway...', 55),
                ('NOVA', 'Crafting value proposition and go-to-market strategy...', 70),
                ('JUDGE', 'Conducting investor-style evaluation...', 85),
            ]
            
            for agent_name, thought, progress in specialists:
                await stream_typing_indicator(sid, agent_name, True)
                await stream_agent_log(sid, agent_name, thought, 'thought')
                
                # Record handoff
                orchestrator.record_handoff(AgentHandoff(
                    from_agent=AgentRole.ROUTER,
                    to_agent=AgentRole(agent_name.lower()),
                    reason=HandoffReason.TASK_COMPLETE,
                    context={"stage": "analysis"},
                ))
                
                await asyncio.sleep(0.5)  # Brief pause for UI effect
                await stream_typing_indicator(sid, agent_name, False)
                
                await sio.emit('pipeline_update', {
                    'current_stage': 'analyzing',
                    'active_agent': agent_name,
                    'progress_percent': progress,
                    'stage_description': f'{agent_name} is analyzing...',
                }, to=sid)
            
            response = await router.execute(context)
            orchestrator.add_conversation_turn("router", response.content)
        
        # Final completion
        await sio.emit('pipeline_update', {
            'current_stage': 'complete',
            'active_agent': None,
            'progress_percent': 100,
            'stage_description': 'Analysis complete!',
        }, to=sid)
        
        await stream_agent_log(sid, 'ROUTER', response.content, 'result')
        
        # Emit smart next-steps checkpoint
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
    """Executes Pillar 2 with intelligent orchestration."""
    orch_agent = OrchestratorAgent()
    
    orchestrator.add_conversation_turn("user", user_input)
    
    context = AgentContext(
        session_state=session_state,
        conversation=session_state.pillar2_conversation,
        user_input=user_input,
    )
    
    await stream_agent_log(sid, 'ORCHESTRATOR', f'Starting Engineering Workforce for: {user_input}', 'action')
    await sio.emit('pipeline_update', {
        'current_stage': 'intake',
        'active_agent': 'ORCHESTRATOR',
        'progress_percent': 10,
        'stage_description': 'Understanding your requirements',
    }, to=sid)

    try:
        # Step 1: Planning
        await sio.emit('pipeline_update', {
            'current_stage': 'planning',
            'active_agent': 'PLANNER',
            'progress_percent': 20,
            'stage_description': 'Designing architecture and specifications',
        }, to=sid)
        await stream_typing_indicator(sid, 'PLANNER', True)
        await stream_agent_log(sid, 'PLANNER', 'Creating ERD, UML, and Architecture diagrams...', 'thought')
        
        planner_response = await orch_agent.planner.execute(context)
        await stream_typing_indicator(sid, 'PLANNER', False)
        await stream_agent_log(sid, 'PLANNER', planner_response.content, 'result')
        
        context.metadata["engineering_spec"] = planner_response.metadata
        context.metadata["spec_text"] = planner_response.content
        
        # Step 2: Coding
        await sio.emit('pipeline_update', {
            'current_stage': 'coding',
            'active_agent': 'CODER',
            'progress_percent': 45,
            'stage_description': 'Implementing feature code',
        }, to=sid)
        await stream_typing_indicator(sid, 'CODER', True)
        await stream_agent_log(sid, 'CODER', 'Building project files and installing dependencies...', 'thought')
        
        coder_response = await orch_agent.coder.execute(context)
        await stream_typing_indicator(sid, 'CODER', False)
        await stream_agent_log(sid, 'CODER', coder_response.content, 'result')
        
        context.metadata["code_output"] = coder_response.metadata.get("code_output", {})
        
        # Save generated project to filesystem (Kilo Code style)
        try:
            import os
            project_dir = os.path.join(os.getcwd(), "output", "projects", sid)
            code_output = coder_response.metadata.get("code_output", {})
            all_files = {**code_output.get("files", {}), **code_output.get("tests", {}), **code_output.get("documentation", {})}
            
            if all_files:
                saved_paths = save_project_files(project_dir, all_files)
                await stream_agent_log(sid, 'SYSTEM', f'📂 Project files saved to `{project_dir}` ({len(saved_paths)} files)', 'action')
        except Exception as fs_err:
            logger.error(f"Failed to save project files: {fs_err}")
        
        # Step 3: Testing
        await sio.emit('pipeline_update', {
            'current_stage': 'testing',
            'active_agent': 'TESTER',
            'progress_percent': 70,
            'stage_description': 'Validating implementation with tests',
        }, to=sid)
        await stream_typing_indicator(sid, 'TESTER', True)
        await stream_agent_log(sid, 'TESTER', 'Running automated test suites...', 'thought')
        
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
            
            decision = await hitl_handler.present_checkpoint(checkpoint)
            
            user_response = hitl_handler._pending.get(str(checkpoint.id), {}).get('input', '')
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

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.2.0"}


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
