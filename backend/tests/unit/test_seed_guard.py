"""FIX11: `scripts/seed_dev.py` must never run outside development/test.

None of these tests needs a database: the guard has to fire BEFORE any engine/connection is
created, and the "allowed" path uses fakes.
"""

from __future__ import annotations

import importlib.util
import sys
import typing
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from app.config import Settings
from app.core.seed_guard import (
    ALLOWED_SEED_ENVIRONMENTS,
    SeedBlockedError,
    assert_dev_seed_allowed,
    read_environment,
)

SEED_PATH = Path(__file__).resolve().parents[2] / "scripts" / "seed_dev.py"


class DatabaseTouched(AssertionError):
    """Raised by fakes if the seed script reaches for the database."""


@pytest.fixture(scope="module")
def seed_dev() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed_dev_under_test", SEED_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _use_environment(monkeypatch: pytest.MonkeyPatch, module: ModuleType, env: str) -> None:
    monkeypatch.setenv("ENVIRONMENT", env)
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(
            environment=env, database_url="postgresql+asyncpg://u:p@db.example.com/hms"
        ),
    )


def _forbid_database(monkeypatch: pytest.MonkeyPatch, module: ModuleType) -> list[str]:
    calls: list[str] = []

    def _boom(*_a: object, **_k: object) -> None:
        calls.append("db")
        raise DatabaseTouched("seed script touched the database while it should be blocked")

    monkeypatch.setattr(module, "create_async_engine", _boom)
    monkeypatch.setattr(module, "async_sessionmaker", _boom)
    return calls


# --- pure guard -------------------------------------------------------------------------------


@pytest.mark.parametrize("env", ["development", "test"])
def test_guard_allows_local_environments(env: str) -> None:
    assert_dev_seed_allowed(env)


@pytest.mark.parametrize("env", ["production", "staging", "prod", "", "PRODUCTION", "anything"])
def test_guard_blocks_everything_else(env: str) -> None:
    with pytest.raises(SeedBlockedError) as exc:
        assert_dev_seed_allowed(env)
    assert "init_production.py" in str(exc.value)


def test_allow_list_is_only_dev_and_test_and_valid_settings_values() -> None:
    assert ALLOWED_SEED_ENVIRONMENTS == {"development", "test"}
    literals = set(typing.get_args(Settings.model_fields["environment"].annotation))
    assert ALLOWED_SEED_ENVIRONMENTS <= literals
    assert {"production", "staging"} <= literals - ALLOWED_SEED_ENVIRONMENTS


# --- script behaviour -------------------------------------------------------------------------


@pytest.mark.parametrize("env", ["production", "staging"])
async def test_run_seed_blocked_before_any_db_access(
    seed_dev: ModuleType, monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    _use_environment(monkeypatch, seed_dev, env)
    calls = _forbid_database(monkeypatch, seed_dev)
    with pytest.raises(SeedBlockedError):
        await seed_dev.run_seed()
    assert calls == []


@pytest.mark.parametrize("flag", ["true", "TRUE", "1", "yes"])
async def test_legacy_force_env_var_no_longer_bypasses(
    seed_dev: ModuleType, monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    monkeypatch.setenv("FORCE_DEV_SEED_IN_PRODUCTION", flag)
    _use_environment(monkeypatch, seed_dev, "production")
    calls = _forbid_database(monkeypatch, seed_dev)
    with pytest.raises(SeedBlockedError):
        await seed_dev.run_seed()
    assert calls == []


@pytest.mark.parametrize("env", ["production", "staging"])
async def test_blocked_even_if_full_settings_validation_would_fail(
    seed_dev: ModuleType, monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    """Production with placeholder secrets: user must see the guard message, not a pydantic dump."""
    monkeypatch.setenv("ENVIRONMENT", env)

    def _settings_must_not_load() -> None:
        raise AssertionError("get_settings() reached before the environment guard")

    monkeypatch.setattr(seed_dev, "get_settings", _settings_must_not_load)
    calls = _forbid_database(monkeypatch, seed_dev)
    with pytest.raises(SeedBlockedError):
        await seed_dev.run_seed()
    assert calls == []


def test_read_environment_follows_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert read_environment() == "production"
    monkeypatch.setenv("ENVIRONMENT", "test")
    assert read_environment() == "test"


async def test_seed_staff_users_blocked_when_called_directly(
    seed_dev: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_environment(monkeypatch, seed_dev, "production")

    class ExplodingSession:
        def __getattr__(self, name: str) -> None:
            raise DatabaseTouched(name)

    with pytest.raises(SeedBlockedError):
        await seed_dev.seed_staff_users(ExplodingSession())


def test_main_returns_1_and_prints_error_in_production(
    seed_dev: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _use_environment(monkeypatch, seed_dev, "production")
    calls = _forbid_database(monkeypatch, seed_dev)
    assert seed_dev.main() == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "FATAL ERROR" in err
    assert "ENVIRONMENT='production'" in err
    assert "AdminPass123!" in err  # explains why, but never seeds


async def test_run_seed_proceeds_in_development_with_fakes(
    seed_dev: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_environment(monkeypatch, seed_dev, "development")
    order: list[str] = []

    class FakeTx:
        async def __aenter__(self) -> None:
            order.append("begin")

        async def __aexit__(self, *_a: object) -> None:
            order.append("commit")

    class FakeSession:
        def begin(self) -> FakeTx:
            return FakeTx()

        async def __aenter__(self) -> FakeSession:
            return self

        async def __aexit__(self, *_a: object) -> None:
            return None

    class FakeEngine:
        async def dispose(self) -> None:
            order.append("dispose")

    monkeypatch.setattr(seed_dev, "create_async_engine", lambda *_a, **_k: FakeEngine())
    monkeypatch.setattr(seed_dev, "async_sessionmaker", lambda *_a, **_k: FakeSession)

    def _recorder(name: str):
        async def _step(*_a: object, **_k: object) -> None:
            order.append(name)

        return _step

    for name in ("seed_settings", "seed_staff_users", "seed_menu", "seed_tables_and_qr"):
        monkeypatch.setattr(seed_dev, name, _recorder(name))

    await seed_dev.run_seed()
    assert order == [
        "begin",
        "seed_settings",
        "seed_staff_users",
        "seed_menu",
        "seed_tables_and_qr",
        "commit",
        "dispose",
    ]


def test_script_has_no_bypass_switches() -> None:
    source = SEED_PATH.read_text(encoding="utf-8")
    assert "FORCE_DEV_SEED" not in source
    assert "argparse" not in source
    assert "sys.argv" not in source
    assert "os.getenv" not in source
    assert "os.environ" not in source
