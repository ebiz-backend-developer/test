"""Test fixtures: isolated SQLite DB per test + authenticated API clients."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import schoolms.security as security
from schoolms import models
from schoolms.database import Base, get_db
from schoolms.main import create_app

security._ITERATIONS = 2000  # keep hashing real but fast under test


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    app = create_app()

    def override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client


def _register(client: TestClient, username: str, role: str, password: str = "Password123") -> dict:
    res = client.post("/api/v1/auth/register", json={
        "username": username, "full_name": username, "email": f"{username}@test.local",
        "password": password, "role": role,
    })
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture()
def admin_client(client: TestClient, db_session):
    db_session.add(models.User(
        username="admin", full_name="Admin", email="admin@test.local",
        password_hash=security.hash_password("Admin1234"), role="admin"))
    db_session.commit()
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "Admin1234"})
    assert res.status_code == 200, res.text
    client.headers["Authorization"] = f"Bearer {res.json()['access_token']}"
    return client


@pytest.fixture()
def staff_token(client: TestClient):
    return _register(client, "office", "staff")["access_token"]


@pytest.fixture()
def teacher_token(client: TestClient):
    return _register(client, "teach", "teacher")["access_token"]


@pytest.fixture()
def student_token(client: TestClient):
    return _register(client, "stud", "student")["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
