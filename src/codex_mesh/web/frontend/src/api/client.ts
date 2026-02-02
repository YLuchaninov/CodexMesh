import {
    ProjectStatusSnapshot,
    FileListResponse,
    FileReadResponse,
    FileReadSpanResponse,
    ReviewRequest,
    ReviewResponse,
    GeminiConfig,
    GeminiTestResponse,
    SystemConfig,
    IntentItem,
    IntentExecuteResponse,
    ChatThread,
    ChatListResponse,
    ChatCreateResponse,
    ChatMessagesListResponse,
} from './types';

const API_BASE = '/api';

export class ApiError extends Error {
    constructor(public status: number, public statusText: string, message?: string) {
        super(message || `API Error: ${status} ${statusText}`);
        this.name = 'ApiError';
    }
}

export function isRetryableError(error: unknown): boolean {
    if (error instanceof ApiError) {
        return [408, 429, 500, 502, 503, 504].includes(error.status);
    }
    return false;
}

interface FetchOptions extends RequestInit {
    timeout?: number;
    retries?: number;
    retryDelay?: number;
}

async function fetchJson<T>(url: string, options?: FetchOptions): Promise<T> {
    const { timeout = 60000, retries = 3, retryDelay = 1000, ...fetchOptions } = options || {};

    let lastError: any;

    for (let attempt = 0; attempt <= retries; attempt++) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);

        try {
            const res = await fetch(`${API_BASE}${url}`, {
                ...fetchOptions,
                signal: controller.signal,
            });
            clearTimeout(id);

            if (!res.ok) {
                throw new ApiError(res.status, res.statusText);
            }
            return res.json();
        } catch (err: any) {
            clearTimeout(id);
            lastError = err;

            // Don't retry if aborted by user (unless it was our timeout)
            if (err.name === 'AbortError' && !controller.signal.aborted) {
                throw err;
            }

            // Check if retryable
            const isRetryable = isRetryableError(err) || err.name === 'TypeError' || err.name === 'AbortError'; // Fetch error or timeout

            if (attempt === retries || !isRetryable) {
                throw err;
            }

            // Wait before retry with exponential backoff
            await new Promise(resolve => setTimeout(resolve, retryDelay * Math.pow(2, attempt)));
        }
    }

    throw lastError;
}

export const api = {
    getStatus: async () => {
        const res = await fetchJson<{ status: ProjectStatusSnapshot }>('/v1/project/status');
        return res.status;
    },

    connect: async (path: string, options?: { force_reindex?: boolean }) => {
        const res = await fetchJson<{ ok: boolean, status: ProjectStatusSnapshot }>('/v1/project/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_path: path,
                options: {
                    auto_index: true,
                    force_reindex: options?.force_reindex ?? false,
                    watch: true
                }
            })
        });
        return { status: res.status.status, message: res.status.message };
    },

    listDir: (path: string = '.', opts?: { recursive?: boolean; include_hidden?: boolean }) =>
        fetchJson<FileListResponse>('/v1/fs/list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path,
                recursive: opts?.recursive ?? false,
                include_hidden: opts?.include_hidden ?? false,
            })
        }),

    readFile: (path: string, opts?: { max_bytes?: number }) =>
        fetchJson<FileReadResponse>('/v1/fs/read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path,
                ...(opts?.max_bytes ? { max_bytes: opts.max_bytes } : {})
            })
        }),

    askReviewer: (req: ReviewRequest) => fetchJson<ReviewResponse>('/reviewer/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req)
    }),

    getGeminiConfig: () => fetchJson<GeminiConfig>('/llm/gemini'),

    setGeminiConfig: (config: Partial<GeminiConfig>) => fetchJson<GeminiConfig>('/llm/gemini', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
    }),

    testGemini: () => fetchJson<GeminiTestResponse>('/llm/gemini/test', {
        method: 'POST'
    }),

    getSystemConfig: () => fetchJson<SystemConfig>('/v1/system/config'),

    setSystemConfig: (updates: Partial<SystemConfig>) => fetchJson<SystemConfig>('/v1/system/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
    }),

    getIntents: () => fetchJson<{ intents: IntentItem[] }>('/v1/intents'),

    executeIntent: (intentId: string, input: any) => fetchJson<IntentExecuteResponse>('/v1/intents/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            intent_id: intentId,
            input: input,
            options: { include_trace: true }
        })
    }),

    listChats: (scope: 'current' | 'all' = 'current', limit: number = 50, offset: number = 0) =>
        fetchJson<ChatListResponse>(`/v1/chats?scope=${scope}&limit=${limit}&offset=${offset}`),

    createChat: (title?: string) =>
        fetchJson<ChatCreateResponse>('/v1/chats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        }),

    getChat: (chatId: string) =>
        fetchJson<{ thread: ChatThread }>(`/v1/chats/${chatId}`),

    renameChat: (chatId: string, title: string) =>
        fetchJson<{ thread: ChatThread }>(`/v1/chats/${chatId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        }),

    cloneChat: (chatId: string, title?: string) =>
        fetchJson<ChatCreateResponse>(`/v1/chats/${chatId}/clone`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        }),

    deleteChat: (chatId: string, hard: boolean = false) =>
        fetchJson<{ ok: boolean }>(`/v1/chats/${chatId}${hard ? '?hard=true' : ''}`, {
            method: 'DELETE'
        }),

    listMessages: (chatId: string, limit: number = 200, offset: number = 0) =>
        fetchJson<ChatMessagesListResponse>(`/v1/chats/${chatId}/messages?limit=${limit}&offset=${offset}`),

    deleteMessage: (chatId: string, messageId: string) =>
        fetchJson<{ ok: boolean }>(`/v1/chats/${chatId}/messages/${messageId}`, {
            method: 'DELETE'
        }),

    setPinnedContext: (chatId: string, pinnedContext: string | null) =>
        fetchJson<{ thread: ChatThread }>(`/v1/chats/${chatId}/pinned_context`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pinned_context: pinnedContext })
        }),

    readFileSpan: (path: string, startLine: number, endLine: number, contextLines: number = 20) =>
        fetchJson<FileReadSpanResponse>('/v1/fs/read-span', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path,
                start_line: startLine,
                end_line: endLine,
                context_lines: contextLines
            })
        }),

    bulkAppendMessages: (chatId: string, messages: { role: string; content: string; evidence?: any[] }[]) =>
        fetchJson<ChatMessagesListResponse>(`/v1/chats/${chatId}/messages/bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages })
        }),

    // Health check (P4-2) - /health is at root level, not under /api
    getHealth: () => fetch('/health').then(res => res.json()) as Promise<import('./types').HealthResponse>,

    // Semantic index refresh (P4-2) - matches backend /analysis/index-refresh
    refreshSemanticIndex: (paths?: string[]) =>
        fetchJson<import('./types').IndexRefreshResponse>('/v1/analysis/index-refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths: paths || [] })
        }),

    // Hotspot auto-tune (P1.1)
    autotuneHotspots: (req?: {
        path?: string;
        apply?: boolean;
        target_rate?: number;
        percentile?: number;
        max_files?: number;
    }) => fetchJson<{
        recommended: Record<string, any>;
        before: Record<string, any>;
        after: Record<string, any>;
        applied: boolean;
    }>('/v1/analysis/hotspots/autotune', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req || {})
    }),

    fetchJson
};
