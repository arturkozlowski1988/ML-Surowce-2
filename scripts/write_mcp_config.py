import json
import os

config_path = r"c:\Users\Artut\.gemini\antigravity\mcp_config.json"

new_config = {
  "mcpServers": {
    "mcp-toolbox-for-databases": {
      "command": "npx",
      "args": [
        "-y",
        "@toolbox-sdk/server",
        "--tools-file=/path/to/tools.yaml",
        "--stdio"
      ],
      "env": {}
    },
    "cloud-sql-sqlserver-admin": {
      "command": "npx",
      "args": [
        "-y",
        "@toolbox-sdk/server",
        "--prebuilt",
        "cloud-sql-mssql-admin",
        "--stdio"
      ],
      "env": {}
    },
    "sequential-thinking": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sequential-thinking"
      ],
      "env": {}
    },
    "mssql": {
      "command": "npx",
      "args": [
        "-y",
        "mssql-mcp-server"
      ],
      "env": {
        "MSSQL_CONNECTION_STRING": "Server=127.0.0.1,61470;Database=cdn_test;User Id=sa;Password=Cti123456&;Encrypt=true;TrustServerCertificate=true;"
      }
    }
  }
}

try:
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, indent=2)
    print(f"Successfully wrote config to {config_path}")
except Exception as e:
    print(f"Error writing file: {e}")
