# CodexMesh — Codebase Intelligence Engine (MCP)

CodexMesh is a **codebase intelligence layer** exposed through **MCP tools**. It turns a repository into a structured graph of **entrypoints**, **call chains**, **imports**, **symbol containment**, **dependency paths**, **hotpoints (hotspots)**, and (optionally) **semantic retrieval** — with **line-accurate evidence**.

It is designed to work with **agent systems where the LLM already exists** (Cursor / Claude / Copilot / custom agents). The agent handles chat, memory, and reasoning, while CodexMesh provides **verified data** and **clickable evidence** that leads you to the exact code responsible for behavior.

---

## What problems it solves

### Wrong file / shallow understanding

LLMs often guess based on names and limited context. CodexMesh gives deterministic structure:

* **Entrypoints → call graphs → dependency paths → data sinks**
* Real graph edges and metadata (not “dummy” relationships)
* Tracking **unresolved** calls/imports with candidates and confidence (no silent drops)

### No proof / hard-to-trust answers

CodexMesh is **evidence-first**:

* Results include **file + line range + snippet**
* Any mention like `path/to/file:120-165` can be used as a **one-click jump** to open the file and highlight the responsible lines

### Real-world repo resilience

Large monorepos, generated code, binaries, messy histories and encodings shouldn’t break tooling:

* **Degraded mode** (partial answers instead of crashes)
* Strict limits and safe reading
* Health reporting and index diagnostics

---

## Core capabilities

### Graph intelligence

* **Entrypoints map** (ranked web/CLI/worker/tests entrypoints, with “why” + evidence)
* **Call graphs** (in/out/both, depth/limits, branch visibility, unresolved tracking)
* **Dependency paths** (real nodes/edges + metadata for debugging and impact analysis)
* **Module/import graphs** and **cycle explanations**
* **Symbols & references** (resolve symbols, find references, callers/callees, containment/inheritance relations)

### Evidence-first navigation

CodexMesh outputs are structured so UIs/agents can implement:

* **Click-to-open** file references
* **Highlight exact line ranges**
* Minimal snippets (spans) for quick verification and low-token prompting

### Documentation support (partial)

CodexMesh provides **partial documentation awareness**:

* Index and search docs (e.g., Markdown and other text formats)
* Return doc hits with file/line spans where supported
* Bridge doc references to code files/symbols to build mixed **docs + code context packs**

### Hotpoints (hotspots)

Hotpoints are **structural complexity / risk centers** in the code graph:

* Nodes (files/symbols/modules) with outsized influence or change impact
* Scored using graph signals such as:

  * fan-in / fan-out
  * centrality-like measures
  * proximity to cycles
  * reachability across key entrypoints
* “Explain” outputs include score breakdown, top neighbors, cycle proximity, and evidence for edges driving the score

---

## JSON Flows (agent orchestration)

CodexMesh supports **JSON flows**: predefined, machine-readable workflows that describe how an agent should call tools to answer a class of questions.

**Why it matters:**

* **Deterministic** orchestration (less wandering)
* **Reproducible** results (easy to replay the same tool plan)
* **Auditable** usage (policy-friendly in enterprise)
* **Token-efficient** prompting (minimal spans instead of whole files)

Flows are especially useful when running **local/on-prem LLMs**, where reducing tokens and round-trips makes the experience feel significantly faster.

---

## Web UI vs MCP

CodexMesh typically ships with both:

### MCP (core)

* The integration surface for agents
* **LLM-agnostic**: can run fully without any LLM
* Provides structured tools + evidence

### Web UI (control plane)

* Configuration, observability, and convenience (projects, indexes, settings, providers)
* May optionally include LLM-driven review/chat features depending on how you deploy it
* Not required for agents that only need MCP tools

---

## Security & privacy (enterprise-friendly)

CodexMesh is designed to keep source code under your control:

* Runs locally/on-prem as an MCP tool server
* **No code exfiltration by default**
* Read-only posture is compatible with strict enterprise approvals
* Supports deployments that use **local/on-prem LLMs** via the agent, keeping prompts and code on your network
* Encourages **data minimization**: send only necessary evidence spans and context packs, not entire files

---

## Performance: bridging LLM speed gaps

Local LLMs can be slower than cloud models. CodexMesh compensates by:

* Producing **high-signal, minimal context** (spans + context packs)
* Using **graph expansion** to recover system flow without brute-force reading
* Leveraging caching and incremental indexing so repeated tool calls remain fast and predictable

A typical pattern:

1. Get ranked entrypoints
2. Build a bounded call graph
3. Find a path to a target layer
4. Fetch only the relevant spans
5. Let the LLM summarize just that evidence

---

## Why it’s different

CodexMesh isn’t “another AI chat”. It’s a **fact engine**:

* **MCP-first** and **LLM-agnostic**
* Outputs are **structured**, **reproducible**, and **evidence-backed**
* Enables **click-to-open + highlight** debugging navigation
* Designed for secure, enterprise-friendly, local/on-prem deployments
* Makes any agent system materially more correct by supplying deterministic structure and verified context

---

## Supported Languages

CodexMesh builds a **structural code graph** (symbols + relationships) primarily via **Tree-sitter AST parsing**, and augments it with **semantic search** and **documentation linking**.

### Code (Tree-sitter graph)
- **Python**
- **JavaScript / TypeScript**
- **Go**
- **Rust**
- **Java**
- **Kotlin**
- **C / C++**
- **C#**
- **PHP**
- **Ruby**
- **Dart**
- **Swift**
- **Scala**

### SQL (SQLGlot)
- **SQL** parsing + structural extraction via SQLGlot (PostgreSQL, MySQL, SQLite, etc.). Useful for query-heavy projects and migrations.

### Documentation (partial)
- **Markdown docs** are indexed into **doc sections**, can be **linked to code symbols**, and can be audited for **staleness** (docs updated later than code, or vice versa).

---

## Support Depth by Language (practical expectations)

| Language | Graph extraction | Symbol types | Relationships | Notes |
|---|---|---|---|---|
| Python | Strong | files, classes, functions, methods | imports, basic calls, inheritance | Doc/comments extraction focuses on text **above** definitions (not in-body docstrings). |
| JS / TS | Medium → Strong | files, functions, classes (where available) | imports, basic calls | Good for modern TS/React repos (entrypoints + module graph works well). |
| Go | Medium | types, funcs, methods | imports, basic calls | Clean AST makes symbol extraction reliable. |
| Rust | Medium | structs/enums, impl fns | module relations, basic calls | Needs grammar/query tuning per idioms/macros. |
| Java / Kotlin | Medium | classes, methods | imports, inheritance, basic calls | Works well for typical OOP layouts. |
| C / C++ | Medium | funcs, structs/classes (limited) | includes/imports, basic calls | Preprocessor-heavy projects reduce precision. |
| C# | Medium | classes, methods | using/imports, basic calls | Good for typical .NET layouts. |
| PHP / Ruby | Partial → Medium | funcs, classes | limited calls/relations | Dynamic patterns reduce call-link confidence; improves with query tuning + heuristics. |
| Dart | Medium | classes, funcs | imports, basic calls | Good for Flutter-style repos. |
| Swift | Medium | types, funcs | imports, basic calls | Works best with clean Swift modules. |
| Scala | Partial → Medium | classes/objects, defs | imports, limited calls | Syntax richness may need extra query tuning. |
| SQL (SQLGlot) | Strong (for SQL) | statements, referenced tables/cols | references/dependencies | Complements code graph for data-heavy systems. |
| Markdown docs | Partial | doc sections | documents→symbol links | Includes docs map + doc coverage + staleness audit. |

---

## What else to mention (often forgotten, but highly “sellable”)

- **30+ MCP tools** out of the box (graph search, semantic search, hotspots, repomap, entrypoints, subgraph/tree/path, rendering).  
- **Intent / JSON workflows** (`list_intents`, `execute_intent`) for multi-step reasoning without hardcoding agent logic.  
- **Graph rendering** to Mermaid for instant visualization (subgraphs, neighborhoods, paths).  
- **Tracing / auditability**: workflow/tool steps can be recorded and exported as a trace subgraph.  
- **Semantic search storage** via **LanceDB**, embeddings via **FastEmbed** (with local cache), plus “has_index / reindex” style lifecycle.  
- **Auto-Tuner**: `autotune_hotspots` tool to automatically calibrate scoring weights to your repository's statistical profile.
- **Docs tooling**: docs map, doc coverage metrics, and staleness audit for doc→code links.  
- **Ignore system** (.codexignore + defaults like node_modules/.git/dist) so it stays stable across messy repos.  
- **Raw JSON variants** for most tools (`*_raw`) to make agent integration deterministic and UI-friendly.  
- **Entry points + reachability**: quickly narrow the code that is actually reachable from user-facing roots.  
- **Hotspots** combine lint/TODO/churn/coupling signals into a prioritized “where AI will struggle” list.  
- **Call-linking heuristics** to reduce false positives (same-file, same-class, otherwise skip ambiguous).  
- **Failure modes are observable** (status snapshot, busy/progress).
- **Docs can be included into semantic search** (opt-in) so “how to use X” queries find docs + code in one pass.

---

