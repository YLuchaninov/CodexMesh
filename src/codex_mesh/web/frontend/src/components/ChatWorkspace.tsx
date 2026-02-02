import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import { ChatThread } from '../api/types';
import ChatCard from './ChatCard';
import { Plus, MessageSquare, Trash2, Edit3, Share2 } from 'lucide-react';

export default function ChatWorkspace() {
    const [threads, setThreads] = useState<ChatThread[]>([]);
    const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [showSidebar, setShowSidebar] = useState(true);

    const loadThreads = useCallback(async () => {
        try {
            const res = await api.listChats('current');
            setThreads(res.threads);

            // If there are threads but none selected, select the first one
            if (res.threads.length > 0 && !currentThreadId) {
                setCurrentThreadId(res.threads[0].id);
            } else if (res.threads.length === 0) {
                // Check for migration
                const legacy = localStorage.getItem('codex_mesh_chat_messages');
                if (legacy) {
                    try {
                        const messages = JSON.parse(legacy);
                        const newThread = await api.createChat('Migrated Chat');
                        // Bulk upload or sequence? Let's do a sequence for safety in MVP
                        const bulkMessages = messages.map((msg: any) => ({
                            role: msg.role === 'user' ? 'user' : 'agent',
                            content: msg.text,
                            evidence: msg.evidence?.map((e: string) => ({ kind: 'legacy', title: e, content: e }))
                        }));
                        await api.bulkAppendMessages(newThread.thread.id, bulkMessages);
                        localStorage.removeItem('codex_mesh_chat_messages');
                        loadThreads();
                        return;
                    } catch (e) {
                        console.error('Migration failed', e);
                    }
                }

                // Create first chat if truly empty
                const newThread = await api.createChat('New Chat');
                setThreads([newThread.thread]);
                setCurrentThreadId(newThread.thread.id);
            }
        } catch (e) {
            console.error('Failed to load chats', e);
        } finally {
            setLoading(false);
        }
    }, [currentThreadId]);

    useEffect(() => {
        loadThreads();
    }, []);

    const handleCreateChat = async () => {
        try {
            const res = await api.createChat('New Chat');
            setThreads([res.thread, ...threads]);
            setCurrentThreadId(res.thread.id);
        } catch (e) {
            console.error('Failed to create chat', e);
        }
    };

    const handleDeleteChat = async (id: string) => {
        if (!confirm('Are you sure you want to delete this chat?')) return;
        try {
            await api.deleteChat(id);
            const updated = threads.filter(t => t.id !== id);
            setThreads(updated);
            if (currentThreadId === id) {
                setCurrentThreadId(updated.length > 0 ? updated[0].id : null);
            }
        } catch (e) {
            console.error('Failed to delete chat', e);
        }
    };

    const handleRenameChat = async (id: string) => {
        const thread = threads.find(t => t.id === id);
        const newTitle = prompt('Rename chat:', thread?.title);
        if (!newTitle || newTitle === thread?.title) return;

        try {
            const res = await api.renameChat(id, newTitle);
            setThreads(threads.map(t => t.id === id ? res.thread : t));
        } catch (e) {
            console.error('Failed to rename chat', e);
        }
    };

    const handleCloneChat = async (id: string) => {
        try {
            const res = await api.cloneChat(id);
            setThreads([res.thread, ...threads]);
            setCurrentThreadId(res.thread.id);
        } catch (e) {
            console.error('Failed to clone chat', e);
        }
    };

    if (loading) {
        return <div className="flex h-full items-center justify-center text-slate-400">Loading chats...</div>;
    }

    return (
        <div className="flex h-full bg-bg overflow-hidden relative">
            {/* Sidebar */}
            <div className={`${showSidebar ? 'w-72' : 'w-0'} transition-all duration-300 border-r border-border flex flex-col bg-sidebar h-full overflow-hidden`}>
                <div className="p-4 border-b border-border flex justify-between items-center">
                    <span className="font-bold text-slate-200">History</span>
                    <button
                        onClick={handleCreateChat}
                        className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors border border-border"
                        title="New Chat"
                    >
                        <Plus size={18} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {threads.map(thread => (
                        <div
                            key={thread.id}
                            onClick={() => setCurrentThreadId(thread.id)}
                            className={`group flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${currentThreadId === thread.id
                                ? 'bg-slate-800 text-slate-100 ring-1 ring-border shadow-md'
                                : 'text-slate-400 hover:bg-slate-900/50 hover:text-slate-300'
                                }`}
                        >
                            <MessageSquare size={16} className={currentThreadId === thread.id ? 'text-blue-400' : ''} />
                            <span className="flex-1 truncate text-sm font-medium">{thread.title}</span>

                            <div className={`flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ${currentThreadId === thread.id ? 'opacity-100' : ''}`}>
                                <button
                                    onClick={(e) => { e.stopPropagation(); e.preventDefault(); handleRenameChat(thread.id); }}
                                    className="p-2 hover:text-blue-400 transition-colors"
                                >
                                    <Edit3 size={14} />
                                </button>
                                <button
                                    onClick={(e) => { e.stopPropagation(); e.preventDefault(); handleCloneChat(thread.id); }}
                                    className="p-2 hover:text-emerald-400 transition-colors"
                                >
                                    <Share2 size={14} />
                                </button>
                                <button
                                    onClick={(e) => { e.stopPropagation(); e.preventDefault(); handleDeleteChat(thread.id); }}
                                    className="p-2 hover:text-red-400 transition-colors"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Toggle Sidebar Button */}
            <button
                onClick={() => setShowSidebar(!showSidebar)}
                className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-4 h-12 bg-slate-800/80 hover:bg-slate-700 transition-colors border-y border-r border-border rounded-r-lg flex items-center justify-center group"
            >
                <div className={`w-1 h-3 bg-slate-500 group-hover:bg-slate-300 rounded-full ${showSidebar ? 'mr-0.5' : 'ml-0.5'}`} />
            </button>

            {/* Chat Card */}
            <div className="flex-1 min-w-0">
                {currentThreadId ? (
                    <ChatCard
                        key={currentThreadId}
                        chatId={currentThreadId}
                        onTitleUpdate={(newTitle) => {
                            setThreads(prev => prev.map(t => t.id === currentThreadId ? { ...t, title: newTitle } : t));
                        }}
                    />
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
                        <MessageSquare size={48} className="opacity-20" />
                        <p>Select or create a chat to begin</p>
                        <button
                            onClick={handleCreateChat}
                            className="bg-accent hover:bg-blue-600 text-white px-6 py-2 rounded-lg font-medium transition-colors"
                        >
                            New Chat
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
