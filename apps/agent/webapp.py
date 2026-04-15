"""ASGI app exposed to LangGraph for custom HTTP routes."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.upload_routes import router as upload_router

app = FastAPI(title="Agent custom routes")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
