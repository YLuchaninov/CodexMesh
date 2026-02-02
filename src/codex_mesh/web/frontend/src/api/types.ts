export interface ProjectStatusSnapshot {
    status: 'IDLE' | 'LOADING' | 'READY' | 'ERROR';
    progress: number;
    message: string;
    project_path: string | null;
}

export interface FileEntry {
    name: string;
    type: 'dir' | 'file';
    path: string;
    size?: number | null;
    modified?: string | null;
}

export interface FileListResponse {
    entries: FileEntry[];
}

export interface FileReadResponse {
    path: string;
    content: string;
    truncated: boolean;
}

export interface SearchResult {
    result: any;
}

export interface ReviewRequest {
    message: string;
    mode: 'quick' | 'standard' | 'deep' | 'autopilot';
    chat_id?: string;
    title?: string;
    include_history?: boolean;
}

export interface EvidenceItem {
    kind: string;
    title: string;
    content: string;
    data?: any;
}

export interface ReviewResponse {
    answer: string;
    evidence: EvidenceItem[];
    checked_items: string[];
    intent?: string;
    chat_id: string;
    user_message_id: string;
    agent_message_id: string;
}

export interface GeminiConfig {
    api_key: string | null;
    model: string;
    temperature: number;
    has_key: boolean;
    key_last4?: string;
}

export interface GeminiTestResponse {
    ok: boolean;
    latency_ms?: number;
    model?: string;
    sample?: string;
    error?: string;
}

// --- New Types for Multi-Provider & System Config ---

export type LLMProvider = 'google' | 'anthropic' | 'ollama' | 'openai' | 'mistral';

export interface LLMProfile {
    name: string;
    model: string;
    provider: LLMProvider;
    max_tokens?: number;
    temperature?: number;
    api_key_env?: string;
    api_base?: string; // For Ollama

    // UI-only fields for persistence
    api_key?: string;
}

export interface EmbeddingConfig {
    engine: string;
    model: string;
}

export interface HotspotConfig {
    error_weight: number;
    warning_weight: number;
    todo_weight: number;
    fixme_weight: number;
    hack_weight: number;
    churn_days: number;
    churn_threshold: number;
    churn_commit_weight: number;
    import_in_weight: number;
    import_out_weight: number;
    centrality_weight: number;
    high_hotspot_threshold: number;
    analysis_timeout: number;
}

export interface SystemConfig {
    embedding: EmbeddingConfig;
    hotspot: HotspotConfig;
    storage: { backend: string; vector_db: string; path: string };
    mcp: { tools: boolean; resources: boolean; prompts: boolean };
    docs: { enabled: boolean };
    profiles: Record<string, LLMProfile>
}

export interface IntentItem {
    id: string;
    title: string;
    description: string;
    slots: Record<string, any>;
    examples: string[];
    tags: string[];
}

export interface IntentExecuteResponse {
    output: string;
    trace: any[];
    logs: string[];
    artifacts: Record<string, any>;
    stats: { steps: number };
}

// Tool registry types for command palette
export type HttpMethod = 'GET' | 'POST';

export interface ToolFormField {
    name: string;
    type: 'string' | 'number' | 'boolean' | 'select';
    default?: any;
    options?: any[];
    placeholder?: string;
}

export interface ToolUIHints {
    form: ToolFormField[];
}

export interface ToolMeta {
    id: string;
    title: string;
    category: string;
    method: HttpMethod;
    endpoint: string;
    ui?: ToolUIHints;
}

export interface ToolsRegistryResponse {
    tools: ToolMeta[];
}

export interface RunRecord {
    tool: ToolMeta;
    payload: any;
    result: any;
    error?: any;
    ts: number;
}

// --- Chat Types ---

export interface ChatThread {
    id: string;
    title: string;
    project_path: string | null;
    created_at: number;
    updated_at: number;
    pinned_context: string | null;
    summary: string | null;
}

export interface ChatMessage {
    id: string;
    thread_id: string;
    role: 'user' | 'agent' | 'system';
    content: string;
    ts: number;
    evidence?: EvidenceItem[] | null;
    deleted_at?: number | null;
}

export interface ChatListResponse {
    threads: ChatThread[];
    total: number;
}

export interface ChatCreateResponse {
    thread: ChatThread;
}

export interface ChatMessagesListResponse {
    messages: ChatMessage[];
    total: number;
}

export interface FileReadSpanResponse {
    path: string;
    content: string;
    base_line: number;
    highlight_start: number;
    highlight_end: number;
    truncated: boolean;
}

export interface OpenFileDetail {
    path: string;
    start_line?: number;
    end_line?: number;
    source?: 'chat' | 'tools' | 'evidence' | 'raw';
}

// Health check types (P4-1)
export interface HealthResponse {
    ok: boolean;
    timestamp: string;
    project: {
        storage_path: string;
        storage_exists: boolean;
    };
    semantic_index: {
        exists: boolean;
        stale: boolean;
        chunks_indexed: number | null;
        updated_at: string | null;
    };
    llm_providers: Record<string, boolean>;
}

export interface IndexRefreshResponse {
    success: boolean;
    chunks_indexed?: number;
    error?: string;
}
