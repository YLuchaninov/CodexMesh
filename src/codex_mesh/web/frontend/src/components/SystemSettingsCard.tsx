
import { useState, useEffect, useMemo } from 'react';
import { api } from '../api/client';
import { SystemConfig } from '../api/types';
import { useProject } from '../api/context';
import { Section, Button, Input } from './ui';
import { Save, RefreshCw, AlertTriangle, Wand2 } from 'lucide-react';

// Fields that should be parsed as integers
const INT_FIELDS = new Set(['churn_days', 'churn_threshold', 'analysis_timeout']);

export default function SystemSettingsCard() {
    const { connect, project_path, status } = useProject();
    const [config, setConfig] = useState<SystemConfig | null>(null);
    const [initialConfig, setInitialConfig] = useState<SystemConfig | null>(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [tuning, setTuning] = useState(false);

    useEffect(() => {
        loadConfig();
    }, [status]);


    const loadConfig = async () => {
        setLoading(true);
        try {
            const res = await api.getSystemConfig();
            setConfig(res);
            setInitialConfig(JSON.parse(JSON.stringify(res)));
        } catch (e) {
            console.error("Failed to load config", e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async (shouldReindex = false) => {
        if (!config) return;
        setSaving(true);
        try {
            await api.setSystemConfig(config);

            if (shouldReindex && project_path) {
                // Trigger reindex if critical settings changed
                await connect(project_path, { force_reindex: true });
            }

            // Update initial config to new state
            setInitialConfig(JSON.parse(JSON.stringify(config)));
        } catch (e) {
            console.error("Failed to save config", e);
        } finally {
            setSaving(false);
        }
    };

    const handleAutotune = async () => {
        setTuning(true);
        try {
            const result = await api.autotuneHotspots({ apply: true });
            if (result.applied) {
                // Reload config to get new values
                await loadConfig();
            }
        } catch (e) {
            console.error("Auto-tune failed", e);
        } finally {
            setTuning(false);
        }
    };

    const isEmbeddingDirty = useMemo(() => {
        if (!config || !initialConfig) return false;
        return config.embedding.engine !== initialConfig.embedding.engine ||
            config.embedding.model !== initialConfig.embedding.model;
    }, [config, initialConfig]);

    const updateHotspot = (field: string, val: string) => {
        if (!config) return;
        const num = INT_FIELDS.has(field) ? parseInt(val || '0', 10) : parseFloat(val || '0');
        setConfig({
            ...config,
            hotspot: {
                ...config.hotspot,
                [field]: isNaN(num) ? 0 : num
            }
        });
    };

    const updateEmbedding = (field: string, val: string) => {
        if (!config) return;
        setConfig({
            ...config,
            embedding: {
                ...config.embedding,
                [field]: val
            }
        });
    }

    if (loading && !config) return <div className="p-4 text-slate-400">Loading system config...</div>;
    if (!config) return <div className="p-4 text-red-400">Failed to load configuration</div>;

    return (
        <Section title="System Settings">
            <div className="space-y-6">

                {/* Embeddings */}
                <div className="p-4 bg-bg/50 rounded-lg border border-border/50">
                    <h4 className="text-sm font-bold text-slate-200 mb-3 border-b border-border/30 pb-2">Embeddings Engine</h4>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-xs text-slate-400 uppercase font-semibold mb-1 block">Engine</label>
                            <Input
                                value={config.embedding.engine}
                                onChange={e => updateEmbedding('engine', e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="text-xs text-slate-400 uppercase font-semibold mb-1 block">Model</label>
                            <Input
                                value={config.embedding.model}
                                onChange={e => updateEmbedding('model', e.target.value)}
                            />
                        </div>
                    </div>
                </div>

                {/* Hotspots - Structural */}
                <div className="p-4 bg-bg/50 rounded-lg border border-border/50">
                    <h4 className="text-sm font-bold text-slate-200 mb-3 border-b border-border/30 pb-2">Hotspot Scoring Weights</h4>

                    {/* Row 1: Lint weights */}
                    <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-2">Lint Weights</p>
                    <div className="grid grid-cols-5 gap-3 mb-4">
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Error</label>
                            <Input type="number" value={config.hotspot.error_weight} onChange={e => updateHotspot('error_weight', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Warning</label>
                            <Input type="number" value={config.hotspot.warning_weight} onChange={e => updateHotspot('warning_weight', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">TODO</label>
                            <Input type="number" value={config.hotspot.todo_weight} onChange={e => updateHotspot('todo_weight', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">FIXME</label>
                            <Input type="number" value={config.hotspot.fixme_weight} onChange={e => updateHotspot('fixme_weight', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">HACK</label>
                            <Input type="number" value={config.hotspot.hack_weight} onChange={e => updateHotspot('hack_weight', e.target.value)} />
                        </div>
                    </div>

                    {/* Row 2: Graph & Churn */}
                    <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-2">Graph & Churn</p>
                    <div className="grid grid-cols-5 gap-3 mb-4">
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Import In</label>
                            <Input type="number" step="0.1" value={config.hotspot.import_in_weight} onChange={e => updateHotspot('import_in_weight', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Import Out</label>
                            <Input type="number" step="0.1" value={config.hotspot.import_out_weight} onChange={e => updateHotspot('import_out_weight', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Centrality</label>
                            <Input type="number" step="0.1" value={config.hotspot.centrality_weight} onChange={e => updateHotspot('centrality_weight', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Churn Wt</label>
                            <Input type="number" step="0.1" value={config.hotspot.churn_commit_weight} onChange={e => updateHotspot('churn_commit_weight', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Churn Days</label>
                            <Input type="number" value={config.hotspot.churn_days} onChange={e => updateHotspot('churn_days', e.target.value)} />
                        </div>
                    </div>

                    {/* Row 3: Thresholds */}
                    <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-2">Thresholds</p>
                    <div className="grid grid-cols-4 gap-3">
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Churn Min</label>
                            <Input type="number" value={config.hotspot.churn_threshold} onChange={e => updateHotspot('churn_threshold', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Hotspot Thr</label>
                            <Input type="number" step="0.5" value={config.hotspot.high_hotspot_threshold} onChange={e => updateHotspot('high_hotspot_threshold', e.target.value)} />
                        </div>
                        <div>
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 block">Timeout (s)</label>
                            <Input type="number" value={config.hotspot.analysis_timeout} onChange={e => updateHotspot('analysis_timeout', e.target.value)} />
                        </div>
                        <div className="flex items-end">
                            <Button
                                onClick={handleAutotune}
                                disabled={tuning}
                                className="w-full bg-purple-700 hover:bg-purple-600 border-purple-600 text-white"
                            >
                                <Wand2 size={14} className={tuning ? "animate-spin" : ""} />
                                {tuning ? "Tuning..." : "Auto-tune"}
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Storage Info (Read Only for now mostly) */}
                <div className="p-4 bg-slate-900/30 rounded-lg border border-border/50 opacity-70">
                    <h4 className="text-sm font-bold text-slate-200 mb-3 border-b border-border/30 pb-2">Storage (Read-Only)</h4>
                    <div className="text-xs font-mono text-slate-400 flex flex-col gap-1">
                        <div>Backend: <span className="text-slate-200">{config.storage.backend}</span></div>
                        <div>Vector DB: <span className="text-slate-200">{config.storage.vector_db}</span></div>
                        <div>Path: <span className="text-slate-200">{config.storage.path}</span></div>
                    </div>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                    {isEmbeddingDirty && (
                        <div className="flex items-center gap-2 text-amber-400 text-xs mr-auto bg-amber-950/30 px-3 py-1 rounded border border-amber-900/50">
                            <AlertTriangle size={12} />
                            <span>Changes require re-indexing</span>
                        </div>
                    )}
                    <Button className="bg-sidebar hover:bg-slate-700 border border-border" onClick={loadConfig}>
                        <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
                        Reload
                    </Button>
                    {isEmbeddingDirty ? (
                        <Button onClick={() => handleSave(true)} disabled={saving} className="bg-amber-600 hover:bg-amber-500 text-white border-amber-500">
                            <RefreshCw size={14} />
                            {saving ? "Re-indexing..." : "Save & Reindex"}
                        </Button>
                    ) : (
                        <Button onClick={() => handleSave(false)} disabled={saving}>
                            <Save size={14} />
                            {saving ? "Saving..." : "Save Config"}
                        </Button>
                    )}
                </div>

            </div>
        </Section>
    );
}

