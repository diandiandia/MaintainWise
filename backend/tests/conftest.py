import os
import tempfile

# Override Docker path settings before importing app modules
_test_upload_dir = os.path.join(tempfile.gettempdir(), "maintainwise_test_uploads")
os.makedirs(_test_upload_dir, exist_ok=True)
os.environ["UPLOAD_DIR"] = _test_upload_dir
# Override database to SQLite for tests
_test_db_path = os.path.join(tempfile.gettempdir(), "maintainwise_test.db")
# Remove stale test DB if exists
if os.path.exists(_test_db_path):
    os.remove(_test_db_path)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.init_db import init_db
from app.models.user import User

# 使用独立的测试数据库 (与 app engine 共享同一 SQLite 文件)
TEST_DB_URL = os.environ["DATABASE_URL"]

@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = Session()
    # 初始化种子数据
    init_db(session)
    yield session
    session.rollback()
    session.close()
@pytest.fixture(scope="session", autouse=True)
def setup_app_db():
    """Session-scoped: Create all tables and seed data once before any TestClient tests."""
    from app.core.database import engine as app_engine, Base as AppBase
    from app.core.init_db import init_db as app_init_db
    from app.core.database import SessionLocal
    AppBase.metadata.create_all(bind=app_engine)
    db = SessionLocal()
    try:
        app_init_db(db)
        db.commit()
    finally:
        db.close()
