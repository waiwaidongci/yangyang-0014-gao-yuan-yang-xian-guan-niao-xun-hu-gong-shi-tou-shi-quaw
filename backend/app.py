import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import domain
from agreement_api import router as agreement_router
from edition_api import router as edition_router
from weather_api import router as weather_router
from core import CACHE, db, initialize, password_hash, require, token_for
from scripts.seed_demo import seed_all

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("application")

@asynccontextmanager
async def lifespan(_app):
    with db() as connection:
        initialize(connection, Path(__file__).with_name("schema.sql").read_text())
        for migration in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
            connection.execute(migration.read_text())
    if os.environ.get("SEED_DEMO", "true").lower() == "true":
        try:
            seed_all()
        except Exception:
            log.exception("Demo seed failed")
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(domain.router)
app.include_router(weather_router)
app.include_router(agreement_router)
app.include_router(edition_router)

@app.middleware("http")
async def audit(request: Request, call_next):
    request_id = str(uuid4())
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    log.info("%s %s %s %s %.0fms", request_id, request.method,
             request.url.path, response.status_code, (time.monotonic() - start) * 1000)
    return response

@app.middleware("http")
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

@app.exception_handler(psycopg.IntegrityError)
async def invalid_record(request, exc):
    log.warning("Constraint violation on %s: %s", request.url.path, exc.diag.constraint_name)
    return JSONResponse({"detail": "记录违反唯一性、引用关系或业务范围约束"}, status_code=409)

class Login(BaseModel):
    email: str = Field(max_length=100)
    password: str = Field(max_length=100)

@app.get("/health")
@app.get("/api/health")
def health():
    with db() as connection:
        connection.execute("SELECT 1")
    CACHE.ping()
    return {"status": "ok"}

@app.post("/api/auth/login")
def login(data: Login, request: Request):
    key = f"login:{request.client.host if request.client else 'local'}"
    with CACHE.pipeline() as pipeline:
        count, _ = pipeline.incr(key).expire(key, 60, nx=True).execute()
    if count > 45:
        raise HTTPException(429, "登录尝试过多，请稍后重试")
    with db() as connection:
        user = connection.execute(
            "SELECT * FROM app_users WHERE email=%s", (data.email.strip().lower(),)
        ).fetchone()
    salt = bytes.fromhex(user["salt"]) if user else bytes(16)
    digest = password_hash(data.password, salt)
    if not user or not secrets.compare_digest(digest, user["digest"]):
        raise HTTPException(401, "邮箱或密码有误")
    return {key: user[key] for key in ("email", "role")} | {"access_token": token_for(user)}

@app.get("/api/jobs/{job_id}")
def job_receipt(job_id: int, _user=Depends(require())):
    with db() as connection:
        row = connection.execute(
            """SELECT id,kind,status,result,error,available_at,created_at,finished_at
               FROM app_jobs WHERE id=%s""", (job_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "没有这条处理记录")
    return row
