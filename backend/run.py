import os
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    is_debug = os.environ.get("ENVIRONMENT", "development") == "development"
    reload_dirs = [BACKEND_DIR] if is_debug else None
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=is_debug, reload_dirs=reload_dirs)
