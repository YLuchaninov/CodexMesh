import { useState, useRef, useEffect, useCallback } from 'react';
import { api, ApiError } from '../api/client';
import { Check, Copy, AlertCircle, Trash2, ChevronDown, ChevronUp, FileCode } from 'lucide-react';
import { Spinner } from './ui';
import { ReviewRequest, ChatMessage, ChatThread } from '../api/types';
import { dispatchOpenFile } from './fileLinkify';
import { MessageRenderer } from './MessageRenderer';

interface ChatCardProps {
    chatId: string;
    onTitleUpdate?: (newTitle: string) => void;
}

export default function ChatCard({ chatId, onTitleUpdate }: ChatCardProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [thread, setThread] = useState<ChatThread | null>(null);
    const [input, setInput] = useState('');
    const [mode, setMode] = useState<ReviewRequest['mode']>('standard');
    const [showPinned, setShowPinned] = useState(false);
    const [pinnedContext, setPinnedContext] = useState('');
    const [loading, setLoading] = useState(false);
    const [initializing, setInitializing] = useState(true);
    const [justCopiedAll, setJustCopiedAll] = useState(false);
    const [copiedMessageIndex, setCopiedMessageIndex] = useState<string | null>(null);
    const [allowedFiles, setAllowedFiles] = useState<Set<string> | undefined>(undefined);
    const scrollRef = useRef<HTMLDivElement>(null);

    const loadData = useCallback(async () => {
        try {
            const [msgRes, threadRes, filesRes] = await Promise.all([
                api.listMessages(chatId),
                api.getChat(chatId),
                api.listDir('.', { recursive: true, include_hidden: false })
            ]);
            setMessages(msgRes.messages);
            setThread(threadRes.thread);
            setPinnedContext(threadRes.thread.pinned_context || '');

            // Build set of allowed files
            const files = new Set<string>();
            const walk = (items: any[]) => {
                for (const item of items) {
                    if (item.type === 'file') files.add(item.path);
                    if (item.children) walk(item.children); // output is flat but let's be safe if format changes, actually listDir is flat usually or recursive?
                    // actually listDir returns { entries: [...] } usually but check api types.
                    // api.listDir definition: listDir(path: string, opts?: ...) -> Promise<{ entries: DirEntry[] }>
                }
            };
            // api.listDir returns { entries: DirEntry[] }
            if (filesRes && filesRes.entries) {
                filesRes.entries.forEach((e: any) => {
                    if (e.type === 'file') files.add(e.path);
                });
            }
            setAllowedFiles(files);

        } catch (e) {
            console.error('Failed to load chat data', e);
        } finally {
            setInitializing(false);
        }
    }, [chatId]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async (textOverride?: string) => {
        const textToSend = textOverride || input;
        if (!textToSend.trim() || loading) return;

        if (!textOverride) {
            setInput('');
        }

        setLoading(true);

        // Optimistic update for local UI (will be refreshed by API response or manual reload)
        const tempId = 'temp-' + Date.now();
        const tempMsg: ChatMessage = {
            id: tempId,
            thread_id: chatId,
            role: 'user',
            content: textToSend,
            ts: Date.now()
        };
        setMessages(prev => [...prev, tempMsg]);

        try {
            await api.askReviewer({
                message: textToSend,
                mode,
                chat_id: chatId
            });

            // Reload messages to get real IDs and agent response
            const msgRes = await api.listMessages(chatId);
            setMessages(msgRes.messages);

            // If it was the first message and we don't have a good title yet
            if (onTitleUpdate && messages.length < 2) {
                const threadRes = await api.getChat(chatId);
                onTitleUpdate(threadRes.thread.title);
            }
        } catch (e: any) {
            console.error(e);
            let errorText = `Error: ${e.message}`;

            if (e instanceof ApiError) {
                if (e.status === 503) errorText = "Server is overloaded. Please try again later.";
                else if (e.status === 504) errorText = "Request timed out. Server might be busy.";
            }

            setMessages(prev => [...prev, {
                id: 'err-' + Date.now(),
                thread_id: chatId,
                role: 'agent',
                content: errorText,
                ts: Date.now(),
                deleted_at: -1 // Special flag for UI error
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteMessage = async (msgId: string) => {
        try {
            await api.deleteMessage(chatId, msgId);
            setMessages(prev => prev.filter(m => m.id !== msgId));
        } catch (e) {
            console.error('Failed to delete message', e);
        }
    };

    const handleSavePinned = async () => {
        try {
            await api.setPinnedContext(chatId, pinnedContext);
            setShowPinned(false);
        } catch (e) {
            console.error('Failed to save pinned context', e);
        }
    };

    const copyToClipboard = async (text: string, onSuccess: () => void) => {
        if (!text) return;

        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                onSuccess();
            } else {
                // Fallback for non-secure contexts
                const textArea = document.createElement("textarea");
                textArea.value = text;
                textArea.style.position = "fixed";
                textArea.style.left = "-9999px";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {
                    document.execCommand('copy');
                    onSuccess();
                } catch (err) {
                    console.error('Fallback copy failed', err);
                    alert('Failed to copy text. Please copy manually.');
                }
                document.body.removeChild(textArea);
            }
        } catch (err) {
            console.error('Failed to copy!', err);
            alert('Failed to copy text. Check console for details.');
        }
    };

    const handleCopyMessage = (msg: ChatMessage) => {
        let text = msg.content;
        if (msg.role === 'agent' && msg.evidence && msg.evidence.length > 0) {
            text += `\n\n*Evidence: ${msg.evidence.map(e => e.title).join(', ')}*`;
        }

        copyToClipboard(text, () => {
            setCopiedMessageIndex(msg.id);
            setTimeout(() => setCopiedMessageIndex(null), 2000);
        });
    };


    const handleCopyAll = () => {
        const fullChat = messages.map(m => {
            let content = `## ${m.role === 'user' ? 'User' : 'Agent'}\n${m.content}`;
            if (m.evidence && m.evidence.length > 0) {
                content += `\n\n*Evidence: ${m.evidence.map(e => e.title).join(', ')}*`;
            }
            return content;
        }).join('\n\n---\n\n');

        copyToClipboard(fullChat, () => {
            setJustCopiedAll(true);
            setTimeout(() => setJustCopiedAll(false), 2000);
        });
    };

    if (initializing) {
        return <div className="flex h-full items-center justify-center text-slate-500">Initializing chat...</div>;
    }

    return (
        <div className="bg-sidebar flex flex-col h-full border-l border-border shadow-2xl relative overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-border flex justify-between items-center bg-sidebar/50 backdrop-blur-md z-20">
                <div className="flex-1 min-w-0 mr-4">
                    <h3 className="font-bold text-lg text-slate-200 truncate">{thread?.title || 'Chat'}</h3>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleCopyAll}
                        className="flex items-center gap-2 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition-all active:scale-95"
                        title="Copy entire chat to Markdown"
                    >
                        {justCopiedAll ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                        <span className="hidden sm:inline">{justCopiedAll ? 'Copied' : 'Copy Chat'}</span>
                    </button>
                    <button
                        onClick={() => setShowPinned(!showPinned)}
                        className={`p-1.5 rounded-lg border border-slate-700 transition-all active:scale-95 ${showPinned ? 'bg-accent/20 text-accent border-accent/50' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                        title="Pinned Context / Instructions"
                    >
                        {showPinned ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </button>
                    <select
                        value={mode}
                        onChange={(e) => setMode(e.target.value as any)}
                        className="bg-bg border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-accent transition-all"
                    >
                        <option value="quick">Quick</option>
                        <option value="standard">Standard</option>
                        <option value="deep">Deep</option>
                        <option value="autopilot">Autopilot</option>
                    </select>
                </div>
            </div>

            {/* Pinned Context Drawer */}
            {showPinned && (
                <div className="absolute top-[65px] inset-x-0 z-30 bg-slate-900 border-b border-border shadow-2xl p-4 animate-in slide-in-from-top duration-200">
                    <div className="flex flex-col gap-3">
                        <div className="flex justify-between items-center">
                            <span className="text-sm font-medium text-slate-300">Pinned Context (System Instructions)</span>
                            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Always included in chat</span>
                        </div>
                        <textarea
                            className="w-full h-32 bg-bg border border-slate-700 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-accent transition-all"
                            placeholder="e.g. Always respond in Python, focusing on SOLID principles..."
                            value={pinnedContext}
                            onChange={(e) => setPinnedContext(e.target.value)}
                        />
                        <div className="flex justify-end gap-2">
                            <button
                                onClick={() => setShowPinned(false)}
                                className="px-4 py-1.5 text-sm text-slate-400 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSavePinned}
                                className="px-4 py-1.5 text-sm bg-accent hover:bg-blue-600 text-white rounded-lg font-medium transition-colors"
                            >
                                Save Context
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-slate-950/20 scroll-smooth custom-scrollbar" ref={scrollRef}>
                {messages.length === 0 && !loading && (
                    <div className="h-full flex flex-col items-center justify-center opacity-30 text-slate-500 space-y-4">
                        <MessageSquare size={48} />
                        <p className="text-center font-medium">No messages yet.<br />Start the conversation below.</p>
                    </div>
                )}

                {messages.map((m) => (
                    <div key={m.id} className={`flex flex-col gap-1.5 max-w-[90%] md:max-w-[85%] ${m.role === 'user' ? 'self-end ml-auto' : 'self-start'} group relative`}>
                        <div className={`p-4 rounded-2xl text-sm leading-relaxed shadow-lg relative ${m.role === 'user'
                            ? 'bg-accent text-white rounded-br-none'
                            : m.deleted_at === -1
                                ? 'bg-red-900/10 text-red-200 border border-red-800/30 rounded-bl-none'
                                : 'bg-slate-800 text-slate-100 border border-border rounded-bl-none'
                            }`}>

                            {m.deleted_at === -1 && <AlertCircle size={16} className="inline-block mr-2 mb-0.5 text-red-400" />}

                            <div className="w-full">
                                <MessageRenderer
                                    content={m.content}
                                    onOpen={(ref) => dispatchOpenFile(ref)}
                                    allowedFiles={allowedFiles}
                                />
                            </div>

                            {/* Actions Group */}
                            <div className={`absolute -top-3 ${m.role === 'user' ? '-left-3' : '-right-3'} flex items-center gap-1 opacity-100 transition-all duration-200 z-10`}>
                                <button
                                    onClick={() => handleCopyMessage(m)}
                                    className="p-1.5 rounded-full bg-slate-900 border border-slate-700 text-slate-400 hover:text-white shadow-xl"
                                    title="Copy Message"
                                >
                                    {copiedMessageIndex === m.id ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                                </button>
                                <button
                                    onClick={() => handleDeleteMessage(m.id)}
                                    className="p-1.5 rounded-full bg-slate-900 border border-slate-700 text-slate-400 hover:text-red-400 shadow-xl"
                                    title="Delete Message"
                                >
                                    <Trash2 size={12} />
                                </button>
                            </div>
                        </div>

                        {/* Evidence Pills */}
                        {m.evidence && m.evidence.length > 0 && (
                            <div className="flex flex-wrap gap-2 px-1 mt-1">
                                {m.evidence.map((ev, j) => {
                                    const hasLink = ev.data?.path || (ev.kind === 'file' && ev.title.includes('.'));
                                    const path = ev.data?.path || (ev.kind === 'file' ? ev.title : null);

                                    return (
                                        <button
                                            key={j}
                                            onClick={() => {
                                                if (path) {
                                                    dispatchOpenFile({
                                                        path,
                                                        start_line: ev.data?.start_line,
                                                        end_line: ev.data?.end_line,
                                                        source: 'evidence'
                                                    });
                                                }
                                            }}
                                            className={`flex items-center gap-1.5 bg-slate-900/60 backdrop-blur-md px-2 py-0.5 rounded-full border border-border/50 text-[10px] transition-all ${hasLink
                                                ? 'text-slate-300 hover:text-accent hover:border-accent/40 cursor-pointer active:scale-95'
                                                : 'text-slate-500 cursor-default'
                                                }`}
                                            title={hasLink ? `Jump to ${path}` : ev.title}
                                        >
                                            <div className={`w-1 h-1 rounded-full ${hasLink ? 'bg-emerald-500 shadow-[0_0_4px_rgba(16,185,129,0.5)]' : 'bg-slate-600'}`} />
                                            <span className="truncate max-w-[150px]">{ev.title}</span>
                                            {hasLink && <FileCode size={10} className="ml-0.5 opacity-50" />}
                                        </button>
                                    );
                                })}
                            </div>
                        )}

                        {/* Timestamp */}
                        <div className={`text-[9px] text-slate-600 px-2 flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {new Date(m.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex flex-col gap-1.5 self-start animate-pulse">
                        <div className="bg-slate-800 text-slate-400 border border-border p-4 rounded-2xl rounded-bl-none text-sm flex items-center gap-3">
                            <Spinner size={16} className="text-accent" />
                            <span>Reviewer is thinking...</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 bg-sidebar/80 backdrop-blur-xl border-t border-border z-20">
                <div className="max-w-4xl mx-auto flex gap-3 relative">
                    <div className="flex-1 relative flex items-center group">
                        <input
                            className="w-full bg-bg border border-border rounded-2xl pl-5 pr-12 py-3.5 text-sm text-text focus:outline-none focus:ring-2 focus:ring-accent/40 placeholder:text-slate-500 transition-all shadow-inner"
                            placeholder="Message Reviewer..."
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSend();
                                }
                            }}
                        />
                        <div className={`absolute right-4 w-2 h-2 rounded-full transition-all duration-500 ${loading ? 'bg-accent animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.6)]' : 'bg-slate-700 opacity-50'}`} />
                    </div>
                    <button
                        onClick={() => handleSend()}
                        disabled={loading}
                        className={`px-8 rounded-2xl font-semibold transition-all shadow-lg active:scale-95 flex items-center justify-center gap-2 ${loading ? 'bg-slate-700 text-slate-500 cursor-not-allowed' : 'bg-accent hover:bg-blue-600 text-white'}`}
                    >
                        {loading ? <Spinner size={18} /> : 'Send'}
                    </button>
                </div>
                <div className="mt-2 text-center">
                    <p className="text-[10px] text-slate-600 font-medium uppercase tracking-widest">CodexMesh Control Plane Chat</p>
                </div>
            </div>
        </div>
    );
}

// Stub for local Lucide icons use for now, can be replaced by real symbols
function MessageSquare({ size, className }: { size: number, className?: string }) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>;
}
