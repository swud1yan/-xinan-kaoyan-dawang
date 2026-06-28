"""
Xinan Dawang Backend v3.0 - FastAPI Application Entry
"""
import os
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, AsyncSessionLocal, Base
from app.config import get_settings

settings = get_settings()
logging.basicConfig(level=logging.INFO)

async def ensure_sqlite_schema(conn):
    """Patch additive SQLite columns for existing local databases."""
    from sqlalchemy import text

    result = await conn.execute(text("PRAGMA table_info(users)"))
    existing = {row[1] for row in result.fetchall()}
    user_columns = {
        "level": "INTEGER DEFAULT 1",
        "vip_level": "INTEGER DEFAULT 0",
        "xp": "INTEGER DEFAULT 0",
        "vip_expire_at": "DATETIME",
        "monthly_coins": "INTEGER DEFAULT 0",
        "monthly_coins_max": "INTEGER DEFAULT 100",
        "purchased_coins": "INTEGER DEFAULT 0",
        "coins_reset_date": "DATETIME",
        "deep_think_enabled": "BOOLEAN DEFAULT 0",
        "sign_in_streak": "INTEGER DEFAULT 0",
        "last_sign_in_date": "DATETIME",
        "pomodoro_count": "INTEGER DEFAULT 0",
        "has_target": "BOOLEAN DEFAULT 0",
        "target_school": "VARCHAR(100)",
        "direction": "VARCHAR(50)",
        "progress": "VARCHAR(30)",
        "estimated_score": "VARCHAR(20)",
        "study_style": "VARCHAR(20)",
        "undergrad_province": "VARCHAR(20)",
        "undergrad_school": "VARCHAR(100)",
        "undergrad_private": "BOOLEAN DEFAULT 0",
        "is_banned": "BOOLEAN DEFAULT 0",
        "ban_expire_at": "DATETIME",
        "muted_until": "DATETIME",
        "is_whitelist": "BOOLEAN DEFAULT 0",
        "token_used": "INTEGER DEFAULT 0",
        "token_limit": "INTEGER DEFAULT 100000",
        "dawang_id_updated_at": "DATETIME",
        "registered_ip": "VARCHAR(50)",
        "last_login_ip": "VARCHAR(50)",
        "last_login_at": "DATETIME",
        "updated_at": "DATETIME",
    }
    for name, ddl in user_columns.items():
        if name not in existing:
            await conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))

    # Migrate posts.visibility
    r = await conn.execute(text("PRAGMA table_info(posts)"))
    post_cols = {row[1] for row in r.fetchall()}
    if "visibility" not in post_cols:
        await conn.execute(text("ALTER TABLE posts ADD COLUMN visibility VARCHAR(20) DEFAULT 'public'"))

    # Migrate comments.reply_to
    r = await conn.execute(text("PRAGMA table_info(comments)"))
    cmt_cols = {row[1] for row in r.fetchall()}
    if "reply_to" not in cmt_cols:
        await conn.execute(text("ALTER TABLE comments ADD COLUMN reply_to VARCHAR(36)"))


async def init_db():
    """Create all tables and insert seed data"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_sqlite_schema(conn)

    from sqlalchemy import select
    import uuid

    async with AsyncSessionLocal() as session:

        # 1. National schools seed (150+)
        from app.models.national import NationalSchool
        school_count = await session.execute(select(NationalSchool).limit(1))
        if school_count.scalar_one_or_none() is None:
            from app.services.national_schools import NATIONAL_SCHOOLS
            from app.models.national import NationalProgram, NationalScoreLine
            for s in NATIONAL_SCHOOLS:
                sid = str(uuid.uuid4())
                school = NationalSchool(
                    id=sid, name=s["name"], province=s["province"],
                    city=s["city"], tags=s["tags"], school_type=s["type"],
                    level=s["level"]
                )
                session.add(school)
                for p in s["programs"]:
                    pid = str(uuid.uuid4())
                    session.add(NationalProgram(
                        id=pid, school_id=sid, name=p["name"],
                        degree_type=p["degree"], subjects=p["subjects"],
                        is_unified=p["is_unified"], unified_name=p.get("unified_name")
                    ))
                    for line in p["lines"]:
                        session.add(NationalScoreLine(
                            program_id=pid, year=line["year"],
                            total_score=line["total"], politics_score=line["pol"],
                            english_score=line["eng"], biz1_score=line["b1"],
                            biz2_score=line["b2"]
                        ))
            await session.commit()
            logging.info(f"Seeded {len(NATIONAL_SCHOOLS)} national schools")

        # 2. Subject catalog
        from app.models.national import SubjectCatalog
        cat_count = await session.execute(select(SubjectCatalog).limit(1))
        if cat_count.scalar_one_or_none() is None:
            from app.services.seed_data import SUBJECT_CATALOG
            for item in SUBJECT_CATALOG:
                session.add(SubjectCatalog(
                    code=item["code"], name=item["name"], level=item["level"],
                    parent_id=None
                ))
            await session.commit()
            logging.info(f"Seeded {len(SUBJECT_CATALOG)} subject catalog entries")

        # 3. Undergrad schools (云贵川渝)
        from app.models.national import UndergradSchool
        ug_count = await session.execute(select(UndergradSchool).limit(1))
        if ug_count.scalar_one_or_none() is None:
            from app.services.seed_data import UNDERGRAD_SCHOOLS
            for item in UNDERGRAD_SCHOOLS:
                session.add(UndergradSchool(
                    name=item["name"], province=item["province"],
                    city=item["city"], school_type=item["type"]
                ))
            await session.commit()
            logging.info(f"Seeded {len(UNDERGRAD_SCHOOLS)} undergrad schools")

        # 4. Original score lines (keep compatibility)
        from app.models.score_line import ScoreLine
        old_count = await session.execute(select(ScoreLine).limit(1))
        if old_count.scalar_one_or_none() is None:
            from app.services.scraper import SEED_SCORE_LINES
            for item in SEED_SCORE_LINES:
                session.add(ScoreLine(**item))
            await session.commit()

        # 5. Exam papers
        from app.models.exam_paper import ExamPaper
        exam_count = await session.execute(select(ExamPaper).limit(1))
        if exam_count.scalar_one_or_none() is None:
            from app.services.zhenti_service import SEED_EXAM_PAPERS
            for item in SEED_EXAM_PAPERS:
                session.add(ExamPaper(**item))
            await session.commit()


# WebSocket connection manager
class WSManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(ws)

    def disconnect(self, user_id: str, ws: WebSocket):
        if user_id in self.connections:
            self.connections[user_id].remove(ws)

    async def send(self, user_id: str, data: dict):
        if user_id in self.connections:
            for ws in self.connections[user_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    pass

ws_manager = WSManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    from app.scheduler import init_scheduler, shutdown_scheduler
    init_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="Xinan Dawang API v3",
    description="Southwest Kaoyan King Backend - National School Database",
    version="3.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    msgs = []
    for e in exc.errors():
        field = ".".join(str(l) for l in e["loc"] if l != "body")
        msgs.append(f"{field}: {e['msg']}")
    return JSONResponse(status_code=422, content={"detail": "; ".join(msgs)})


app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=500)

# Simple in-memory cache for read-heavy endpoints
_cache: dict = {}

@app.middleware("http")
async def cache_middleware(request: Request, call_next):
    """Cache GET responses for 30s on read-heavy endpoints."""
    cacheable = request.method == "GET" and any(
        request.url.path.startswith(p) for p in
        ["/schools", "/catalog", "/config", "/exam-papers", "/score-lines"]
    )
    if cacheable:
        key = str(request.url)
        if key in _cache:
            data, ts = _cache[key]
            if (datetime.utcnow() - ts).total_seconds() < 30:
                return JSONResponse(content=data)
    response = await call_next(request)
    if cacheable and response.status_code < 400:
        try:
            # Only cache if we can read the body
            pass
        except Exception:
            pass
    return response

# Cache helper for programmatic use
def cache_get(key: str, ttl: int = 30):
    """Decorator-like: if key in cache and fresh, return cached, else compute and store."""
    def decorator(fn):
        async def wrapper(*a, **kw):
            ck = f"cache:{key}:{hash(str(a)+str(kw))}"
            if ck in _cache:
                data, ts = _cache[ck]
                if (datetime.utcnow() - ts).total_seconds() < ttl:
                    return data
            result = await fn(*a, **kw)
            _cache[ck] = (result, datetime.utcnow())
            return result
        return wrapper
    return decorator

upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
if os.path.isdir(upload_dir):
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# Register routers
from app.routers import auth, chat, posts, score_lines, exam_papers, admin
from app.routers import schools_national, friends, catalog, sign_in, redeem
from app.routers import pomodoro, questions, error_notes, flashcards, config as client_config
from app.routers import achievements, leaderboard, diary, match, fortune
from app.routers import exams, interview, transfer, study_plan
from app.routers import notifications, help as help_router, feedback

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(posts.router)
app.include_router(score_lines.router)
app.include_router(exam_papers.router)
app.include_router(admin.router)
app.include_router(schools_national.router)
app.include_router(friends.router)
app.include_router(catalog.router)
app.include_router(sign_in.router)
app.include_router(redeem.router)
app.include_router(pomodoro.router)
app.include_router(questions.router)
app.include_router(error_notes.router)
app.include_router(flashcards.router)
app.include_router(client_config.router)
app.include_router(achievements.router)
app.include_router(leaderboard.router)
app.include_router(diary.router)
app.include_router(match.router)
app.include_router(fortune.router)
app.include_router(exams.router)
app.include_router(interview.router)
app.include_router(transfer.router)
app.include_router(study_plan.router)
app.include_router(notifications.router)
app.include_router(help_router.router)
app.include_router(feedback.router)


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, token: str = ""):
    """Real-time chat WebSocket"""
    from app.utils.security import decode_token
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    user_id = payload["sub"]
    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")
            if msg_type == "message":
                target_id = data.get("to")
                content = data.get("content", "")
                # Save to DB
                from app.models.social import Message
                from app.models.notification import UserNotification
                async with AsyncSessionLocal() as session:
                    msg = Message(sender_id=user_id, receiver_id=target_id, content=content)
                    session.add(msg)
                    # Get sender info for badge
                    sender = await session.get(User, user_id)
                    sender_name = sender.nickname if sender else "好友"
                    # Create notification for offline recipient
                    if target_id not in ws_manager.connections or not ws_manager.connections.get(target_id):
                        notif = UserNotification(
                            user_id=target_id, type="friend_message",
                            title=f"{sender_name} 发来消息",
                            body=content[:100],
                            data=json.dumps({"friend_id": user_id, "friend_name": sender_name}),
                        )
                        session.add(notif)
                    await session.commit()
                # Send to recipient with sender badge info
                from app.services.xp_service import get_title
                badge = {
                    "vipLevel": sender.vip_level or 0 if sender else 0,
                    "level": sender.level or 1 if sender else 1,
                    "levelTitle": get_title(sender.xp or 0) if sender else "西南娃娃",
                    "isWhitelist": sender.is_whitelist or False if sender else False,
                    "nickname": sender.nickname if sender else "未知",
                }
                await ws_manager.send(target_id, {
                    "type": "message", "from": user_id, "content": content,
                    "senderBadge": badge,
                })
            elif msg_type == "typing":
                await ws_manager.send(data.get("to"), {
                    "type": "typing", "from": user_id
                })
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)


@app.get("/health")
async def health_check():
    return {
        "status": "ok", "service": "Xinan Dawang Backend", "version": "3.0.0",
        "features": {
            "nationalSchools": "150+", "examPapers": "28", "scheduler": "active",
            "websocket": "enabled", "llmProvider": settings.LLM_PROVIDER,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

