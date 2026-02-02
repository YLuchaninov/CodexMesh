import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { ProjectStatusSnapshot, HealthResponse } from './types';
import { api } from './client';
import { useProjectEvents } from './sse';

interface ProjectContextType extends ProjectStatusSnapshot {
    connect: (path: string, options?: { force_reindex?: boolean }) => Promise<void>;
    health: HealthResponse | null;
    refreshSemanticIndex: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextType | null>(null);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
    const [state, setState] = useState<ProjectStatusSnapshot>({
        status: 'IDLE',
        progress: 0,
        message: 'Waiting...',
        project_path: null
    });
    const [health, setHealth] = useState<HealthResponse | null>(null);

    const updateState = useCallback((newData: Partial<ProjectStatusSnapshot>) => {
        setState(prev => ({ ...prev, ...newData }));
    }, []);

    // Initial status fetch
    useEffect(() => {
        api.getStatus().then(updateState).catch(console.error);
    }, [updateState]);

    // Health polling (every 10s)
    useEffect(() => {
        const fetchHealth = async () => {
            try {
                const h = await api.getHealth();
                setHealth(h);
            } catch (e) {
                console.error('Health check failed:', e);
            }
        };
        fetchHealth();
        const interval = setInterval(fetchHealth, 10000);
        return () => clearInterval(interval);
    }, []);

    // SSE subscription
    useProjectEvents(updateState);

    const connect = async (path: string, options?: { force_reindex?: boolean }) => {
        await api.connect(path, options);
        // State updates will come via SSE
    };

    const refreshSemanticIndex = async () => {
        await api.refreshSemanticIndex();
        // Refresh health after index rebuild
        const h = await api.getHealth();
        setHealth(h);
    };

    return (
        <ProjectContext.Provider value={{ ...state, connect, health, refreshSemanticIndex }}>
            {children}
        </ProjectContext.Provider>
    );
}

export function useProject() {
    const ctx = useContext(ProjectContext);
    if (!ctx) throw new Error("useProject must be used within ProjectProvider");
    return ctx;
}
