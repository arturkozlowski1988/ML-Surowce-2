import json
import os

config_path = r"c:\Users\Artut\.gemini\antigravity\mcp_config.json"
output_path = "mcp_config_dump.json"

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
        try:
            data = json.loads(content)
            print(json.dumps(data, indent=2))
            # Also save to local file just in case
            with open(output_path, 'w', encoding='utf-8') as out:
                json.dump(data, out, indent=2)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print("Raw content:")
            print(content)
except Exception as e:
    print(f"Error reading file: {e}")
