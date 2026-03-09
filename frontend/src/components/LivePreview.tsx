"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { WebContainer, FileSystemTree } from '@webcontainer/api';
import { fileSystemService } from '@/services/FileSystemService';
import CodeEditor from './CodeEditor';

/**
 * LivePreview Component - Bolt.new Style
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

interface LivePreviewProps {
  files: GeneratedFile[];
  projectType?: 'react' | 'nextjs' | 'vue' | 'vanilla' | 'node';
  onTerminalOutput?: (output: string) => void;
  onError?: (error: string) => void;
  onReady?: (url: string) => void;
  onFileSynced?: (path: string) => void;
  syncToLocal?: boolean;
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
  syncToLocal = true,
  className = '',
}: LivePreviewProps) {
  const [status, setStatus] = useState<'idle' | 'streaming' | 'booting' | 'installing' | 'running' | 'ready' | 'error'>('idle');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [terminalOutput, setTerminalOutput] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<'preview' | 'terminal' | 'files'>('files'); // Default to files tab to show streaming
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<Record<string, 'pending' | 'syncing' | 'synced' | 'error'>>({});
  const [isFilesComplete, setIsFilesComplete] = useState(false);
  const [hasStartedInstall, setHasStartedInstall] = useState(false);
  
  const webcontainerRef = useRef<WebContainer | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const terminalRef = useRef<HTMLDivElement>(null);

  // Add terminal output
  const addTerminalOutput = useCallback((output: string) => {
    setTerminalOutput(prev => [...prev, output]);
    onTerminalOutput?.(output);
    
    // Auto-scroll terminal
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [onTerminalOutput]);

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
        <div className="flex gap-2">
          <button
            onClick={bootAndRun}
            disabled={status === 'booting' || status === 'installing' || status === 'running'}
            className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {status === 'idle' ? '▶ Run' : '🔄 Restart'}
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
          <div
            ref={terminalRef}
            className="h-full p-4 font-mono text-sm text-green-400 bg-black overflow-auto"
          >
            {terminalOutput.length === 0 ? (
              <p className="text-gray-500">Terminal output will appear here...</p>
            ) : (
              terminalOutput.map((line, i) => (
                <div key={i} className="whitespace-pre-wrap">
                  {line}
                </div>
              ))
            )}
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
