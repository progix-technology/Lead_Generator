import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    is_debug = os.environ.get("ENVIRONMENT", "development") == "development"
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=is_debug)
