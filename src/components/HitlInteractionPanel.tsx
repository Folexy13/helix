import { useState } from 'react';
import { useHelixStore, HitlCheckpoint } from '@/store/helixStore';
import { useHelixSocket } from '@/hooks/useHelixSocket';
import ReactMarkdown from 'react-markdown';
import { CheckCircle2, XCircle, Edit3, MessageSquareWarning } from 'lucide-react';

export default function HitlInteractionPanel() {
  const { pendingCheckpoints } = useHelixStore();
  const { sendHitlDecision } = useHelixSocket();
  const [userInput, setUserInput] = useState('');

  if (pendingCheckpoints.length === 0) return null;

  const currentCheckpoint = pendingCheckpoints[0];

  const handleDecision = (decision: string) => {
    sendHitlDecision(currentCheckpoint.id, decision, userInput);
    setUserInput('');
  };

  const renderIcon = (option: string) => {
    switch (option.toLowerCase()) {
      case 'approve': return <CheckCircle2 className="w-4 h-4 mr-2" />;
      case 'reject': return <XCircle className="w-4 h-4 mr-2" />;
      case 'edit': return <Edit3 className="w-4 h-4 mr-2" />;
      default: return null;
    }
  };

  const getButtonClass = (option: string) => {
    switch (option.toLowerCase()) {
      case 'approve': return 'bg-green-600 hover:bg-green-700 text-white';
      case 'reject': return 'bg-red-600 hover:bg-red-700 text-white';
      case 'edit': return 'bg-blue-600 hover:bg-blue-700 text-white';
      default: return 'bg-slate-700 hover:bg-slate-600 text-white';
    }
  };

  return (
    <div className="bg-card border-2 border-orange-500/50 rounded-xl shadow-lg flex flex-col h-full overflow-hidden animate-in fade-in zoom-in duration-300">
      <div className="bg-orange-500/10 border-b border-orange-500/20 px-4 py-3 flex items-center gap-3">
        <MessageSquareWarning className="text-orange-500 w-5 h-5" />
        <h3 className="font-semibold text-orange-500">
          Human Input Required: {currentCheckpoint.gate_type.replace(/_/g, ' ').toUpperCase()}
        </h3>
        <span className="ml-auto text-xs font-mono bg-slate-800 px-2 py-1 rounded text-slate-300">
          Agent: {currentCheckpoint.agent.toUpperCase()}
        </span>
      </div>

      <div className="p-4 flex-1 overflow-y-auto">
        <div className="prose prose-invert prose-sm max-w-none mb-6">
          <ReactMarkdown>{currentCheckpoint.prompt}</ReactMarkdown>
        </div>

        {currentCheckpoint.options.some(opt => opt.toLowerCase() === 'edit' || opt.toLowerCase() === 'explain') && (
           <div className="mb-4">
               <label className="block text-sm font-medium text-slate-400 mb-2">Additional Instructions / Clarification:</label>
               <textarea 
                  className="w-full bg-slate-900 border border-slate-700 rounded-md p-3 text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none resize-none h-24"
                  placeholder="Type your feedback here..."
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
               />
           </div>
        )}

      </div>

      <div className="p-4 bg-slate-900/50 border-t border-border flex flex-wrap gap-3">
         {currentCheckpoint.options.map((option) => (
             <button
               key={option}
               onClick={() => handleDecision(option)}
               className={`flex-1 flex items-center justify-center px-4 py-2.5 rounded-md font-medium text-sm transition-colors ${getButtonClass(option)}`}
             >
                 {renderIcon(option)}
                 {option.toUpperCase()}
             </button>
         ))}
      </div>
    </div>
  );
}