"use client";

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
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
  PanelLeft,
  ChevronLeft,
  ChevronRight,
  Settings,
  Plus,
  MessageSquare,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const pillars = [
  {
    href: '/pillar1',
    title: 'Founding Team',
    subtitle: 'Pillar 1',
    description: 'Get your startup idea analyzed by an AI founding team. ARIA, FELIX, NOVA, and JUDGE will evaluate your concept.',
    icon: Rocket,
    color: '#f97316',
    gradient: 'from-orange-500/20 to-rose-500/20',
    border: 'group-hover:border-orange-500/50',
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
    gradient: 'from-cyan-500/20 to-blue-500/20',
    border: 'group-hover:border-cyan-500/50',
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
    description: 'Connect your repository and have natural conversations about your code. SAGE understands your entire architecture.',
    icon: Database,
    color: '#8b5cf6',
    gradient: 'from-purple-500/20 to-indigo-500/20',
    border: 'group-hover:border-purple-500/50',
    features: [
      'Codebase Q&A',
      'Architecture analysis',
      'Security scanning',
      'Onboarding guides',
    ],
  },
];

const navItems = [
  {
    href: '/pillar1',
    label: 'Founding Team',
    icon: Rocket,
    color: '#f97316',
  },
  {
    href: '/pillar2',
    label: 'Engineering',
    icon: Code2,
    color: '#06b6d4',
  },
  {
    href: '/pillar3',
    label: 'Codebase Intel',
    icon: Database,
    color: '#8b5cf6',
  },
];

function PillarCard({ pillar }: { pillar: typeof pillars[0] }) {
  return (
    <Link
      href={pillar.href}
      className={cn(
        "group relative flex flex-col p-8 rounded-2xl bg-[#252525] border border-[#3a3a3a] transition-all duration-300 hover:border-[#4a4a4a] hover:shadow-2xl hover:shadow-black/40 hover:-translate-y-1 overflow-hidden",
      )}
    >
      {/* Background Glow */}
      <div 
        className={cn(
          "absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br pointer-events-none",
          pillar.gradient
        )}
      />
      
      <div className="relative z-10 flex items-start justify-between mb-6">
        <div 
          className="p-4 rounded-xl border backdrop-blur-md transition-transform duration-300 group-hover:scale-110"
          style={{ 
            backgroundColor: `${pillar.color}15`,
            borderColor: `${pillar.color}30`,
          }}
        >
          <pillar.icon className="w-7 h-7" style={{ color: pillar.color }} />
        </div>
        <span 
          className="text-xs font-bold px-3 py-1.5 rounded-full border tracking-wide uppercase"
          style={{ 
            backgroundColor: `${pillar.color}10`,
            borderColor: `${pillar.color}30`,
            color: pillar.color,
          }}
        >
          {pillar.subtitle}
        </span>
      </div>
      
      <h3 className="relative z-10 text-xl font-bold text-white mb-3 group-hover:text-white transition-colors tracking-tight">
        {pillar.title}
      </h3>
      
      <p className="relative z-10 text-sm text-slate-400 mb-6 leading-relaxed flex-1">
        {pillar.description}
      </p>
      
      <div className="relative z-10 space-y-2 mb-6">
        {pillar.features.map((feature, idx) => (
          <div key={idx} className="flex items-center gap-2 text-sm text-slate-300">
            <CheckCircle className="w-4 h-4 shrink-0" style={{ color: pillar.color }} />
            {feature}
          </div>
        ))}
      </div>
      
      <div className="relative z-10 flex items-center justify-between mt-auto pt-4 border-t border-[#3a3a3a] group-hover:border-[#4a4a4a] transition-colors">
        <span className="text-sm font-semibold" style={{ color: pillar.color }}>
          Start Chat
        </span>
        <div 
          className="p-2 rounded-full transition-transform duration-300 group-hover:translate-x-1"
          style={{ backgroundColor: `${pillar.color}15`, color: pillar.color }}
        >
          <ArrowRight className="w-4 h-4" />
        </div>
      </div>
    </Link>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  const hasWorkspace = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return !!localStorage.getItem('helix_workspace');
  }, []);

  useEffect(() => {
    if (!hasWorkspace) {
      router.push('/onboarding');
    }
  }, [hasWorkspace, router]);

  if (!hasWorkspace) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#1a1a1a]">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-6" />
          <p className="text-slate-400 font-medium animate-pulse">Initializing...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#1a1a1a]">
      {/* Sidebar */}
      <aside 
        className={cn(
          "bg-[#1a1a1a] border-r border-[#2a2a2a] flex flex-col transition-all duration-300 ease-in-out relative",
          sidebarCollapsed ? "w-16" : "w-64"
        )}
      >
        {/* Toggle Button */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute -right-3 top-6 z-50 p-1.5 rounded-full bg-[#2a2a2a] border border-[#3a3a3a] hover:bg-[#3a3a3a] transition-colors shadow-lg"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
          ) : (
            <ChevronLeft className="w-3.5 h-3.5 text-slate-400" />
          )}
        </button>

        {/* Logo */}
        <div className={cn(
          "border-b border-[#2a2a2a] transition-all duration-300",
          sidebarCollapsed ? "p-3" : "p-4"
        )}>
          <Link href="/" className="flex items-center gap-3 group">
            <div className="p-2 rounded-xl bg-gradient-to-br from-orange-500/20 to-purple-500/20 border border-white/10">
              <Zap className="w-5 h-5 text-orange-400" />
            </div>
            {!sidebarCollapsed && (
              <div className="animate-fade-in">
                <h1 className="text-lg font-bold text-white tracking-tight">Helix</h1>
                <p className="text-[10px] text-slate-500">AI Workspace</p>
              </div>
            )}
          </Link>
        </div>

        {/* New Chat */}
        <div className={cn(
          "border-b border-[#2a2a2a]",
          sidebarCollapsed ? "p-2" : "p-3"
        )}>
          <button
            className={cn(
              "w-full flex items-center gap-2 rounded-lg bg-[#2a2a2a] hover:bg-[#3a3a3a] border border-[#3a3a3a] transition-all text-slate-300",
              sidebarCollapsed ? "p-2 justify-center" : "px-3 py-2.5"
            )}
          >
            <Plus className="w-4 h-4" />
            {!sidebarCollapsed && <span className="text-sm font-medium">New Chat</span>}
          </button>
        </div>

        {/* Navigation */}
        <nav className={cn("flex-1 space-y-1", sidebarCollapsed ? "p-2" : "p-3")}>
          {!sidebarCollapsed && (
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] px-2 mb-3">
              Pillars
            </p>
          )}
          
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg transition-all group hover:bg-[#252525] border border-transparent",
                sidebarCollapsed ? "p-2 justify-center" : "px-3 py-2.5"
              )}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <item.icon 
                className={cn("transition-colors", sidebarCollapsed ? "w-5 h-5" : "w-4 h-4")}
                style={{ color: item.color }}
              />
              {!sidebarCollapsed && (
                <span className="text-sm font-medium text-slate-400 group-hover:text-slate-300">
                  {item.label}
                </span>
              )}
            </Link>
          ))}
        </nav>

        {/* Footer */}
        <div className={cn("border-t border-[#2a2a2a]", sidebarCollapsed ? "p-2" : "p-3")}>
          <Link
            href="/settings"
            className={cn(
              "flex items-center gap-3 rounded-lg transition-all group hover:bg-[#252525]",
              sidebarCollapsed ? "p-2 justify-center" : "px-3 py-2"
            )}
          >
            <Settings className={cn("text-slate-500", sidebarCollapsed ? "w-5 h-5" : "w-4 h-4")} />
            {!sidebarCollapsed && (
              <span className="text-sm font-medium text-slate-400 group-hover:text-slate-300">
                Settings
              </span>
            )}
          </Link>
          {!sidebarCollapsed && (
            <p className="text-[10px] text-slate-700 px-3 mt-3">Helix v0.2.0</p>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        {/* Hero Section */}
        <div className="relative px-8 py-16 lg:py-20">
          {/* Background glow */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />
          
          <div className="relative max-w-4xl mx-auto text-center z-10">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#252525] border border-[#3a3a3a] mb-6">
              <Sparkles className="w-4 h-4 text-orange-400" />
              <span className="text-sm font-medium text-slate-300">Powered by Amazon Nova</span>
            </div>
            
            <h1 className="text-4xl lg:text-5xl font-bold text-white mb-4 tracking-tight">
              Intelligence That{' '}
              <span className="bg-gradient-to-r from-orange-400 via-pink-500 to-purple-500 bg-clip-text text-transparent">
                Spirals Forward
              </span>
            </h1>
            
            <p className="text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
              From idea to deployed product, with an entire AI founding team behind you.
            </p>
          </div>
        </div>

        {/* Pillars Grid */}
        <div className="flex-1 px-8 pb-16">
          <div className="max-w-6xl mx-auto">
            <div className="mb-8 text-center">
              <h2 className="text-2xl font-bold text-white mb-2">Choose Your Workspace</h2>
              <p className="text-sm text-slate-500">Each pillar works independently or together as one unified workflow.</p>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {pillars.map((pillar) => (
                <PillarCard key={pillar.href} pillar={pillar} />
              ))}
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="px-8 py-12 border-t border-[#2a2a2a] bg-[#1a1a1a]">
          <div className="max-w-5xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { icon: Users, color: 'text-orange-400', bg: 'bg-orange-500/10', title: 'Multi-Agent', desc: '6+ specialized agents' },
                { icon: GitPullRequest, color: 'text-cyan-400', bg: 'bg-cyan-500/10', title: 'Real PRs', desc: 'Actual GitHub integration' },
                { icon: Brain, color: 'text-purple-400', bg: 'bg-purple-500/10', title: 'Multimodal RAG', desc: 'Code, images, diagrams' },
                { icon: Zap, color: 'text-emerald-400', bg: 'bg-emerald-500/10', title: 'Human-in-Loop', desc: 'Always in control' },
              ].map((feat, i) => (
                <div key={i} className="p-5 rounded-xl bg-[#252525] border border-[#3a3a3a]">
                  <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center mb-3", feat.bg)}>
                    <feat.icon className={cn("w-5 h-5", feat.color)} />
                  </div>
                  <h3 className="text-sm font-bold text-white mb-1">{feat.title}</h3>
                  <p className="text-xs text-slate-500">{feat.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-8 py-6 border-t border-[#2a2a2a]">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
              <p className="text-xs text-slate-500">Built for Amazon Nova AI Hackathon</p>
            </div>
            <p className="text-xs text-slate-600">Nova 2 Lite • Nova 2 Sonic • Nova Act</p>
          </div>
        </div>
      </div>
    </div>
  );
}
