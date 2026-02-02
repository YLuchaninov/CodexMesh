/**
 * CommandPalette component.
 *
 * Ctrl+K command palette for searching and running tools.
 */
import { useEffect, useMemo, useState } from 'react';
import type { ToolMeta } from '../api/types';
import { Input } from './ui';

interface CommandPaletteProps {
    tools: ToolMeta[];
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSelect: (tool: ToolMeta) => void;
}

export function CommandPalette({ tools, open, onOpenChange, onSelect }: CommandPaletteProps) {
    const [q, setQ] = useState('');

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                onOpenChange(!open);
            }
            if (e.key === 'Escape') onOpenChange(false);
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [open, onOpenChange]);

    const items = useMemo(() => {
        const s = q.trim().toLowerCase();
        const base = tools;
        if (!s) return base.slice(0, 30);
        return base
            .filter(
                (t) =>
                    (t.title + ' ' + t.category + ' ' + t.id).toLowerCase().includes(s)
            )
            .slice(0, 50);
    }, [tools, q]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 bg-black/40 flex items-start justify-center p-4 z-50 backdrop-blur-sm">
            <div className="w-full max-w-2xl rounded-2xl bg-sidebar shadow-2xl border border-border overflow-hidden mt-16 animate-in fade-in zoom-in duration-200">
                <div className="p-3 border-b border-border">
                    <Input
                        autoFocus
                        placeholder="Type a command… (RepoMap, Hotspots, Subgraph, Run intent...)"
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                    />
                </div>
                <div className="max-h-[420px] overflow-auto">
                    {items.map((t) => (
                        <button
                            key={t.id}
                            className="w-full text-left px-4 py-3 hover:bg-white/5 border-b border-border/50 last:border-0 transition-colors group"
                            onClick={() => {
                                onSelect(t);
                                onOpenChange(false);
                                setQ('');
                            }}
                        >
                            <div className="text-sm font-medium text-text group-hover:text-white transition-colors">{t.title}</div>
                            <div className="text-xs text-slate-400">
                                {t.category} · {t.id}
                            </div>
                        </button>
                    ))}
                    {items.length === 0 && (
                        <div className="p-8 text-center text-sm text-slate-500">No results found for "{q}"</div>
                    )}
                </div>
            </div>
        </div>
    );
}
