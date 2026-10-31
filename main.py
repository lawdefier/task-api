"""
Task API — FlyRank W2 · A1
Stage 1: Root and health endpoints
"""

from fastapi import FastAPI

app = FastAPI(title="Task API")


@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}
