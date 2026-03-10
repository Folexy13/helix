"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { WebContainer, FileSystemTree } from '@webcontainer/api';
import { fileSystemService } from '@/services/FileSystemService';
import CodeEditor from './CodeEditor';

/**
 * LivePreview Component 
 *
 * Uses WebContainers to run Node.js in the browser for live preview
 * of generated code. This is the key differentiator that makes Helix
 * feel like a professional development platform.
 *
 * Features:
 * - In-browser Node.js execution
 * - Live preview iframe
 * - Terminal output streaming
 * - File system sync to local folder
 * - Hot reload support
 * - Real-time file tree display
 */

interface GeneratedFile {
  path: string;
  content: string;
  language?: string;
  status?: 'pending' | 'writing' | 'written' | 'error';
}

interface BuildError {
  type: 'import' | 'syntax' | 'runtime' | 'unknown';
  message: string;
  file?: string;
  line?: number;
  column?: number;
  fullError: string;
}

interface LivePreviewProps {
  files: GeneratedFile[];
  projectType?: 'react' | 'nextjs' | 'vue' | 'vanilla' | 'node';
  onTerminalOutput?: (output: string) => void;
  onError?: (error: string) => void;
  onReady?: (url: string) => void;
  onFileSynced?: (path: string) => void;
  onBuildError?: (error: BuildError) => void;
  onRequestFix?: (error: BuildError) => void;
  syncToLocal?: boolean;
  autoFix?: boolean;
  className?: string;
}

// Template package.json for different project types
const PROJECT_TEMPLATES: Record<string, FileSystemTree> = {
  react: {
    'package.json': {
      file: {
        contents: JSON.stringify({
          name: 'helix-preview',
          version: '1.0.0',
          type: 'module',
          scripts: {
            dev: 'vite',
            build: 'vite build',
            preview: 'vite preview',
          },
          dependencies: {
            react: '^18.2.0',
            'react-dom': '^18.2.0',
          },
          devDependencies: {
            '@vitejs/plugin-react': '^4.0.0',
            vite: '^5.0.0',
          },
        }, null, 2),
      },
    },
    'vite.config.js': {
      file: {
        contents: `
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
  },
});
        `.trim(),
      },
    },
    'index.html': {
      file: {
        contents: `
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Helix Preview</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
        `.trim(),
      },
    },
    src: {
      directory: {
        'main.jsx': {
          file: {
            contents: `
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
            `.trim(),
          },
        },
      },
    },
  },
  vanilla: {
    'package.json': {
      file: {
        contents: JSON.stringify({
          name: 'helix-preview',
          version: '1.0.0',
          type: 'module',
          scripts: {
            dev: 'vite',
            build: 'vite build',
          },
          devDependencies: {
            vite: '^5.0.0',
          },
        }, null, 2),
      },
    },
    'vite.config.js': {
      file: {
        contents: `
import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: true,
    port: 3000,
  },
});
        `.trim(),
      },
    },
    'index.html': {
      file: {
        contents: `
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Helix Preview</title>
    <link rel="stylesheet" href="/style.css" />
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/main.js"></script>
  </body>
</html>
        `.trim(),
      },
    },
  },
  node: {
    'package.json': {
      file: {
        contents: JSON.stringify({
          name: 'helix-preview',
          version: '1.0.0',
          type: 'module',
          scripts: {
            start: 'node index.js',
            dev: 'node --watch index.js',
          },
        }, null, 2),
      },
    },
  },
};

export default function LivePreview({
  files,
  projectType = 'react',
  onTerminalOutput,
  onError,
  onReady,
  onFileSynced,
  onBuildError,
  onRequestFix,
  syncToLocal = true,
  autoFix = false,
  className = '',
}: LivePreviewProps) {
  const [status, setStatus] = useState<'idle' | 'streaming' | 'booting' | 'installing' | 'running' | 'ready' | 'error' | 'fixing'>('idle');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'preview' | 'terminal' | 'files'>('files'); // Default to files tab to show streaming
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<Record<string, 'pending' | 'syncing' | 'synced' | 'error'>>({});
  const [isFilesComplete, setIsFilesComplete] = useState(false);
  const [hasStartedInstall, setHasStartedInstall] = useState(false);
  const [installProgress, setInstallProgress] = useState<{ current: number; total: number; package: string } | null>(null);
  const [installedPackages, setInstalledPackages] = useState<string[]>([]);
  const [currentBuildError, setCurrentBuildError] = useState<BuildError | null>(null);
  const [fixAttempts, setFixAttempts] = useState(0);
  const MAX_FIX_ATTEMPTS = 3;
  
  const webcontainerRef = useRef<WebContainer | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const terminalRef = useRef<HTMLDivElement>(null);
  const errorBufferRef = useRef<string[]>([]);

  // Parse npm install output to extract package info
  const parseNpmOutput = useCallback((output: string) => {
    // Match patterns like "added 150 packages" or "npm WARN" or package names
    const addedMatch = output.match(/added (\d+) packages?/i);
    if (addedMatch) {
      return { type: 'complete', count: parseInt(addedMatch[1]) };
    }
    
    // Match "npm http fetch" or downloading patterns
    const fetchMatch = output.match(/npm http fetch (GET|POST) \d+ ([\w@/.-]+)/);
    if (fetchMatch) {
      return { type: 'fetching', package: fetchMatch[2] };
    }
    
    // Match "reify:" patterns (npm 7+)
    const reifyMatch = output.match(/reify:([^:]+):/);
    if (reifyMatch) {
      return { type: 'installing', package: reifyMatch[1].trim() };
    }
    
    // Match progress like "⸨░░░░░░░░░░░░░░░░░░⸩ ⠋ reify"
    const progressMatch = output.match(/(\d+)\/(\d+)/);
    if (progressMatch) {
      return { type: 'progress', current: parseInt(progressMatch[1]), total: parseInt(progressMatch[2]) };
    }
    
    return null;
  }, []);

  // Strip ANSI escape codes from terminal output
  const stripAnsiCodes = useCallback((str: string): string => {
    // Remove ANSI escape codes (colors, cursor movement, etc.)
    // eslint-disable-next-line no-control-regex
    return str.replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, '')
              .replace(/\[\d*[ABCDEFGJKST]/g, '') // Cursor movement
              .replace(/\[\d*;\d*[Hf]/g, '') // Cursor position
              .replace(/\[\d*[mK]/g, '') // SGR and erase
              .replace(/\[[\d;]*m/g, '') // More SGR codes
              .replace(/\r/g, ''); // Carriage returns
  }, []);

  // Parse build errors from terminal output
  const parseBuildError = useCallback((output: string): BuildError | null => {
    // Vite import resolution error
    const importMatch = output.match(/Failed to resolve import ["']([^"']+)["'] from ["']([^"']+)["']/);
    if (importMatch) {
      return {
        type: 'import',
        message: `Cannot find module "${importMatch[1]}"`,
        file: importMatch[2],
        fullError: output,
      };
    }
    
    // Vite/esbuild syntax error with file location
    const syntaxMatch = output.match(/(?:SyntaxError|ParseError).*?(?:in|at)\s+([^\s:]+):(\d+):(\d+)/);
    if (syntaxMatch) {
      return {
        type: 'syntax',
        message: output.split('\n')[0],
        file: syntaxMatch[1],
        line: parseInt(syntaxMatch[2]),
        column: parseInt(syntaxMatch[3]),
        fullError: output,
      };
    }
    
    // Generic error with file path
    const fileErrorMatch = output.match(/(?:Error|error).*?([\/\w.-]+\.[jt]sx?):(\d+)(?::(\d+))?/);
    if (fileErrorMatch) {
      return {
        type: 'runtime',
        message: output.split('\n')[0],
        file: fileErrorMatch[1],
        line: parseInt(fileErrorMatch[2]),
        column: fileErrorMatch[3] ? parseInt(fileErrorMatch[3]) : undefined,
        fullError: output,
      };
    }
    
    // ENOENT (file not found) error
    const enoentMatch = output.match(/ENOENT.*?open\s+['"]?([^'"]+)['"]?/);
    if (enoentMatch) {
      return {
        type: 'import',
        message: `File not found: ${enoentMatch[1]}`,
        file: enoentMatch[1],
        fullError: output,
      };
    }
    
    // Generic error detection
    if (output.toLowerCase().includes('error') && !output.includes('0 errors')) {
      return {
        type: 'unknown',
        message: output.split('\n')[0],
        fullError: output,
      };
    }
    
    return null;
  }, []);

  // Add terminal output with parsing and error detection
  const addTerminalOutput = useCallback((output: string) => {
    // Strip ANSI codes first
    const strippedOutput = stripAnsiCodes(output);
    
    // Parse npm output for progress tracking
    const parsed = parseNpmOutput(strippedOutput);
    if (parsed) {
      if (parsed.type === 'installing' || parsed.type === 'fetching') {
        setInstalledPackages(prev => {
          const pkg = parsed.package || '';
          if (pkg && !prev.includes(pkg)) {
            return [...prev.slice(-9), pkg]; // Keep last 10 packages
          }
          return prev;
        });
      }
      if (parsed.type === 'progress' && parsed.current !== undefined && parsed.total !== undefined) {
        setInstallProgress({ current: parsed.current, total: parsed.total, package: '' });
      }
    }
    
    // Filter out noisy npm output, keep important messages
    const cleanOutput = strippedOutput.trim();
    if (!cleanOutput) return;
    
    // Skip very long lines (usually progress bars)
    if (cleanOutput.length > 200 && !cleanOutput.includes('error') && !cleanOutput.includes('Error')) {
      return;
    }
    
    // Skip repetitive progress indicators (spinners)
    if (cleanOutput.match(/^[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏\s]+$/)) {
      return;
    }
    
    // Skip npm spinner characters (backslash, forward slash, pipe, dash patterns)
    if (cleanOutput.match(/^[\\/|\-\s]+$/) || cleanOutput.match(/^[\\\/\|\-]{1,3}$/)) {
      return;
    }
    
    // Skip single character spinner frames
    if (cleanOutput.length <= 2 && cleanOutput.match(/^[\\/\|\-\s]*$/)) {
      return;
    }
    
    // Skip lines that are just escape code remnants
    if (cleanOutput.match(/^\[?\d*[A-Za-z]?$/)) {
      return;
    }
    
    // Skip empty or whitespace-only lines
    if (cleanOutput.match(/^\s*$/)) {
      return;
    }
    
    // Buffer output for error detection
    errorBufferRef.current.push(cleanOutput);
    if (errorBufferRef.current.length > 20) {
      errorBufferRef.current.shift();
    }
    
    // Check for build errors - only if not already fixing and no current error
    const buildError = parseBuildError(cleanOutput);
    if (buildError && status !== 'fixing' && !currentBuildError) {
      setCurrentBuildError(buildError);
      onBuildError?.(buildError);
      
      // Auto-fix if enabled and within attempt limit
      // Note: We don't auto-fix anymore - let user click the button
      // This prevents infinite loops
    }
    
    setTerminalOutput(prev => [...prev.slice(-100), cleanOutput]); // Keep last 100 lines
    onTerminalOutput?.(cleanOutput);
    
    // Auto-scroll terminal
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [onTerminalOutput, parseNpmOutput, stripAnsiCodes, parseBuildError, status, currentBuildError, onBuildError]);

  // Manual request fix function (for UI button)
  const requestManualFix = useCallback(() => {
    if (currentBuildError && fixAttempts < MAX_FIX_ATTEMPTS) {
      setStatus('fixing');
      setFixAttempts(prev => prev + 1);
      setTerminalOutput(prev => [...prev, `🔧 Requesting fix (attempt ${fixAttempts + 1}/${MAX_FIX_ATTEMPTS})...`]);
      onRequestFix?.(currentBuildError);
    }
  }, [currentBuildError, fixAttempts, onRequestFix]);

  // Sync files to local filesystem
  const syncFilesToLocal = useCallback(async (filesToSync: GeneratedFile[]) => {
    if (!syncToLocal || !fileSystemService.getRootHandle()) {
      return;
    }

    for (const file of filesToSync) {
      try {
        setSyncStatus(prev => ({ ...prev, [file.path]: 'syncing' }));
        addTerminalOutput(`📁 Syncing ${file.path} to local folder...`);
        
        await fileSystemService.writeFile(file.path, file.content);
        
        setSyncStatus(prev => ({ ...prev, [file.path]: 'synced' }));
        addTerminalOutput(`✅ Synced ${file.path}`);
        onFileSynced?.(file.path);
      } catch (error) {
        setSyncStatus(prev => ({ ...prev, [file.path]: 'error' }));
        addTerminalOutput(`❌ Failed to sync ${file.path}: ${error}`);
      }
    }
  }, [syncToLocal, addTerminalOutput, onFileSynced]);

  // Convert generated files to WebContainer file tree
  const filesToFileTree = useCallback((generatedFiles: GeneratedFile[]): FileSystemTree => {
    const tree: FileSystemTree = {};
    
    for (const file of generatedFiles) {
      const parts = file.path.split('/').filter(Boolean);
      let current = tree as Record<string, { directory?: FileSystemTree; file?: { contents: string } }>;
      
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        if (!current[part]) {
          current[part] = { directory: {} };
        }
        current = current[part].directory as Record<string, { directory?: FileSystemTree; file?: { contents: string } }>;
      }
      
      const fileName = parts[parts.length - 1];
      current[fileName] = {
        file: {
          contents: file.content,
        },
      };
    }
    
    return tree;
  }, []);

  // Merge template with generated files
  const mergeFileTrees = useCallback((template: FileSystemTree, generated: FileSystemTree): FileSystemTree => {
    const merged = { ...template } as Record<string, unknown>;
    
    const deepMerge = (target: Record<string, unknown>, source: Record<string, unknown>) => {
      for (const key of Object.keys(source)) {
        const sourceVal = source[key] as { directory?: Record<string, unknown> };
        const targetVal = target[key] as { directory?: Record<string, unknown> } | undefined;
        if (sourceVal?.directory && targetVal?.directory) {
          deepMerge(targetVal.directory, sourceVal.directory);
        } else {
          target[key] = source[key];
        }
      }
    };
    
    deepMerge(merged, generated as Record<string, unknown>);
    return merged as FileSystemTree;
  }, []);

  // Boot WebContainer and run project
  const bootAndRun = useCallback(async () => {
    if (files.length === 0) return;
    
    try {
      setStatus('booting');
      addTerminalOutput('🚀 Booting WebContainer...');
      
      // Boot WebContainer (singleton)
      if (!webcontainerRef.current) {
        webcontainerRef.current = await WebContainer.boot();
        addTerminalOutput('✅ WebContainer booted');
      }
      
      const webcontainer = webcontainerRef.current;
      
      // Prepare file tree
      const template = PROJECT_TEMPLATES[projectType] || PROJECT_TEMPLATES.vanilla;
      const generatedTree = filesToFileTree(files);
      const fileTree = mergeFileTrees(template, generatedTree);
      
      addTerminalOutput('📁 Mounting file system...');
      await webcontainer.mount(fileTree);
      addTerminalOutput('✅ Files mounted');
      
      // Install dependencies
      setStatus('installing');
      addTerminalOutput('📦 Installing dependencies...');
      
      const installProcess = await webcontainer.spawn('npm', ['install']);
      
      installProcess.output.pipeTo(new WritableStream({
        write(data) {
          addTerminalOutput(data);
        },
      }));
      
      const installExitCode = await installProcess.exit;
      
      if (installExitCode !== 0) {
        throw new Error(`npm install failed with exit code ${installExitCode}`);
      }
      
      addTerminalOutput('✅ Dependencies installed');
      
      // Start dev server
      setStatus('running');
      addTerminalOutput('🔥 Starting development server...');
      
      const devProcess = await webcontainer.spawn('npm', ['run', 'dev']);
      
      devProcess.output.pipeTo(new WritableStream({
        write(data) {
          addTerminalOutput(data);
        },
      }));
      
      // Listen for server ready
      webcontainer.on('server-ready', (port, url) => {
        addTerminalOutput(`✅ Server ready at ${url}`);
        setPreviewUrl(url);
        setStatus('ready');
        onReady?.(url);
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addTerminalOutput(`❌ Error: ${errorMessage}`);
      setStatus('error');
      onError?.(errorMessage);
    }
  }, [files, projectType, filesToFileTree, mergeFileTrees, addTerminalOutput, onReady, onError]);

  // Update files in running container
  const updateFiles = useCallback(async () => {
    if (!webcontainerRef.current || status !== 'ready') return;
    
    try {
      addTerminalOutput('🔄 Updating files...');
      
      for (const file of files) {
        await webcontainerRef.current.fs.writeFile(file.path, file.content);
      }
      
      addTerminalOutput('✅ Files updated (hot reload should trigger)');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addTerminalOutput(`❌ Update error: ${errorMessage}`);
    }
  }, [files, status, addTerminalOutput]);

  // Check if all files are complete (have 'written' status)
  useEffect(() => {
    if (files.length > 0) {
      const allWritten = files.every(f => f.status === 'written' || !f.status);
      const anyWriting = files.some(f => f.status === 'writing' || f.status === 'pending');
      
      if (anyWriting && status === 'idle') {
        // Files are streaming in
        setStatus('streaming');
        setActiveTab('files'); // Switch to files tab to show streaming
      }
      
      // Auto-select the first file or the currently writing file
      if (!selectedFile && files.length > 0) {
        const writingFile = files.find(f => f.status === 'writing');
        setSelectedFile(writingFile?.path || files[0].path);
      }
      
      // Update selected file to show the one currently being written
      const writingFile = files.find(f => f.status === 'writing');
      if (writingFile && status === 'streaming') {
        setSelectedFile(writingFile.path);
      }
      
      if (allWritten && files.length > 0) {
        setIsFilesComplete(true);
      }
    }
  }, [files, status, selectedFile]);

  // Boot only after all files are complete
  useEffect(() => {
    if (isFilesComplete && !hasStartedInstall && files.length > 0) {
      setHasStartedInstall(true);
      addTerminalOutput(`📦 All ${files.length} files received. Starting installation...`);
      bootAndRun();
      // Also sync to local folder
      syncFilesToLocal(files);
    } else if (files.length > 0 && status === 'ready') {
      updateFiles();
      // Also sync to local folder
      syncFilesToLocal(files);
    }
  }, [isFilesComplete, hasStartedInstall, files, status, bootAndRun, updateFiles, syncFilesToLocal, addTerminalOutput]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (webcontainerRef.current) {
        webcontainerRef.current.teardown();
        webcontainerRef.current = null;
      }
    };
  }, []);

  // Render status indicator
  const renderStatus = () => {
    const statusConfig: Record<typeof status, { color: string; text: string }> = {
      idle: { color: 'bg-gray-500', text: 'Idle' },
      streaming: { color: 'bg-cyan-500 animate-pulse', text: 'Receiving files...' },
      booting: { color: 'bg-yellow-500 animate-pulse', text: 'Booting...' },
      installing: { color: 'bg-blue-500 animate-pulse', text: 'Installing...' },
      running: { color: 'bg-purple-500 animate-pulse', text: 'Starting...' },
      ready: { color: 'bg-green-500', text: 'Ready' },
      error: { color: 'bg-red-500', text: 'Error' },
      fixing: { color: 'bg-orange-500 animate-pulse', text: 'Auto-fixing...' },
    };
    
    const config = statusConfig[status];
    
    return (
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${config.color}`} />
        <span className="text-sm text-gray-400">{config.text}</span>
      </div>
    );
  };

  return (
    <div className={`flex flex-col bg-gray-900 rounded-xl overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <h3 className="text-white font-semibold">Live Preview</h3>
          {renderStatus()}
        </div>
        
        {/* Tabs */}
        <div className="flex gap-1">
          {(['preview', 'terminal', 'files'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                activeTab === tab
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
        
        {/* Actions */}
        <div className="flex gap-2 items-center">
          {/* Status indicator */}
          {status === 'streaming' && (
            <span className="text-xs text-cyan-400 flex items-center gap-1">
              <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
              Receiving files...
            </span>
          )}
          {status === 'installing' && (
            <span className="text-xs text-blue-400 flex items-center gap-1">
              <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
              Installing...
            </span>
          )}
          
          <button
            onClick={bootAndRun}
            disabled={
              status === 'booting' || 
              status === 'installing' || 
              status === 'running' || 
              status === 'streaming' ||
              !isFilesComplete
            }
            className={`px-3 py-1 text-sm rounded transition-all ${
              isFilesComplete && (status === 'idle' || status === 'ready' || status === 'error')
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-gray-600 text-gray-400 cursor-not-allowed'
            }`}
          >
            {status === 'idle' || status === 'streaming' ? '▶ Run' : 
             status === 'installing' ? '📦 Installing...' :
             status === 'running' ? '🔄 Starting...' :
             status === 'ready' ? '� Restart' : '▶ Run'}
          </button>
          {previewUrl && (
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1 text-sm bg-gray-700 text-white rounded hover:bg-gray-600"
            >
              ↗ Open
            </a>
          )}
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 min-h-[400px]">
        {/* Preview Tab */}
        {activeTab === 'preview' && (
          <div className="h-full">
            {previewUrl ? (
              <iframe
                ref={iframeRef}
                src={previewUrl}
                className="w-full h-full border-0"
                title="Live Preview"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
              />
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                {status === 'idle' ? (
                  <div className="text-center">
                    <p className="text-lg mb-2">No preview available</p>
                    <p className="text-sm">Generate some code to see it live!</p>
                  </div>
                ) : (
                  <div className="text-center">
                    <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                    <p>Preparing preview...</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        
        {/* Terminal Tab */}
        {activeTab === 'terminal' && (
          <div className="h-full flex flex-col bg-[#1e1e1e]">
            {/* Install Progress Header */}
            {status === 'installing' && (
              <div className="px-4 py-3 border-b border-[#3c3c3c] bg-[#252526]">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm text-blue-400 font-medium">Installing dependencies...</span>
                  </div>
                  {installProgress && (
                    <span className="text-xs text-gray-500">
                      {installProgress.current}/{installProgress.total}
                    </span>
                  )}
                </div>
                {/* Progress bar */}
                <div className="h-1.5 bg-[#3c3c3c] rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
                    style={{ width: installProgress ? `${(installProgress.current / installProgress.total) * 100}%` : '0%' }}
                  />
                </div>
                {/* Recently installed packages */}
                {installedPackages.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {installedPackages.slice(-5).map((pkg, i) => (
                      <span 
                        key={i} 
                        className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 text-blue-300 rounded"
                      >
                        📦 {pkg}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {/* Build Error Banner with Fix Button */}
            {currentBuildError && status !== 'fixing' && (
              <div className="px-4 py-3 border-b border-red-500/30 bg-red-500/10">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-red-400 font-medium text-sm">❌ Build Error</span>
                      {currentBuildError.file && (
                        <span className="text-xs text-red-300/70 truncate">
                          in {currentBuildError.file}
                          {currentBuildError.line && `:${currentBuildError.line}`}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-red-200/80 truncate">{currentBuildError.message}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {fixAttempts < MAX_FIX_ATTEMPTS ? (
                      <button
                        onClick={requestManualFix}
                        className="px-3 py-1.5 text-xs font-medium bg-orange-500 hover:bg-orange-600 text-white rounded transition-colors flex items-center gap-1"
                      >
                        🔧 Auto-Fix
                        <span className="text-orange-200">({MAX_FIX_ATTEMPTS - fixAttempts} left)</span>
                      </button>
                    ) : (
                      <span className="text-xs text-red-300">Max attempts reached</span>
                    )}
                    <button
                      onClick={() => setCurrentBuildError(null)}
                      className="p-1 text-red-300 hover:text-red-100 transition-colors"
                      title="Dismiss"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Fixing Status Banner */}
            {status === 'fixing' && (
              <div className="px-4 py-3 border-b border-orange-500/30 bg-orange-500/10">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm text-orange-400 font-medium">
                    Auto-fixing error (attempt {fixAttempts}/{MAX_FIX_ATTEMPTS})...
                  </span>
                </div>
                <p className="text-xs text-orange-200/70 mt-1">
                  CODER agent is analyzing and fixing the issue
                </p>
              </div>
            )}
            
            {/* Terminal Output */}
            <div
              ref={terminalRef}
              className="flex-1 p-4 font-mono text-sm overflow-auto"
            >
              {terminalOutput.length === 0 ? (
                <p className="text-gray-500">Terminal output will appear here...</p>
              ) : (
                terminalOutput.map((line, i) => {
                  // Color code different types of output
                  let textColor = 'text-gray-300';
                  
                  if (line.startsWith('✅') || line.includes('success') || line.includes('ready')) {
                    textColor = 'text-green-400';
                  } else if (line.startsWith('❌') || line.includes('error') || line.includes('Error')) {
                    textColor = 'text-red-400';
                  } else if (line.startsWith('⚠️') || line.includes('warn') || line.includes('WARN')) {
                    textColor = 'text-yellow-400';
                  } else if (line.startsWith('📦') || line.includes('added') || line.includes('packages')) {
                    textColor = 'text-blue-400';
                  } else if (line.startsWith('🚀') || line.startsWith('🔥')) {
                    textColor = 'text-purple-400';
                  } else if (line.startsWith('📁') || line.startsWith('💾')) {
                    textColor = 'text-cyan-400';
                  }
                  
                  return (
                    <div key={i} className={`whitespace-pre-wrap ${textColor} leading-relaxed`}>
                      {line}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
        
        {/* Files Tab - VS Code Style Editor */}
        {activeTab === 'files' && (
          <CodeEditor
            files={files}
            workspaceName={projectType === 'react' ? 'React App' : projectType === 'node' ? 'Node.js App' : 'Project'}
            selectedFile={selectedFile}
            onSelectFile={setSelectedFile}
            className="h-full"
          />
        )}
      </div>
    </div>
  );
}
