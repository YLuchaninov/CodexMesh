/**
 * ToolsCard component.
 *
 * Main interface for running tools and viewing results.
 */
import { useEffect, useState } from 'react';
import type { ToolMeta, ToolsRegistryResponse, RunRecord } from '../api/types';
import { CommandPalette } from './CommandPalette';
import { ToolRunnerModal } from './ToolRunnerModal';
import { ResultCard } from './ResultCard';
import { Card, CardHeader, H2, SubTitle, Button } from './ui';

export default function ToolsCard() {
    const [tools, setTools] = useState<ToolMeta[]>([]);
    const [selectedTool, setSelectedTool] = useState<ToolMeta | null>(null);
    const [openRunner, setOpenRunner] = useState(false);
    const [paletteOpen, setPaletteOpen] = useState(false);
    const [runs, setRuns] = useState<RunRecord[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const res = await fetch('/api/v1/tools');
                const data: ToolsRegistryResponse = await res.json();
                setTools(data.tools);
            } catch (e) {
                console.error('Failed to load tools', e);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    const onSelectTool = (t: ToolMeta) => {
        setSelectedTool(t);
        setOpenRunner(true);
    };

    const onResult = (tool: ToolMeta, payload: any, result: any, error?: any) => {
        setRuns((prev) => [{ tool, payload, result, error, ts: Date.now() }, ...prev].slice(0, 30));
    };

    // Quick actions - common tools
    const quickActions = ['analysis.repomap', 'analysis.hotspots', 'analysis.semantic', 'graph.entrypoints'];

    return (
        <div className="h-full flex flex-col">
            {/* Command Palette (global Ctrl+K) */}
            <CommandPalette
                tools={tools}
                open={paletteOpen}
                onOpenChange={setPaletteOpen}
                onSelect={onSelectTool}
            />

            {/* Tool Runner Modal */}
            <ToolRunnerModal
                tool={selectedTool}
                open={openRunner}
                onClose={() => setOpenRunner(false)}
                onResult={onResult}
            />

            {/* Header */}
            <Card className="shrink-0 mb-4">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <div>
                            <H2>Tools</H2>
                            <SubTitle>Press Ctrl+K or use Search button</SubTitle>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                className="bg-slate-600"
                                onClick={() => setPaletteOpen(true)}
                            >
                                Search...
                            </Button>
                            {loading ? (
                                <span className="text-sm text-slate-400">Loading...</span>
                            ) : (
                                quickActions.map((id) => {
                                    const t = tools.find((x) => x.id === id);
                                    if (!t) return null;
                                    return (
                                        <Button
                                            key={id}
                                            onClick={() => onSelectTool(t)}
                                        >
                                            {t.title}
                                        </Button>
                                    );
                                })
                            )}
                        </div>
                    </div>
                </CardHeader>
            </Card>

            {/* Results */}
            <div className="flex-1 overflow-y-auto space-y-3">
                {runs.length === 0 ? (
                    <div className="text-center text-slate-400 py-12">
                        <p className="text-lg mb-2">No results yet</p>
                        <p className="text-sm">Press Ctrl+K or click a quick action above to run a tool</p>
                    </div>
                ) : (
                    runs.map((r) => (
                        <ResultCard
                            key={r.ts}
                            tool={r.tool}
                            payload={r.payload}
                            result={r.result}
                            error={r.error}
                            onSendToChat={(content) => {
                                // Dispatched to layout for handling
                                window.dispatchEvent(new CustomEvent('codex-mesh:chat-input', { detail: { content } }));
                            }}
                            onOpenFile={(detail) => {
                                // Dispatched to layout for handling
                                window.dispatchEvent(new CustomEvent('codex-mesh:open-file', { detail }));
                            }}
                        />
                    ))
                )}
            </div>
        </div>
    );
}
