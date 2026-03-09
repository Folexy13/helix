import { create } from 'zustand';

// Agent persona type
export interface AgentPersona {
  name: string;
  title: string;
  avatar: string;
  color: string;
  voice: string;
  description: string;
}

// Next step option for smart navigation
export interface NextStepOption {
  id: string;
  label: string;
  description: string;
  action: string;
  color: string;
}

// Enhanced checkpoint with smart features
export interface HitlCheckpoint {
  id: string;
  gate_type: string;
  pillar: number;
  agent: string;
  prompt: string;
  options: string[];
  // Enhanced fields
  questions?: Array<{
    id: string;
    text: string;
    type: 'text' | 'select' | 'multiselect';
    required: boolean;
    placeholder?: string;
    options?: string[];
  }>;
  suggestions?: string[];
  context_summary?: string;
  conversation_history?: Array<{
    speaker: string;
    content: string;
  }>;
  agent_persona?: AgentPersona;
  allows_follow_up?: boolean;
  timestamp?: string;
  // Next steps specific
  is_next_steps?: boolean;
  next_step_options?: NextStepOption[];
}

// Agent log with persona
export interface AgentLog {
  agent: string;
  message: string;
  type: 'thought' | 'action' | 'result' | 'error';
  timestamp: number;
  persona?: AgentPersona;
}

// Agent handoff event
export interface AgentHandoff {
  from_agent: string;
  to_agent: string;
  reason: string;
  from_persona?: AgentPersona;
  to_persona?: AgentPersona;
  timestamp: string;
}

// Conversation message
export interface ConversationMessage {
  id: string;
  speaker: 'user' | string;
  content: string;
  timestamp: number;
  type: 'message' | 'checkpoint' | 'handoff' | 'result';
  metadata?: Record<string, unknown>;
}

interface HelixState {
  // Session State
  sessionId: string | null;
  activePillar: number | null;
  setSession: (id: string, pillar: number) => void;

  // Agent Personas
  agentPersonas: Record<string, AgentPersona>;
  setAgentPersonas: (personas: Record<string, AgentPersona>) => void;

  // Pipeline State
  currentStage: string;
  stageDescription: string;
  activeAgent: string | null;
  pipelineProgress: number;
  isProcessing: boolean;
  setPipelineUpdate: (stage: string, agent: string | null, progress: number, description?: string) => void;
  setIsProcessing: (processing: boolean) => void;
  resetPipeline: () => void;

  // HITL State
  pendingCheckpoints: HitlCheckpoint[];
  addCheckpoint: (checkpoint: HitlCheckpoint) => void;
  removeCheckpoint: (id: string) => void;
  updateCheckpoint: (id: string, updates: Partial<HitlCheckpoint>) => void;

  // Agent Logs (legacy support)
  agentLogs: AgentLog[];
  addAgentLog: (log: Omit<AgentLog, 'timestamp'>) => void;
  clearAgentLogs: () => void;

  // Conversation (new conversational UI)
  conversation: ConversationMessage[];
  addConversationMessage: (message: Omit<ConversationMessage, 'id' | 'timestamp'>) => void;
  clearConversation: () => void;

  // Agent Handoffs
  handoffs: AgentHandoff[];
  addHandoff: (handoff: AgentHandoff) => void;

  // Typing Indicators
  typingAgents: Set<string>;
  setAgentTyping: (agent: string, isTyping: boolean) => void;

  // UI State
  isHitlDrawerOpen: boolean;
  setHitlDrawerOpen: (open: boolean) => void;
  selectedAgent: string | null;
  setSelectedAgent: (agent: string | null) => void;
}

export const useHelixStore = create<HelixState>((set, get) => ({
  // Session
  sessionId: null,
  activePillar: null,
  setSession: (id, pillar) => set({ sessionId: id, activePillar: pillar }),

  // Agent Personas
  agentPersonas: {},
  setAgentPersonas: (personas) => set({ agentPersonas: personas }),

  // Pipeline
  currentStage: 'idle',
  stageDescription: '',
  activeAgent: null,
  pipelineProgress: 0,
  isProcessing: false,
  setPipelineUpdate: (stage, agent, progress, description = '') => set({ 
    currentStage: stage, 
    activeAgent: agent, 
    pipelineProgress: progress,
    stageDescription: description,
    isProcessing: stage !== 'complete' && stage !== 'idle'
  }),
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  resetPipeline: () => set({ 
    currentStage: 'idle', 
    stageDescription: '',
    activeAgent: null, 
    pipelineProgress: 0, 
    isProcessing: false,
    agentLogs: [],
    conversation: [],
    pendingCheckpoints: [],
    handoffs: [],
    typingAgents: new Set(),
  }),

  // HITL Checkpoints
  pendingCheckpoints: [],
  addCheckpoint: (checkpoint) => set((state) => ({ 
    pendingCheckpoints: [...state.pendingCheckpoints, checkpoint],
    isHitlDrawerOpen: true, // Auto-open drawer on new checkpoint
  })),
  removeCheckpoint: (id) => set((state) => ({ 
    pendingCheckpoints: state.pendingCheckpoints.filter((cp) => cp.id !== id),
    isHitlDrawerOpen: state.pendingCheckpoints.length > 1, // Close if last checkpoint
  })),
  updateCheckpoint: (id, updates) => set((state) => ({
    pendingCheckpoints: state.pendingCheckpoints.map((cp) =>
      cp.id === id ? { ...cp, ...updates } : cp
    ),
  })),

  // Agent Logs
  agentLogs: [],
  addAgentLog: (log) => set((state) => {
    const newLog = { ...log, timestamp: Date.now() };
    
    // Also add to conversation for unified view
    const conversationMessage: ConversationMessage = {
      id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      speaker: log.agent.toLowerCase(),
      content: log.message,
      timestamp: Date.now(),
      type: log.type === 'result' ? 'result' : 'message',
      metadata: { logType: log.type, persona: log.persona },
    };
    
    return { 
      agentLogs: [...state.agentLogs, newLog],
      conversation: [...state.conversation, conversationMessage],
    };
  }),
  clearAgentLogs: () => set({ agentLogs: [] }),

  // Conversation
  conversation: [],
  addConversationMessage: (message) => set((state) => ({
    conversation: [...state.conversation, {
      ...message,
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
    }],
  })),
  clearConversation: () => set({ conversation: [] }),

  // Handoffs
  handoffs: [],
  addHandoff: (handoff) => set((state) => {
    // Also add to conversation
    const conversationMessage: ConversationMessage = {
      id: `handoff-${Date.now()}`,
      speaker: 'system',
      content: `${handoff.from_agent.toUpperCase()} → ${handoff.to_agent.toUpperCase()}: ${handoff.reason}`,
      timestamp: Date.now(),
      type: 'handoff',
      metadata: { handoff },
    };
    
    return {
      handoffs: [...state.handoffs, handoff],
      conversation: [...state.conversation, conversationMessage],
    };
  }),

  // Typing Indicators
  typingAgents: new Set(),
  setAgentTyping: (agent, isTyping) => set((state) => {
    const newSet = new Set(state.typingAgents);
    if (isTyping) {
      newSet.add(agent);
    } else {
      newSet.delete(agent);
    }
    return { typingAgents: newSet };
  }),

  // UI State
  isHitlDrawerOpen: false,
  setHitlDrawerOpen: (open) => set({ isHitlDrawerOpen: open }),
  selectedAgent: null,
  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
}));
