import os
import uvicorn

if __name__ == "__main__":
    # PORT is the convention used by Render/Railway/Fly.io/Docker; FDC_PORT stays
    # as the local Windows/macOS demo default (8174) for backward compatibility.
    port = int(os.getenv("PORT", os.getenv("FDC_PORT", "8174")))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
