"use client";

import Link from 'next/link';
import { 
  Rocket, 
  Code2, 
  Database, 
  ArrowRight,
  Zap,
  Users,
  GitPullRequest,
  Brain,
  CheckCircle,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const pillars = [
  {
    href: '/pillar1',
    title: 'Founding Team',
    subtitle: 'Pillar 1',
    description: 'Get your startup idea analyzed by an AI founding team. ARIA (CTO), FELIX (CFO), NOVA (CMO), and JUDGE (Investor) will evaluate your concept.',
    icon: Rocket,
    color: '#f97316',
    features: [
      'Technical feasibility analysis',
      'Financial projections',
      'Go-to-market strategy',
      'Investor evaluation',
    ],
  },
  {
    href: '/pillar2',
    title: 'Engineering Workforce',
    subtitle: 'Pillar 2',
    description: 'Describe a feature in plain English and let the autonomous engineering team plan, code, test, document, and review it.',
    icon: Code2,
    color: '#06b6d4',
    features: [
      'Engineering spec generation',
      'Code implementation',
      'Automated testing',
      'GitHub PR creation',
    ],
  },
  {
    href: '/pillar3',
    title: 'Codebase Intelligence',
    subtitle: 'Pillar 3',
    description: 'Connect your repository and have natural conversations about your code. SAGE understands your entire codebase.',
    icon: Database,
    color: '#8b5cf6',
    features: [
      'Codebase Q&A',
      'Architecture analysis',
      'Security scanning',
      'Onboarding guides',
    ],
  },
];

function PillarCard({ pillar }: { pillar: typeof pillars[0] }) {
  return (
    <Link
      href={pillar.href}
      className="group relative flex flex-col p-6 rounded-2xl bg-slate-900/50 border border-slate-800 hover:border-white/20 transition-all duration-300 hover:shadow-xl hover:shadow-black/20"
    >
      {/* Glow effect */}
      <div 
        className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
        style={{
          background: `radial-gradient(600px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), ${pillar.color}10, transparent 40%)`,
        }}
      />
      
      <div className="flex items-start justify-between mb-4">
        <div 
          className="p-3 rounded-xl border transition-all group-hover:scale-110"
          style={{ 
            backgroundColor: `${pillar.color}15`,
            borderColor: `${pillar.color}30`,
          }}
        >
          <pillar.icon className="w-6 h-6" style={{ color: pillar.color }} />
        </div>
        <span 
          className="text-xs font-bold px-2.5 py-1 rounded-full border"
          style={{ 
            backgroundColor: `${pillar.color}10`,
            borderColor: `${pillar.color}30`,
            color: pillar.color,
          }}
        >
          {pillar.subtitle}
        </span>
      </div>
      
      <h3 className="text-xl font-bold text-white mb-2 group-hover:text-white transition-colors">
        {pillar.title}
      </h3>
      
      <p className="text-sm text-slate-400 mb-4 leading-relaxed flex-1">
        {pillar.description}
      </p>
      
      <div className="space-y-2 mb-4">
        {pillar.features.map((feature, idx) => (
          <div key={idx} className="flex items-center gap-2 text-xs text-slate-500">
            <CheckCircle className="w-3 h-3" style={{ color: pillar.color }} />
            {feature}
          </div>
        ))}
      </div>
      
      <div className="flex items-center gap-2 text-sm font-medium group-hover:gap-3 transition-all" style={{ color: pillar.color }}>
        Get Started
        <ArrowRight className="w-4 h-4" />
      </div>
    </Link>
  );
}

export default function HomePage() {
  return (
    <div className="flex flex-col h-screen overflow-y-auto bg-[#0a0f1a]">
      {/* Hero Section */}
      <div className="relative px-8 py-16 border-b border-slate-800">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-orange-500/5 via-transparent to-purple-500/5 pointer-events-none" />
        
        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-800/50 border border-slate-700 mb-6">
            <Sparkles className="w-4 h-4 text-orange-400" />
            <span className="text-xs font-medium text-slate-300">Powered by Amazon Nova</span>
          </div>
          
          <h1 className="text-5xl font-bold text-white mb-4 tracking-tight">
            Intelligence That{' '}
            <span className="bg-gradient-to-r from-orange-400 to-purple-400 bg-clip-text text-transparent">
              Spirals Forward
            </span>
          </h1>
          
          <p className="text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
            From idea to deployed product, with an entire AI founding team behind you. 
            Helix brings together strategic analysis, autonomous engineering, and codebase intelligence.
          </p>
        </div>
      </div>

      {/* Pillars Grid */}
      <div className="flex-1 px-8 py-12">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">Choose Your Pillar</h2>
              <p className="text-sm text-slate-500">Each pillar can work independently or together as one unified workflow</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {pillars.map((pillar) => (
              <PillarCard key={pillar.href} pillar={pillar} />
            ))}
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="px-8 py-12 border-t border-slate-800 bg-slate-900/30">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-xl font-bold text-white mb-8 text-center">Key Differentiators</h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center mx-auto mb-3">
                <Users className="w-6 h-6 text-orange-400" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">Multi-Agent System</h3>
              <p className="text-xs text-slate-500">6+ specialized agents with clear roles</p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mx-auto mb-3">
                <GitPullRequest className="w-6 h-6 text-cyan-400" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">Real GitHub PRs</h3>
              <p className="text-xs text-slate-500">Nova Act creates actual pull requests</p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mx-auto mb-3">
                <Brain className="w-6 h-6 text-purple-400" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">Multimodal RAG</h3>
              <p className="text-xs text-slate-500">Code, images, and diagrams in one space</p>
            </div>
            
            <div className="text-center">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-3">
                <Zap className="w-6 h-6 text-emerald-400" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">Human-in-the-Loop</h3>
              <p className="text-xs text-slate-500">You&apos;re always in control</p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="px-8 py-6 border-t border-slate-800">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <p className="text-xs text-slate-600">
            Built for the Amazon Nova AI Hackathon, March 2026
          </p>
          <p className="text-xs text-slate-600">
            Powered by Nova 2 Lite • Nova 2 Sonic • Nova Act • Nova Multimodal Embeddings
          </p>
        </div>
      </div>
    </div>
  );
}
