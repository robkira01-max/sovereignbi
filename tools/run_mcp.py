#!/usr/bin/env python3
"""MizanBI MCP server entry point — stdio transport for Claude Code.

Usage:
    python tools/run_mcp.py

Configuration via environment variables:
    SOVEREIGN_MCP_BASE_URL   Backend URL (default: http://localhost:9001)
    SOVEREIGN_VIEWER_KEY     API key   (default: viewer)

Add to Claude Code (~/.claude.json) :
    {
      "mcpServers": {
        "mizanbi": {
          "command": "python",
          "args": ["/home/kali/sovereignbi/tools/run_mcp.py"],
          "env": {
            "SOVEREIGN_MCP_BASE_URL": "https://sovereignbi-api.147-5-126-188.sslip.io",
            "SOVEREIGN_VIEWER_KEY": "viewer"
          }
        }
      }
    }
"""
import sys
from pathlib import Path

# allow `python tools/run_mcp.py` from any working dir
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.mcp.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
