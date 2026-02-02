
function fixMermaidCode(code) {
    const lines = code.split('\n');
    const fixedLines = lines.map(line => {
        let fixedLine = line;

        // Fix 1: subgraph
        const subgraphMatch = fixedLine.match(/^(\s*subgraph\s+)(.+)$/);
        if (subgraphMatch) {
            const content = subgraphMatch[2].trim();
            if (
                (/[()]/.test(content)) &&
                (!content.startsWith('"')) &&
                (!content.includes('['))
            ) {
                fixedLine = `${subgraphMatch[1]}"${content}"`;
            }
        }

        // Fix 2: Edge labels
        fixedLine = fixedLine.replace(/\|([^"\|]*?[()][^"\|]*?)\|/g, (match, content) => {
            if (content.trim().startsWith('"')) return match;
            return `|"${content}"|`;
        });

        // Fix 3: Node labels

        // Handle []
        fixedLine = fixedLine.replace(/(\[[^"\]]*?[\(\)][^"\]]*?\])/g, (match) => {
            const content = match.slice(1, -1);
            if (content.startsWith('"') && content.endsWith('"')) return match;
            return `["${content}"]`;
        });

        // Handle {} - Rhombus
        // Match { content } where content is not fully quoted AND contains parens
        fixedLine = fixedLine.replace(/(\{[^"\}]*?[\(\)][^"\}]*?\})/g, (match) => {
            const content = match.slice(1, -1);
            if (content.trim().startsWith('"') && content.trim().endsWith('"')) return match;
            return `{"${content}"}`;
        });

        // Handle () - Round braces validation
        // STRATEGY: Match quoted strings OR parens. If quoted, ignore.
        // Regex: 
        // Group 1: "[^"]*"  (quoted string)
        // Group 2: \((?:[^()"]|(?:\([^()"]*\)))*\)  (balanced parens not containing quotes at top level)
        fixedLine = fixedLine.replace(/("[^"]*")|(\((?:[^()"]|(?:\([^()"]*\)))*\))/g, (match, quoted, parens) => {
            if (quoted) return quoted;
            if (!parens) return match;

            const content = parens.slice(1, -1);
            // Safety check: if content is just a quoted string?
            if (content.trim().startsWith('"') && content.trim().endsWith('"')) return match;

            // Double circle protection
            if (parens.startsWith('((') && parens.endsWith('))')) return match;

            if (/[:\/\.\(\)]/.test(content)) {
                return `("${content}")`;
            }
            return match;
        });

        return fixedLine;
    });
    return fixedLines.join('\n');
}

const inputs = [
    "B --> C{Middleware (apps/client-ssr/middleware.ts)}",
    "subgraph My Subgraph (Details)",
    "D{Simple}",
    "E{Rhombus with (nested) parens}",
    "F{Already \"Quoted\"}"
];

inputs.forEach(input => {
    console.log("Original:", input);
    console.log("Fixed:   ", fixMermaidCode(input));
    console.log("---");
});
