
import { x } from "./b";

export class A { m(x: number): number { return x + 1; } }
export function f(): number { return new A().m(1); }
