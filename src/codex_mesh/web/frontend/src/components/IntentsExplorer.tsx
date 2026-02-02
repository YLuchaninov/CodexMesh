
import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { IntentItem, IntentExecuteResponse } from '../api/types';
import { Section, Button, Input } from './ui';
import { Play, Activity, ChevronRight, Box } from 'lucide-react';
import { MermaidViewer } from './MermaidViewer';

export default function IntentsExplorer() {
    const [intents, setIntents] = useState<IntentItem[]>([]);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [executing, setExecuting] = useState(false);
    const [result, setResult] = useState<IntentExecuteResponse | null>(null);
    const [inputs, setInputs] = useState<Record<string, string>>({});
    const [activeTab, setActiveTab] = useState<'output' | 'trace' | 'logs'>('output');

    useEffect(() => {
        loadIntents();
    }, []);

    const loadIntents = async () => {
        setLoading(true);
        try {
            const res = await api.getIntents();
            setIntents(res.intents);
        } catch (e) {
            console.error("Failed to load intents", e);
        } finally {
            setLoading(false);
        }
    };

    const handleSelect = (id: string) => {
        setSelectedId(id);
        setResult(null);
        setInputs({});
    };

    const handleExecute = async () => {
        if (!selectedId) return;
        setExecuting(true);
        setResult(null);
        try {
            // Convert inputs if necessary (currently just passing strings)
            // Ideally we parse based on slot types
            const res = await api.executeIntent(selectedId, inputs);
            setResult(res);
        } catch (e) {
            console.error(e);
            alert("Execution failed: " + e);
        } finally {
            setExecuting(false);
        }
    };

    const selectedIntent = intents.find(i => i.id === selectedId);

    return (
        <div className="flex h-full gap-4">
            {/* List */}
            <div className="w-1/3 min-w-[300px] flex flex-col gap-2 overflow-y-auto pr-2">
                <h3 className="font-bold text-lg text-slate-100 mb-2">My Intents</h3>

                {loading && <div className="text-sm text-slate-400">Loading...</div>}

                {intents.map(intent => (
                    <div
                        key={intent.id}
                        onClick={() => handleSelect(intent.id)}
                        className={`p-3 rounded-lg border cursor-pointer transition-all ${selectedId === intent.id
                            ? 'bg-accent/10 border-accent'
                            : 'bg-sidebar border-border hover:border-slate-600'
                            }`}
                    >
                        <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold text-slate-200 text-sm">{intent.title}</span>
                            {selectedId === intent.id && <ChevronRight size={14} className="text-accent" />}
                        </div>
                        <p className="text-xs text-slate-400 line-clamp-2">{intent.description}</p>
                        <div className="flex gap-2 mt-2">
                            {intent.tags.map(t => (
                                <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-bg text-slate-400 border border-border">
                                    {t}
                                </span>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {/* Detail / Runner */}
            <div className="flex-1 flex flex-col overflow-hidden bg-sidebar rounded-lg border border-border">
                {selectedIntent ? (
                    <div className="flex flex-col h-full">
                        <div className="p-4 border-b border-border">
                            <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
                                <Activity size={20} className="text-accent" />
                                {selectedIntent.title}
                            </h2>
                            <p className="text-sm text-slate-400">{selectedIntent.description}</p>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
                            {/* Slots Inputs */}
                            {selectedIntent.slots && Object.keys(selectedIntent.slots).length > 0 && (
                                <Section title="Inputs">
                                    <div className="grid grid-cols-1 gap-3">
                                        {Object.entries(selectedIntent.slots).map(([key, desc]) => (
                                            <div key={key}>
                                                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">
                                                    {key} <span className="text-slate-600 font-normal normal-case">- {String(desc)}</span>
                                                </label>
                                                <Input
                                                    value={inputs[key] || ''}
                                                    onChange={e => setInputs({ ...inputs, [key]: e.target.value })}
                                                    placeholder={`Enter value for ${key}`}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                </Section>
                            )}

                            {/* Example */}
                            {selectedIntent.examples && selectedIntent.examples.length > 0 && (
                                <div className="p-3 bg-bg/50 rounded border border-border/50 text-xs text-slate-400 font-mono whitespace-pre-wrap">
                                    <div className="text-[10px] uppercase font-bold text-slate-500 mb-1">Example</div>
                                    {selectedIntent.examples[0]}
                                </div>
                            )}

                            {/* Actions */}
                            <div>
                                <Button
                                    onClick={handleExecute}
                                    disabled={executing}
                                    className="w-full py-3 text-base"
                                >
                                    <Play size={16} className={executing ? "animate-spin" : ""} />
                                    {executing ? "Running Workflow..." : "Execute Intent"}
                                </Button>
                            </div>

                            {/* Result Area */}
                            {result && (
                                <div className="mt-4 flex flex-col gap-2 flex-1">
                                    <div className="flex items-center gap-2 border-b border-border">
                                        <button
                                            onClick={() => setActiveTab('output')}
                                            className={`px-3 py-2 text-xs font-bold border-b-2 transition-colors ${activeTab === 'output' ? 'border-accent text-accent' : 'border-transparent text-slate-500'}`}
                                        >
                                            Output
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('trace')}
                                            className={`px-3 py-2 text-xs font-bold border-b-2 transition-colors ${activeTab === 'trace' ? 'border-accent text-accent' : 'border-transparent text-slate-500'}`}
                                        >
                                            Trace ({result.stats.steps})
                                        </button>
                                        <button
                                            onClick={() => setActiveTab('logs')}
                                            className={`px-3 py-2 text-xs font-bold border-b-2 transition-colors ${activeTab === 'logs' ? 'border-accent text-accent' : 'border-transparent text-slate-500'}`}
                                        >
                                            Logs
                                        </button>
                                    </div>

                                    <div className="flex-1 bg-bg rounded p-4 font-mono text-xs overflow-auto border border-border/50">
                                        {activeTab === 'output' && (
                                            <div className="flex flex-col gap-4">
                                                {result.output?.includes('graph TD') && (
                                                    <MermaidViewer chart={result.output} />
                                                )}
                                                <div className="whitespace-pre-wrap text-slate-300">{result.output || "No text output."}</div>
                                            </div>
                                        )}
                                        {activeTab === 'trace' && (
                                            <div className="flex flex-col gap-4">
                                                {result.trace.map((step: any, i: number) => (
                                                    <div key={i} className="border-l-2 border-slate-700 pl-3">
                                                        <div className="text-accent font-bold mb-1 flex justify-between">
                                                            {step.tool}
                                                            <span className="text-slate-600">{step.duration_ms}ms</span>
                                                        </div>
                                                        <div className="text-slate-500 mb-1">Args: {JSON.stringify(step.input)}</div>
                                                        <div className="text-slate-300 bg-bg/50 p-2 rounded">{step.output_preview}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {activeTab === 'logs' && (
                                            <div className="flex flex-col gap-1 text-slate-400">
                                                {result.logs.map((log, i) => (
                                                    <div key={i}>{log}</div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="flex items-center justify-center h-full text-slate-500 flex-col gap-2">
                        <Box size={48} className="opacity-20" />
                        <p>Select an intent to view details</p>
                    </div>
                )}
            </div>
        </div>
    );
}
