"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';

/**
 * VoiceInterface Component
 * 
 * Real-time voice interaction with Helix agents using Nova 2 Sonic.
 * Features:
 * - Bidirectional audio streaming
 * - Real-time transcription display
 * - Agent voice responses
 * - Crossmodal switching (voice <-> text)
 * - Visual feedback for turn-taking
 */

// Message types from WebSocket
interface WebSocketMessage {
  type: string;
  session_id?: string;
  text?: string;
  is_final?: boolean;
  confidence?: number;
  speaker?: string;
  audio?: string;
  voice_id?: string;
  tool?: string;
  args?: Record<string, unknown>;
  message?: string;
  conversation_history?: ConversationEntry[];
}

interface ConversationEntry {
  role: string;
  content: string;
}

interface VoiceInterfaceProps {
  agentName: string;
  pillar: 1 | 2 | 3;
  onTranscript?: (text: string, isFinal: boolean) => void;
  onAgentResponse?: (text: string) => void;
  onSessionEnd?: (history: ConversationEntry[]) => void;
}

interface TranscriptEntry {
  id: string;
  speaker: 'user' | 'agent';
  text: string;
  timestamp: Date;
  isFinal: boolean;
}

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
type SpeakingState = 'idle' | 'user_speaking' | 'agent_speaking' | 'processing';

export default function VoiceInterface({
  agentName,
  pillar,
  onTranscript,
  onAgentResponse,
  onSessionEnd,
}: VoiceInterfaceProps) {
  // State
  const [isActive, setIsActive] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [speakingState, setSpeakingState] = useState<SpeakingState>('idle');
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [voiceId, setVoiceId] = useState<string>('');
  const [remainingTime, setRemainingTime] = useState(480); // 8 minutes
  const [textInput, setTextInput] = useState('');
  const [showTextInput, setShowTextInput] = useState(false);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll transcripts
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts, currentTranscript]);

  // Countdown timer
  useEffect(() => {
    if (!isActive || remainingTime <= 0) return;

    const timer = setInterval(() => {
      setRemainingTime((prev) => {
        if (prev <= 1) {
          handleStop();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isActive, remainingTime]);

  // Create voice session
  const createSession = async (): Promise<string | null> => {
    try {
      const response = await fetch('/api/voice/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_name: agentName,
          pillar,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create session');
      }

      const data = await response.json();
      setSessionId(data.session_id);
      setVoiceId(data.voice_id);
      return data.session_id;
    } catch (error) {
      console.error('Session creation error:', error);
      return null;
    }
  };

  // Connect WebSocket
  const connectWebSocket = (sessionId: string) => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/voice/ws/${sessionId}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      console.log('Voice WebSocket connected');
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('error');
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      setIsActive(false);
    };
  };

  // Handle WebSocket messages
  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'session_started':
        console.log('Session started:', message.session_id);
        break;

      case 'transcript':
        handleTranscript(message);
        break;

      case 'speech':
        handleSpeech(message);
        break;

      case 'turn_change':
        handleTurnChange(message.speaker || 'user');
        break;

      case 'tool_call':
        console.log('Tool call:', message.tool, message.args);
        break;

      case 'voice_switched':
        setVoiceId(message.voice_id || '');
        break;

      case 'session_ended':
        handleSessionEnd(message.conversation_history || []);
        break;

      case 'error':
        console.error('Voice error:', message.message);
        setConnectionStatus('error');
        break;
    }
  };

  // Handle transcript events
  const handleTranscript = (message: WebSocketMessage) => {
    if (message.is_final) {
      // Add final transcript
      const entry: TranscriptEntry = {
        id: Date.now().toString(),
        speaker: message.speaker === 'user' ? 'user' : 'agent',
        text: message.text || '',
        timestamp: new Date(),
        isFinal: true,
      };
      setTranscripts((prev) => [...prev, entry]);
      setCurrentTranscript('');
      onTranscript?.(message.text || '', true);
    } else {
      // Update interim transcript
      setCurrentTranscript(message.text || '');
      onTranscript?.(message.text || '', false);
    }
  };

  // Handle speech events
  const handleSpeech = (message: WebSocketMessage) => {
    if (message.audio) {
      // Decode and queue audio
      const audioData = base64ToArrayBuffer(message.audio);
      audioQueueRef.current.push(audioData);
      playAudioQueue();
    }

    if (message.is_final && message.text) {
      onAgentResponse?.(message.text);
    }
  };

  // Handle turn changes
  const handleTurnChange = (speaker: string) => {
    if (speaker === 'user') {
      setSpeakingState('user_speaking');
    } else {
      setSpeakingState('agent_speaking');
    }
  };

  // Handle session end
  const handleSessionEnd = (history: ConversationEntry[]) => {
    setIsActive(false);
    setConnectionStatus('disconnected');
    onSessionEnd?.(history);
  };

  // Start voice session
  const handleStart = async () => {
    setConnectionStatus('connecting');

    // Create session
    const newSessionId = await createSession();
    if (!newSessionId) {
      setConnectionStatus('error');
      return;
    }

    // Connect WebSocket
    connectWebSocket(newSessionId);

    // Start audio capture
    try {
      await startAudioCapture();
      setIsActive(true);
      setRemainingTime(480);
    } catch (error) {
      console.error('Audio capture error:', error);
      setConnectionStatus('error');
    }
  };

  // Stop voice session
  const handleStop = () => {
    // Stop audio capture
    stopAudioCapture();

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({ type: 'close' }));
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsActive(false);
    setConnectionStatus('disconnected');
    setSpeakingState('idle');
  };

  // Start audio capture
  const startAudioCapture = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    mediaStreamRef.current = stream;

    const audioContext = new AudioContext({ sampleRate: 16000 });
    audioContextRef.current = audioContext;

    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (event) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

      const inputData = event.inputBuffer.getChannelData(0);
      const pcmData = float32ToPCM16(inputData);
      const base64Audio = arrayBufferToBase64(pcmData.buffer as ArrayBuffer);

      wsRef.current.send(JSON.stringify({
        type: 'audio',
        data: base64Audio,
      }));
    };

    source.connect(processor);
    processor.connect(audioContext.destination);
  };

  // Stop audio capture
  const stopAudioCapture = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
  };

  // Play audio queue
  const playAudioQueue = async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;

    isPlayingRef.current = true;

    while (audioQueueRef.current.length > 0) {
      const audioData = audioQueueRef.current.shift()!;
      await playAudio(audioData);
    }

    isPlayingRef.current = false;
  };

  // Play single audio buffer
  const playAudio = async (audioData: ArrayBuffer): Promise<void> => {
    return new Promise((resolve) => {
      const audioContext = new AudioContext({ sampleRate: 16000 });
      const audioBuffer = audioContext.createBuffer(1, audioData.byteLength / 2, 16000);
      const channelData = audioBuffer.getChannelData(0);

      const pcmData = new Int16Array(audioData);
      for (let i = 0; i < pcmData.length; i++) {
        channelData[i] = pcmData[i] / 32768;
      }

      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.onended = () => {
        audioContext.close();
        resolve();
      };
      source.start();
    });
  };

  // Send text input (crossmodal)
  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim() || !wsRef.current) return;

    wsRef.current.send(JSON.stringify({
      type: 'text',
      data: textInput,
    }));

    // Add to transcripts
    setTranscripts((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        speaker: 'user',
        text: textInput,
        timestamp: new Date(),
        isFinal: true,
      },
    ]);

    setTextInput('');
  };

  // Utility functions
  const float32ToPCM16 = (float32Array: Float32Array): Int16Array => {
    const pcm16 = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return pcm16;
  };

  const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  const base64ToArrayBuffer = (base64: string): ArrayBuffer => {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Get status color
  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-yellow-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  // Get speaking indicator
  const getSpeakingIndicator = () => {
    switch (speakingState) {
      case 'user_speaking':
        return (
          <div className="flex items-center gap-2 text-blue-400">
            <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse" />
            <span>You are speaking...</span>
          </div>
        );
      case 'agent_speaking':
        return (
          <div className="flex items-center gap-2 text-purple-400">
            <div className="w-3 h-3 bg-purple-400 rounded-full animate-pulse" />
            <span>{agentName} is speaking...</span>
          </div>
        );
      case 'processing':
        return (
          <div className="flex items-center gap-2 text-yellow-400">
            <div className="w-3 h-3 bg-yellow-400 rounded-full animate-pulse" />
            <span>Processing...</span>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg border border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
          <span className="font-medium text-white">
            Voice: {agentName}
          </span>
          {voiceId && (
            <span className="text-xs text-gray-400">
              ({voiceId})
            </span>
          )}
        </div>
        {isActive && (
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-400">
              {formatTime(remainingTime)}
            </span>
            {getSpeakingIndicator()}
          </div>
        )}
      </div>

      {/* Transcript Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {transcripts.map((entry) => (
          <div
            key={entry.id}
            className={`flex ${entry.speaker === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                entry.speaker === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-100'
              }`}
            >
              <p className="text-sm">{entry.text}</p>
              <span className="text-xs opacity-60">
                {entry.timestamp.toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}

        {/* Current interim transcript */}
        {currentTranscript && (
          <div className="flex justify-end">
            <div className="max-w-[80%] rounded-lg px-4 py-2 bg-blue-600/50 text-white/80 italic">
              <p className="text-sm">{currentTranscript}</p>
            </div>
          </div>
        )}

        <div ref={transcriptEndRef} />
      </div>

      {/* Controls */}
      <div className="p-4 border-t border-gray-700">
        {/* Text input (crossmodal) */}
        {showTextInput && isActive && (
          <form onSubmit={handleTextSubmit} className="mb-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Type a message (crossmodal)..."
                className="flex-1 px-4 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Send
              </button>
            </div>
          </form>
        )}

        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            {!isActive ? (
              <button
                onClick={handleStart}
                disabled={connectionStatus === 'connecting'}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" />
                </svg>
                {connectionStatus === 'connecting' ? 'Connecting...' : 'Start Voice'}
              </button>
            ) : (
              <button
                onClick={handleStop}
                className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
                </svg>
                Stop
              </button>
            )}
          </div>

          {isActive && (
            <button
              onClick={() => setShowTextInput(!showTextInput)}
              className={`px-4 py-2 rounded-lg transition-colors ${
                showTextInput
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </button>
          )}
        </div>

        {/* Instructions */}
        {!isActive && (
          <p className="mt-3 text-sm text-gray-400 text-center">
            Click &quot;Start Voice&quot; to begin a conversation with {agentName}.
            <br />
            You can speak naturally or switch to text input at any time.
          </p>
        )}
      </div>
    </div>
  );
}
