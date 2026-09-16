from fastapi.testclient import TestClient

from app import database
from app.main import app

client = TestClient(app)

ADMIN = {"id": 1, "username": "admin", "role": "admin"}
ANALYST = {"id": 2, "username": "analyst", "role": "analyst"}


def auth_as(monkeypatch, user: dict) -> dict[str, str]:
    monkeypatch.setattr(database, "get_session", lambda token: user if token == "valid" else None)
    return {"Authorization": "Bearer valid"}


def test_categorize_returns_404_for_unknown_alert(monkeypatch) -> None:
    headers = auth_as(monkeypatch, ANALYST)
    monkeypatch.setattr(database, "get_alert", lambda alert_id: None)

    response = client.post("/api/alerts/999/categorize", json={"category_id": 1}, headers=headers)

    assert response.status_code == 404


def test_categorize_records_category_and_actor(monkeypatch) -> None:
    headers = auth_as(monkeypatch, ANALYST)
    monkeypatch.setattr(database, "get_alert", lambda alert_id: {"id": alert_id})
    calls: list[tuple[int, int, int]] = []
    monkeypatch.setattr(database, "categorize_alert", lambda alert_id, category_id, user_id: calls.append((alert_id, category_id, user_id)))

    response = client.post("/api/alerts/5/categorize", json={"category_id": 3}, headers=headers)

    assert response.status_code == 204
    assert calls == [(5, 3, ANALYST["id"])]


def test_add_user_requires_admin(monkeypatch) -> None:
    headers = auth_as(monkeypatch, ANALYST)

    response = client.post("/api/users", json={"username": "new", "password": "secret", "role": "analyst"}, headers=headers)

    assert response.status_code == 403


def test_add_user_allowed_for_admin(monkeypatch) -> None:
    headers = auth_as(monkeypatch, ADMIN)
    calls: list[tuple[str, str, str, int]] = []
    monkeypatch.setattr(database, "create_user", lambda username, password, role, actor_id: (calls.append((username, password, role, actor_id)) or 7))

    response = client.post("/api/users", json={"username": "new", "password": "secret", "role": "analyst"}, headers=headers)

    assert response.status_code == 201
    assert response.json() == {"id": 7}
    assert calls == [("new", "secret", "analyst", ADMIN["id"])]


def test_add_autocategory_requires_admin(monkeypatch) -> None:
    headers = auth_as(monkeypatch, ANALYST)

    response = client.post(
        "/api/autocategories",
        json={"name": "scan", "category_id": 1, "field_path": "alert.signature", "match_value": "ET SCAN"},
        headers=headers,
    )

    assert response.status_code == 403


def test_update_autocategory_enabled_requires_admin(monkeypatch) -> None:
    headers = auth_as(monkeypatch, ANALYST)

    response = client.patch("/api/autocategories/1/enabled", json={"is_enabled": False}, headers=headers)

    assert response.status_code == 403


def test_update_autocategory_enabled_allowed_for_admin(monkeypatch) -> None:
    headers = auth_as(monkeypatch, ADMIN)
    calls: list[tuple[int, bool, int]] = []
    monkeypatch.setattr(database, "set_autocategory_enabled", lambda autocategory_id, is_enabled, actor_id: calls.append((autocategory_id, is_enabled, actor_id)))

    response = client.patch("/api/autocategories/1/enabled", json={"is_enabled": False}, headers=headers)

    assert response.status_code == 204
    assert calls == [(1, False, ADMIN["id"])]


def test_endpoints_require_authentication() -> None:
    response = client.get("/api/users")

    assert response.status_code == 401
