"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { codeToHtml } from 'shiki';
import { ChevronRight, ChevronDown, File, Folder, FolderOpen } from 'lucide-react';

/**
 * VS Code-like Code Editor Component
 * 
 * Features:
 * - Hierarchical file tree with collapsible folders
 * - Syntax highlighting with Shiki
 * - Line numbers
 * - File icons based on extension
 * - Workspace root display
 */

interface GeneratedFile {
  path: string;
  content: string;
  language?: string;
  status?: 'pending' | 'writing' | 'written' | 'error';
}

interface CodeEditorProps {
  files: GeneratedFile[];
  workspaceName?: string;
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
  className?: string;
}

// File tree node structure
interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: TreeNode[];
  file?: GeneratedFile;
}

// File icon mapping based on extension
const getFileIcon = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const iconMap: Record<string, string> = {
    'ts': '🟦',
    'tsx': '⚛️',
    'js': '🟨',
    'jsx': '⚛️',
    'json': '📋',
    'html': '🌐',
    'css': '🎨',
    'scss': '🎨',
    'md': '📝',
    'py': '🐍',
    'sql': '🗃️',
    'yaml': '⚙️',
    'yml': '⚙️',
    'env': '🔐',
    'gitignore': '📁',
    'dockerfile': '🐳',
  };
  return iconMap[ext] || '📄';
};

// Get language from file extension
const getLanguage = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const langMap: Record<string, string> = {
    'ts': 'typescript',
    'tsx': 'tsx',
    'js': 'javascript',
    'jsx': 'jsx',
    'json': 'json',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'md': 'markdown',
    'py': 'python',
    'sql': 'sql',
    'yaml': 'yaml',
    'yml': 'yaml',
    'sh': 'bash',
    'bash': 'bash',
  };
  return langMap[ext] || 'text';
};

// Build tree structure from flat file list
function buildFileTree(files: GeneratedFile[]): TreeNode[] {
  const root: TreeNode[] = [];
  
  for (const file of files) {
    const parts = file.path.split('/').filter(Boolean);
    let currentLevel = root;
    let currentPath = '';
    
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isFile = i === parts.length - 1;
      
      let existing = currentLevel.find(n => n.name === part);
      
      if (!existing) {
        existing = {
          name: part,
          path: currentPath,
          type: isFile ? 'file' : 'folder',
          children: isFile ? undefined : [],
          file: isFile ? file : undefined,
        };
        currentLevel.push(existing);
      }
      
      if (!isFile && existing.children) {
        currentLevel = existing.children;
      }
    }
  }
  
  // Sort: folders first, then files, alphabetically
  const sortNodes = (nodes: TreeNode[]): TreeNode[] => {
    return nodes.sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === 'folder' ? -1 : 1;
      }
      return a.name.localeCompare(b.name);
    }).map(node => ({
      ...node,
      children: node.children ? sortNodes(node.children) : undefined,
    }));
  };
  
  return sortNodes(root);
}

// Tree Node Component
function TreeNodeComponent({
  node,
  selectedFile,
  onSelectFile,
  expandedFolders,
  onToggleFolder,
  depth = 0,
}: {
  node: TreeNode;
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
  expandedFolders: Set<string>;
  onToggleFolder: (path: string) => void;
  depth?: number;
}) {
  const isExpanded = expandedFolders.has(node.path);
  const isSelected = selectedFile === node.path;
  const paddingLeft = depth * 12 + 8;
  
  if (node.type === 'folder') {
    return (
      <div>
        <button
          onClick={() => onToggleFolder(node.path)}
          className="w-full flex items-center gap-1 py-1 hover:bg-[#2a2d2e] text-gray-300 text-sm"
          style={{ paddingLeft }}
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />
          )}
          {isExpanded ? (
            <FolderOpen className="w-4 h-4 text-yellow-500 shrink-0" />
          ) : (
            <Folder className="w-4 h-4 text-yellow-500 shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
        </button>
        {isExpanded && node.children && (
          <div>
            {node.children.map(child => (
              <TreeNodeComponent
                key={child.path}
                node={child}
                selectedFile={selectedFile}
                onSelectFile={onSelectFile}
                expandedFolders={expandedFolders}
                onToggleFolder={onToggleFolder}
                depth={depth + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  }
  
  // File node
  const status = node.file?.status;
  const statusIndicator = status === 'writing' ? '✍️' : 
                          status === 'written' ? '' : 
                          status === 'pending' ? '⏳' : '';
  
  return (
    <button
      onClick={() => onSelectFile(node.path)}
      className={`w-full flex items-center gap-1 py-1 text-sm transition-colors ${
        isSelected 
          ? 'bg-[#094771] text-white' 
          : status === 'writing'
          ? 'bg-cyan-500/10 text-cyan-300 animate-pulse'
          : 'hover:bg-[#2a2d2e] text-gray-300'
      }`}
      style={{ paddingLeft: paddingLeft + 16 }}
    >
      <span className="shrink-0">{getFileIcon(node.name)}</span>
      <span className="truncate flex-1 text-left">{node.name}</span>
      {statusIndicator && <span className="shrink-0 text-xs">{statusIndicator}</span>}
    </button>
  );
}

// Code Display with Syntax Highlighting
function CodeDisplay({ content, language, filename }: { content: string; language: string; filename: string }) {
  const [highlightedCode, setHighlightedCode] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    let cancelled = false;
    
    const highlight = async () => {
      setIsLoading(true);
      try {
        const html = await codeToHtml(content, {
          lang: language,
          theme: 'github-dark',
        });
        if (!cancelled) {
          setHighlightedCode(html);
        }
      } catch (error) {
        // Fallback to plain text if highlighting fails
        if (!cancelled) {
          setHighlightedCode(`<pre><code>${content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };
    
    highlight();
    
    return () => {
      cancelled = true;
    };
  }, [content, language]);
  
  const lines = content.split('\n');
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-sm">Loading syntax highlighting...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex h-full overflow-auto bg-[#1e1e1e]">
      {/* Line Numbers */}
      <div className="flex-shrink-0 py-4 px-2 text-right text-gray-500 text-sm font-mono select-none bg-[#1e1e1e] border-r border-[#3c3c3c]">
        {lines.map((_, i) => (
          <div key={i} className="leading-6 h-6">
            {i + 1}
          </div>
        ))}
      </div>
      
      {/* Code Content */}
      <div 
        className="flex-1 py-4 px-4 overflow-x-auto"
        dangerouslySetInnerHTML={{ __html: highlightedCode }}
        style={{
          fontFamily: "'Fira Code', 'Consolas', 'Monaco', monospace",
          fontSize: '14px',
          lineHeight: '24px',
        }}
      />
    </div>
  );
}

export default function CodeEditor({
  files,
  workspaceName = 'Project',
  selectedFile,
  onSelectFile,
  className = '',
}: CodeEditorProps) {
  // Build file tree
  const fileTree = useMemo(() => buildFileTree(files), [files]);
  
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [hasInitialized, setHasInitialized] = useState(false);
  
  // Calculate folders that should be expanded
  const foldersToExpand = useMemo(() => {
    const folders = new Set<string>();
    
    // Get all folder paths from tree
    const collectFolders = (nodes: TreeNode[]) => {
      for (const node of nodes) {
        if (node.type === 'folder') {
          folders.add(node.path);
          if (node.children) {
            collectFolders(node.children);
          }
        }
      }
    };
    collectFolders(fileTree);
    
    // Add folders containing selected file
    if (selectedFile) {
      const parts = selectedFile.split('/');
      let path = '';
      for (let i = 0; i < parts.length - 1; i++) {
        path = path ? `${path}/${parts[i]}` : parts[i];
        folders.add(path);
      }
    }
    
    return folders;
  }, [fileTree, selectedFile]);
  
  // Expand all folders by default (VS Code style)
  const effectiveExpandedFolders = useMemo(() => {
    if (!hasInitialized && foldersToExpand.size > 0) {
      return foldersToExpand;
    }
    return expandedFolders;
  }, [hasInitialized, foldersToExpand, expandedFolders]);
  
  const toggleFolder = useCallback((path: string) => {
    if (!hasInitialized) {
      setHasInitialized(true);
    }
    setExpandedFolders(prev => {
      // Start from effective state if not initialized
      const base = hasInitialized ? prev : foldersToExpand;
      const next = new Set(base);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, [hasInitialized, foldersToExpand]);
  
  const selectedFileData = files.find(f => f.path === selectedFile);
  
  return (
    <div className={`flex h-full bg-[#1e1e1e] ${className}`}>
      {/* File Explorer */}
      <div className="w-64 border-r border-[#3c3c3c] flex flex-col bg-[#252526]">
        {/* Explorer Header */}
        <div className="px-4 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-[#3c3c3c]">
          Explorer
        </div>
        
        {/* Workspace Name */}
        <div className="px-2 py-2 border-b border-[#3c3c3c]">
          <div className="flex items-center gap-2 text-sm text-gray-300 font-medium">
            <Folder className="w-4 h-4 text-yellow-500" />
            <span className="truncate">{workspaceName}</span>
            <span className="text-xs text-gray-500 ml-auto">{files.length} files</span>
          </div>
        </div>
        
        {/* File Tree */}
        <div className="flex-1 overflow-auto py-1">
          {files.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-500 text-sm">
              <File className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Waiting for files...</p>
            </div>
          ) : (
            fileTree.map(node => (
              <TreeNodeComponent
                key={node.path}
                node={node}
                selectedFile={selectedFile}
                onSelectFile={onSelectFile}
                expandedFolders={effectiveExpandedFolders}
                onToggleFolder={toggleFolder}
              />
            ))
          )}
        </div>
      </div>
      
      {/* Editor Area */}
      <div className="flex-1 flex flex-col">
        {/* Tab Bar */}
        {selectedFile && (
          <div className="flex items-center bg-[#252526] border-b border-[#3c3c3c]">
            <div className="flex items-center gap-2 px-4 py-2 bg-[#1e1e1e] border-r border-[#3c3c3c] text-sm text-white">
              <span>{getFileIcon(selectedFile.split('/').pop() || '')}</span>
              <span>{selectedFile.split('/').pop()}</span>
            </div>
            <div className="flex-1" />
            <div className="px-4 text-xs text-gray-500">
              {selectedFile}
            </div>
          </div>
        )}
        
        {/* Code Content */}
        <div className="flex-1 overflow-hidden">
          {selectedFileData ? (
            <CodeDisplay
              content={selectedFileData.content}
              language={getLanguage(selectedFile || '')}
              filename={selectedFile || ''}
            />
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              <div className="text-center">
                <File className="w-16 h-16 mx-auto mb-4 opacity-30" />
                <p className="text-lg">Select a file to view its contents</p>
                <p className="text-sm mt-2">Use the explorer on the left to browse files</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
