"""Database, authentication and durable work shared by the small applications."""
import hashlib
import json
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import jwt
import psycopg
import redis
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

ROLES = ("operator", "reviewer", "viewer")
JOB_STATES = ("queued", "running", "done", "failed")
SECRET = os.environ["JWT_SECRET"]
ISSUER = os.environ.get("APP_NAME", "yangyang")
AUTH = HTTPBearer(auto_error=False)
CACHE = redis.Redis.from_url(os.environ["REDIS_URL"], socket_timeout=3)
BUSINESS_PATH = "/api"

@contextmanager
def db():
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as connection:
        yield connection

def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1).hex()

def token_for(user):
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": user["email"], "role": user["role"], "iat": now,
        "exp": now + timedelta(hours=8), "iss": ISSUER,
    }, SECRET, algorithm="HS256")

def require(*roles):
    def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(AUTH)):
        try:
            data = jwt.decode(
                credentials.credentials if credentials else "",
                SECRET, algorithms=["HS256"], issuer=ISSUER,
                options={"require": ["exp", "sub", "role", "iss"]},
            )
        except jwt.InvalidTokenError as exc:
            raise HTTPException(401, "请重新登录") from exc
        if data["role"] not in ROLES or (roles and data["role"] not in roles):
            raise HTTPException(403, "当前角色没有此操作权限")
        return {"email": data["sub"], "role": data["role"]}
    return authenticate

def initialize(connection, domain_sql):
    connection.execute("SELECT pg_advisory_xact_lock(381613)")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS app_users (
            email text PRIMARY KEY, role text UNIQUE NOT NULL
                CHECK (role IN ('operator','reviewer','viewer')),
            salt text NOT NULL, digest text NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_jobs (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            kind text NOT NULL, payload jsonb NOT NULL,
            status text NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','running','done','failed')),
            result jsonb, error text,
            available_at timestamptz NOT NULL DEFAULT now(),
            created_at timestamptz NOT NULL DEFAULT now(),
            finished_at timestamptz
        );
        CREATE INDEX IF NOT EXISTS app_jobs_ready ON app_jobs (available_at,id)
            WHERE status='queued';
    """)
    connection.execute(domain_sql)

def seed_users(connection):
    password = os.environ.get("DEMO_PASSWORD", "Demo2026!")
    for role in ROLES:
        salt = secrets.token_bytes(16)
        connection.execute(
            "INSERT INTO app_users VALUES (%s,%s,%s,%s) ON CONFLICT (email) DO NOTHING",
            (f"{role}@demo.local", role, salt.hex(), password_hash(password, salt)),
        )

def enqueue(connection, kind, payload, *, available_at=None):
    """Commit work atomically with the domain action that created it."""
    return connection.execute(
        """INSERT INTO app_jobs(kind,payload,available_at)
           VALUES (%s,%s,COALESCE(%s::timestamptz,now())) RETURNING id""",
        (kind, Jsonb(payload, dumps=json.dumps), available_at),
    ).fetchone()["id"]
