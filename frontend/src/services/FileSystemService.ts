"use client";

/**
 * FileSystemService - Cross-platform file system access
 * 
 * Uses the File System Access API to read/write files to the user's
 * selected workspace folder. This enables:
 * - Pillar 1/2: Write generated code to local folder
 * - Pillar 3: Read codebase for intelligence
 * - Live sync between WebContainer and local filesystem
 */

// Type for extended FileSystemDirectoryHandle with permission and iteration methods
type ExtendedDirectoryHandle = FileSystemDirectoryHandle & {
  requestPermission?: (descriptor?: { mode?: 'read' | 'readwrite' }) => Promise<PermissionState>;
  queryPermission?: (descriptor?: { mode?: 'read' | 'readwrite' }) => Promise<PermissionState>;
  values(): AsyncIterableIterator<FileSystemHandle>;
  entries(): AsyncIterableIterator<[string, FileSystemHandle]>;
  keys(): AsyncIterableIterator<string>;
};

export interface FileEntry {
  name: string;
  path: string;
  type: 'file' | 'directory';
  content?: string;
  children?: FileEntry[];
  handle?: FileSystemHandle;
}

export interface GeneratedFile {
  path: string;
  content: string;
  language?: string;
}

class FileSystemService {
  private rootHandle: FileSystemDirectoryHandle | null = null;
  private fileCache: Map<string, string> = new Map();
  private watchCallbacks: Set<(files: FileEntry[]) => void> = new Set();

  /**
   * Check if File System Access API is supported
   */
  isSupported(): boolean {
    return typeof window !== 'undefined' && 'showDirectoryPicker' in window;
  }

  /**
   * Set the root directory handle (from onboarding)
   */
  setRootHandle(handle: FileSystemDirectoryHandle): void {
    this.rootHandle = handle;
    this.fileCache.clear();
  }

  /**
   * Get the current root handle
   */
  getRootHandle(): FileSystemDirectoryHandle | null {
    return this.rootHandle;
  }

  /**
   * Open folder picker and set as root
   */
  async openFolderPicker(): Promise<FileSystemDirectoryHandle | null> {
    if (!this.isSupported() || !window.showDirectoryPicker) {
      console.error('File System Access API not supported');
      return null;
    }

    try {
      const handle = await window.showDirectoryPicker({
        id: 'helix-workspace',
        mode: 'readwrite',
        startIn: 'documents',
      });
      this.setRootHandle(handle);
      return handle;
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        return null; // User cancelled
      }
      throw error;
    }
  }

  /**
   * Request permission for the directory
   */
  async requestPermission(): Promise<boolean> {
    if (!this.rootHandle) return false;

    try {
      // Cast to extended type for permission methods (not in standard TS types yet)
      const handle = this.rootHandle as ExtendedDirectoryHandle;
      if (handle.requestPermission) {
        const permission = await handle.requestPermission({ mode: 'readwrite' });
        return permission === 'granted';
      }
      // If requestPermission doesn't exist, try to access the directory to verify permission
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for await (const _ of (this.rootHandle as ExtendedDirectoryHandle).values()) {
        break; // Just check if we can iterate
      }
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Read all files from the workspace recursively
   */
  async readWorkspace(maxDepth: number = 10): Promise<FileEntry[]> {
    if (!this.rootHandle) {
      throw new Error('No workspace folder selected');
    }

    return this.readDirectory(this.rootHandle, '', maxDepth);
  }

  /**
   * Read a directory recursively
   */
  private async readDirectory(
    dirHandle: FileSystemDirectoryHandle,
    basePath: string,
    maxDepth: number
  ): Promise<FileEntry[]> {
    if (maxDepth <= 0) return [];

    const entries: FileEntry[] = [];
    const ignoredDirs = ['node_modules', '.git', '.next', '__pycache__', 'venv', '.venv', 'dist', 'build'];
    const ignoredFiles = ['.DS_Store', 'Thumbs.db'];

    for await (const entry of (dirHandle as ExtendedDirectoryHandle).values()) {
      const path = basePath ? `${basePath}/${entry.name}` : entry.name;

      if (entry.kind === 'directory') {
        if (ignoredDirs.includes(entry.name)) continue;

        const subDirHandle = await dirHandle.getDirectoryHandle(entry.name);
        const children = await this.readDirectory(subDirHandle, path, maxDepth - 1);
        
        entries.push({
          name: entry.name,
          path,
          type: 'directory',
          children,
          handle: subDirHandle,
        });
      } else {
        if (ignoredFiles.includes(entry.name)) continue;

        entries.push({
          name: entry.name,
          path,
          type: 'file',
          handle: entry,
        });
      }
    }

    // Sort: directories first, then files, alphabetically
    return entries.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  }

  /**
   * Read a single file's content
   */
  async readFile(path: string): Promise<string> {
    if (!this.rootHandle) {
      throw new Error('No workspace folder selected');
    }

    // Check cache first
    if (this.fileCache.has(path)) {
      return this.fileCache.get(path)!;
    }

    const parts = path.split('/').filter(Boolean);
    const fileName = parts.pop()!;
    
    let currentDir = this.rootHandle;
    for (const part of parts) {
      currentDir = await currentDir.getDirectoryHandle(part);
    }

    const fileHandle = await currentDir.getFileHandle(fileName);
    const file = await fileHandle.getFile();
    const content = await file.text();

    // Cache the content
    this.fileCache.set(path, content);

    return content;
  }

  /**
   * Write a file to the workspace
   */
  async writeFile(path: string, content: string): Promise<void> {
    if (!this.rootHandle) {
      throw new Error('No workspace folder selected');
    }

    const parts = path.split('/').filter(Boolean);
    const fileName = parts.pop()!;

    // Create directories if they don't exist
    let currentDir = this.rootHandle;
    for (const part of parts) {
      currentDir = await currentDir.getDirectoryHandle(part, { create: true });
    }

    // Create or get the file
    const fileHandle = await currentDir.getFileHandle(fileName, { create: true });
    
    // Write content
    const writable = await fileHandle.createWritable();
    await writable.write(content);
    await writable.close();

    // Update cache
    this.fileCache.set(path, content);

    // Notify watchers
    this.notifyWatchers();
  }

  /**
   * Write multiple files at once
   */
  async writeFiles(files: GeneratedFile[]): Promise<void> {
    for (const file of files) {
      await this.writeFile(file.path, file.content);
    }
  }

  /**
   * Create a directory
   */
  async createDirectory(path: string): Promise<void> {
    if (!this.rootHandle) {
      throw new Error('No workspace folder selected');
    }

    const parts = path.split('/').filter(Boolean);
    let currentDir = this.rootHandle;

    for (const part of parts) {
      currentDir = await currentDir.getDirectoryHandle(part, { create: true });
    }
  }

  /**
   * Delete a file
   */
  async deleteFile(path: string): Promise<void> {
    if (!this.rootHandle) {
      throw new Error('No workspace folder selected');
    }

    const parts = path.split('/').filter(Boolean);
    const fileName = parts.pop()!;

    let currentDir = this.rootHandle;
    for (const part of parts) {
      currentDir = await currentDir.getDirectoryHandle(part);
    }

    await currentDir.removeEntry(fileName);
    this.fileCache.delete(path);
    this.notifyWatchers();
  }

  /**
   * Check if a file exists
   */
  async fileExists(path: string): Promise<boolean> {
    try {
      await this.readFile(path);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get file tree for display
   */
  async getFileTree(): Promise<FileEntry[]> {
    return this.readWorkspace();
  }

  /**
   * Subscribe to file changes
   */
  onFilesChanged(callback: (files: FileEntry[]) => void): () => void {
    this.watchCallbacks.add(callback);
    return () => this.watchCallbacks.delete(callback);
  }

  /**
   * Notify all watchers of file changes
   */
  private async notifyWatchers(): Promise<void> {
    try {
      const files = await this.readWorkspace();
      this.watchCallbacks.forEach(cb => cb(files));
    } catch (error) {
      console.error('Error notifying watchers:', error);
    }
  }

  /**
   * Clear the file cache
   */
  clearCache(): void {
    this.fileCache.clear();
  }

  /**
   * Get all code files for Pillar 3 indexing
   */
  async getCodeFiles(): Promise<GeneratedFile[]> {
    const codeExtensions = [
      '.ts', '.tsx', '.js', '.jsx', '.py', '.java', '.go', '.rs',
      '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift',
      '.kt', '.scala', '.vue', '.svelte', '.html', '.css', '.scss',
      '.json', '.yaml', '.yml', '.md', '.txt', '.sql', '.sh', '.bash'
    ];

    const files = await this.readWorkspace();
    const codeFiles: GeneratedFile[] = [];

    const processEntry = async (entry: FileEntry) => {
      if (entry.type === 'file') {
        const ext = '.' + entry.name.split('.').pop()?.toLowerCase();
        if (codeExtensions.includes(ext)) {
          try {
            const content = await this.readFile(entry.path);
            codeFiles.push({
              path: entry.path,
              content,
              language: this.getLanguageFromExtension(ext),
            });
          } catch (error) {
            console.warn(`Could not read file: ${entry.path}`, error);
          }
        }
      } else if (entry.children) {
        for (const child of entry.children) {
          await processEntry(child);
        }
      }
    };

    for (const entry of files) {
      await processEntry(entry);
    }

    return codeFiles;
  }

  /**
   * Get language from file extension
   */
  private getLanguageFromExtension(ext: string): string {
    const langMap: Record<string, string> = {
      '.ts': 'typescript',
      '.tsx': 'typescript',
      '.js': 'javascript',
      '.jsx': 'javascript',
      '.py': 'python',
      '.java': 'java',
      '.go': 'go',
      '.rs': 'rust',
      '.cpp': 'cpp',
      '.c': 'c',
      '.cs': 'csharp',
      '.rb': 'ruby',
      '.php': 'php',
      '.swift': 'swift',
      '.kt': 'kotlin',
      '.vue': 'vue',
      '.svelte': 'svelte',
      '.html': 'html',
      '.css': 'css',
      '.scss': 'scss',
      '.json': 'json',
      '.yaml': 'yaml',
      '.yml': 'yaml',
      '.md': 'markdown',
      '.sql': 'sql',
      '.sh': 'bash',
    };
    return langMap[ext] || 'text';
  }
}

// Singleton instance
export const fileSystemService = new FileSystemService();
export default fileSystemService;
