import asyncio
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from . import database
from .config import settings
from .ingest import handle_client


class CategorizeRequest(BaseModel):
    category_id: int = Field(gt=0)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class CategoryRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""


class UserRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    role: str = Field(pattern="^(admin|analyst|auditor)$")


class UserActiveRequest(BaseModel):
    is_active: bool


class AutocategoryRequest(BaseModel):
    name: str = Field(min_length=1)
    category_id: int = Field(gt=0)
    field_path: str = Field(min_length=1)
    match_value: str = Field(min_length=1)


class AutocategoryEnabledRequest(BaseModel):
    is_enabled: bool


def require_admin(user: dict) -> None:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin access required")


def current_user(authorization: Annotated[str | None, Header()] = None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    user = database.get_session(authorization.removeprefix("Bearer ").strip())
    if user is None:
        raise HTTPException(status_code=401, detail="invalid session")
    return user


async def store_alert(source_id: str, payload: dict) -> None:
    await asyncio.to_thread(database.insert_alert, source_id, payload)


app = FastAPI(title="Alert Rule Manager API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(request: LoginRequest) -> dict[str, str]:
    token = database.create_session(request.username, request.password)
    if token is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    user = database.get_session(token)
    assert user is not None
    return {"token": token, "username": user["username"], "role": user["role"]}


@app.get("/api/alerts")
def alerts(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), user: dict = Depends(current_user)) -> list[dict]:
    return database.list_uncategorized(limit, offset)


@app.get("/api/alerts/{alert_id}")
def alert(alert_id: int, user: dict = Depends(current_user)) -> dict:
    result = database.get_alert(alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail="alert not found")
    return result


@app.post("/api/alerts/{alert_id}/categorize", status_code=204)
def categorize(alert_id: int, request: CategorizeRequest, user: dict = Depends(current_user)) -> None:
    if database.get_alert(alert_id) is None:
        raise HTTPException(status_code=404, detail="alert not found")
    database.categorize_alert(alert_id, request.category_id, user["id"])


@app.get("/api/categories")
def categories(user: dict = Depends(current_user)) -> list[dict]:
    return database.list_categories()


@app.post("/api/categories", status_code=201)
def add_category(request: CategoryRequest, user: dict = Depends(current_user)) -> dict[str, int]:
    require_admin(user)
    return {"id": database.create_category(request.name, request.description)}


@app.get("/api/users")
def users(user: dict = Depends(current_user)) -> list[dict]:
    require_admin(user)
    return database.list_users()


@app.post("/api/users", status_code=201)
def add_user(request: UserRequest, user: dict = Depends(current_user)) -> dict[str, int]:
    require_admin(user)
    return {"id": database.create_user(request.username, request.password, request.role, user["id"])}


@app.patch("/api/users/{user_id}/active", status_code=204)
def update_user_active(user_id: int, request: UserActiveRequest, user: dict = Depends(current_user)) -> None:
    require_admin(user)
    database.set_user_active(user_id, request.is_active, user["id"])


@app.get("/api/autocategories")
def autocategories(user: dict = Depends(current_user)) -> list[dict]:
    return database.list_autocategories()


@app.post("/api/autocategories", status_code=201)
def add_autocategory(request: AutocategoryRequest, user: dict = Depends(current_user)) -> dict[str, int]:
    require_admin(user)
    return {
        "id": database.create_autocategory(
            request.name, request.category_id, request.field_path, request.match_value, user["id"]
        )
    }


@app.patch("/api/autocategories/{autocategory_id}/enabled", status_code=204)
def update_autocategory_enabled(
    autocategory_id: int, request: AutocategoryEnabledRequest, user: dict = Depends(current_user)
) -> None:
    require_admin(user)
    database.set_autocategory_enabled(autocategory_id, request.is_enabled, user["id"])


@app.post("/api/alerts/{alert_id}/focus", status_code=204)
def focus(alert_id: int, user: dict = Depends(current_user)) -> None:
    database.set_focus(alert_id, user["id"])


@app.delete("/api/alerts/{alert_id}/focus", status_code=204)
def unfocus(alert_id: int, user: dict = Depends(current_user)) -> None:
    database.clear_focus(alert_id, user["id"])


@app.get("/api/alerts/{alert_id}/focus")
def focused_users(alert_id: int, user: dict = Depends(current_user)) -> list[dict]:
    return database.list_focus(alert_id)


@app.get("/api/reports/multi-categorized-rules")
def multi_categorized_rules(user: dict = Depends(current_user)) -> list[dict]:
    return database.report_multi_categorized_rules()


@app.get("/api/reports/rules-by-category")
def rules_by_category(user: dict = Depends(current_user)) -> list[dict]:
    return database.report_rules_by_category()


@app.get("/api/reports/autocategorized-rules")
def autocategorized_rules(user: dict = Depends(current_user)) -> list[dict]:
    return database.report_autocategorized_rules()


@app.on_event("startup")
async def start_ingest_server() -> None:
    app.state.ingest_server = await asyncio.start_server(
        lambda reader, writer: handle_client(reader, writer, store_alert),
        settings.ingest_host,
        settings.ingest_port,
    )


@app.on_event("shutdown")
async def stop_ingest_server() -> None:
    app.state.ingest_server.close()
    await app.state.ingest_server.wait_closed()
