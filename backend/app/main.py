import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from .config import CORS_ORIGINS
from .db import Base, SessionLocal, engine
from .models import User
from .routers import admin, auth, chat, conversations, courses, dm, export, knowledge, memory, rag, tools
from .security import hash_password
from .services.dm_bootstrap import ensure_dm_rls, ensure_dm_schemas

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
    ensure_dm_schemas(engine)
    Base.metadata.create_all(bind=engine)
    ensure_dm_rls(engine)
    db = SessionLocal()
    try:
        demo_user = db.query(User).filter(User.username == "demo").first()
        if not demo_user:
            db.add(
                User(
                    username="demo",
                    email=None,
                    hashed_password=hash_password("demo@Just"),
                )
            )
            db.commit()
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            db.add(
                User(
                    username="admin",
                    email=None,
                    hashed_password=hash_password("admin@Just"),
                )
            )
            db.commit()
    except SQLAlchemyError:
        logging.exception("Failed to ensure demo user exists")
        db.rollback()
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(export.router)
app.include_router(courses.router)
app.include_router(dm.router)
app.include_router(knowledge.router)
app.include_router(rag.router)
app.include_router(tools.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
