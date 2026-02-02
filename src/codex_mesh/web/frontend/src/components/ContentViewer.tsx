import { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';

interface Props {
    selectedFile: string | null;
    selectedSpan?: { start_line: number; end_line: number } | null;
}

export default function ContentViewer({ selectedFile, selectedSpan }: Props) {
    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!selectedFile) return;

        const load = async () => {
            setLoading(true);
            try {
                const res = await api.readFile(selectedFile);
                setContent(res.content);
            } catch (e) {
                setContent(`Error reading file: ${e}`);
            } finally {
                setLoading(false);
            }
        };

        load();
    }, [selectedFile]);

    useEffect(() => {
        if (selectedSpan && content) {
            // Need to wait for DOM to update
            setTimeout(() => {
                const line = document.getElementById(`line-${selectedSpan.start_line}`);
                if (line) {
                    line.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 100);
        }
    }, [selectedSpan, content]);

    const lines = content.split('\n');

    return (
        <div className="bg-sidebar border border-border rounded-lg flex flex-col h-full overflow-hidden">
            {/* Header */}
            <div className="px-4 py-2 border-b border-border flex items-center justify-between bg-sidebar/50 shrink-0">
                <div className="flex items-center gap-2">
                    <h3 className="font-bold text-sm text-slate-200">Content Viewer</h3>
                    {selectedFile && (
                        <span className="text-[10px] font-mono text-slate-500 bg-slate-100/5 px-2 py-0.5 rounded">
                            {selectedFile}
                        </span>
                    )}
                </div>
            </div>

            {/* Content Area */}
            <div
                ref={scrollRef}
                className="flex-1 bg-[#1e1e1e] overflow-auto font-mono text-xs relative custom-scrollbar"
            >
                {selectedFile ? (
                    <div className="py-4 h-full">
                        {loading ? (
                            <div className="flex items-center justify-center h-full text-slate-500">
                                <span>Loading source...</span>
                            </div>
                        ) : (
                            <div className="flex flex-col min-w-max">
                                {lines.map((line, i) => {
                                    const lineNum = i + 1;
                                    const isHighlighted = selectedSpan && lineNum >= selectedSpan.start_line && lineNum <= selectedSpan.end_line;

                                    return (
                                        <div
                                            key={i}
                                            className={`flex group transition-colors ${isHighlighted
                                                    ? 'bg-accent/20 border-l-4 border-accent -ml-1 pl-1'
                                                    : 'border-l-4 border-transparent hover:bg-white/5'
                                                }`}
                                            id={`line-${lineNum}`}
                                        >
                                            <span className="w-12 text-slate-600 text-right pr-3 select-none group-hover:text-slate-400 shrink-0 font-mono text-[10px] py-0.5">
                                                {lineNum}
                                            </span>
                                            <span className={`block whitespace-pre pr-4 py-0.5 ${isHighlighted ? 'text-white' : 'text-slate-300'}`}>
                                                {line || ' '}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-4">
                        <div className="w-16 h-16 rounded-full bg-slate-100/5 flex items-center justify-center">
                            <span className="text-2xl opacity-20">?</span>
                        </div>
                        <span className="text-sm opacity-50">Select a file to view content</span>
                    </div>
                )}
            </div>
        </div>
    );
}
