import json
import os
import sys

# Add the project root to sys.path to allow importing netpulse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from netpulse.controller import app
    
    output_path = "ai-docs/openapi.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully exported OpenAPI schema to {output_path}")
except ImportError as e:
    print(f"❌ Error: Could not import NetPulse app. Make sure dependencies are installed. {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ An error occurred: {e}")
    sys.exit(1)
