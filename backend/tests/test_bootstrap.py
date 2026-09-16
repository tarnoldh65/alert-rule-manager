import app.bootstrap as bootstrap


def test_bootstrap_uses_idempotent_admin_creation(monkeypatch, capsys) -> None:
    monkeypatch.setenv("ALERT_MANAGER_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ALERT_MANAGER_ADMIN_PASSWORD", "secret")

    calls: list[tuple[str, str]] = []

    def fake_ensure_admin_user(username: str, password: str) -> int:
        calls.append((username, password))
        return 42

    monkeypatch.setattr(bootstrap.database, "ensure_admin_user", fake_ensure_admin_user)

    bootstrap.main()

    assert calls == [("admin", "secret")]
    assert "created admin user admin" in capsys.readouterr().out
