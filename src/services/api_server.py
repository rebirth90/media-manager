import sys
from typing import Dict
import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="Secure PyQt6 + FastAPI Service",
    description="A cleanly architected Python micro-desktop application.",
    version="1.0.0"
)

@app.get("/", response_model=Dict[str, str])
async def root_status() -> Dict[str, str]:
    return {"status": "success", "message": "Secure Local Server is Running."}

def run_server(host: str, port: int) -> None:
    try:
        config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"Error starting Uvicorn background server: {e}", file=sys.stderr)
