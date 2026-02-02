/**
 * Payload builder for tool forms.
 *
 * Handles dotted paths, CSV arrays, and JSON parsing for tool forms.
 */
import type { ToolFormField } from './types';

function setDeep(obj: any, path: string, value: any): void {
    const parts = path.split('.');
    let cur = obj;
    for (let i = 0; i < parts.length - 1; i++) {
        const k = parts[i];
        if (cur[k] == null || typeof cur[k] !== 'object') cur[k] = {};
        cur = cur[k];
    }
    cur[parts[parts.length - 1]] = value;
}

function parseCsv(value: string): string[] {
    return value
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
}

function isJsonLike(s: string): boolean {
    const t = s.trim();
    return (t.startsWith('{') && t.endsWith('}')) || (t.startsWith('[') && t.endsWith(']'));
}

/**
 * Build payload from form fields and values.
 *
 * Heuristics:
 * - fields named roots/edge_types/prefer_types/context.files => CSV -> array
 * - fields named "input" => JSON.parse if JSON-like; otherwise keep string
 * - dotted names set nested objects
 */
export function buildPayload(
    fields: ToolFormField[],
    values: Record<string, any>
): Record<string, any> {
    const payload: any = {};

    for (const f of fields) {
        const raw = values[f.name];

        // if empty string and default exists, use default; if empty and no default, skip
        const hasUserValue =
            raw !== undefined && raw !== null && !(typeof raw === 'string' && raw.trim() === '');
        const v0 = hasUserValue ? raw : f.default !== undefined ? f.default : undefined;
        if (v0 === undefined) continue;

        let v: any = v0;

        // coerce by type
        if (f.type === 'number') {
            const num = typeof v === 'number' ? v : Number(v);
            if (!Number.isFinite(num)) continue;
            v = num;
        } else if (f.type === 'boolean') {
            v = Boolean(v);
        } else if (f.type === 'string') {
            v = String(v);
        } else if (f.type === 'select') {
            v = v; // already a string/option
        }

        // heuristics for arrays / JSON
        const lname = f.name.toLowerCase();
        const arrayish =
            lname.endsWith('roots') ||
            lname.endsWith('edge_types') ||
            lname.endsWith('prefer_types') ||
            lname.endsWith('context.files') ||
            lname.endsWith('context.pinned_results');

        if (arrayish && typeof v === 'string') {
            v = parseCsv(v);
        }

        if (lname === 'input' && typeof v === 'string') {
            const t = v.trim();
            if (t === '') {
                v = {};
            } else if (isJsonLike(t)) {
                try {
                    v = JSON.parse(t);
                } catch {
                    /* keep string */
                }
            }
        }

        setDeep(payload, f.name, v);
    }

    return payload;
}
