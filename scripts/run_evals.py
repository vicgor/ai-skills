#!/usr/bin/env python3
"""Runs eval cases from evals/<domain>/<skill>.cases.yaml against an LLM.

Examples:
    python scripts/run_evals.py --provider dry-run
    python scripts/run_evals.py --provider anthropic --model <model> --skill db-sql
    python scripts/run_evals.py --provider openai --model <model> --skill db-sql.write-migration --case destructive_drop_column
    python scripts/run_evals.py --list
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import click  # noqa: E402
from render import load_registry, load_skill, render_prompt  # noqa: E402

EVALS_DIR = ROOT / "evals"
RESULTS_DIR = EVALS_DIR / "results"
RETRY_STATUS = {429, 500, 502, 503, 529}
LAST_FINISH = {"v": None}


def _openai_extract(j):
    ch = j["choices"][0]
    LAST_FINISH["v"] = ch.get("finish_reason")
    return ch["message"].get("content") or ""


def _anthropic_extract(j):
    LAST_FINISH["v"] = j.get("stop_reason")
    return "".join(b.get("text", "") for b in j.get("content", []))


def iter_cases(selector: str | None, case_id: str | None):
    """Yield (skill_id, domain, case) for selected skills and cases."""
    registry = load_registry()
    for domain, domain_data in registry.get("domains", {}).items():
        for skill in domain_data.get("skills", []):
            sid = skill["id"]
            if selector and selector != domain and selector != sid:
                continue
            name = sid.split(".", 1)[1]
            path = EVALS_DIR / domain / f"{name}.cases.yaml"
            if not path.exists():
                continue
            data = yaml.safe_load(path.read_text()) or {}
            for case in data.get("cases", []):
                if case_id and case.get("id") != case_id:
                    continue
                yield sid, domain, case


PLACEHOLDER = re.compile(r"^<см\.\s+(.+?)>$")


def resolve_placeholder(value: str) -> str:
    """Replace '<см. path>' with the first code block of that file (or the whole file)."""
    m = PLACEHOLDER.match(value.strip())
    if not m:
        return value
    path = ROOT / m.group(1)
    if not path.exists():
        return value
    text = path.read_text()
    blocks = re.findall(r"```\w*\n(.*?)```", text, re.S)
    return blocks[0].strip() if blocks else text


def build_prompt(skill_id: str, case: dict) -> str:
    skill = load_skill(skill_id)
    variables = {
        k: resolve_placeholder("" if v is None else str(v))
        for k, v in (case.get("input") or {}).items()
    }
    return render_prompt(skill, variables)


def call_llm(provider: str, model: str, prompt: str, max_tokens: int, timeout: float) -> str:
    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        extract = _anthropic_extract
    elif provider == "openai":
        url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "content-type": "application/json"}
        body = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
        extract = _openai_extract
    elif provider == "ollama":
        url = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/") + "/api/chat"
        headers = {"content-type": "application/json"}
        body = {"model": model, "stream": False, "messages": [{"role": "user", "content": prompt}]}
        extract = lambda j: j["message"]["content"]
    else:
        raise ValueError(f"unknown provider: {provider}")

    last_err = ""
    for attempt in range(4):
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=timeout)
        except httpx.TimeoutException:
            last_err = "timeout"
            time.sleep(2 ** attempt * 2)
            continue
        if r.status_code in RETRY_STATUS:
            last_err = f"HTTP {r.status_code}"
            time.sleep(2 ** attempt * 2)
            continue
        r.raise_for_status()
        return extract(r.json())
    raise RuntimeError(f"retries exhausted ({last_err})")


def check_expected(output: str, expected: dict) -> list[str]:
    """Return list of failure messages (empty = pass)."""
    failures = []
    low = output.lower()
    for s in expected.get("must_contain", []) or []:
        options = s if isinstance(s, list) else [s]
        if not any(str(o).lower() in low for o in options):
            failures.append(f"нет обязательной подстроки: {s!r}")
    for s in expected.get("should_not_contain", []) or []:
        if str(s).lower() in low:
            failures.append(f"найдена запрещённая подстрока: {s!r}")
    return failures


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill", help="домен (db-sql) или id скилла (db-sql.write-migration)")
    ap.add_argument("--case", help="id одного кейса")
    ap.add_argument("--provider", choices=["anthropic", "openai", "ollama", "dry-run"], default="dry-run")
    ap.add_argument("--model", default=os.environ.get("AI_SKILLS_MODEL"), help="имя модели или env AI_SKILLS_MODEL")
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--list", action="store_true", help="показать кейсы и выйти")
    ap.add_argument("--no-save", action="store_true", help="не сохранять результаты на диск")
    args = ap.parse_args()

    selected = list(iter_cases(args.skill, args.case))
    if not selected:
        print("Нет кейсов под заданный фильтр.", file=sys.stderr)
        return 2

    if args.list:
        for sid, _, case in selected:
            print(f"{sid}  {case.get('id')}  — {case.get('description', '')}")
        print(f"\nВсего: {len(selected)}")
        return 0

    live = args.provider != "dry-run"
    if live and not args.model:
        print("Укажи --model или переменную AI_SKILLS_MODEL.", file=sys.stderr)
        return 2
    key_env = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}.get(args.provider)
    if key_env and key_env not in os.environ:
        print(f"Не задана переменная окружения {key_env}.", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = RESULTS_DIR / stamp
    if not args.no_save:
        out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    failed = errored = 0
    print(f"Провайдер: {args.provider}  Модель: {args.model or '-'}  Кейсов: {len(selected)}\n")

    for sid, _, case in selected:
        cid = case.get("id")
        label = f"{sid} / {cid}"
        record = {"skill": sid, "case": cid, "status": "", "failures": [], "quality": case.get("expected", {}).get("quality", {})}
        try:
            prompt = build_prompt(sid, case)
        except Exception as exc:  # noqa: BLE001
            record.update(status="ERROR", failures=[f"рендер: {exc}"])
            errored += 1
            print(f"ERROR  {label}\n         рендер: {exc}")
            results.append(record)
            continue

        base = safe_name(f"{sid}__{cid}")
        if not args.no_save:
            (out_dir / f"{base}.prompt.md").write_text(prompt)

        if not live:
            record["status"] = "RENDERED"
            print(f"OK     {label}  (промпт {len(prompt)} символов)")
            results.append(record)
            continue

        try:
            output = call_llm(args.provider, args.model, prompt, args.max_tokens, args.timeout)
        except Exception as exc:  # noqa: BLE001
            record.update(status="ERROR", failures=[f"вызов модели: {exc}"])
            errored += 1
            print(f"ERROR  {label}\n         вызов модели: {exc}")
            results.append(record)
            continue

        if not args.no_save:
            (out_dir / f"{base}.output.md").write_text(output)

        failures = check_expected(output, case.get("expected", {}) or {})
        record["finish_reason"] = LAST_FINISH["v"]
        if not output.strip():
            failures.insert(0, "пустой ответ (токены могли уйти на reasoning)")
        elif LAST_FINISH["v"] in ("length", "max_tokens"):
            failures.insert(0, "ответ обрезан по лимиту токенов")
        record["failures"] = failures
        if failures:
            record["status"] = "FAIL"
            failed += 1
            print(f"FAIL   {label}")
            for f in failures:
                print(f"         - {f}")
        else:
            record["status"] = "PASS"
            print(f"PASS   {label}")
        if record["quality"]:
            flags = ", ".join(record["quality"].keys())
            print(f"         ручная проверка: {flags}")
        results.append(record)

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"\nИтого: {total} кейсов" + (f", {passed} PASS, {failed} FAIL, {errored} ERROR" if live else f", ERROR: {errored}"))

    if not args.no_save:
        summary = {"provider": args.provider, "model": args.model, "timestamp": stamp, "results": results}
        (out_dir / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"Результаты: {out_dir.relative_to(ROOT)}")

    return 1 if (failed or errored) else 0


if __name__ == "__main__":
    sys.exit(main())
