
import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { LLMProvider, LLMProfile } from '../api/types';
import { Section, Button, Input } from './ui';
import { AlertCircle, CheckCircle } from 'lucide-react';

export default function LLMSettingsCard() {
    // We assume 'profiles' come from SystemConfig
    // But for MVP we might just edit the "Active" settings or a specific profile
    // The backend `LLMFactory` uses profiles.
    // Let's implement a simple view: Select Active Profile, and Edit its details.

    const [provider, setProvider] = useState<LLMProvider>('google');
    const [model, setModel] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [apiBase, setApiBase] = useState('');
    const [temperature, setTemperature] = useState(0.2);

    // Status
    const [status, setStatus] = useState<{ msg: string, type: 'success' | 'error' | 'info' } | null>(null);

    // Initial Load - we reuse legacy Gemini storage for Google, but new logic for others?
    // Actually, let's load from system config if possible, or local storage for secrets
    useEffect(() => {
        const savedProvider = localStorage.getItem('llm_provider') as LLMProvider || 'google';
        setProvider(savedProvider);
        loadProviderSettings(savedProvider);
    }, []);

    const loadProviderSettings = (p: LLMProvider) => {
        setApiKey(localStorage.getItem(`${p}_api_key`) || '');
        setModel(localStorage.getItem(`${p}_model`) || defaultModel(p));
        setApiBase(localStorage.getItem(`${p}_api_base`) || defaultBase(p));
    };

    const defaultModel = (p: LLMProvider) => {
        switch (p) {
            case 'google': return 'gemini-2.5-flash';
            case 'anthropic': return 'claude-3-opus-20240229';
            case 'ollama': return 'mistral';
            case 'openai': return 'gpt-4o';
            case 'mistral': return 'mistral-large-latest';
        }
    };

    const defaultBase = (p: LLMProvider) => {
        if (p === 'ollama') return 'http://localhost:11434';
        return '';
    }

    const handleProviderChange = (p: LLMProvider) => {
        setProvider(p);
        loadProviderSettings(p);
        localStorage.setItem('llm_provider', p);
    };

    const handleSave = async () => {
        // Save to local storage for persistence
        localStorage.setItem(`${provider}_api_key`, apiKey);
        localStorage.setItem(`${provider}_model`, model);
        localStorage.setItem(`${provider}_api_base`, apiBase);

        // Also update backend system config (runtime)
        // We construct a profile object to push to backend
        // Note: Backend might need a specific endpoint to set "Active LLM" 
        // OR we just update the specific named profile in config.

        setStatus({ msg: "Settings saved locally", type: 'success' });

        setStatus({ msg: "Settings saved locally", type: 'success' });

        // Push to backend /api/v1/system/config
        // Construct partial update for SystemConfig
        // We need to support updating the "active" profile or all profiles.
        // For now, let's just assume we are configuring the tool to work with this provider.
        // The backend `routes_v1` config update relies on us sending a `profiles` dict.

        try {
            const profileUpdate: LLMProfile = {
                name: "custom_ui", // We might need to override the default profile used by factory
                provider,
                model,
                api_key: apiKey, // Backend doesn't persist this usually, but in-memory config might need it if we want it to work immediately
                api_base: apiBase,
                temperature
            };

            // To make this work with existing routing.py, we might need to update the default profile 
            // OR update the environment variables in memory? Config update seems best.
            // But routing.py `get_profile` looks at `custom_profiles`.

            await api.setSystemConfig({
                profiles: {
                    "ui_active": profileUpdate
                    // We might need to tell backend to USE this profile for global actions
                }
            });
            setStatus({ msg: "Settings saved & synced to backend", type: 'success' });
        } catch (e) {
            console.error(e);
            setStatus({ msg: "Saved locally but failed to sync backend", type: 'error' });
        }

        setTimeout(() => setStatus(null), 3000);
    };

    return (
        <Section title="LLM Configuration">
            <div className="grid grid-cols-1 gap-4">
                {/* Provider Selection */}
                <div>
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5 ml-1">Provider</label>
                    <div className="flex gap-2">
                        {(['google', 'anthropic', 'ollama', 'openai', 'mistral'] as LLMProvider[]).map(p => (
                            <button
                                key={p}
                                onClick={() => handleProviderChange(p)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-all ${provider === p
                                    ? 'bg-accent text-white border-accent'
                                    : 'bg-transparent border-border text-slate-400 hover:border-slate-500'
                                    }`}
                            >
                                {p.charAt(0).toUpperCase() + p.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Dynamic Fields */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2 md:col-span-1">
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5 ml-1">Model Name</label>
                        <Input
                            value={model}
                            onChange={e => setModel(e.target.value)}
                            placeholder={defaultModel(provider)}
                        />
                    </div>

                    {provider === 'ollama' ? (
                        <div className="col-span-2 md:col-span-1">
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5 ml-1">API Base URL</label>
                            <Input
                                value={apiBase}
                                onChange={e => setApiBase(e.target.value)}
                                placeholder="http://localhost:11434"
                            />
                        </div>
                    ) : (
                        <div className="col-span-2 md:col-span-1">
                            <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5 ml-1">API Key</label>
                            <Input
                                type="password"
                                value={apiKey}
                                onChange={e => setApiKey(e.target.value)}
                                placeholder="sk-..."
                            />
                        </div>
                    )}
                </div>

                <div>
                    <div className="flex justify-between mb-2 px-1">
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Temperature</label>
                        <span className="text-xs font-mono text-accent">{temperature}</span>
                    </div>
                    <input
                        type="range"
                        min="0" max="1"
                        step="0.1"
                        value={temperature}
                        onChange={e => setTemperature(parseFloat(e.target.value))}
                        className="w-full h-1.5 bg-sidebar rounded-lg appearance-none cursor-pointer accent-accent"
                    />
                </div>

                <div className="flex items-center justify-between mt-2">
                    {status ? (
                        <div className={`text-xs flex items-center gap-1.5 ${status.type === 'error' ? 'text-red-400' : 'text-emerald-400'}`}>
                            {status.type === 'success' ? <CheckCircle size={12} /> : <AlertCircle size={12} />}
                            {status.msg}
                        </div>
                    ) : <div></div>}

                    <Button onClick={handleSave} className="min-w-[100px]">
                        Save Settings
                    </Button>
                </div>
            </div>
        </Section>
    );
}
