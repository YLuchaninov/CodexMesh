
/**
 * Complex TypeScript fixture for testing extraction depth.
 */

import { util, UtilityClass } from "./lib";

export interface Processor {
    process(data: string): number;
}

/**
 * TS Class with modifiers and generic bases.
 */
export class DataProcessor<T> extends UtilityClass implements Processor {
    private _cache: Map<string, T> = new Map();

    constructor(public name: string) {
        super();
    }

    /**
     * Public method with signature and modifiers.
     */
    public async process(data: string): Promise<number> {
        util();
        return data.length;
    }
}

export function runMain() {
    const p = new DataProcessor<number>("Test");
    p.process("hello");
}
