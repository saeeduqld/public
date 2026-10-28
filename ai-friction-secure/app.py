"""Small, server-side OpenRouter proxy for AI friction research pilot.

Secrets are read only from environment/.env and never sent to browsers.
This is a research pilot, not a public production or clinical service.
"""
import asyncio
import hmac
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, model_validator

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
app = FastAPI(title="AI Friction Research Lab", docs_url=None, redoc_url=None)


def settings():
    return {
        "key": os.getenv("OPENROUTER_API_KEY", "").strip(),
        "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini").strip(),
        "access_code": os.getenv("APP_ACCESS_CODE", "").strip(),
        "max_per_hour": max(1, int(os.getenv("MAX_REQUESTS_PER_IP_PER_HOUR", "60"))),
    }


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    arm: Literal["vanilla", "friction"]
    messages: list[Message] = Field(min_length=1, max_length=30)
    temperature: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def check_design(self):
        roles = [m.role for m in self.messages]
        if self.arm == "vanilla" and "system" in roles:
            raise ValueError("Vanilla AI must not receive a system prompt")
        if self.arm == "friction" and (not roles or roles[0] != "system" or roles.count("system") != 1):
            raise ValueError("Friction AI requires exactly one first-position system prompt")
        if not any(m.role == "user" for m in self.messages):
            raise ValueError("At least one user message is required")
        return self


# In-memory limit suitable only for a small pilot on one free instance.
# Set a spend limit on the OpenRouter key as the primary cost protection.
_hits = defaultdict(deque)
_lock = asyncio.Lock()


async def rate_limit(client_id: str, max_per_hour: int):
    now = time.monotonic()
    async with _lock:
        times = _hits[client_id]
        while times and times[0] < now - 3600:
            times.popleft()
        if len(times) >= max_per_hour:
            raise HTTPException(status_code=429, detail="Pilot usage limit reached. Please try again later.")
        times.append(now)


@app.get("/")
async def homepage():
    return FileResponse(HERE / "index.html", media_type="text/html", headers={"Cache-Control":"no-store"})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/config")
async def config():
    s = settings()
    return JSONResponse({
        "model": s["model"],
        "access_code_required": True,
        "ready": bool(s["key"] and s["model"] and s["access_code"]),
    }, headers={"Cache-Control": "no-store"})


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request, x_lab_access_code: str = Header(default="")):
    s = settings()
    if not s["key"] or not s["model"] or not s["access_code"]:
        raise HTTPException(status_code=503, detail="The server owner must configure the research lab.")
    if not hmac.compare_digest(x_lab_access_code, s["access_code"]):
        raise HTTPException(status_code=403, detail="Invalid pilot access code.")
    await rate_limit(request.client.host if request.client else "unknown", s["max_per_hour"])

    # Model is ALWAYS selected server-side. The browser cannot override it.
    payload = {
        "model": s["model"],
        "messages": [m.model_dump() for m in req.messages],
        "temperature": req.temperature,
        "max_completion_tokens": 650,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=65.0) as client:
            response = await client.post(
                OPENROUTER_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {s['key']}",
                    "Content-Type": "application/json",
                    "X-OpenRouter-Title": "AI Friction Research Test Lab",
                },
                json=payload,
            )
        if response.status_code >= 400:
            # Never echo provider response details, request headers or secrets.
            raise HTTPException(status_code=502, detail=f"Model provider request failed (status {response.status_code}).")
        data = response.json()
        answer = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not isinstance(answer, str) or not answer.strip():
            raise HTTPException(status_code=502, detail="The model returned no readable reply.")
        return JSONResponse({
            "message": answer.strip(),
            "model": data.get("model", s["model"]),
            "usage": data.get("usage"),
            "id": data.get("id"),
        }, headers={"Cache-Control": "no-store"})
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="The model provider is currently unreachable.")