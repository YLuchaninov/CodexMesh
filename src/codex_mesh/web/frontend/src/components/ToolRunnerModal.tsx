/**
 * ToolRunnerModal component.
 *
 * Universal modal for running any tool from the registry.
 */
import { useEffect, useMemo, useState } from 'react';
import type { ToolMeta, ToolFormField } from '../api/types';
import { buildPayload } from '../api/payload';
import { Card, CardBody, CardHeader, H2, SubTitle, Button } from './ui';

interface ToolRunnerModalProps {
    tool: ToolMeta | null;
    open: boolean;
    onClose: () => void;
    onResult: (tool: ToolMeta, payload: any, result: any, error?: any) => void;
}

function defaultValues(fields: ToolFormField[]): Record<string, any> {
    const v: Record<string, any> = {};
    for (const f of fields) {
        v[f.name] = f.default ?? (f.type === 'boolean' ? false : '');
    }
    return v;
}

export function ToolRunnerModal({ tool, open, onClose, onResult }: ToolRunnerModalProps) {
    const fields = tool?.ui?.form ?? [];
    const [values, setValues] = useState<Record<string, any>>({});
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        if (!open || !tool) return;
        setValues(defaultValues(fields));
    }, [open, tool, fields]);

    const payloadPreview = useMemo(() => {
        try {
            return JSON.stringify(buildPayload(fields, values), null, 2);
        } catch {
            return '{}';
        }
    }, [fields, values]);

    if (!open || !tool) return null;

    const onChange = (name: string, value: any) =>
        setValues((prev) => ({ ...prev, [name]: value }));

    const run = async () => {
        const payload = buildPayload(fields, values);
        setBusy(true);
        try {
            const opts: RequestInit = {
                method: tool.method,
                headers: tool.method === 'POST' ? { 'Content-Type': 'application/json' } : undefined,
                body: tool.method === 'POST' ? JSON.stringify(payload) : undefined,
            };
            const res = await fetch(tool.endpoint, opts);
            const data = await res.json();
            if (!res.ok) {
                throw { status: res.status, message: data?.error?.message ?? 'Request failed' };
            }
            onResult(tool, payload, data);
            onClose();
        } catch (e: any) {
            onResult(tool, payload, null, e);
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50">
            <Card className="w-full max-w-3xl">
                <CardHeader className="flex justify-between items-start border-b pb-3">
                    <div>
                        <H2>{tool.title}</H2>
                        <SubTitle>
                            {tool.method} {tool.endpoint}
                        </SubTitle>
                    </div>
                    <Button onClick={onClose}>Close</Button>
                </CardHeader>

                <CardBody className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-4">
                        {fields.length === 0 ? (
                            <p className="text-sm text-slate-400 italic">No parameters required</p>
                        ) : (
                            fields.map((f) => (
                                <div key={f.name}>
                                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 block">
                                        {f.name}
                                    </label>
                                    {f.type === 'select' ? (
                                        <div className="relative">
                                            <select
                                                className="w-full bg-bg border border-border rounded-lg p-2.5 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/50 appearance-none cursor-pointer transition-all"
                                                value={values[f.name] ?? ''}
                                                onChange={(e) => onChange(f.name, e.target.value)}
                                            >
                                                {(f.options ?? []).map((opt) => (
                                                    <option key={String(opt)} value={opt}>
                                                        {String(opt)}
                                                    </option>
                                                ))}
                                            </select>
                                            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                                            </div>
                                        </div>
                                    ) : f.type === 'boolean' ? (
                                        <label className="flex items-center gap-3 text-sm text-slate-200 cursor-pointer group">
                                            <input
                                                type="checkbox"
                                                className="w-4 h-4 rounded border-border bg-bg text-accent focus:ring-accent cursor-pointer"
                                                checked={Boolean(values[f.name])}
                                                onChange={(e) => onChange(f.name, e.target.checked)}
                                            />
                                            <span className="group-hover:text-white transition-colors">{f.placeholder ?? ''}</span>
                                        </label>
                                    ) : (
                                        <input
                                            className="w-full bg-bg border border-border rounded-lg p-2.5 text-sm text-text placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-accent/50 transition-all"
                                            type={f.type === 'number' ? 'number' : 'text'}
                                            placeholder={f.placeholder ?? ''}
                                            value={values[f.name] ?? ''}
                                            onChange={(e) => onChange(f.name, e.target.value)}
                                        />
                                    )}
                                </div>
                            ))
                        )}
                    </div>

                    <div className="flex flex-col h-full">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 block">
                            Payload preview
                        </label>
                        <div className="flex-1 min-h-[200px] relative">
                            <pre className="absolute inset-0 text-xs overflow-auto bg-slate-900 text-emerald-400 p-4 rounded-lg border border-border font-mono leading-relaxed shadow-inner">
                                {payloadPreview}
                            </pre>
                        </div>
                    </div>
                </CardBody>

                <div className="p-6 bg-slate-900/50 border-t border-border flex justify-end gap-3 rounded-b-lg">
                    <Button
                        onClick={onClose}
                        disabled={busy}
                        className="bg-transparent border border-border hover:bg-white/5 text-slate-300"
                    >
                        Cancel
                    </Button>
                    <Button onClick={run} disabled={busy} className="min-w-[100px]">
                        {busy ? 'Running...' : 'Execute Tool'}
                    </Button>
                </div>
            </Card>
        </div>
    );
}
