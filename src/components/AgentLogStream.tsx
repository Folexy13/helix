import { useEffect, useRef } from 'react';
import { useHelixStore } from '@/store/helixStore';
import ReactMarkdown from 'react-markdown';

export default function AgentLogStream() {
  const { agentLogs } = useHelixStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [agentLogs]);

  const getAgentColor = (agent: string) => {
    const colors: Record<string, string> = {
      ARIA: 'text-blue-400',
      FELIX: 'text-green-400',
      NOVA: 'text-pink-400',
      JUDGE: 'text-purple-400',
      ROUTER: 'text-slate-400',
      PLANNER: 'text-indigo-400',
      CODER: 'text-yellow-400',
      TESTER: 'text-red-400',
      DOCS: 'text-teal-400',
      REVIEWER: 'text-orange-400',
      ORCHESTRATOR: 'text-slate-400',
      SAGE: 'text-cyan-400',
    };
    return colors[agent.toUpperCase()] || 'text-slate-400';
  };

  return (
    <div className="flex flex-col h-full bg-[#0f172a] rounded-xl border border-border font-mono text-sm overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-slate-900/50">
        <span className="text-muted-foreground font-semibold">Agent Activity Stream</span>
        <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <span className="text-xs text-muted-foreground">Live</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {agentLogs.length === 0 ? (
           <div className="text-slate-500 italic">Waiting for agent activity...</div>
        ) : (
            agentLogs.map((log, index) => (
            <div key={index} className="flex gap-3">
                <div className="w-20 shrink-0 text-right">
                <span className={`font-bold ${getAgentColor(log.agent)}`}>
                    {log.agent}
                </span>
                </div>
                <div className="text-slate-600 shrink-0">|</div>
                <div className={`flex-1 ${
                log.type === 'thought' ? 'text-slate-400 italic' : 
                log.type === 'action' ? 'text-blue-300 font-semibold' : 
                'text-slate-200'
                }`}>
                {log.type === 'result' ? (
                     <div className="prose prose-invert prose-sm max-w-none">
                         <ReactMarkdown>{log.message}</ReactMarkdown>
                     </div>
                ) : (
                    log.message
                )}
                </div>
            </div>
            ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}