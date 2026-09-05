import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.init_db import init_db
from app.models.user import User

# 使用独立的测试数据库
TEST_DB_URL = "sqlite:///:memory:"

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
