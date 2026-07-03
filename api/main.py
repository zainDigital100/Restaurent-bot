"""
FastAPI wrapper. Notice this file is short — that's the point of building
chatbot.py as a separate, framework-agnostic module. This file's only job
is: parse HTTP request -> call bot logic -> return HTTP response. If you
find yourself putting actual bot logic here (prompt building, tool calls),
that's a sign it belongs in bot/chatbot.py instead.

Run:
    uvicorn main:app --reload

Then POST to http://127.0.0.1:8000/chat
"""

import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from bot.chatbot import send_message, reset_session
app = FastAPI(title="Restaurant Chatbot API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    reply = send_message(session_id, req.message)
    return ChatResponse(session_id=session_id, reply=reply)


@app.post("/api/reset/{session_id}")
def reset(session_id: str):
    reset_session(session_id)
    return {"status": "reset", "session_id": session_id}


@app.get("/api/health")
def health():
    return {"status": "ok"}
@app.get("/")
def read_root():
    return {"message": "Chatbot API is running"}
