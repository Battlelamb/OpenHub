"""Phase 4 Plan 07: FastAPI /dashboard mount smoke tests.

Verifies that:
1. The React SPA build at web/dist is mounted under /dashboard
2. Deep-link paths (e.g. /dashboard/agents/foo) fall back to index.html
3. Static assets under /dashboard/assets/ are served

Skips gracefully if web/dist is not present (e.g. in CI before the frontend is built).
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


def _require_dist() -> None:
    if not WEB_DIST.exists() or not (WEB_DIST / "index.html").exists():
        pytest.skip(
            "web/dist not built - run `cd web && npm run build` to enable this test"
        )


@pytest.fixture(scope="module")
def client() -> TestClient:
    _require_dist()
    from app.main import app  # import after skip check

    return TestClient(app)


def test_dashboard_root_serves_index(client: TestClient) -> None:
    r = client.get("/dashboard/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert 'id="root"' in r.text


def test_dashboard_deep_link_falls_back_to_index(client: TestClient) -> None:
    # SPA deep links MUST serve index.html so the client router can handle them.
    # Before 04-08 gap closure StaticFiles(html=True) returned 404 here; the
    # catch-all /dashboard/{full_path:path} route added in app/main.py fixes it.
    # If this test starts failing, the SPA fallback has regressed - do NOT
    # weaken the assertion; restore the catch-all route instead.
    r = client.get("/dashboard/agents/some-agent-id")
    assert r.status_code == 200, (
        f"Deep-link returned {r.status_code}; SPA fallback regressed. "
        "Check app/main.py /dashboard/{full_path:path} route."
    )
    assert "text/html" in r.headers.get("content-type", "")
    assert 'id="root"' in r.text


def test_dashboard_asset_served(client: TestClient) -> None:
    # Find a built JS bundle under web/dist/assets and verify it is served
    assets_dir = WEB_DIST / "assets"
    if not assets_dir.exists():
        pytest.skip("web/dist/assets not present")
    js_files = sorted(assets_dir.glob("*.js"))
    if not js_files:
        pytest.skip("no JS bundle under web/dist/assets")
    rel = js_files[0].relative_to(WEB_DIST).as_posix()
    r = client.get(f"/dashboard/{rel}")
    assert r.status_code == 200
    # Vite serves JS with application/javascript or text/javascript
    ct = r.headers.get("content-type", "")
    assert "javascript" in ct or "text" in ct


def test_api_routes_still_take_precedence(client: TestClient) -> None:
    # /v1/health must still respond from the JSON API, not the SPA
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert "application/json" in r.headers.get("content-type", "")


def test_built_index_references_dashboard_base(client: TestClient) -> None:
    # Vite build with base='/dashboard/' must rewrite asset hrefs so the
    # browser fetches /dashboard/assets/index-<hash>.js, not /assets/... .
    # If this assertion fails, web/vite.config.ts `base` has regressed or the
    # build was run with the wrong env.
    r = client.get("/dashboard/")
    assert r.status_code == 200
    body = r.text
    # There must be at least one script/link src pointing under /dashboard/assets/
    assert "/dashboard/assets/" in body, (
        "Built index.html does not reference /dashboard/assets/ - Vite base "
        "config or build output is wrong. Expected "
        'src="/dashboard/assets/index-*.js".'
    )
    # And there must NOT be bare /assets/ hrefs in <script>/<link> tags -
    # those would 404 under /dashboard/ in production.
    import re

    bare_asset_refs = re.findall(r'(?:src|href)="(/assets/[^"]+)"', body)
    assert not bare_asset_refs, (
        f"Built index.html contains bare /assets/ refs: {bare_asset_refs}. "
        "These will 404 under /dashboard/. Fix vite.config.ts `base` and "
        "rebuild."
    )


def test_favicon_served_under_dashboard(client: TestClient) -> None:
    # With favicon href changed to './vite.svg' in web/index.html, Vite rewrites
    # it against the /dashboard/ base. The file itself (web/public/vite.svg)
    # is copied to web/dist/vite.svg on build, and our catch-all serves bare
    # files from dist root. Guard against anyone moving the favicon back to an
    # absolute /vite.svg href (which would 404 under /dashboard).
    r = client.get("/dashboard/vite.svg")
    assert r.status_code == 200, (
        f"/dashboard/vite.svg returned {r.status_code}; favicon routing "
        "regressed. Check web/index.html favicon href is './vite.svg' "
        "(relative) and web/public/vite.svg exists."
    )
