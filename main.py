"""
Task API — FlyRank W2 · A1
Stage 0: Hello server
"""

from fastapi import FastAPI

app = FastAPI(title="Task API")


@app.get("/")
def root():
    return {"message": "Hello, server!"}
