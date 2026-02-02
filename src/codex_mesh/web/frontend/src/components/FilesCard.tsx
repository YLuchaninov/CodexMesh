import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useProject } from '../api/context';
import { Section } from './ui';
import { Folder, File, ChevronRight, RefreshCw } from 'lucide-react';
import type { FileEntry } from '../api/types';

interface Props {
    onFileSelect: (path: string) => void;
    selectedFile?: string | null;
    revealFile?: string | null;
    onRevealed?: () => void;
}

export default function FilesCard({ onFileSelect, selectedFile, revealFile, onRevealed }: Props) {
    const { status } = useProject();
    const [entries, setEntries] = useState<FileEntry[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [currentPath, setCurrentPath] = useState('.');

    const loadList = async (path: string = '.') => {
        try {
            setError(null);
            const res = await api.listDir(path);
            setEntries(res.entries ?? []);
        } catch (e) {
            setEntries([]);
            setError(String(e));
        }
    };

    useEffect(() => {
        if (status === 'READY') {
            loadList(currentPath);
        }
    }, [status]);

    useEffect(() => {
        if (revealFile) {
            const parts = revealFile.split('/');
            parts.pop();
            const dir = parts.join('/') || '.';
            if (dir !== currentPath) {
                setCurrentPath(dir);
                loadList(dir);
            }
            onRevealed?.();
        }
    }, [revealFile, currentPath, onRevealed]);

    const sorted = [...entries].sort((a, b) => {
        if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
        return a.name.localeCompare(b.name);
    });

    return (
        <Section title="File Explorer" className="flex-1 overflow-hidden">
            <div className="flex justify-between items-center px-1 mb-1">
                <span className="text-[10px] font-mono text-slate-500 truncate max-w-[200px]">{currentPath}</span>
                <button onClick={() => loadList(currentPath)} className="text-slate-500 hover:text-white transition-colors">
                    <RefreshCw size={10} />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                <div className="flex flex-col gap-0.5">
                    {/* Add Up button if not root */}
                    {currentPath !== '.' && (
                        <div
                            className="flex items-center gap-2 text-slate-400 hover:text-slate-100 cursor-pointer text-sm py-1 select-none pl-1 rounded hover:bg-white/5 transition-colors"
                            onClick={() => {
                                const parts = currentPath.split('/').filter(Boolean);
                                parts.pop();
                                const newPath = parts.join('/') || '.';
                                setCurrentPath(newPath);
                                loadList(newPath);
                            }}
                        >
                            <div className="w-[14px]" />
                            <span className="truncate text-slate-500 italic">.. (parent)</span>
                        </div>
                    )}

                    {error && (
                        <div className="text-xs text-red-400 px-1 py-2 bg-red-400/5 rounded border border-red-400/10">
                            {error}
                        </div>
                    )}

                    {!error && sorted.length === 0 && (
                        <div className="text-xs text-slate-600 px-1 py-1 italic">
                            (empty directory)
                        </div>
                    )}

                    {sorted.map((entry) => {
                        const isDir = entry.type === 'dir';
                        const isSelected = entry.path === selectedFile;

                        return (
                            <div
                                key={entry.path}
                                className={`flex items-center gap-2 cursor-pointer text-sm py-1 select-none pl-1 rounded transition-all ${isSelected
                                        ? 'bg-accent/10 text-accent font-medium border-l-2 border-accent pl-0.5'
                                        : 'text-slate-400 hover:text-slate-100 hover:bg-white/5 border-l-2 border-transparent'
                                    }`}
                                onClick={() => {
                                    if (isDir) {
                                        setCurrentPath(entry.path);
                                        loadList(entry.path);
                                    } else {
                                        onFileSelect(entry.path);
                                    }
                                }}
                            >
                                <div className="text-slate-600">
                                    {isDir ? <ChevronRight size={14} className={isSelected ? 'text-accent' : ''} /> : <div className="w-[14px]" />}
                                </div>
                                {isDir ? (
                                    <Folder size={14} className={isSelected ? 'text-accent' : 'text-slate-500'} />
                                ) : (
                                    <File size={14} className={isSelected ? 'text-accent' : 'text-slate-500'} />
                                )}
                                <span className="truncate">{entry.name}</span>
                                {!isDir && typeof entry.size === 'number' && (
                                    <span className="ml-auto text-[10px] text-slate-600 font-mono pr-1">
                                        {(entry.size / 1024).toFixed(1)}k
                                    </span>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </Section>
    );
}
