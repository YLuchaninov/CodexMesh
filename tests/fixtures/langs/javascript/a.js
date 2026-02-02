
import { x } from "./b.js";

export class A { m(x) { return x + 1; } }
export function f() { return new A().m(1); }
