from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from argon2 import PasswordHasher
import psycopg
from psycopg.rows import dict_row

from .config import settings

password_hasher = PasswordHasher()


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


def insert_alert(source_id: str, payload: dict) -> int:
    with connection() as conn:
        row = conn.execute(
            """
            INSERT INTO alerts (source_id, event_timestamp, event_type, rule_gid,
                rule_signature_id, rule_revision, rule_signature, rule_category,
                rule_severity, payload)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                source_id,
                payload["timestamp"],
                payload["event_type"],
                payload["alert"]["gid"],
                payload["alert"]["signature_id"],
                payload["alert"]["rev"],
                payload["alert"]["signature"],
                payload["alert"].get("category"),
                payload["alert"].get("severity"),
                psycopg.types.json.Jsonb(payload),
            ),
        ).fetchone()
        conn.commit()
        return row["id"]


def list_uncategorized(limit: int, offset: int) -> list[dict]:
    with connection() as conn:
        return list(
            conn.execute(
                """
                SELECT a.* FROM alerts a
                LEFT JOIN alert_categorizations c ON c.alert_id = a.id
                WHERE c.alert_id IS NULL
                ORDER BY a.event_timestamp DESC, a.id DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
        )


def get_alert(alert_id: int) -> dict | None:
    with connection() as conn:
        return conn.execute("SELECT * FROM alerts WHERE id = %s", (alert_id,)).fetchone()


def categorize_alert(alert_id: int, category_id: int, user_id: int) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO alert_categorizations (alert_id, category_id, user_id)
            VALUES (%s, %s, %s)
            """,
            (alert_id, category_id, user_id),
        )
        conn.execute(
            """
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
            VALUES (%s, 'categorize_alert', 'alert', %s, %s)
            """,
            (user_id, alert_id, psycopg.types.json.Jsonb({"category_id": category_id})),
        )
        conn.commit()


def create_user(username: str, password: str, role: str) -> int:
    with connection() as conn:
        row = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) RETURNING id",
            (username, password_hasher.hash(password), role),
        ).fetchone()
        conn.commit()
        return row["id"]


def ensure_admin_user(username: str, password: str) -> int:
    with connection() as conn:
        row = conn.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (%s, %s, 'admin')
            ON CONFLICT (username) DO UPDATE
                SET password_hash = EXCLUDED.password_hash, role = 'admin', is_active = TRUE
            RETURNING id
            """,
            (username, password_hasher.hash(password)),
        ).fetchone()
        conn.commit()
        return row["id"]


def create_session(username: str, password: str) -> str | None:
    with connection() as conn:
        user = conn.execute("SELECT id, password_hash FROM users WHERE username = %s AND is_active", (username,)).fetchone()
        if user is None:
            return None
        try:
            password_hasher.verify(user["password_hash"], password)
        except Exception:
            return None
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (%s, %s, %s)",
            (sha256(token.encode()).hexdigest(), user["id"], datetime.now(timezone.utc) + timedelta(hours=12)),
        )
        conn.commit()
        return token


def get_session(token: str) -> dict | None:
    with connection() as conn:
        return conn.execute(
            "SELECT u.id, u.username, u.role FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = %s AND s.expires_at > now() AND u.is_active",
            (sha256(token.encode()).hexdigest(),),
        ).fetchone()


def list_categories() -> list[dict]:
    with connection() as conn:
        return list(conn.execute("SELECT * FROM categories ORDER BY name"))


def create_category(name: str, description: str) -> int:
    with connection() as conn:
        row = conn.execute(
            "INSERT INTO categories (name, description) VALUES (%s, %s) RETURNING id",
            (name, description),
        ).fetchone()
        conn.commit()
        return row["id"]


def set_focus(alert_id: int, user_id: int) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO alert_focus (alert_id, user_id) VALUES (%s, %s) ON CONFLICT (alert_id, user_id) DO UPDATE SET focused_at = now()",
            (alert_id, user_id),
        )
        conn.commit()


def clear_focus(alert_id: int, user_id: int) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM alert_focus WHERE alert_id = %s AND user_id = %s", (alert_id, user_id))
        conn.commit()


def list_focus(alert_id: int) -> list[dict]:
    with connection() as conn:
        return list(conn.execute(
            "SELECT u.username, f.focused_at FROM alert_focus f JOIN users u ON u.id = f.user_id "
            "WHERE f.alert_id = %s AND f.focused_at > now() - interval '2 minutes'",
            (alert_id,),
        ))


def report_multi_categorized_rules() -> list[dict]:
    with connection() as conn:
        return list(conn.execute(
            "SELECT rule_gid, rule_signature_id, rule_revision, rule_signature, count(DISTINCT category_id) AS category_count "
            "FROM alerts JOIN alert_categorizations ON alert_categorizations.alert_id = alerts.id "
            "GROUP BY rule_gid, rule_signature_id, rule_revision, rule_signature HAVING count(DISTINCT category_id) > 1"
        ))


def report_rules_by_category() -> list[dict]:
    with connection() as conn:
        return list(conn.execute(
            "SELECT c.name AS category, a.rule_gid, a.rule_signature_id, a.rule_revision, a.rule_signature, count(*) AS alert_count "
            "FROM categories c JOIN alert_categorizations ac ON ac.category_id = c.id JOIN alerts a ON a.id = ac.alert_id "
            "GROUP BY c.name, a.rule_gid, a.rule_signature_id, a.rule_revision, a.rule_signature ORDER BY c.name, alert_count DESC"
        ))


def report_autocategorized_rules() -> list[dict]:
    with connection() as conn:
        return list(conn.execute(
            "SELECT ac.name AS autocategory, c.name AS category, ac.field_path, ac.match_value, ac.is_enabled "
            "FROM autocategories ac JOIN categories c ON c.id = ac.category_id ORDER BY ac.name"
        ))
