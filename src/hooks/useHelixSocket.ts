import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { useHelixStore } from '../store/helixStore';

const SOCKET_URL = process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:8000';

export function useHelixSocket() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const { setPipelineUpdate, addAgentLog, addCheckpoint, removeCheckpoint } = useHelixStore();

  useEffect(() => {
    const socketInstance = io(SOCKET_URL, {
      reconnectionDelayMax: 10000,
    });

    socketInstance.on('connect', () => {
      setIsConnected(true);
      console.log('Connected to Helix Backend via WebSocket');
    });

    socketInstance.on('disconnect', () => {
      setIsConnected(false);
      console.log('Disconnected from Helix Backend');
    });

    socketInstance.on('pipeline_update', (data) => {
      setPipelineUpdate(data.current_stage, data.active_agent, data.progress_percent);
    });

    socketInstance.on('agent_log', (data) => {
      addAgentLog({
        agent: data.agent,
        message: data.message,
        type: data.type
      });
    });

    socketInstance.on('hitl_checkpoint', (data) => {
      addCheckpoint(data);
    });
    
    socketInstance.on('hitl_resolved', (data) => {
      removeCheckpoint(data.checkpoint_id);
    });

    setSocket(socketInstance);

    return () => {
      socketInstance.disconnect();
    };
  }, [setPipelineUpdate, addAgentLog, addCheckpoint, removeCheckpoint]);

  const sendHitlDecision = (checkpointId: string, decision: string, input?: string) => {
    if (socket && isConnected) {
      socket.emit('hitl_decision', { checkpoint_id: checkpointId, decision, user_input: input });
      // Optimistically remove
      removeCheckpoint(checkpointId); 
    }
  };

  const startPipeline = (pillar: number, input: string, repo?: string) => {
      if(socket && isConnected) {
          socket.emit('start_pipeline', {pillar, input, repo})
      }
  }

  return { socket, isConnected, sendHitlDecision, startPipeline };
}
