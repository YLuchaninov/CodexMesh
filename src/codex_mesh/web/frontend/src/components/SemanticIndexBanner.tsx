import { useState } from 'react';
import { HealthResponse } from '../api/types';
import { api } from '../api/client';
import { useProjectEvents } from '../api/sse';

interface SemanticIndexBannerProps {
    health: HealthResponse | null;
    onRefreshComplete?: () => void;
}

export function SemanticIndexBanner({ health, onRefreshComplete }: SemanticIndexBannerProps) {
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [error, setError] = useState<string | null>(null);

    // Listen for progress events
    useProjectEvents((status) => {
        if (status.message?.includes('Indexing') || status.message?.includes('index refresh')) {
            setIsRefreshing(true);
            setProgress(status.progress || 0);
            setProgressMessage(status.message);
        } else if (status.message === 'Semantic index refreshed') {
            setIsRefreshing(false);
            setProgress(100);
            onRefreshComplete?.();
        } else if (status.message?.includes('failed')) {
            setIsRefreshing(false);
            setError(status.message);
        }
    });

    // Don't show if health data not loaded or index is fresh
    if (!health) return null;

    const { semantic_index } = health;
    const shouldShow = !semantic_index.exists || semantic_index.stale;

    if (!shouldShow && !isRefreshing) return null;

    const handleRefresh = async () => {
        setIsRefreshing(true);
        setError(null);
        setProgress(0);
        setProgressMessage('Starting refresh...');
        try {
            // Now returns immediately with "job started" message
            const result = await api.refreshSemanticIndex();
            // We rely on SSE for updates now, but check immediate error
            if (!result.success && result.error) {
                setError(result.error);
                setIsRefreshing(false);
            }
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Unknown error');
            setIsRefreshing(false);
        }
    };

    const message = !semantic_index.exists
        ? 'Semantic index not built yet. Semantic search will not work.'
        : 'Semantic index is outdated. Results may not reflect recent changes.';

    return (
        <div style={{
            background: 'linear-gradient(90deg, #f59e0b22, #f59e0b11)',
            border: '1px solid #f59e0b55',
            borderRadius: '8px',
            padding: '12px 16px',
            margin: '0 0 16px 0',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
        }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '18px' }}>⚠️</span>
                    <span style={{ color: '#f59e0b', fontWeight: 500 }}>
                        {isRefreshing ? progressMessage || 'Refreshing index...' : message}
                    </span>
                </div>
                {!isRefreshing && (
                    <button
                        onClick={handleRefresh}
                        style={{
                            background: '#f59e0b',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '6px',
                            padding: '8px 16px',
                            cursor: 'pointer',
                            fontWeight: 500,
                            fontSize: '13px',
                            whiteSpace: 'nowrap',
                        }}
                    >
                        Refresh Index
                    </button>
                )}
            </div>

            {isRefreshing && (
                <div style={{ width: '100%', height: '4px', background: '#f59e0b33', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{
                        width: `${progress}%`,
                        height: '100%',
                        background: '#f59e0b',
                        transition: 'width 0.3s ease'
                    }} />
                </div>
            )}

            {error && (
                <span style={{ color: '#ef4444', fontSize: '12px' }}>{error}</span>
            )}
        </div>
    );
}
