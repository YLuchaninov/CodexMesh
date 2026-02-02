# CodexMesh Web UI Guide

The CodexMesh Web UI is a comprehensive control plane for managing your codebase intelligence, configuring AI agents, and performing manual or automated code analysis.

## Overview

The interface is divided into several functional zones:

1.  **Project Panel**: Manage connections to your local repositories.
2.  **Files Section**: Navigate the codebase and view file-level graph status.
3.  **Tools & Intents**: Execute individual graph tools or high-level reasoning workflows.
4.  **Chat Interface**: The primary interaction point with the **Reviewer Agent**.
5.  **Settings**: Configure LLM providers, embedding engines, and hotspot scoring.

---

## Chat Modes

CodexMesh provides four distinct chat modes to balance speed, depth, and autonomy:

### 1. **Quick**
*   **Best for**: Fast questions about specific symbols or functions.
*   **Behavior**: Uses a very limited conversation history and skips deep semantic search fallbacks if an intent isn't immediately matched.
*   **Advantage**: Minimal token usage and fast response times.

### 2. **Standard** (Default)
*   **Best for**: General navigation and "how does this work" questions.
*   **Behavior**: Balanced history window and includes semantic search fallback to provide context even when specific identifiers aren't mentioned.

### 3. **Deep**
*   **Best for**: Complex architectural questions or impact analysis.
*   **Behavior**: Provides the largest possible conversation history and context window to the LLM. 

### 4. **Autopilot**
*   **Best for**: Abstract tasks like "Compare two implementations" or "Find all risks in the payment flow".
*   **Behavior**: Instead of a single response, Autopilot uses an **Agentic Loop**:
    1.  **Planning**: An agent analyzes your query and selects multiple tools or workflows to run.
    2.  **Execution**: The system runs these tools sequentially (e.g., search, then call graph, then hotspot check).
    3.  **Synthesis**: A final agent combines all tool outputs into a comprehensive answer.

---

## Chat Features

*   **Pinned Context (System Instructions)**: Click the **Chevron** in the chat header to open the Pinned Context drawer. Use this to provide persistent instructions (e.g., "Always suggest SOLID improvements" or "Focus on security vulnerabilities") that will be included in every message.
*   **Evidence Pills**: When the agent finds relevant code, it displays "Evidence" buttons below its message. Click them to instantly jump to the file and highlight the relevant lines.
*   **Copy Chat**: Export the entire conversation as formatted Markdown for your reports.

---

## Navigation & Shortcuts

### **Command Palette (Ctrl+K / Cmd+K)**
The Command Palette is the fastest way to navigate the system. Press `Ctrl+K` (or `Cmd+K` on Mac) to:
*   Search for any **Tool** (e.g., Search, Graph, Hotspots).
*   Search for any **Intent** (e.g., Impact analysis, Feature slice).
*   Jump directly to file analysis.

### **Global Shortcuts**
*   **Ctrl+K / Cmd+K**: Open Command Palette.
*   **Esc**: Close modals or Command Palette.
*   **Enter**: Send message in Chat or execute tool in runner.

---

## Settings & Configuration

### LLM Settings (Gemini)
Configure your Gemini API key and model (e.g., `gemini-1.5-pro-latest`) to enable Chat and Autopilot features.

### System Settings
*   **Embeddings**: Change the engine (default: `fastembed`) and model. **Warning**: Changing these requires a full re-indexing of your projects.
*   **Hotspot Scoring**: Manually adjust weights for Churn, Lint errors (E/F), Warnings, TODOs, and Graph Centrality.
*   **Auto-Tune**: Click the **Wand** icon to automatically calibrate hotspot weights based on the statistical profile of your specific repository.

---

## Visualizations

Many tools (like `get_subgraph` or `feature_slice`) generate **Mermaid.js** diagrams. The Web UI renders these diagrams interactively, allowing you to visualize call paths and dependency cycles directly in the dashboard.
