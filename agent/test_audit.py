"""Trusted executor. Runs cases the agent wrote to work/cases.json. Never changes per run."""
import json, os, pathlib
import pytest
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
BASE = os.getenv("API_BASE", "http://localhost:8080")
CASES = json.loads((HERE / "work" / "cases.json").read_text())
RESULTS = HERE / "work" / "results.jsonl"

@pytest.fixture(scope="session")
def api():
    with sync_playwright() as p:
        ctx = p.request.new_context(
            base_url=BASE,
            extra_http_headers={"Content-Type": "application/json"}
        )
        yield ctx
        ctx.dispose()

@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_case(api, case):
    payload = case.get("payload")
    r = api.fetch(
        case["path"],
        method=case["method"].upper(),
        data=json.dumps(payload) if payload is not None else None
    )
    body = r.text()[:300]
    with RESULTS.open("a") as f:
        f.write(json.dumps({**case, "status": r.status, "body": body}) + "\n")
    # Oracle: a robust API may reject input (4xx) but must never crash (5xx).
    assert r.status < 500, f"{r.status}: {body}"
