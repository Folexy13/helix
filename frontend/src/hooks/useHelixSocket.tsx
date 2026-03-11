"use client";

import React, { createContext, useContext, useEffect, useState, useRef, useCallback, ReactNode } from 'react';
import { io, Socket } from 'socket.io-client';
import { useHelixStore, AgentPersona, HitlCheckpoint, AgentHandoff, PillarConversations } from '../store/helixStore';

const SOCKET_URL = process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:8000';

interface HelixSocketContextType {
  isConnected: boolean;
  sendHitlDecision: (checkpointId: string, decision: string, input?: string, fieldResponses?: Record<string, string>) => void;
  startPipeline: (pillar: number, input: string, repo?: string, context?: { fromPillar?: number; summary?: string }) => void;
  sendUserMessage: (message: string, targetAgent?: string, pillar?: number) => void;
  requestClarification: (agent: string, question: string) => void;
  transitionToPillar: (targetPillar: number, context?: { summary?: string; userIntent?: string }) => void;
}

const HelixSocketContext = createContext<HelixSocketContextType | undefined>(undefined);

export function HelixSocketProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const storeRef = useRef(useHelixStore.getState());
  
  useEffect(() => {
    const unsubscribe = useHelixStore.subscribe((state) => {
      storeRef.current = state;
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    console.log('Global Socket: Initializing to:', SOCKET_URL);
    const socketInstance = io(SOCKET_URL, {
      reconnectionDelayMax: 10000,
      transports: ['websocket', 'polling'],
      autoConnect: true,
    });

    socketRef.current = socketInstance;

    socketInstance.on('connect', () => {
      console.log('Global Socket: Connected');
      setIsConnected(true);
    });

    socketInstance.on('disconnect', (reason) => {
      console.log('Global Socket: Disconnected, reason:', reason);
      setIsConnected(false);
    });

    // Agent personas (sent on connect)
    socketInstance.on('agent_personas', (personas: Record<string, AgentPersona>) => {
      console.log('Global Socket: Received agent personas');
      storeRef.current.setAgentPersonas(personas);
    });

    // Pipeline updates with enhanced info
    socketInstance.on('pipeline_update', (data: {
      current_stage: string;
      active_agent: string | null;
      progress_percent: number;
      stage_description?: string;
    }) => {
      console.log('Global Socket: Pipeline Update', data);
      storeRef.current.setPipelineUpdate(
        data.current_stage, 
        data.active_agent, 
        data.progress_percent,
        data.stage_description || ''
      );
    });

    // Agent logs with persona
    socketInstance.on('agent_log', (data: {
      agent: string;
      message: string;
      type: 'thought' | 'action' | 'result' | 'error';
      timestamp?: string;
      persona?: AgentPersona;
    }) => {
      storeRef.current.addAgentLog({
        agent: data.agent,
        message: data.message,
        type: data.type,
        persona: data.persona,
      });
    });

    // Enhanced HITL checkpoint
    socketInstance.on('hitl_checkpoint', (data: HitlCheckpoint) => {
      console.log('Global Socket: Received HITL checkpoint', data.id);
      storeRef.current.addCheckpoint(data);
    });
    
    // HITL resolved with context
    socketInstance.on('hitl_resolved', (data: {
      checkpoint_id: string;
      decision?: string;
      has_follow_up?: boolean;
      context_summary?: string;
    }) => {
      console.log('Global Socket: HITL resolved', data.checkpoint_id);
      storeRef.current.removeCheckpoint(data.checkpoint_id);
    });

    // Agent handoff events
    socketInstance.on('agent_handoff', (data: AgentHandoff) => {
      console.log('Global Socket: Agent handoff', data.from_agent, '->', data.to_agent);
      storeRef.current.addHandoff(data);
    });

    // Typing indicators
    socketInstance.on('agent_typing', (data: {
      agent: string;
      is_typing: boolean;
      persona?: AgentPersona;
    }) => {
      storeRef.current.setAgentTyping(data.agent, data.is_typing);
    });

    // Generated files for LivePreview (batch)
    socketInstance.on('generated_files', (data: {
      files: Array<{ path: string; content: string; language?: string }>;
      project_type?: string;
    }) => {
      console.log('Global Socket: Received generated files', data.files.length);
      storeRef.current.addGeneratedFiles(data.files);
    });

    // Streaming file generation - files arrive one at a time as they're generated
    socketInstance.on('file_streaming', (data: {
      path: string;
      content: string;
      language?: string;
      status: 'pending' | 'writing' | 'written' | 'error';
      index: number;
      total: number;
    }) => {
      console.log(`Global Socket: Streaming file ${data.index + 1}/${data.total}: ${data.path}`);
      storeRef.current.addGeneratedFile({
        path: data.path,
        content: data.content,
        language: data.language,
        status: data.status,
      });
    });

    // File generation complete - trigger installation
    socketInstance.on('files_complete', (data: {
      total_files: number;
      project_type: string;
      ready_for_install: boolean;
    }) => {
      console.log(`Global Socket: All ${data.total_files} files generated, ready for install: ${data.ready_for_install}`);
      // The LivePreview component will handle installation when it sees all files are 'written'
    });

    // Message acknowledgment
    socketInstance.on('message_received', (data: {
      message_id: string;
      intent: string;
    }) => {
      console.log('Global Socket: Message received', data.message_id, 'intent:', data.intent);
    });

    // Error handling
    socketInstance.on('error', (data: { message: string }) => {
      console.error('Global Socket: Error', data.message);
      storeRef.current.addAgentLog({
        agent: 'SYSTEM',
        message: `Error: ${data.message}`,
        type: 'error',
      });
    });

    return () => {
      console.log('Global Socket: Cleaning up');
      socketInstance.disconnect();
      socketRef.current = null;
    };
  }, []);

  const sendHitlDecision = useCallback((
    checkpointId: string, 
    decision: string, 
    input?: string,
    fieldResponses?: Record<string, string>
  ) => {
    const socket = socketRef.current;
    if (socket && socket.connected) {
      console.log('Global Socket: Sending HITL decision', decision);
      
      // Add user's decision to conversation
      storeRef.current.addConversationMessage({
        speaker: 'user',
        content: input || `Decision: ${decision}`,
        type: 'message',
        metadata: { decision, fieldResponses },
      });
      
      socket.emit('hitl_decision', { 
        checkpoint_id: checkpointId, 
        decision, 
        user_input: input,
        field_responses: fieldResponses,
      });
      
      // Optimistically remove locally
      storeRef.current.removeCheckpoint(checkpointId);
    } else {
      console.warn('Global Socket: Cannot send decision, socket not connected');
    }
  }, []);

  const startPipeline = useCallback((pillar: number, input: string, repo?: string, context?: { fromPillar?: number; summary?: string }) => {
    const socket = socketRef.current;
    if (socket && socket.connected) {
      console.log('Global Socket: Starting pipeline', pillar, context ? 'with context' : '');
      
      // Only reset the specific pillar's pipeline, not all
      storeRef.current.resetPillarPipeline(pillar);
      storeRef.current.setActivePillar(pillar);
      storeRef.current.setIsProcessing(true);
      
      // Add user's initial message to pillar-specific conversation
      storeRef.current.addPillarMessage(pillar, {
        speaker: 'user',
        content: input,
        type: 'message',
      });
      
      // Include context from previous pillar if transitioning
      socket.emit('start_pipeline', { 
        pillar, 
        input, 
        repo,
        context: context ? {
          from_pillar: context.fromPillar,
          summary: context.summary,
        } : undefined,
      });
    } else {
      console.warn('Global Socket: Cannot start pipeline, socket not connected');
    }
  }, []);

  const sendUserMessage = useCallback((message: string, targetAgent?: string, pillar?: number) => {
    const socket = socketRef.current;
    if (socket && socket.connected) {
      console.log('Global Socket: Sending user message');
      const activePillar = pillar || storeRef.current.activePillar || 1;
      
      // Add to pillar-specific conversation
      storeRef.current.addPillarMessage(activePillar, {
        speaker: 'user',
        content: message,
        type: 'message',
        metadata: { targetAgent },
      });
      
      socket.emit('user_message', { 
        message, 
        target_agent: targetAgent,
        pillar: activePillar,
      });
    } else {
      console.warn('Global Socket: Cannot send message, socket not connected');
    }
  }, []);

  const requestClarification = useCallback((agent: string, question: string) => {
    const socket = socketRef.current;
    if (socket && socket.connected) {
      console.log('Global Socket: Requesting clarification from', agent);
      const activePillar = storeRef.current.activePillar || 1;
      
      storeRef.current.addPillarMessage(activePillar, {
        speaker: 'user',
        content: `@${agent}: ${question}`,
        type: 'message',
        metadata: { targetAgent: agent, isQuestion: true },
      });
      
      socket.emit('request_clarification', { agent, question });
    } else {
      console.warn('Global Socket: Cannot request clarification, socket not connected');
    }
  }, []);

  // Intelligent pillar transition with context passing
  const transitionToPillar = useCallback((targetPillar: number, context?: { summary?: string; userIntent?: string }) => {
    const socket = socketRef.current;
    if (socket && socket.connected) {
      const currentPillar = storeRef.current.activePillar || 1;
      console.log(`Global Socket: Transitioning from Pillar ${currentPillar} to Pillar ${targetPillar}`);
      
      // Use store's transition function to handle context passing
      storeRef.current.transitionToPillar(targetPillar, context);
      
      // Notify backend of pillar transition
      socket.emit('pillar_transition', {
        from_pillar: currentPillar,
        to_pillar: targetPillar,
        context: context,
      });
    } else {
      console.warn('Global Socket: Cannot transition, socket not connected');
    }
  }, []);

  return (
    <HelixSocketContext.Provider value={{ 
      isConnected, 
      sendHitlDecision, 
      startPipeline,
      sendUserMessage,
      requestClarification,
      transitionToPillar,
    }}>
      {children}
    </HelixSocketContext.Provider>
  );
}

export function useHelixSocket() {
  const context = useContext(HelixSocketContext);
  if (context === undefined) {
    throw new Error('useHelixSocket must be used within a HelixSocketProvider');
  }
  return context;
}
