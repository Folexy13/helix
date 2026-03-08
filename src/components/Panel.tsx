import { ReactNode } from 'react';

export function Panel({ children, className = '', title }: { children: ReactNode; className?: string; title?: string }) {
  return (
    <div className={`bg-card rounded-xl border border-border shadow-sm overflow-hidden flex flex-col ${className}`}>
      {title && (
        <div className="px-4 py-3 border-b border-border bg-muted/50">
          <h3 className="font-semibold text-sm text-foreground">{title}</h3>
        </div>
      )}
      <div className="flex-1 overflow-auto p-4">
        {children}
      </div>
    </div>
  );
}
