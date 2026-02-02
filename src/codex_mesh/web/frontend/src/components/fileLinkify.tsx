import { OpenFileDetail } from '../api/types';

export const dispatchOpenFile = (detail: OpenFileDetail) => {
    window.dispatchEvent(new CustomEvent('codex-mesh:open-file', { detail }));
};

/**
 * Regex to detect file paths and line ranges.
 * Examples:
 * - src/main.py
 * - src/main.py:10
 * - src/main.py:10-20
 * - src/main.py#L10
 * - src/main.py#L10-L20
 */
const FILE_LINKS_REGEX =
    /([a-zA-Z0-9_.\-/]+\.(?:tsx|ts|jsx|js|py|go|rs|java|kt|cpp|cc|cs|c|hpp|h|php|rb|swift|dart|sql|yaml|yml|toml|json|md))(?::(\d+)(?:-(\d+))?|#L(\d+)(?:-L?(\d+))?)?/g;

export function parseFileMentions(text: string, allowed?: Set<string>): Array<{ type: 'text'; value: string } | { type: 'file'; ref: OpenFileDetail; value: string }> {
    FILE_LINKS_REGEX.lastIndex = 0;
    const results: Array<{ type: 'text'; value: string } | { type: 'file'; ref: OpenFileDetail; value: string }> = [];
    let lastIndex = 0;
    let match;

    while ((match = FILE_LINKS_REGEX.exec(text)) !== null) {
        // Text before match
        if (match.index > lastIndex) {
            results.push({ type: 'text', value: text.substring(lastIndex, match.index) });
        }

        const fullMatch = match[0];
        const path = match[1];

        // startLine can be in group 2 (colon) or 4 (hash)
        // endLine can be in group 3 (colon) or 5 (hash)
        const startLineStr = match[2] || match[4];
        const endLineStr = match[3] || match[5];

        const start_line = startLineStr ? parseInt(startLineStr, 10) : undefined;
        let end_line = endLineStr ? parseInt(endLineStr, 10) : undefined;

        if (start_line && !end_line) {
            end_line = start_line;
        }

        const isAllowed = !allowed || allowed.has(path);

        if (!isAllowed) {
            // Treat as text
            results.push({ type: 'text', value: fullMatch });
        } else {
            results.push({
                type: 'file',
                value: fullMatch,
                ref: {
                    path,
                    start_line,
                    end_line,
                    source: 'chat'
                }
            });
        }

        lastIndex = match.index + fullMatch.length;
    }

    if (lastIndex < text.length) {
        results.push({ type: 'text', value: text.substring(lastIndex) });
    }

    return results;
}

interface RenderFileLinksProps {
    text: string;
    onOpen: (ref: OpenFileDetail) => void;
    allowed?: Set<string>;
}

export function RenderFileLinks({ text, onOpen, allowed }: RenderFileLinksProps) {
    const parts = parseFileMentions(text, allowed);

    return (
        <>
            {parts.map((part, i) => {
                if (part.type === 'text') {
                    return <span key={i}>{part.value}</span>;
                }
                return (
                    <button
                        key={i}
                        onClick={() => onOpen(part.ref)}
                        className="text-accent hover:underline font-mono text-sm bg-accent/5 px-1 rounded transition-colors"
                        title={`Open ${part.value}`}
                    >
                        {part.value}
                    </button>
                );
            })}
        </>
    );
}
