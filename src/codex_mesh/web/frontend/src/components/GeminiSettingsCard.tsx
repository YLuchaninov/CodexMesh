import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Section, Button } from './ui';
import { AlertCircle, CheckCircle } from 'lucide-react';

export default function GeminiSettingsCard() {
    const [key, setKey] = useState('');
    const [model, setModel] = useState('gemini-2.5-flash');
    const [temperature, setTemperature] = useState(0.2);
    const [status, setStatus] = useState<{ msg: string, type: 'success' | 'error' | 'info' } | null>(null);

    useEffect(() => {
        setKey(localStorage.getItem('gemini_api_key') || '');
        setModel(localStorage.getItem('gemini_model') || 'gemini-2.5-flash');
        setTemperature(parseFloat(localStorage.getItem('gemini_temp') || '0.2'));
        refreshServer();
    }, []);

    const refreshServer = async () => {
        try {
            const config = await api.getGeminiConfig();
            if (!config.has_key) {
                const localKey = localStorage.getItem('gemini_api_key');
                if (localKey) {
                    await api.setGeminiConfig({
                        api_key: localKey,
                        model: localStorage.getItem('gemini_model') || model,
                        temperature: parseFloat(localStorage.getItem('gemini_temp') || String(temperature))
                    });
                    setStatus({ msg: "Restored key to server", type: 'success' });
                    setTimeout(() => setStatus(null), 3000);
                } else {
                    setStatus({ msg: "Not configured on server", type: 'info' });
                }
            }
        } catch (e) {
            // ignore
        }
    };

    const handleSave = async () => {
        localStorage.setItem('gemini_api_key', key);
        localStorage.setItem('gemini_model', model);
        localStorage.setItem('gemini_temp', String(temperature));

        try {
            await api.setGeminiConfig({ api_key: key, model, temperature });
            setStatus({ msg: "Settings saved", type: 'success' });
            setTimeout(() => setStatus(null), 3000);
        } catch (e) {
            console.error(e);
            setStatus({ msg: "Failed to save settings", type: 'error' });
        }
    };

    const handleTest = async () => {
        setStatus({ msg: "Testing connection...", type: 'info' });
        try {
            const res = await api.testGemini();
            if (res.ok) {
                setStatus({ msg: `OK (${res.model}) ${res.latency_ms}ms`, type: 'success' });
            } else {
                setStatus({ msg: `Test failed: ${res.error}`, type: 'error' });
            }
        } catch (e) {
            setStatus({ msg: "Test request failed", type: 'error' });
        }
    };

    return (
        <Section title="AI Settings">
            <div className="flex gap-4">
                <div className="flex-1">
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5 ml-1">API Key</label>
                    <input
                        type="password"
                        value={key}
                        onChange={e => setKey(e.target.value)}
                        placeholder="••••••••••••••••"
                        className="w-full bg-bg border border-border rounded-lg px-3 py-2.5 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/50 placeholder:text-slate-600 transition-all"
                    />
                </div>
                <div className="w-1/2">
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5 ml-1">Model</label>
                    <div className="relative">
                        <select
                            value={model}
                            onChange={e => setModel(e.target.value)}
                            className="w-full bg-bg border border-border rounded-lg px-3 py-2.5 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/50 appearance-none cursor-pointer transition-all"
                        >
                            <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                            <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                            <option value="gemini-pro">gemini-pro</option>
                            <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                        </select>
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                        </div>
                    </div>
                </div>
            </div>

            <div className="mt-4">
                <div className="flex justify-between mb-2 px-1">
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Temperature</label>
                    <span className="text-xs font-mono text-accent">{temperature}</span>
                </div>
                <div className="flex items-center gap-6">
                    <input
                        type="range"
                        min="0" max="1"
                        step="0.1"
                        value={temperature}
                        onChange={e => setTemperature(parseFloat(e.target.value))}
                        className="flex-1 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-accent"
                    />
                    <div className="flex gap-3">
                        <Button className="min-w-[80px]" onClick={handleSave}>Save</Button>
                        <Button className="bg-transparent border border-accent/50 text-accent hover:bg-accent/10 min-w-[80px]" onClick={handleTest}>Test</Button>
                    </div>
                </div>
                {status && (
                    <div className={`mt-2 text-[10px] flex items-center gap-1.5 ${status.type === 'error' ? 'text-red-400' : status.type === 'success' ? 'text-emerald-400' : 'text-slate-400'}`}>
                        {status.type === 'success' ? <CheckCircle size={10} /> : <AlertCircle size={10} />}
                        {status.msg}
                    </div>
                )}
            </div>
        </Section>
    );
}
