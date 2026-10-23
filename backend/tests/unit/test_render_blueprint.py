"""FIX10 — render.yaml keeps the health check and WebSocket ping settings (free-plan hardening)."""

from __future__ import annotations

from pathlib import Path

import pytest

RENDER_YAML = Path(__file__).resolve().parents[3] / "render.yaml"


@pytest.fixture(scope="module")
def render_text() -> str:
    if not RENDER_YAML.exists():
        pytest.skip("render.yaml not present in this checkout")
    return RENDER_YAML.read_text(encoding="utf-8")


def test_health_check_path_is_unchanged(render_text: str) -> None:
    assert "healthCheckPath: /api/v1/health\n" in render_text


def test_start_command_keeps_migrations_and_ws_ping(render_text: str) -> None:
    line = next(ln for ln in render_text.splitlines() if ln.strip().startswith("startCommand:"))
    assert "alembic upgrade head" in line
    assert "uvicorn app.main:app" in line
    assert "--ws-ping-interval 25" in line
    assert "--ws-ping-timeout 20" in line


def test_free_plan_documents_the_sleep_mitigation(render_text: str) -> None:
    assert "plan: free" in render_text
    assert "docs/14 Step 2b" in render_text


def test_query_token_flag_and_proxy_hops_are_declared(render_text: str) -> None:
    assert "key: WS_ALLOW_QUERY_TOKEN" in render_text
    assert "key: PROXY_HOPS" in render_text
