"use client";

import React, { useState, useEffect, useRef } from 'react';

/**
 * OnboardingFlow Component
 * 
 * Smart onboarding that guides users to connect their workspace:
 * 1. GitHub OAuth for repository access
 * 2. Local folder selection (using native File System Access API)
 * 3. Create new project folder
 * 
 * This is the first point of contact for new users.
 */

// Extend Window interface for File System Access API
declare global {
  interface Window {
    showDirectoryPicker?: (options?: {
      id?: string;
      mode?: 'read' | 'readwrite';
      startIn?: 'desktop' | 'documents' | 'downloads' | 'music' | 'pictures' | 'videos';
    }) => Promise<FileSystemDirectoryHandle>;
  }
}

interface Repository {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  private: boolean;
  html_url: string;
  language: string | null;
  updated_at: string;
}

interface LocalFolder {
  name: string;
  path: string;
  is_git: boolean;
  handle?: FileSystemDirectoryHandle;
}

interface WorkspaceConfig {
  type: 'github' | 'local' | 'new';
  github_repo?: string;
  github_owner?: string;
  local_path?: string;
  name: string;
  folder_handle?: FileSystemDirectoryHandle;
}

interface OnboardingFlowProps {
  onComplete: (workspace: WorkspaceConfig) => void;
  onSkip?: () => void;
}

type Step = 'welcome' | 'choose-source' | 'github-repos' | 'local-browse' | 'create-new' | 'confirm';

// Check if File System Access API is supported
const isFileSystemAccessSupported = () => {
  return typeof window !== 'undefined' && 'showDirectoryPicker' in window;
};

export default function OnboardingFlow({ onComplete, onSkip }: OnboardingFlowProps) {
  // State
  const [step, setStep] = useState<Step>('welcome');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [githubUser, setGithubUser] = useState<{ login: string; avatar_url: string } | null>(null);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [currentPath, setCurrentPath] = useState('');
  const [selectedFolder, setSelectedFolder] = useState<LocalFolder | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectPath, setNewProjectPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [folderHandle, setFolderHandle] = useState<FileSystemDirectoryHandle | null>(null);
  const [supportsFilePicker, setSupportsFilePicker] = useState(false);
  const folderInputRef = useRef<HTMLInputElement>(null);

  // Check for File System Access API support
  useEffect(() => {
    setSupportsFilePicker(isFileSystemAccessSupported());
  }, []);

  // Check for OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const githubUserParam = params.get('github_user');
    const githubId = params.get('github_id');
    
    if (githubUserParam && githubId) {
      setIsAuthenticated(true);
      setGithubUser({ login: githubUserParam, avatar_url: '' });
      localStorage.setItem('github_user_id', githubId);
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
      setStep('github-repos');
      fetchRepositories(githubId);
    }
  }, []);

  // Open native folder picker (File System Access API)
  const openFolderPicker = async () => {
    setError(null);
    
    if (!window.showDirectoryPicker) {
      setError('Your browser does not support folder selection. Please enter the path manually.');
      return;
    }
    
    try {
      const handle = await window.showDirectoryPicker({
        id: 'helix-workspace',
        mode: 'readwrite',
        startIn: 'documents',
      });
      
      setFolderHandle(handle);
      setCurrentPath(handle.name);
      setSelectedFolder({
        name: handle.name,
        path: handle.name, // Browser doesn't expose full path for security
        is_git: false,
        handle: handle,
      });
      
      // Check if it's a git repository by looking for .git folder
      try {
        await handle.getDirectoryHandle('.git');
        setSelectedFolder(prev => prev ? { ...prev, is_git: true } : null);
      } catch {
        // Not a git repo, that's fine
      }
      
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        // User cancelled, not an error
        return;
      }
      setError('Failed to select folder. Please try again or enter the path manually.');
    }
  };

  // Fallback: Handle folder input change (for browsers without File System Access API)
  const handleFolderInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      // Get the folder path from the first file's webkitRelativePath
      const firstFile = files[0];
      const pathParts = firstFile.webkitRelativePath.split('/');
      const folderName = pathParts[0];
      
      setCurrentPath(folderName);
      setSelectedFolder({
        name: folderName,
        path: folderName,
        is_git: false,
      });
    }
  };

  // Fetch GitHub repositories
  const fetchRepositories = async (userId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/github/repos?user_id=${userId}`);
      if (!response.ok) throw new Error('Failed to fetch repositories');
      
      const repos = await response.json();
      setRepositories(repos);
    } catch (err) {
      setError('Failed to load repositories. Please try again.');
    } finally {
      setLoading(false);
    }
  };



  // Handle GitHub login
  const handleGitHubLogin = () => {
    window.location.href = '/api/github/auth/login?redirect_uri=' + encodeURIComponent(window.location.href);
  };

  // Handle workspace selection
  const handleSelectWorkspace = () => {
    if (selectedRepo) {
      onComplete({
        type: 'github',
        github_repo: selectedRepo.name,
        github_owner: selectedRepo.full_name.split('/')[0],
        name: selectedRepo.name,
      });
    } else if (selectedFolder) {
      onComplete({
        type: 'local',
        local_path: selectedFolder.path,
        name: selectedFolder.name,
      });
    }
  };

  // Filter repositories
  const filteredRepos = repositories.filter(repo =>
    repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (repo.description && repo.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // Render step content
  const renderStep = () => {
    switch (step) {
      case 'welcome':
        return (
          <div className="text-center space-y-8">
            <div className="space-y-4">
              <div className="text-6xl">🧬</div>
              <h1 className="text-4xl font-bold text-white">Welcome to Helix</h1>
              <p className="text-xl text-gray-400 max-w-md mx-auto">
                Your AI founding team is ready. Let&apos;s connect your workspace to get started.
              </p>
            </div>
            
            <div className="flex flex-col gap-4 max-w-sm mx-auto">
              <button
                onClick={() => setStep('choose-source')}
                className="px-8 py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-semibold text-lg hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105"
              >
                Get Started
              </button>
              
              {onSkip && (
                <button
                  onClick={onSkip}
                  className="px-8 py-3 text-gray-400 hover:text-white transition-colors"
                >
                  Skip for now
                </button>
              )}
            </div>
          </div>
        );

      case 'choose-source':
        return (
          <div className="space-y-8">
            <div className="text-center space-y-2">
              <h2 className="text-3xl font-bold text-white">Choose Your Workspace</h2>
              <p className="text-gray-400">Where is your project located?</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {/* GitHub Option */}
              <button
                onClick={() => {
                  if (isAuthenticated) {
                    setStep('github-repos');
                    const userId = localStorage.getItem('github_user_id');
                    if (userId) fetchRepositories(userId);
                  } else {
                    handleGitHubLogin();
                  }
                }}
                className="p-8 bg-gray-800 rounded-2xl border-2 border-gray-700 hover:border-purple-500 transition-all group"
              >
                <div className="space-y-4">
                  <div className="w-16 h-16 mx-auto bg-gray-700 rounded-xl flex items-center justify-center group-hover:bg-purple-600 transition-colors">
                    <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">GitHub Repository</h3>
                    <p className="text-sm text-gray-400 mt-1">
                      {isAuthenticated ? 'Select from your repos' : 'Connect with GitHub'}
                    </p>
                  </div>
                  {isAuthenticated && githubUser && (
                    <div className="text-xs text-green-400 flex items-center justify-center gap-1">
                      <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                      Connected as @{githubUser.login}
                    </div>
                  )}
                </div>
              </button>

              {/* Local Folder Option */}
              <button
                onClick={() => {
                  setStep('local-browse');
                  setError(null);
                }}
                className="p-8 bg-gray-800 rounded-2xl border-2 border-gray-700 hover:border-blue-500 transition-all group"
              >
                <div className="space-y-4">
                  <div className="w-16 h-16 mx-auto bg-gray-700 rounded-xl flex items-center justify-center group-hover:bg-blue-600 transition-colors">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">Local Folder</h3>
                    <p className="text-sm text-gray-400 mt-1">Browse existing projects</p>
                  </div>
                </div>
              </button>

              {/* Create New Option */}
              <button
                onClick={() => setStep('create-new')}
                className="p-8 bg-gray-800 rounded-2xl border-2 border-gray-700 hover:border-green-500 transition-all group"
              >
                <div className="space-y-4">
                  <div className="w-16 h-16 mx-auto bg-gray-700 rounded-xl flex items-center justify-center group-hover:bg-green-600 transition-colors">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-white">Create New</h3>
                    <p className="text-sm text-gray-400 mt-1">Start a fresh project</p>
                  </div>
                </div>
              </button>
            </div>

            <button
              onClick={() => setStep('welcome')}
              className="block mx-auto text-gray-400 hover:text-white transition-colors"
            >
              ← Back
            </button>
          </div>
        );

      case 'github-repos':
        return (
          <div className="space-y-6 max-w-3xl mx-auto">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">Select Repository</h2>
                <p className="text-gray-400">Choose a repository to work with</p>
              </div>
              {githubUser && (
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                  @{githubUser.login}
                </div>
              )}
            </div>

            {/* Search */}
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search repositories..."
                className="w-full px-4 py-3 pl-10 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-purple-500"
              />
              <svg className="absolute left-3 top-3.5 w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>

            {/* Repository List */}
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {loading ? (
                <div className="text-center py-8 text-gray-400">Loading repositories...</div>
              ) : filteredRepos.length === 0 ? (
                <div className="text-center py-8 text-gray-400">No repositories found</div>
              ) : (
                filteredRepos.map((repo) => (
                  <button
                    key={repo.id}
                    onClick={() => setSelectedRepo(repo)}
                    className={`w-full p-4 rounded-xl text-left transition-all ${
                      selectedRepo?.id === repo.id
                        ? 'bg-purple-600 border-2 border-purple-400'
                        : 'bg-gray-800 border-2 border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-white">{repo.name}</span>
                          {repo.private && (
                            <span className="px-2 py-0.5 text-xs bg-gray-700 text-gray-300 rounded">Private</span>
                          )}
                        </div>
                        {repo.description && (
                          <p className="text-sm text-gray-400 mt-1 line-clamp-1">{repo.description}</p>
                        )}
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                          {repo.language && <span>{repo.language}</span>}
                          <span>Updated {new Date(repo.updated_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      {selectedRepo?.id === repo.id && (
                        <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <div className="flex justify-between">
              <button
                onClick={() => setStep('choose-source')}
                className="px-6 py-2 text-gray-400 hover:text-white transition-colors"
              >
                ← Back
              </button>
              <button
                onClick={handleSelectWorkspace}
                disabled={!selectedRepo}
                className="px-8 py-3 bg-purple-600 text-white rounded-xl font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-purple-700 transition-colors"
              >
                Continue with {selectedRepo?.name || 'selected repo'}
              </button>
            </div>
          </div>
        );

      case 'local-browse':
        return (
          <div className="space-y-6 max-w-xl mx-auto">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-white">Select Project Folder</h2>
              <p className="text-gray-400">Choose your existing project folder</p>
            </div>

            <div className="space-y-4">
              {/* Native Folder Picker Button */}
              <div className="flex flex-col items-center gap-4">
                <button
                  onClick={openFolderPicker}
                  className="w-full p-6 bg-gray-800 rounded-2xl border-2 border-dashed border-gray-600 hover:border-blue-500 transition-all group flex flex-col items-center gap-3"
                >
                  <div className="w-16 h-16 bg-gray-700 rounded-xl flex items-center justify-center group-hover:bg-blue-600 transition-colors">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                  </div>
                  <div className="text-center">
                    <p className="text-white font-medium">
                      {selectedFolder ? selectedFolder.name : 'Click to Select Folder'}
                    </p>
                    <p className="text-sm text-gray-400">
                      {selectedFolder 
                        ? (selectedFolder.is_git ? '📦 Git repository detected' : '📁 Folder selected')
                        : 'Opens your system file picker'
                      }
                    </p>
                  </div>
                </button>

                {/* Hidden input for fallback */}
                <input
                  ref={folderInputRef}
                  type="file"
                  /* @ts-expect-error webkitdirectory is a non-standard attribute */
                  webkitdirectory="true"
                  directory=""
                  multiple
                  onChange={handleFolderInputChange}
                  className="hidden"
                />

                {/* Fallback button for browsers without File System Access API */}
                {!supportsFilePicker && (
                  <button
                    onClick={() => folderInputRef.current?.click()}
                    className="text-sm text-blue-400 hover:text-blue-300 underline"
                  >
                    Or use legacy folder selector
                  </button>
                )}
              </div>

              {/* Selected folder info */}
              {selectedFolder && (
                <div className="p-4 bg-blue-900/30 rounded-xl border border-blue-700">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-white font-medium">{selectedFolder.name}</p>
                      <p className="text-sm text-gray-400">
                        {selectedFolder.is_git ? 'Git repository' : 'Local folder'}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Manual path input (alternative) */}
              <div className="pt-4 border-t border-gray-700">
                <p className="text-sm text-gray-400 mb-2">Or enter path manually:</p>
                <input
                  type="text"
                  value={currentPath}
                  onChange={(e) => {
                    setCurrentPath(e.target.value);
                    if (e.target.value.trim()) {
                      const name = e.target.value.split('/').pop() || e.target.value.split('\\').pop() || 'project';
                      setSelectedFolder({ name, path: e.target.value, is_git: false });
                    } else {
                      setSelectedFolder(null);
                    }
                  }}
                  placeholder="/path/to/your/project or C:\Users\..."
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 text-sm"
                />
              </div>

              <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700">
                <p className="text-sm text-gray-400 mb-2">💡 Tips:</p>
                <ul className="text-xs text-gray-500 space-y-1">
                  <li>• Works on Windows, macOS, and Linux</li>
                  <li>• The folder should contain your source code</li>
                  <li>• Generated code will be saved to this location</li>
                </ul>
              </div>
            </div>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <div className="flex justify-between">
              <button
                onClick={() => {
                  setStep('choose-source');
                  setSelectedFolder(null);
                  setCurrentPath('');
                  setFolderHandle(null);
                  setError(null);
                }}
                className="px-6 py-2 text-gray-400 hover:text-white transition-colors"
              >
                ← Back
              </button>
              <button
                onClick={() => {
                  if (selectedFolder) {
                    onComplete({
                      type: 'local',
                      local_path: selectedFolder.path || currentPath,
                      name: selectedFolder.name,
                      folder_handle: folderHandle || undefined,
                    });
                  } else {
                    setError('Please select a folder');
                  }
                }}
                disabled={!selectedFolder}
                className="px-8 py-3 bg-blue-600 text-white rounded-xl font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
              >
                Use This Folder
              </button>
            </div>
          </div>
        );

      case 'create-new':
        return (
          <div className="space-y-6 max-w-xl mx-auto">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-white">Create New Project</h2>
              <p className="text-gray-400">Start fresh with a new project folder</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Project Name
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="my-awesome-project"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Location
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newProjectPath}
                    onChange={(e) => setNewProjectPath(e.target.value)}
                    placeholder="Select or enter folder path..."
                    className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
                  />
                  <button
                    onClick={async () => {
                      if (!window.showDirectoryPicker) {
                        setError('Your browser does not support folder selection. Please enter the path manually.');
                        return;
                      }
                      try {
                        const handle = await window.showDirectoryPicker({
                          id: 'helix-new-project',
                          mode: 'readwrite',
                          startIn: 'documents',
                        });
                        setNewProjectPath(handle.name);
                        setFolderHandle(handle);
                      } catch (err: unknown) {
                        if (err instanceof Error && err.name !== 'AbortError') {
                          setError('Failed to select folder');
                        }
                      }
                    }}
                    className="px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl transition-colors"
                    title="Browse for folder"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Project will be created at: {newProjectPath ? `${newProjectPath}/${newProjectName || 'project-name'}` : 'Select a location'}
                </p>
              </div>

              <div className="p-4 bg-gray-800 rounded-xl">
                <p className="text-sm text-gray-400 mb-2">This will create:</p>
                <ul className="text-sm text-gray-300 space-y-1">
                  <li>📁 src/</li>
                  <li>📁 tests/</li>
                  <li>📁 docs/</li>
                  <li>📄 README.md</li>
                  <li>📄 .gitignore</li>
                </ul>
              </div>
            </div>

            {error && <p className="text-red-400 text-sm">{error}</p>}

            <div className="flex justify-between">
              <button
                onClick={() => {
                  setStep('choose-source');
                  setNewProjectName('');
                  setNewProjectPath('');
                  setFolderHandle(null);
                  setError(null);
                }}
                className="px-6 py-2 text-gray-400 hover:text-white transition-colors"
              >
                ← Back
              </button>
              <button
                onClick={() => {
                  if (!newProjectName.trim()) {
                    setError('Please enter a project name');
                    return;
                  }
                  if (!newProjectPath.trim() && !folderHandle) {
                    setError('Please select a location for your project');
                    return;
                  }
                  onComplete({
                    type: 'new',
                    local_path: newProjectPath ? `${newProjectPath}/${newProjectName}` : newProjectName,
                    name: newProjectName,
                    folder_handle: folderHandle || undefined,
                  });
                }}
                disabled={!newProjectName.trim() || loading}
                className="px-8 py-3 bg-green-600 text-white rounded-xl font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-green-700 transition-colors"
              >
                {loading ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-8">
      <div className="w-full max-w-4xl">
        {/* Progress Indicator */}
        {step !== 'welcome' && (
          <div className="mb-8 flex justify-center">
            <div className="flex items-center gap-2">
              {['choose-source', 'github-repos', 'local-browse', 'create-new'].map((s, i) => (
                <div
                  key={s}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    step === s ? 'bg-purple-500' : 'bg-gray-700'
                  }`}
                />
              ))}
            </div>
          </div>
        )}

        {renderStep()}
      </div>
    </div>
  );
}
