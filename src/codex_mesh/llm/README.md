# CodexMesh LLM Module

## Purpose
This module handles integration with Large Language Models (LLMs), specifically Google Gemini via LangChain. It provides reasoning capabilities for code analysis and a high-level "Reviewer Agent".

## Structure
- `reviewer.py`: The `ReviewerAgent` class. Orchestrates analysis tools and LLM reasoning to answer codebase questions.
- `gemini_settings.py`: Configuration management for Gemini API (keys, models, parameters).
- `command_handler.py`: (Internal) Logic for handling LLM-generated commands.

## Usage
The `ReviewerAgent` is the primary interface.

```python
from codex_mesh.llm.reviewer import ReviewerAgent
from codex_mesh.services.analysis_service import AnalysisService
from codex_mesh.services.fs_service import FileSystemService

agent = ReviewerAgent(analysis_service, fs_service)
# Supports conversation history for multi-turn reasoning
response = await agent.ask(
    "How does the indexing flow work?",
    history=[{"role": "user", "content": "..."}]
)
print(response["answer"])
```

## Dependencies
- **External**: `langchain`, `langchain-google-genai`, `pydantic`
- **Internal**: `codex_mesh.services`, `codex_mesh.config`
