
/**
 * Complex JavaScript fixture for testing extraction depth.
 */

// Import aliasing
import { x as renamedX } from "./b.js";
import defaultExport, { part1, part2 } from "./other.js";

/**
 * A class with decorators and methods.
 */
@classDecorator
export class HeavyClass extends BaseClass {
    /**
     * Method docstring.
     */
    @methodDecorator
    async compute(a, b) {
        const result = renamedX(a) + b;
        this.log(result);
        return result;
    }

    log(msg) {
        console.log(msg);
    }
}

/**
 * Top-level function with various styles of docs.
 */
// Single line doc
// with multiple lines
export function processAll(items) {
    const app = new HeavyClass();
    return items.map(i => app.compute(i, 1));
}

// Main guard-like pattern (Node.js style)
if (require.main === module) {
    processAll([1, 2, 3]);
}
