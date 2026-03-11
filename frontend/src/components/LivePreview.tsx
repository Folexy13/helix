"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
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
            test: 'vitest',
            'test:ui': 'vitest --ui',
          },
          dependencies: {
            'react': '18.2.0',
            'react-dom': '18.2.0',
            'react-router-dom': '6.20.0',
            'zustand': '4.4.0',
          },
          devDependencies: {
            '@vitejs/plugin-react': '4.2.0',
            '@types/react': '18.2.0',
            '@types/react-dom': '18.2.0',
            '@testing-library/react': '14.1.0',
            '@testing-library/jest-dom': '6.1.0',
            'jsdom': '23.0.0',
            'vitest': '1.1.0',
            'typescript': '5.3.0',
            'vite': '5.0.0',
            'tailwindcss': '3.4.0',
            'autoprefixer': '10.4.0',
            'postcss': '8.4.0',
          },
        }, null, 2),
      },
    },
    'vite.config.ts': {
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
  resolve: {
    extensions: ['.tsx', '.ts', '.jsx', '.js'],
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
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
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
        `.trim(),
      },
    },
    'tsconfig.json': {
      file: {
        contents: JSON.stringify({
          compilerOptions: {
            target: 'ES2020',
            useDefineForClassFields: true,
            lib: ['ES2020', 'DOM', 'DOM.Iterable'],
            module: 'ESNext',
            skipLibCheck: true,
            moduleResolution: 'bundler',
            allowImportingTsExtensions: true,
            resolveJsonModule: true,
            isolatedModules: true,
            noEmit: true,
            jsx: 'react-jsx',
            strict: true,
            noUnusedLocals: false,
            noUnusedParameters: false,
            noFallthroughCasesInSwitch: true,
          },
          include: ['src'],
          references: [{ path: './tsconfig.node.json' }],
        }, null, 2),
      },
    },
    'tsconfig.node.json': {
      file: {
        contents: JSON.stringify({
          compilerOptions: {
            composite: true,
            skipLibCheck: true,
            module: 'ESNext',
            moduleResolution: 'bundler',
            allowSyntheticDefaultImports: true,
          },
          include: ['vite.config.ts'],
        }, null, 2),
      },
    },
    'tailwind.config.js': {
      file: {
        contents: `
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
}
        `.trim(),
      },
    },
    'postcss.config.js': {
      file: {
        contents: `
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
        `.trim(),
      },
    },
    src: {
      directory: {
        'main.tsx': {
          file: {
            contents: `
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
            `.trim(),
          },
        },
        'App.tsx': {
          file: {
            contents: `
import React from 'react';

/**
 * Default App Component
 * This will be replaced by the generated App.tsx from CODER agent.
 */
export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-500 mx-auto mb-4"></div>
        <h1 className="text-2xl font-bold text-white mb-2">Helix Preview</h1>
        <p className="text-gray-400">Generating your application...</p>
      </div>
    </div>
  );
}
            `.trim(),
          },
        },
        'index.css': {
          file: {
            contents: `
@tailwind base;
@tailwind components;
@tailwind utilities;
            `.trim(),
          },
        },
        // Pre-create common directories to ensure they exist
        components: {
          directory: {
            '.gitkeep': {
              file: { contents: '' },
            },
          },
        },
        pages: {
          directory: {
            '.gitkeep': {
              file: { contents: '' },
            },
          },
        },
        store: {
          directory: {
            '.gitkeep': {
              file: { contents: '' },
            },
          },
        },
        hooks: {
          directory: {
            '.gitkeep': {
              file: { contents: '' },
            },
          },
        },
        services: {
          directory: {
            '.gitkeep': {
              file: { contents: '' },
            },
          },
        },
        utils: {
          directory: {
            'delay.ts': {
              file: {
                contents: `
/**
 * Utility function to simulate network delay
 * Used by mock API services for realistic UX
 */
export const delay = (ms: number = 300): Promise<void> => 
  new Promise(resolve => setTimeout(resolve, ms));

export default delay;
                `.trim(),
              },
            },
          },
        },
        test: {
          directory: {
            'setup.ts': {
              file: {
                contents: `
import '@testing-library/jest-dom';
                `.trim(),
              },
            },
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

  // Normalize file path to ensure consistency
  const normalizeFilePath = useCallback((path: string): string => {
    // Remove leading ./ or /
    let normalized = path.replace(/^\.?\//, '');
    
    // Handle common path variations
    // If path doesn't start with src/ but should (for tsx/jsx files in root)
    if (!normalized.startsWith('src/') && 
        !normalized.includes('/') && 
        (normalized.endsWith('.tsx') || normalized.endsWith('.jsx')) &&
        normalized !== 'App.tsx' && normalized !== 'App.jsx' &&
        normalized !== 'main.tsx' && normalized !== 'main.jsx') {
      // Component files should be in src/components/
      normalized = `src/components/${normalized}`;
    }
    
    // Ensure App.tsx is in src/
    if (normalized === 'App.tsx' || normalized === 'App.jsx') {
      normalized = `src/${normalized}`;
    }
    
    // Ensure main.tsx is in src/
    if (normalized === 'main.tsx' || normalized === 'main.jsx') {
      normalized = `src/${normalized}`;
    }
    
    // Ensure index.css is in src/
    if (normalized === 'index.css' || normalized === 'styles.css') {
      normalized = `src/${normalized}`;
    }
    
    return normalized;
  }, []);

  // Convert generated files to WebContainer file tree
  const filesToFileTree = useCallback((generatedFiles: GeneratedFile[]): FileSystemTree => {
    const tree: FileSystemTree = {};
    
    for (const file of generatedFiles) {
      // Normalize the file path first
      const normalizedPath = normalizeFilePath(file.path);
      const parts = normalizedPath.split('/').filter(Boolean);
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
  }, [normalizeFilePath]);

  // Merge template with generated files
  const mergeFileTrees = useCallback((template: FileSystemTree, generated: FileSystemTree): FileSystemTree => {
    const merged = JSON.parse(JSON.stringify(template)) as Record<string, unknown>;
    
    const deepMerge = (target: Record<string, unknown>, source: Record<string, unknown>) => {
      for (const key of Object.keys(source)) {
        const sourceVal = source[key] as { directory?: Record<string, unknown>; file?: { contents: string } };
        const targetVal = target[key] as { directory?: Record<string, unknown>; file?: { contents: string } } | undefined;
        
        if (sourceVal?.directory) {
          // Source is a directory
          if (targetVal?.directory) {
            // Both are directories, merge recursively
            deepMerge(targetVal.directory, sourceVal.directory);
          } else {
            // Target doesn't have this directory or has a file, replace with directory
            target[key] = JSON.parse(JSON.stringify(sourceVal));
          }
        } else if (sourceVal?.file) {
          // Source is a file, always replace
          target[key] = { file: { contents: sourceVal.file.contents } };
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
      
      // Log the files being mounted for debugging
      const logFileTree = (tree: FileSystemTree, prefix = '') => {
        for (const [name, entry] of Object.entries(tree)) {
          if ('file' in entry) {
            addTerminalOutput(`   📄 ${prefix}${name}`);
          } else if ('directory' in entry) {
            addTerminalOutput(`   📁 ${prefix}${name}/`);
            logFileTree(entry.directory as FileSystemTree, `${prefix}${name}/`);
          }
        }
      };
      logFileTree(fileTree);
      
      await webcontainer.mount(fileTree);
      addTerminalOutput('✅ Files mounted');
      
      // Install dependencies - try pnpm first for faster installation
      setStatus('installing');
      addTerminalOutput('📦 Installing dependencies...');
      
      // Check if pnpm is available
      let packageManager = 'npm';
      let installArgs = ['install'];
      let devCommand = 'npm';
      let devArgs = ['run', 'dev'];
      
      try {
        const pnpmCheck = await webcontainer.spawn('pnpm', ['--version']);
        const pnpmExitCode = await pnpmCheck.exit;
        if (pnpmExitCode === 0) {
          packageManager = 'pnpm';
          installArgs = ['install', '--prefer-offline', '--no-frozen-lockfile'];
          devCommand = 'npx';
          devArgs = ['vite'];
          addTerminalOutput('⚡ Using pnpm for faster installation');
        }
      } catch {
        // pnpm not available, use npm
        addTerminalOutput('📦 Using npm for installation');
      }
      
      const installProcess = await webcontainer.spawn(packageManager, installArgs);
      
      installProcess.output.pipeTo(new WritableStream({
        write(data) {
          addTerminalOutput(data);
        },
      }));
      
      const installExitCode = await installProcess.exit;
      
      if (installExitCode !== 0) {
        throw new Error(`${packageManager} install failed with exit code ${installExitCode}`);
      }
      
      addTerminalOutput('✅ Dependencies installed');
      
      // Start dev server
      setStatus('running');
      addTerminalOutput(`🔥 Starting development server with ${devCommand} ${devArgs.join(' ')}...`);
      
      const devProcess = await webcontainer.spawn(devCommand, devArgs);
      
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
        // Normalize the path to match how files were mounted
        const normalizedPath = normalizeFilePath(file.path);
        
        // Ensure parent directories exist
        const parts = normalizedPath.split('/');
        if (parts.length > 1) {
          const dirPath = parts.slice(0, -1).join('/');
          try {
            await webcontainerRef.current.fs.mkdir(dirPath, { recursive: true });
          } catch {
            // Directory might already exist, ignore
          }
        }
        
        await webcontainerRef.current.fs.writeFile(normalizedPath, file.content);
      }
      
      addTerminalOutput('✅ Files updated (hot reload should trigger)');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addTerminalOutput(`❌ Update error: ${errorMessage}`);
    }
  }, [files, status, addTerminalOutput, normalizeFilePath]);

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
          <div className="h-full relative">
            {previewUrl ? (
              <>
                <iframe
                  ref={iframeRef}
                  src={previewUrl}
                  className="w-full h-full border-0"
                  title="Live Preview"
                  sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-pointer-lock"
                  allow="cross-origin-isolated"
                  onLoad={() => console.log('[Preview] iframe loaded:', previewUrl)}
                  onError={(e) => console.error('[Preview] iframe error:', e)}
                />
                {/* Fallback message if iframe appears blank */}
                <div className="absolute bottom-4 right-4 bg-gray-800/80 text-white text-xs px-3 py-2 rounded-lg opacity-70 hover:opacity-100 transition-opacity">
                  <p>Preview URL: <a href={previewUrl} target="_blank" rel="noopener noreferrer" className="text-cyan-400 underline">Open in new tab</a></p>
                </div>
              </>
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
