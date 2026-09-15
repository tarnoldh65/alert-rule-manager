import os

from . import database


def main() -> None:
    username = os.environ.get("ALERT_MANAGER_ADMIN_USERNAME")
    password = os.environ.get("ALERT_MANAGER_ADMIN_PASSWORD")
    if not username or not password:
        raise SystemExit("Set ALERT_MANAGER_ADMIN_USERNAME and ALERT_MANAGER_ADMIN_PASSWORD")
    database.create_user(username, password, "admin")
    print(f"created admin user {username}")


if __name__ == "__main__":
    main()