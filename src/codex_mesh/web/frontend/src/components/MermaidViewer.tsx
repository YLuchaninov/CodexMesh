
import { useEffect, useState } from 'react';
import mermaid from 'mermaid';
import { Maximize2, X, ZoomIn, ZoomOut } from 'lucide-react';
import { createPortal } from 'react-dom';

mermaid.initialize({
    startOnLoad: true,
    theme: 'dark',
    securityLevel: 'loose',
    themeVariables: {
        primaryColor: '#3b82f6',
        primaryTextColor: '#fff',
        primaryBorderColor: '#334155',
        lineColor: '#64748b',
        secondaryColor: '#1e293b',
        tertiaryColor: '#0f172a',
    }
});

interface MermaidViewerProps {
    chart: string;
}

export function MermaidViewer({ chart }: MermaidViewerProps) {
    const [svgContent, setSvgContent] = useState<string>('');
    const [error, setError] = useState<string | null>(null);
    const [isExpanded, setIsExpanded] = useState(false);
    const [scale, setScale] = useState(1);

    useEffect(() => {
        if (chart) {
            const id = 'mermaid-' + Math.random().toString(36).substring(2, 9);
            setError(null);

            mermaid.render(id, chart)
                .then(({ svg }) => {
                    // Strip fixed dimensions to allow CSS scaling
                    // Remove width/height/style attributes from the <svg> tag
                    const cleanedSvg = svg
                        .replace(/<svg([^>]*?)width="[^"]*"/gi, '<svg$1')
                        .replace(/<svg([^>]*?)height="[^"]*"/gi, '<svg$1')
                        .replace(/<svg([^>]*?)style="[^"]*"/gi, '<svg$1')
                        .replace(/<svg([^>]*)>/gi, (match) => {
                            return match.replace(/>$/, ' style="max-width: none; width: 100%; height: auto;">');
                        });
                    setSvgContent(cleanedSvg);
                })
                .catch(err => {
                    console.error('Mermaid render error:', err);
                    setError(err instanceof Error ? err.message : String(err));
                });
        }
    }, [chart]);

    const handleWheel = (e: React.WheelEvent) => {
        if (isExpanded) {
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();
                const delta = e.deltaY > 0 ? -0.25 : 0.25;
                setScale(s => Math.min(Math.max(0.5, s + delta), 5));
            }
        }
    };

    const ExpandedView = () => (
        <div
            className="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-sm flex items-center justify-center p-8 animate-in fade-in duration-200"
            onClick={() => setIsExpanded(false)}
        >
            <div
                className="relative bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full h-full max-w-[95vw] max-h-[95vh] flex flex-col overflow-hidden"
                onClick={e => e.stopPropagation()}
            >
                {/* Toolbar */}
                <div className="flex justify-between items-center p-4 border-b border-white/10 bg-white/5">
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setScale(s => Math.max(0.5, s - 0.25))}
                            className="p-2 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors"
                            title="Zoom Out"
                        >
                            <ZoomOut size={20} />
                        </button>
                        <span className="text-xs font-mono text-slate-500 w-12 text-center">{Math.round(scale * 100)}%</span>
                        <button
                            onClick={() => setScale(s => Math.min(5, s + 0.25))}
                            className="p-2 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors"
                            title="Zoom In"
                        >
                            <ZoomIn size={20} />
                        </button>
                    </div>
                    <button
                        onClick={() => setIsExpanded(false)}
                        className="p-2 hover:bg-red-500/20 rounded-lg text-slate-400 hover:text-red-400 transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Content */}
                <div
                    className="flex-1 overflow-auto p-8 flex bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iMSIgY3k9IjEiIHI9IjEiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4wNSkiLz48L3N2Zz4=')]"
                    onWheel={handleWheel}
                >
                    <div
                        dangerouslySetInnerHTML={{ __html: svgContent }}
                        style={{
                            width: `${scale * 100}%`,
                            display: 'flex',
                            justifyContent: 'center',
                            transition: 'width 0.1s ease-out',
                            flexShrink: 0,
                            margin: 'auto'
                        }}
                    />
                </div>
            </div>
        </div>
    );

    return (
        <div className="relative group">
            <div className="bg-bg/50 rounded-lg p-4 border border-border/50 overflow-auto flex justify-center min-h-[100px] relative">
                {error ? (
                    <div className="text-red-400 text-xs p-2 font-mono bg-red-900/10 rounded border border-red-900/30">
                        <div>Invalid Diagram Definition</div>
                        <div className="mt-1 opacity-70">{error}</div>
                    </div>
                ) : (
                    <div dangerouslySetInnerHTML={{ __html: svgContent }} />
                )}

                {/* Overlay Button */}
                {!error && svgContent && (
                    <button
                        onClick={() => { setIsExpanded(true); setScale(1.5); }}
                        className="absolute top-2 right-2 p-2 bg-slate-800/80 backdrop-blur text-slate-400 hover:text-white rounded-lg border border-slate-700 opacity-0 group-hover:opacity-100 transition-all shadow-lg"
                        title="Expand Diagram"
                    >
                        <Maximize2 size={16} />
                    </button>
                )}
            </div>

            {isExpanded && createPortal(<ExpandedView />, document.body)}
        </div>
    );
}
