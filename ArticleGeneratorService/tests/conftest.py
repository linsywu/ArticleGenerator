"""
pytest 公共 fixture：测试客户端、数据库
"""
import os
import tempfile

# 使用临时文件确保测试与 app 共享同一数据库
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.name}"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db, engine as app_engine
from app.main import app
from app.config import settings
from app.auth import get_password_hash
from app.models import User

# 使用与 app 相同的 engine，确保表已创建
engine = app_engine
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def _clean_db():
    """每个测试前清空表数据，保证隔离"""
    from app.models import Account, Hotspot, Article, HotspotSource, GenerationTask, RefineTask, User
    db = TestingSessionLocal()
    try:
        for t in [RefineTask, GenerationTask, Article, Hotspot, Account, HotspotSource, User]:
            db.query(t).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    """测试客户端（无认证）"""
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    """带 JWT 认证的测试客户端"""
    db = TestingSessionLocal()
    try:
        # 创建种子用户
        user = User(
            username=settings.seed_username,
            password_hash=get_password_hash(settings.seed_password),
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    # 登录获取 token
    r = client.post("/api/auth/login", json={
        "username": settings.seed_username,
        "password": settings.seed_password,
    })
    token = r.json()["access_token"]

    # 返回带 Bearer 头的客户端
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def db_session():
    """测试用数据库会话（供直接操作模型）"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
