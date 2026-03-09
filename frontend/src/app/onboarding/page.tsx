"use client";

import { useRouter } from 'next/navigation';
import OnboardingFlow from '@/components/OnboardingFlow';

interface WorkspaceConfig {
  type: 'github' | 'local' | 'new';
  github_repo?: string;
  github_owner?: string;
  local_path?: string;
  name: string;
}

export default function OnboardingPage() {
  const router = useRouter();

  const handleComplete = (workspace: WorkspaceConfig) => {
    // Store workspace config
    localStorage.setItem('helix_workspace', JSON.stringify(workspace));
    
    // Redirect to appropriate pillar based on workspace type
    if (workspace.type === 'github' || workspace.type === 'local') {
      // Existing project - go to Pillar 3 (Codebase Intelligence)
      router.push('/pillar3');
    } else {
      // New project - go to Pillar 1 (Founding Team)
      router.push('/pillar1');
    }
  };

  const handleSkip = () => {
    // Skip onboarding and go to home
    router.push('/');
  };

  return (
    <OnboardingFlow
      onComplete={handleComplete}
      onSkip={handleSkip}
    />
  );
}
