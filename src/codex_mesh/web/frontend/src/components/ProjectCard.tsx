import { useState, useEffect } from 'react';
import { useProject } from '../api/context';
import { Section } from './ui';
import { CheckCircle2, Loader2, Video, AlertCircle, Folder, Plug } from 'lucide-react';

export default function ProjectCard() {
    const { status, progress, project_path, connect } = useProject();
    const [path, setPath] = useState(project_path || '');
    const [forceReindex, setForceReindex] = useState(false);

    useEffect(() => {
        if (project_path) setPath(project_path);
    }, [project_path]);

    const handleConnect = () => {
        if (path) {
            connect(path, { force_reindex: forceReindex });
        }
    };

    const StatusBadge = () => {
        const colors = {
            IDLE: 'bg-slate-700 text-slate-400',
            LOADING: 'bg-amber-500/20 text-amber-500',
            READY: 'bg-emerald-500/20 text-emerald-500',
            ERROR: 'bg-red-500/20 text-red-500'
        };

        const icons = {
            IDLE: Video,
            LOADING: Loader2,
            READY: CheckCircle2,
            ERROR: AlertCircle
        };

        const Icon = icons[status] || Video;

        return (
            <div className={`px-2 py-1 rounded text-xs font-bold flex items-center gap-1 border border-transparent ${colors[status]}`}>
                <Icon size={12} className={status === 'LOADING' ? 'animate-spin' : ''} />
                {status}
            </div>
        );
    };

    return (
        <Section title="Project">
            <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2 bg-sidebar border border-border rounded p-1 pl-2">
                    <Folder size={16} className="text-slate-400" />
                    <input
                        value={path}
                        onChange={(e) => setPath(e.target.value)}
                        placeholder="/path/to/project"
                        className="bg-transparent border-none text-sm text-slate-300 focus:outline-none flex-1 w-full"
                        onKeyDown={(e) => e.key === 'Enter' && handleConnect()}
                    />
                    <StatusBadge />
                </div>

                <div className="flex justify-between items-center px-1">
                    <label className="flex items-center gap-2 text-[10px] text-slate-400 cursor-pointer hover:text-slate-200 transition-colors">
                        <input
                            type="checkbox"
                            checked={forceReindex}
                            onChange={e => setForceReindex(e.target.checked)}
                            className="w-3 h-3 bg-transparent border-border rounded"
                        />
                        Force Reindex
                    </label>
                    <button
                        onClick={handleConnect}
                        className="text-[10px] text-accent hover:text-white flex items-center gap-1 font-bold"
                        disabled={status === 'LOADING'}
                    >
                        <Plug size={10} /> {status === 'READY' ? 'Refresh' : 'Connect'}
                    </button>
                </div>

                {progress > 0 && progress < 100 && (
                    <div className="h-1 w-full bg-slate-700 rounded overflow-hidden">
                        <div
                            className="h-full bg-accent transition-all duration-300 ease-out"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                )}
            </div>
        </Section>
    );
}
