from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

import urllib.parse

db_url = settings.DATABASE_URL
if (db_url.startswith("postgresql://") or db_url.startswith("postgres://")) and "@" in db_url:
    prefix, sep, rest = db_url.partition("://")
    auth, _, host_db = rest.rpartition("@")
    if ":" in auth:
        user, _, passwd = auth.partition(":")
        if "%" not in passwd:
            passwd = urllib.parse.quote_plus(passwd)
        db_url = f"{prefix}://{user}:{passwd}@{host_db}"

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI 请求级数据库会话依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
