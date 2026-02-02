import { MermaidViewer } from './MermaidViewer';
import { RenderFileLinks } from './fileLinkify';
import { OpenFileDetail } from '../api/types';
import { fixMermaidCode, looksLikeMermaid } from '../utils/mermaid';

interface MessageRendererProps {
    content: string;
    onOpen: (ref: OpenFileDetail) => void;
    allowedFiles?: Set<string>;
}

export function MessageRenderer({ content, onOpen, allowedFiles }: MessageRendererProps) {
    if (!content) return null;

    // Split content by code blocks
    // This regex matches ```language\ncode``` or ```\ncode``` blocks
    const parts = content.split(/(```[\s\S]*?```)/g);

    return (
        <div className="space-y-4">
            {parts.map((part, index) => {
                if (part.startsWith('```')) {
                    // Robust extraction using slicing
                    // regex ensure it starts and ends with ```
                    let raw = part;
                    if (raw.endsWith('```')) {
                        raw = raw.slice(0, -3);
                    }
                    if (raw.startsWith('```')) {
                        raw = raw.slice(3);
                    }

                    // The first line is the language (if any)
                    const firstNewLine = raw.indexOf('\n');
                    let language = '';
                    let code = '';

                    if (firstNewLine === -1) {
                        language = raw.trim();
                    } else {
                        language = raw.substring(0, firstNewLine).trim();
                        code = raw.substring(firstNewLine + 1);
                    }

                    language = language.toLowerCase();

                    if (language === 'mermaid') {
                        const fixedCode = fixMermaidCode(code);
                        return (
                            <div key={index} className="my-2">
                                <MermaidViewer chart={fixedCode} />
                            </div>
                        );
                    }

                    return (
                        <div key={index} className="my-2 rounded-lg bg-slate-950 border border-slate-800 overflow-hidden text-xs">
                            {language && (
                                <div className="px-3 py-1 bg-slate-900 border-b border-slate-800 text-slate-500 font-mono flex justify-between select-none">
                                    <span>{language}</span>
                                </div>
                            )}
                            <pre className="p-3 overflow-x-auto font-mono text-slate-300">
                                <code>{code}</code>
                            </pre>
                        </div>
                    );
                }

                // Regular text (render whitespace and links)

                // Detection for mermaid code without fencing
                if (looksLikeMermaid(part)) {
                    const fixed = fixMermaidCode(part);
                    return (
                        <div key={index} className="my-2">
                            <MermaidViewer chart={fixed} />
                        </div>
                    );
                }

                if (!part) return null;

                return (
                    <div key={index} className="whitespace-pre-wrap leading-relaxed">
                        <RenderFileLinks text={part} onOpen={onOpen} allowed={allowedFiles} />
                    </div>
                );
            })}
        </div>
    );
}

