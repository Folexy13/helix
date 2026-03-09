"use client";

import React, { useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useHelixStore } from '@/store/helixStore';

const initialNodes: Node[] = [
  { id: '1', position: { x: 50, y: 50 }, data: { label: 'Intake' }, type: 'input' },
  { id: '2', position: { x: 50, y: 150 }, data: { label: 'PLANNER' } },
  { id: '3', position: { x: 50, y: 250 }, data: { label: 'CODER' } },
  { id: '4', position: { x: -100, y: 350 }, data: { label: 'TESTER' } },
  { id: '5', position: { x: 200, y: 350 }, data: { label: 'DOCS' } },
  { id: '6', position: { x: 50, y: 450 }, data: { label: 'REVIEWER' } },
  { id: '7', position: { x: 50, y: 550 }, data: { label: 'Finalize PR' }, type: 'output' },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2' },
  { id: 'e2-3', source: '2', target: '3' },
  { id: 'e3-4', source: '3', target: '4' },
  { id: 'e3-5', source: '3', target: '5' },
  { id: 'e4-6', source: '4', target: '6' },
  { id: 'e5-6', source: '5', target: '6' },
  { id: 'e6-7', source: '6', target: '7' },
];

export default function PipelineVisualizer() {
  const { currentStage, activeAgent, pendingCheckpoints } = useHelixStore();
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update node styles based on global state
  const styledNodes = useMemo(() => {
    return nodes.map((node) => {
        let isProcessing = false;
        let isWaiting = false;

        if (node.data.label === activeAgent) isProcessing = true;
        if (node.id === '1' && currentStage === 'intake') isProcessing = true;

        const hasCheckpoint = pendingCheckpoints.some(cp => cp.agent === node.data.label);
        if (hasCheckpoint) {
             isWaiting = true;
             isProcessing = false;
        }

      return {
        ...node,
        style: {
          background: isWaiting ? '#f97316' : isProcessing ? '#3b82f6' : '#0f172a',
          color: isProcessing || isWaiting ? '#ffffff' : '#94a3b8',
          border: isWaiting ? '2px solid #fb923c' : isProcessing ? '2px solid #60a5fa' : '1px solid #1e293b',
          borderRadius: '12px',
          padding: '10px 20px',
          fontSize: '11px',
          fontWeight: 'bold',
          letterSpacing: '0.05em',
          boxShadow: isProcessing ? '0 0 20px rgba(59, 130, 246, 0.3)' : isWaiting ? '0 0 20px rgba(249, 115, 22, 0.3)' : 'none',
          transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)'
        },
      };
    });
  }, [nodes, activeAgent, currentStage, pendingCheckpoints]);

  return (
    <div style={{ width: '100%', height: '100%' }} className="bg-[#020617] rounded-xl overflow-hidden border border-slate-800">
      <ReactFlow
        nodes={styledNodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        colorMode="dark"
      >
        <Controls className="bg-slate-900 border-slate-800 fill-white" />
        <MiniMap nodeStrokeWidth={3} nodeColor="#334155" maskColor="#020617" />
        <Background gap={20} size={1} color="#1e293b" />
      </ReactFlow>
    </div>
  );
}
