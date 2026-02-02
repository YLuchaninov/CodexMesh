"""
Debug reproduction script for CodexMesh MCP Server.
"""

import json
import subprocess
import time


def run_debug_session():
    # Start the server
    cmd = ["uv", "run", "codex-mesh"]
    print(f"Starting server: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,  # Unbuffered
    )

    # 1. Initialize
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "debug-script", "version": "1.0"},
        },
    }

    print("\n--> Sending Initialize...")
    process.stdin.write(json.dumps(init_req) + "\n")
    process.stdin.flush()

    # Read response (blocking simpler for script)
    line = process.stdout.readline()
    print(f"<-- Received: {line.strip()}")

    # Send Initialized notification
    process.stdin.write(
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
    )
    process.stdin.flush()

    # 2. Trigger semantic_search (The failure case)
    search_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "semantic_search",
            "arguments": {"query": "show me the biggest project problems", "k": 5},
        },
    }

    print("\n--> Sending semantic_search...")
    process.stdin.write(json.dumps(search_req) + "\n")
    process.stdin.flush()

    # Wait a bit for logs to flush
    time.sleep(2)

    # Read response
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(f"<-- Received: {line.strip()}")
        if "id" in line and "2" in line:  # response to our request
            break

    print("\nCheck codex_mesh_mcp.log for details.")
    process.terminate()


if __name__ == "__main__":
    run_debug_session()
