import { useMemo, useState } from 'react';
import type { ToolMeta, OpenFileDetail } from '../api/types';
import { Card, CardBody, CardHeader, H2, SubTitle, Button } from './ui';
import { MermaidViewer } from './MermaidViewer';
import { RenderFileLinks, dispatchOpenFile } from './fileLinkify';
import { fixMermaidCode } from '../utils/mermaid';

interface ResultCardProps {
    tool: ToolMeta;
    payload: any;
    result: any;
    error?: any;
    onSendToChat?: (content: string) => void;
    onOpenFile?: (detail: OpenFileDetail) => void;
}

function stringify(obj: any): string {
    try {
        return JSON.stringify(obj, null, 2);
    } catch {
        return String(obj);
    }
}

function extractFileRefs(result: any): OpenFileDetail[] {
    const refs: Map<string, OpenFileDetail> = new Map();
    const walk = (x: any) => {
        if (!x || typeof x !== 'object') return;

        // Match various result shapes from extractors/analysis
        if (typeof x.file_path === 'string' && x.file_path) {
            const key = `${x.file_path}:${x.line || ''}`;
            refs.set(key, {
                path: x.file_path,
                start_line: x.line,
                end_line: x.line_end || x.line,
                source: 'tools'
            });
        } else if (typeof x.path === 'string' && x.path && (x.line || x.start_line)) {
            const key = `${x.path}:${x.line || x.start_line || ''}`;
            refs.set(key, {
                path: x.path,
                start_line: x.line || x.start_line,
                end_line: x.line_end || x.end_line || x.line || x.start_line,
                source: 'tools'
            });
        } else if (typeof x.path === 'string' && x.path && x.path.includes('.')) {
            // Simple path match
            if (!refs.has(x.path)) {
                refs.set(x.path, { path: x.path, source: 'tools' });
            }
        }

        for (const k of Object.keys(x)) walk(x[k]);
    };
    walk(result);
    return Array.from(refs.values()).slice(0, 50);
}

export function ResultCard({
    tool,
    payload,
    result,
    error,
    onSendToChat,
    onOpenFile,
}: ResultCardProps) {
    const [tab, setTab] = useState<'pretty' | 'raw'>('pretty');
    const files = useMemo(() => extractFileRefs(result), [result]);

    const summary = useMemo(() => {
        if (error) return `Error: ${error.message ?? 'unknown'}`;
        if (typeof result === 'string') return result.slice(0, 50000);
        if (result?.output) return String(result.output).slice(0, 50000);
        if (result?.map) return String(result.map).slice(0, 50000);
        if (result?.report?.length) return `Hotspots: ${result.report.length}`;
        if (result?.matches?.length) return `Matches: ${result.matches.length}`;
        if (result?.results?.length) return `Results: ${result.results.length}`;
        if (result?.nodes?.length || result?.edges?.length)
            return `Graph: ${result.nodes?.length ?? 0} nodes, ${result.edges?.length ?? 0} edges`;
        return 'OK';
    }, [result, error]);

    const raw = useMemo(
        () => stringify({ tool: tool.id, payload, result, error }),
        [tool, payload, result, error]
    );

    return (
        <Card className="hover:border-slate-700 transition-colors">
            <CardHeader className="flex items-start justify-between gap-3 bg-slate-100/5">
                <div>
                    <H2>{tool.title}</H2>
                    <SubTitle>
                        {tool.category} · {tool.method} {tool.endpoint}
                    </SubTitle>
                </div>
                <div className="flex gap-2">
                    <Button
                        className="bg-slate-700 hover:bg-slate-600 px-3 py-1.5"
                        onClick={() => navigator.clipboard.writeText(raw)}
                    >
                        Copy JSON
                    </Button>
                    {onSendToChat && (
                        <Button
                            className="bg-accent hover:bg-blue-600 px-3 py-1.5"
                            onClick={() => onSendToChat(summary)}
                        >
                            Send to Chat
                        </Button>
                    )}
                </div>
            </CardHeader>

            <CardBody className="p-4">
                <div className="flex gap-2 text-xs mb-4">
                    <button
                        className={`px-3 py-1.5 rounded-lg font-medium transition-all ${tab === 'pretty'
                            ? 'bg-accent text-white shadow-lg shadow-accent/20'
                            : 'bg-slate-800 text-slate-400 hover:text-white'
                            }`}
                        onClick={() => setTab('pretty')}
                    >
                        Interactive Result
                    </button>
                    <button
                        className={`px-3 py-1.5 rounded-lg font-medium transition-all ${tab === 'raw'
                            ? 'bg-accent text-white shadow-lg shadow-accent/20'
                            : 'bg-slate-800 text-slate-400 hover:text-white'
                            }`}
                        onClick={() => setTab('raw')}
                    >
                        Raw JSON
                    </button>
                </div>

                {tab === 'pretty' ? (
                    <div className="flex flex-col gap-4">
                        {(result?.mermaid || (typeof result === 'string' && result.includes('graph TD'))) && (
                            <div className="bg-white/5 rounded-lg p-2 border border-border/30">
                                <MermaidViewer chart={fixMermaidCode(result.mermaid || result)} />
                            </div>
                        )}
                        <div className="bg-bg/50 p-4 rounded-lg border border-border/50 text-sm leading-relaxed whitespace-pre-wrap font-sans text-slate-300 max-h-[600px] overflow-y-auto custom-scrollbar">
                            <RenderFileLinks
                                text={summary}
                                onOpen={(ref) => onOpenFile ? onOpenFile(ref) : dispatchOpenFile(ref)}
                            />
                        </div>
                    </div>
                ) : (
                    <pre className="text-[11px] overflow-auto max-h-[500px] bg-slate-950 text-emerald-400/90 p-4 rounded-lg border border-border font-mono leading-relaxed custom-scrollbar">
                        {raw}
                    </pre>
                )}

                {files.length > 0 && (
                    <div className="mt-5 pt-4 border-t border-border/40">
                        <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block mb-2 opacity-70">Referenced locations</label>
                        <div className="flex flex-wrap gap-2">
                            {files.map((ref, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => onOpenFile ? onOpenFile(ref) : dispatchOpenFile(ref)}
                                    className="bg-slate-900 border border-border/60 hover:border-accent hover:text-accent text-[10px] py-1 px-3 rounded-full transition-all active:scale-95 group font-mono"
                                >
                                    <span className="opacity-70 group-hover:opacity-100">{ref.path}</span>
                                    {ref.start_line && (
                                        <span className="text-accent ml-1 opacity-80">:{ref.start_line}</span>
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </CardBody>
        </Card>
    );
}
