import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Workspace configuration
export interface WorkspaceConfig {
  type: 'github' | 'local' | 'new';
  name: string;
  github_repo?: string;
  github_owner?: string;
  local_path?: string;
  // Note: FileSystemDirectoryHandle cannot be persisted, stored separately
}

// Generated file
export interface GeneratedFile {
  path: string;
  content: string;
  language?: string;
  status?: 'pending' | 'writing' | 'written' | 'error';
}

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
  type: 'message' | 'checkpoint' | 'handoff' | 'result' | 'pillar_transition';
  metadata?: Record<string, unknown>;
  pillar?: number; // Track which pillar this message belongs to
}

// Pillar 1 context (startup brief) to pass to Pillar 2
export interface Pillar1Context {
  idea: string;
  brief_summary: string;
  feasibility_score?: number;
  technical_analysis?: string;
  financial_analysis?: string;
  marketing_analysis?: string;
  investor_feedback?: string;
  timestamp: number;
}

// Cross-pillar context for intelligent transitions
export interface CrossPillarContext {
  sourcePillar: number;
  targetPillar: number;
  summary: string;
  keyInsights: string[];
  userIntent: string;
  timestamp: number;
}

// Pillar-specific conversation histories
export interface PillarConversations {
  pillar1: ConversationMessage[];
  pillar2: ConversationMessage[];
  pillar3: ConversationMessage[];
}

// Helper function to get pillar name
export const getPillarName = (pillar: number): string => {
  switch (pillar) {
    case 1: return 'Founding Team';
    case 2: return 'Engineering Workforce';
    case 3: return 'Knowledge Base';
    default: return `Pillar ${pillar}`;
  }
};

interface HelixState {
  // Session State
  sessionId: string | null;
  activePillar: number | null;
  setSession: (id: string, pillar: number) => void;
  setActivePillar: (pillar: number) => void;

  // Pillar 1 Context (for passing to Pillar 2)
  pillar1Context: Pillar1Context | null;
  setPillar1Context: (context: Pillar1Context | null) => void;
  pendingPillar2Start: boolean;
  setPendingPillar2Start: (pending: boolean) => void;

  // Cross-pillar context for intelligent transitions
  crossPillarContext: CrossPillarContext | null;
  setCrossPillarContext: (context: CrossPillarContext | null) => void;
  
  // Pillar-specific conversations (separate chat histories)
  pillarConversations: PillarConversations;
  addPillarMessage: (pillar: number, message: Omit<ConversationMessage, 'id' | 'timestamp' | 'pillar'>) => void;
  getPillarConversation: (pillar: number) => ConversationMessage[];
  clearPillarConversation: (pillar: number) => void;
  
  // Intelligent pillar transition
  transitionToPillar: (targetPillar: number, context?: { summary?: string; userIntent?: string }) => void;

  // Workspace State
  workspace: WorkspaceConfig | null;
  setWorkspace: (workspace: WorkspaceConfig | null) => void;
  isOnboarded: boolean;
  setOnboarded: (onboarded: boolean) => void;

  // Generated Files (for live preview and local sync)
  generatedFiles: GeneratedFile[];
  addGeneratedFile: (file: GeneratedFile) => void;
  addGeneratedFiles: (files: GeneratedFile[]) => void;
  updateFileStatus: (path: string, status: GeneratedFile['status']) => void;
  clearGeneratedFiles: () => void;

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
  resetPillarPipeline: (pillar: number) => void;

  // HITL State (deprecated - keeping for backward compatibility)
  pendingCheckpoints: HitlCheckpoint[];
  addCheckpoint: (checkpoint: HitlCheckpoint) => void;
  removeCheckpoint: (id: string) => void;
  updateCheckpoint: (id: string, updates: Partial<HitlCheckpoint>) => void;

  // Agent Logs (legacy support)
  agentLogs: AgentLog[];
  addAgentLog: (log: Omit<AgentLog, 'timestamp'>, pillar?: number) => void;
  clearAgentLogs: () => void;

  // Conversation (unified view - combines all pillar conversations)
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
  setActivePillar: (pillar) => set({ activePillar: pillar }),

  // Pillar 1 Context
  pillar1Context: null,
  setPillar1Context: (context) => set({ pillar1Context: context }),
  pendingPillar2Start: false,
  setPendingPillar2Start: (pending) => set({ pendingPillar2Start: pending }),

  // Cross-pillar context
  crossPillarContext: null,
  setCrossPillarContext: (context) => set({ crossPillarContext: context }),

  // Pillar-specific conversations (separate chat histories for each pillar)
  pillarConversations: {
    pillar1: [],
    pillar2: [],
    pillar3: [],
  },
  
  addPillarMessage: (pillar, message) => set((state) => {
    const pillarKey = `pillar${pillar}` as keyof PillarConversations;
    const newMessage: ConversationMessage = {
      ...message,
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      pillar,
    };
    
    return {
      pillarConversations: {
        ...state.pillarConversations,
        [pillarKey]: [...state.pillarConversations[pillarKey], newMessage],
      },
      // Also add to unified conversation view
      conversation: [...state.conversation, newMessage],
    };
  }),
  
  getPillarConversation: (pillar) => {
    const state = get();
    const pillarKey = `pillar${pillar}` as keyof PillarConversations;
    return state.pillarConversations[pillarKey] || [];
  },
  
  clearPillarConversation: (pillar) => set((state) => {
    const pillarKey = `pillar${pillar}` as keyof PillarConversations;
    return {
      pillarConversations: {
        ...state.pillarConversations,
        [pillarKey]: [],
      },
    };
  }),
  
  // Intelligent pillar transition with context passing
  transitionToPillar: (targetPillar, context) => set((state) => {
    const sourcePillar = state.activePillar || 1;
    const sourceKey = `pillar${sourcePillar}` as keyof PillarConversations;
    const sourceConversation = state.pillarConversations[sourceKey];
    
    // Generate summary from source conversation
    const recentMessages = sourceConversation.slice(-10);
    const keyInsights = recentMessages
      .filter(m => m.type === 'result' || (m.metadata as Record<string, unknown>)?.logType === 'result')
      .map(m => m.content.substring(0, 200))
      .slice(-3);
    
    const crossPillarContext: CrossPillarContext = {
      sourcePillar,
      targetPillar,
      summary: context?.summary || `Transitioning from Pillar ${sourcePillar} to Pillar ${targetPillar}`,
      keyInsights,
      userIntent: context?.userIntent || 'Continue workflow',
      timestamp: Date.now(),
    };
    
    // Add transition message to target pillar
    const targetKey = `pillar${targetPillar}` as keyof PillarConversations;
    const transitionMessage: ConversationMessage = {
      id: `transition-${Date.now()}`,
      speaker: 'system',
      content: `📋 **Context from ${getPillarName(sourcePillar)}:**\n\n${crossPillarContext.summary}\n\n${keyInsights.length > 0 ? '**Key Insights:**\n' + keyInsights.map(i => `• ${i}`).join('\n') : ''}`,
      timestamp: Date.now(),
      type: 'pillar_transition',
      pillar: targetPillar,
      metadata: { crossPillarContext },
    };
    
    return {
      activePillar: targetPillar,
      crossPillarContext,
      pillarConversations: {
        ...state.pillarConversations,
        [targetKey]: [transitionMessage, ...state.pillarConversations[targetKey]],
      },
    };
  }),

  // Workspace
  workspace: null,
  setWorkspace: (workspace) => set({ workspace }),
  isOnboarded: false,
  setOnboarded: (onboarded) => set({ isOnboarded: onboarded }),

  // Generated Files
  generatedFiles: [],
  addGeneratedFile: (file) => set((state) => ({
    generatedFiles: [...state.generatedFiles.filter(f => f.path !== file.path), file],
  })),
  addGeneratedFiles: (files) => set((state) => {
    const existingPaths = new Set(files.map(f => f.path));
    const filtered = state.generatedFiles.filter(f => !existingPaths.has(f.path));
    return { generatedFiles: [...filtered, ...files] };
  }),
  updateFileStatus: (path, status) => set((state) => ({
    generatedFiles: state.generatedFiles.map(f => 
      f.path === path ? { ...f, status } : f
    ),
  })),
  clearGeneratedFiles: () => set({ generatedFiles: [] }),

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
    // Not processing when complete, idle, or waiting for user input
    isProcessing: stage !== 'complete' && stage !== 'idle' && stage !== 'waiting_for_input'
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
    generatedFiles: [],
  }),
  
  // Reset pipeline for a specific pillar only
  resetPillarPipeline: (pillar) => set((state) => {
    const pillarKey = `pillar${pillar}` as keyof PillarConversations;
    return {
      currentStage: 'idle',
      stageDescription: '',
      activeAgent: null,
      pipelineProgress: 0,
      isProcessing: false,
      pendingCheckpoints: [],
      typingAgents: new Set(),
      // Only clear the specific pillar's conversation
      pillarConversations: {
        ...state.pillarConversations,
        [pillarKey]: [],
      },
      // Clear generated files only for pillar 2
      generatedFiles: pillar === 2 ? [] : state.generatedFiles,
    };
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
  addAgentLog: (log, pillar) => set((state) => {
    const newLog = { ...log, timestamp: Date.now() };
    const activePillar = pillar || state.activePillar || 1;
    const pillarKey = `pillar${activePillar}` as keyof PillarConversations;
    
    // Create conversation message
    const conversationMessage: ConversationMessage = {
      id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      speaker: log.agent.toLowerCase(),
      content: log.message,
      timestamp: Date.now(),
      type: log.type === 'result' ? 'result' : 'message',
      pillar: activePillar,
      metadata: { logType: log.type, persona: log.persona },
    };
    
    return { 
      agentLogs: [...state.agentLogs, newLog],
      // Add to unified conversation
      conversation: [...state.conversation, conversationMessage],
      // Add to pillar-specific conversation
      pillarConversations: {
        ...state.pillarConversations,
        [pillarKey]: [...state.pillarConversations[pillarKey], conversationMessage],
      },
    };
  }),
  clearAgentLogs: () => set({ agentLogs: [] }),

  // Conversation
  conversation: [],
  addConversationMessage: (message) => set((state) => {
    const activePillar = message.pillar || state.activePillar || 1;
    const pillarKey = `pillar${activePillar}` as keyof PillarConversations;
    
    const newMessage: ConversationMessage = {
      ...message,
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      pillar: activePillar,
    };
    
    return {
      conversation: [...state.conversation, newMessage],
      // Also add to pillar-specific conversation
      pillarConversations: {
        ...state.pillarConversations,
        [pillarKey]: [...state.pillarConversations[pillarKey], newMessage],
      },
    };
  }),
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
