"""Cada teste usa uma cópia isolada da base sintética, sem tocar na demo."""

import os
import shutil
import tempfile
from pathlib import Path

TEST_ROOT = Path(tempfile.mkdtemp(prefix="chargeops-tests-"))
os.environ["DATA_DIR"] = str(TEST_ROOT)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'template.db'}"

import pytest  # noqa: E402
from app.db import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.simulator import seed  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def template():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield
    engine.dispose()
    shutil.rmtree(TEST_ROOT)


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "test.db"
    shutil.copyfile(TEST_ROOT / "template.db", path)
    test_engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})

    @event.listens_for(test_engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    factory = sessionmaker(test_engine, expire_on_commit=False)
    yield factory
    test_engine.dispose()


@pytest.fixture
def client(database):
    def override():
        with database() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def headers(client):
    data = client.post(
        "/api/auth/login", json={"email": "gestor@demo.local", "password": "Demo2026!"}
    ).json()
    return {"Authorization": f"Bearer {data['token']}"}


@pytest.fixture
def resident(client):
    data = client.post(
        "/api/auth/login", json={"email": "morador101@demo.local", "password": "Demo2026!"}
    ).json()
    return {"Authorization": f"Bearer {data['token']}"}
