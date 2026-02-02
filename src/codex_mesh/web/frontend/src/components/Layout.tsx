
import { useState, useEffect } from 'react';
import ProjectCard from './ProjectCard';
import LLMSettingsCard from './LLMSettingsCard';
import SystemSettingsCard from './SystemSettingsCard';
import FilesCard from './FilesCard';
import ChatWorkspace from './ChatWorkspace';
import ContentViewer from './ContentViewer';
import ToolsCard from './ToolsCard';
import IntentsExplorer from './IntentsExplorer';
import { SemanticIndexBanner } from './SemanticIndexBanner';
import { useProject } from '../api/context';
import { Settings, MessageSquare, FolderOpen, Wrench, Zap } from 'lucide-react';
import { OpenFileDetail } from '../api/types';

export default function Layout() {
    const { health, refreshSemanticIndex } = useProject();
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [selectedSpan, setSelectedSpan] = useState<{ start_line: number; end_line: number } | null>(null);
    const [revealFile, setRevealFile] = useState<string | null>(null);

    const [activeTab, setActiveTab] = useState<'settings' | 'chat' | 'explorer' | 'tools' | 'intents'>(() => {
        const saved = localStorage.getItem('codex_mesh_active_tab');
        return (saved as 'settings' | 'chat' | 'explorer' | 'tools' | 'intents') || 'settings';
    });

    useEffect(() => {
        const handleOpenFile = (e: any) => {
            const detail = e.detail as OpenFileDetail;
            if (detail?.path) {
                // Determine if we need to switch tabs
                setActiveTab('explorer');
                setSelectedFile(detail.path);
                setRevealFile(detail.path);
                if (detail.start_line && detail.end_line) {
                    setSelectedSpan({ start_line: detail.start_line, end_line: detail.end_line });
                } else {
                    setSelectedSpan(null);
                }
            }
        };

        window.addEventListener('codex-mesh:open-file', handleOpenFile);
        return () => window.removeEventListener('codex-mesh:open-file', handleOpenFile);
    }, []);

    useEffect(() => {
        localStorage.setItem('codex_mesh_active_tab', activeTab);
    }, [activeTab]);

    const TabButton = ({ id, label, icon: Icon }: { id: typeof activeTab, label: string, icon: any }) => (
        <button
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === id
                ? 'border-accent text-accent'
                : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
        >
            <Icon size={16} />
            {label}
        </button>
    );

    return (
        <div className="flex flex-col h-screen bg-bg overflow-hidden">
            {/* Header Tabs */}
            <div className="flex items-center px-6 border-b border-border bg-sidebar shrink-0">
                <div className="mr-8 font-bold text-lg text-slate-100 py-3">CodexMesh</div>
                <div className="flex gap-2">
                    <TabButton id="settings" label="Settings" icon={Settings} />
                    <TabButton id="intents" label="Intents" icon={Zap} />
                    <TabButton id="tools" label="Tools" icon={Wrench} />
                    <TabButton id="chat" label="Reviewer & Chat" icon={MessageSquare} />
                    <TabButton id="explorer" label="Explorer" icon={FolderOpen} />
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 overflow-hidden relative p-6">
                {/* Semantic Index Banner (P4-5) */}
                <SemanticIndexBanner health={health} onRefreshComplete={refreshSemanticIndex} />

                {/* Tab 1: Settings */}
                <div className={`h-full max-w-2xl mx-auto flex flex-col gap-6 overflow-y-auto ${activeTab === 'settings' ? 'block' : 'hidden'}`}>
                    <ProjectCard />
                    <LLMSettingsCard />
                    <SystemSettingsCard />
                </div>

                {/* Tab 2: Tools */}
                <div className={`h-full max-w-6xl mx-auto flex flex-col ${activeTab === 'tools' ? 'flex' : 'hidden'}`}>
                    <ToolsCard />
                </div>

                {/* Tab 3: Chat */}
                <div className={`h-full max-w-[1200px] mx-auto flex flex-col ${activeTab === 'chat' ? 'block' : 'hidden'}`}>
                    <ChatWorkspace />
                </div>

                {/* Tab 4: Explorer */}
                <div className={`h-full flex gap-4 ${activeTab === 'explorer' ? 'flex' : 'hidden'}`}>
                    <div className="w-[350px] flex flex-col bg-sidebar border border-border rounded-lg overflow-hidden shrink-0">
                        <div className="flex-1 overflow-hidden flex flex-col p-4">
                            <FilesCard
                                onFileSelect={(path) => {
                                    setSelectedFile(path);
                                    setSelectedSpan(null);
                                }}
                                selectedFile={selectedFile}
                                revealFile={revealFile}
                                onRevealed={() => setRevealFile(null)}
                            />
                        </div>
                    </div>
                    <div className="flex-1 flex flex-col overflow-hidden">
                        <div className="flex-1 flex flex-col overflow-hidden">
                            <ContentViewer
                                selectedFile={selectedFile}
                                selectedSpan={selectedSpan}
                            />
                        </div>
                    </div>
                </div>

                {/* Tab 5: Intents */}
                <div className={`h-full max-w-6xl mx-auto flex flex-col ${activeTab === 'intents' ? 'flex' : 'hidden'}`}>
                    <IntentsExplorer />
                </div>

            </div>
        </div>
    );
}

