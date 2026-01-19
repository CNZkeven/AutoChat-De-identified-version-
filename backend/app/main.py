import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .db import Base, engine
from .routers import auth, chat, conversations, courses, export, knowledge, memory, rag, tools

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="AutoChat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(export.router)
app.include_router(courses.router)
app.include_router(knowledge.router)
app.include_router(rag.router)
app.include_router(tools.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
