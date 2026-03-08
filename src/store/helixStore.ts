import { create } from 'zustand';

export interface HitlCheckpoint {
  id: string;
  gate_type: string;
  pillar: number;
  agent: string;
  prompt: string;
  options: string[];
  context_diff?: string; // For code reviews
}

interface HelixState {
  // Session State
  sessionId: string | null;
  activePillar: number | null;
  setSession: (id: string, pillar: number) => void;

  // Pipeline State
  currentStage: string;
  activeAgent: string | null;
  pipelineProgress: number;
  setPipelineUpdate: (stage: string, agent: string | null, progress: number) => void;

  // HITL State
  pendingCheckpoints: HitlCheckpoint[];
  addCheckpoint: (checkpoint: HitlCheckpoint) => void;
  removeCheckpoint: (id: string) => void;

  // Agent Logs
  agentLogs: { agent: string; message: string; type: 'thought' | 'action' | 'result'; timestamp: number }[];
  addAgentLog: (log: { agent: string; message: string; type: 'thought' | 'action' | 'result' }) => void;
}

export const useHelixStore = create<HelixState>((set) => ({
  sessionId: null,
  activePillar: null,
  setSession: (id, pillar) => set({ sessionId: id, activePillar: pillar }),

  currentStage: 'idle',
  activeAgent: null,
  pipelineProgress: 0,
  setPipelineUpdate: (stage, agent, progress) => set({ currentStage: stage, activeAgent: agent, pipelineProgress: progress }),

  pendingCheckpoints: [],
  addCheckpoint: (checkpoint) => set((state) => ({ pendingCheckpoints: [...state.pendingCheckpoints, checkpoint] })),
  removeCheckpoint: (id) => set((state) => ({ pendingCheckpoints: state.pendingCheckpoints.filter((cp) => cp.id !== id) })),

  agentLogs: [],
  addAgentLog: (log) => set((state) => ({ agentLogs: [...state.agentLogs, { ...log, timestamp: Date.now() }] })),
}));
