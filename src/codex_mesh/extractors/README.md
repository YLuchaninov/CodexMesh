# CodexMesh Extractors Module

## Purpose
This module contains decoupled, language-specific extractors for the CodexMesh analysis engine. It follows a plugin-based architecture where improved support for new languages can be added via the `ExtractorRegistry`.

## Structure
- `protocols.py`: Defines the `Extractor` and `ExtractionResult` contracts.
- `registry.py`: Manages extractor registration and file extension mapping.
- `python_treesitter.py`: Dedicated Python extractor (rich analysis).
- `sqlglot_extractor.py`: Dedicated SQL extractor (lineage analysis).
- `treesitter_query.py`: Generic extractor using `tree-sitter-language-pack` for other languages.
- `builtin_treesitter.py`: Configuration for built-in languages (JS, TS, Rust, Java, C++, etc.).

## Adding a New Extractor
To add support for a new language, either:
1.  Add a configuration to `builtin_treesitter.py` if it's supported by `tree-sitter-language-pack`.
2.  Implement the `Extractor` protocol in a new class and register it via `codex_mesh.extractors` entry point or explicitly in `registry.py`.

## Capabilities
| Language | Implementation | Features |
| :--- | :--- | :--- |
| Python | `PythonTreeSitterExtractor` | Classes, Functions, Imports, Calls, Docstrings, **Main guard detection** (auto-entrypoints) |
| SQL | `SqlGlotExtractor` | Tables, Columns, Lineage (READS/WRITES) |
| JS / TS | `TreeSitterQueryExtractor` | Symbols, Imports (Local Resolution), Calls, Bases, Docstrings |
| Go / Rust | `TreeSitterQueryExtractor` | Symbols, Imports (Local Resolution), Calls, Docstrings |
| Java / Kotlin | `TreeSitterQueryExtractor` | Symbols, Imports, Calls, Bases, Docstrings |
| C / C++ / C# | `TreeSitterQueryExtractor` | Symbols, Imports, Calls, Bases, Docstrings |
| PHP / Ruby | `TreeSitterQueryExtractor` | Symbols, Imports, Calls, Bases, Docstrings |
| Dart / Swift | `TreeSitterQueryExtractor` | Symbols, Imports, Calls, Bases, Docstrings |
