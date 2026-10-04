"""MediTest-AI: discover -> guard -> execute -> judge -> report -> learn."""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import requests


API_BASE = os.getenv("API_BASE", "http://localhost:8080")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
N_CASES = int(os.getenv("N_CASES", "8"))
STRICT = os.getenv("STRICT", "0") == "1"

HERE = pathlib.Path(__file__).parent
WORK = HERE / "work"
REPORTS = pathlib.Path(os.getenv("REPORT_DIR", HERE.parent / "reports"))
REGRESSION = HERE / "regression_cases.json"

KEEP = (
    "name",
    "method",
    "path",
    "payload",
    "expect",
    "category",
    "rationale",
)

SYSTEM = (
    "You are a senior QA engineer auditing a healthcare REST API for functional, "
    "validation and security defects. Respond with JSON only."
)
# ---------- helpers ----------

def wait_for_api(timeout=300):
    end = time.time() + timeout

    while time.time() < end:
        try:
            if requests.get(
                f"{API_BASE}/v3/api-docs",
                timeout=5
            ).ok:
                return
        except requests.RequestException:
            pass

        time.sleep(3)

    sys.exit("API never became ready")

def ask_llm(prompt):
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        timeout=900,
        json={
            "model": MODEL,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0
            },
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
    )

    r.raise_for_status()

    return json.loads(
        r.json()["message"]["content"]
    )
# ---------- 1. perceive ----------

def analyze_spec():
    spec = requests.get(
        f"{API_BASE}/v3/api-docs",
        timeout=10
    ).json()

    compact = {
        "paths": spec.get("paths", {}),
        "schemas": spec.get("components", {}).get("schemas", {})
    }

    return spec, compact

# ---------- 3. guard ----------

def endpoint_rules(spec):
    rules = []

    for path, ops in spec["paths"].items():
        rx = re.compile(
            "^" + re.sub(r"\{[^/]+\}", r"[^/]+", path) + "$"
        )

        rules += [
            (method.upper(), rx)
            for method in ops
        ]

    return rules

def is_valid(case, rules):
    if not isinstance(case, dict) or not {
        "name",
        "method",
        "path",
        "expect",
    } <= case.keys():
        return False

    if case["expect"] not in ("2xx", "4xx"):
        return False

    path = str(case["path"]).split("?")[0]

    return any(
        case["method"].upper() == method
        and rx.match(path)
        for method, rx in rules
    )
# ---------- 2. discover ----------

def discover_cases(compact, rules):
    prompt = f"""API specification (OpenAPI, trimmed):
{json.dumps(compact, separators=(",", ":"))}

Think about how each endpoint could fail: missing or null fields,
wrong types, future or impossible dates, references to ids that do
not exist, very long strings, injection-style strings, negative or
huge ids.

Propose {N_CASES} test requests. For each, say whether a correct API
should accept it ("2xx") or reject it ("4xx").

Return JSON:
{{"cases": [{{"name": "snake_case_unique",
"method": "POST",
"path": "/api/patients",
"payload": {{}} or null,
"expect": "4xx",
"category": "validation|reference|boundary|security",
"rationale": "one sentence"}}]}}"""

    try:
        raw = ask_llm(prompt).get("cases", [])
    except Exception as exc:
        print(f"LLM unavailable ({exc}); running regression suite only")
        return []

    valid = [c for c in raw if is_valid(c, rules)]

    print(
        f"LLM proposed {len(raw)} cases; "
        f"{len(valid)} passed guardrails"
    )

    return [
        {
            **{k: c.get(k) for k in KEEP},
            "source": "llm"
        }
        for c in valid
    ]

def load_regression():
    cases = (
        json.loads(REGRESSION.read_text())
        if REGRESSION.exists()
        else []
    )

    return [
        {**case, "source": "regression"}
        for case in cases
    ]
# ---------- 4. execute ----------

def execute(cases):
    WORK.mkdir(exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    (WORK / "cases.json").write_text(
        json.dumps(cases, indent=2)
    )

    results = WORK / "results.jsonl"
    results.unlink(missing_ok=True)

    subprocess.run([
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        str(HERE / "test_audit.py"),
        f"--junitxml={REPORTS / 'junit.xml'}"
    ])

    if not results.exists():
        return []

    return [
        json.loads(line)
        for line in results.read_text().splitlines()
    ]
# ---------- 5. judge ----------

def verdict(r):
    if r["status"] >= 500:
        return "BUG"

    if r.get("expect") == "4xx" and 200 <= r["status"] < 300:
        return "GAP"

    if r.get("expect") == "2xx" and r["status"] >= 400:
        return "CHECK"

    return "PASS"
# ---------- 6. report ----------

def suggest_fixes(findings):
    if not findings:
        return {}

    try:
        slim = [
            {
                k: f[k]
                for k in (
                    "name",
                    "method",
                    "path",
                    "payload",
                    "status",
                    "body",
                )
            }
            for f in findings
        ]

        out = ask_llm(
            "For each failing request, give the likely root cause and a concrete "
            "Spring Boot fix in at most two sentences. "
            'Return {"fixes": [{"name": "...", "fix": "..."}]}\n'
            + json.dumps(slim)
        )

        return {
            x["name"]: x["fix"]
            for x in out.get("fixes", [])
            if "name" in x
        }

    except Exception:
        return {}
def write_report(results, fixes):
    count = {
        v: sum(r["verdict"] == v for r in results)
        for v in ("BUG", "GAP", "CHECK", "PASS")
    }

    lines = [
        "# MediTest-AI audit report",
        "",
        f"Model: `{MODEL}` | Cases: {len(results)} | "
        f"BUG: {count['BUG']} | GAP: {count['GAP']} | "
        f"CHECK: {count['CHECK']} | PASS: {count['PASS']}",
        "",
        "| Verdict | Case | Request | Status | Source |",
        "|---|---|---|---|---|",
    ]

    order = {
        "BUG": 0,
        "GAP": 1,
        "CHECK": 2,
        "PASS": 3,
    }

    for r in sorted(
        results,
        key=lambda r: order[r["verdict"]]
    ):
        lines.append(
            f"| {r['verdict']} | {r['name']} | "
            f"{r['method']} {r['path']} | "
            f"{r['status']} | {r['source']} |"
        )

    findings = [
        r
        for r in results
        if r["verdict"] in ("BUG", "GAP")
    ]

    if findings:
        lines += [
            "",
            "## Findings and suggested fixes "
            "(AI-generated: review before applying)",
        ]

        for r in findings:
            lines += [
                f"### {r['verdict']}: {r['name']}",
                f"- Why tested: {r.get('rationale') or 'n/a'}",
                f"- Payload: `{json.dumps(r.get('payload'))}`",
                f"- Response: {r['status']} `{r['body'][:150]}`",
                f"- Suggested fix: "
                f"{fixes.get(r['name'], 'n/a')}",
                "",
            ]

    (REPORTS / "report.md").write_text(
        "\n".join(lines)
    )
# ---------- 7. learn ----------

def save_candidates(results):
    new = [
        {k: r.get(k) for k in KEEP}
        for r in results
        if r["source"] == "llm"
        and r["verdict"] in ("BUG", "GAP")
    ]

    (REPORTS / "regression_candidates.json").write_text(
        json.dumps(new, indent=2)
    )

    print(
        f"{len(new)} new regression candidate(s). "
        "Review, then: python agent/agent.py --promote"
    )
def promote():
    cands = json.loads(
        (REPORTS / "regression_candidates.json").read_text()
    )

    current = (
        json.loads(REGRESSION.read_text())
        if REGRESSION.exists()
        else []
    )

    names = {c["name"] for c in current}

    added = [
        c
        for c in cands
        if c["name"] not in names
    ]

    REGRESSION.write_text(
        json.dumps(current + added, indent=2)
    )

    print(
        f"Promoted {len(added)} case(s); "
        f"regression suite now has "
        f"{len(current) + len(added)}"
    )
def main():
    wait_for_api()

    spec, compact = analyze_spec()

    rules = endpoint_rules(spec)

    regression = load_regression()

    seen = {
        c["name"]
        for c in regression
    }

    discovered = [
        c
        for c in discover_cases(compact, rules)
        if c["name"] not in seen
    ]

    results = execute(
        regression + discovered
    )

    for r in results:
        r["verdict"] = verdict(r)

    write_report(
        results,
        suggest_fixes([
            r
            for r in results
            if r["verdict"] in ("BUG", "GAP")
        ])
    )

    save_candidates(results)

    bugs = sum(
        r["verdict"] == "BUG"
        for r in results
    )

    gaps = sum(
        r["verdict"] == "GAP"
        for r in results
    )

    print(
        f"BUG={bugs} GAP={gaps}. "
        f"Report: {REPORTS / 'report.md'}"
    )

    sys.exit(
        1
        if bugs or (STRICT and gaps)
        else 0
    )
if __name__ == "__main__":
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--promote",
        action="store_true",
        help="merge candidates into the regression suite",
    )

    promote() if ap.parse_args().promote else main()