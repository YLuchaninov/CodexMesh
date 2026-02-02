import { useEffect, useRef } from 'react';
import { ProjectStatusSnapshot } from './types';

export function useProjectEvents(onUpdate: (status: Partial<ProjectStatusSnapshot>) => void) {
    const esRef = useRef<EventSource | null>(null);

    useEffect(() => {
        // Close existing connection if any
        if (esRef.current) {
            esRef.current.close();
        }

        const es = new EventSource('/api/v1/events');
        esRef.current = es;

        es.addEventListener('progress', (event) => {
            try {
                const data = JSON.parse(event.data);
                onUpdate(data);
            } catch (e) {
                console.error('Failed to parse SSE data', e);
            }
        });

        // Also listen for generic message events as a fallback
        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.status) {
                    onUpdate(data);
                }
            } catch (e) {
                // Ignore non-json messages
            }
        };

        return () => {
            es.close();
        };
    }, [onUpdate]);
}
