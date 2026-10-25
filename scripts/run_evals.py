#!/usr/bin/env python3
"""Runs eval cases from evals/<domain>/<skill>.cases.yaml against an LLM.

Examples:
    python scripts/run_evals.py --provider dry-run
    python scripts/run_evals.py --provider anthropic --model <model> --skill db-sql
    python scripts/run_evals.py --provider openai --model <model> --jobs 8
    python scripts/run_evals.py --provider openai --model <model> --judge --judge-model <model>
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
from concurrent.futures import ThreadPoolExecutor, as_completed
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
RETRY_ATTEMPTS = 4
TRUNCATED = {"length", "max_tokens"}
sleep = time.sleep  # подменяется в тестах


def _openai_extract(j) -> tuple[str, str | None]:
    ch = j["choices"][0]
    return ch["message"].get("content") or "", ch.get("finish_reason")


def _anthropic_extract(j) -> tuple[str, str | None]:
    return "".join(b.get("text", "") for b in j.get("content", [])), j.get("stop_reason")


def _ollama_extract(j) -> tuple[str, str | None]:
    return j["message"]["content"], j.get("done_reason")


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


def call_llm(provider: str, model: str, prompt: str, max_tokens: int, timeout: float) -> tuple[str, str | None]:
    """Return (text, finish_reason). Retries on network errors, timeouts and 429/5xx."""
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
        body = {
            "model": model,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [{"role": "user", "content": prompt}],
        }
        extract = _ollama_extract
    else:
        raise ValueError(f"unknown provider: {provider}")

    last_err = ""
    for attempt in range(RETRY_ATTEMPTS):
        if attempt:
            sleep(2 ** attempt)
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=timeout)
        except httpx.TimeoutException:
            last_err = "timeout"
            continue
        except httpx.TransportError as exc:  # обрыв соединения, DNS, reset и т.п.
            last_err = f"{type(exc).__name__}: {exc}"
            continue
        if r.status_code in RETRY_STATUS:
            last_err = f"HTTP {r.status_code}"
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
    for pattern in expected.get("should_not_match", []) or []:
        if re.search(pattern, output, re.M):
            failures.append(f"найдено совпадение с запрещённым шаблоном: {pattern!r}")
    return failures


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)


JUDGE_VERDICTS = ("pass", "fail", "unknown")
JUDGE_PROMPT = """Ты строгий и беспристрастный эксперт-оценщик. Оцени ответ ассистента по каждому критерию отдельно.

## Задача, на которую отвечал ассистент
{description}

## Ответ ассистента
<answer>
{output}
</answer>

## Критерии
{criteria}

## Правила
- Оценивай только то, что есть в ответе. Не додумывай за ассистента.
- pass — критерий явно выполнен; fail — явно не выполнен; unknown — по ответу нельзя уверенно решить.
- Сомневаешься между pass и fail — ставь unknown.
- reason — одно короткое предложение, со ссылкой на конкретное место ответа.

Верни только JSON без пояснений вокруг, ровно с этими ключами:
{{{keys}}}
"""


def build_judge_prompt(case: dict, output: str, quality: dict) -> str:
    criteria = "\n".join(
        f"- `{name}`" + ("" if value is True else f" (ожидаемое значение: {value})") for name, value in quality.items()
    )
    keys = ", ".join(f'"{name}": {{"verdict": "pass|fail|unknown", "reason": "..."}}' for name in quality)
    return JUDGE_PROMPT.format(
        description=case.get("description") or case.get("id"), output=output, criteria=criteria, keys=keys
    )


def parse_judge(text: str, flags) -> dict:
    """Extract {flag: {verdict, reason}} from the judge answer; anything missing or malformed is 'unknown'."""
    data = {}
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            data = {}
    verdicts = {}
    for flag in flags:
        item = data.get(flag) if isinstance(data, dict) else None
        verdict = str(item.get("verdict", "")).lower() if isinstance(item, dict) else ""
        if verdict in JUDGE_VERDICTS:
            verdicts[flag] = {"verdict": verdict, "reason": str(item.get("reason", ""))}
        else:
            verdicts[flag] = {"verdict": "unknown", "reason": "судья не вернул корректный вердикт"}
    return verdicts


def judge_case(args, case: dict, output: str, quality: dict, out_dir: Path | None, base: str) -> dict:
    prompt = build_judge_prompt(case, output, quality)
    try:
        text, _ = call_llm(args.provider, args.judge_model or args.model, prompt, args.max_tokens, args.timeout)
    except Exception as exc:  # noqa: BLE001
        return {flag: {"verdict": "unknown", "reason": f"ошибка вызова судьи: {exc}"} for flag in quality}
    if out_dir:
        (out_dir / f"{base}.judge.md").write_text(text)
    return parse_judge(text, quality)


def run_case(sid: str, case: dict, args, out_dir: Path | None) -> tuple[dict, list[str]]:
    """Render, call the model and check one case. Returns (record, lines to print)."""
    cid = case.get("id")
    label = f"{sid} / {cid}"
    record = {"skill": sid, "case": cid, "status": "", "failures": [], "quality": (case.get("expected") or {}).get("quality", {})}
    try:
        prompt = build_prompt(sid, case)
    except Exception as exc:  # noqa: BLE001
        record.update(status="ERROR", failures=[f"рендер: {exc}"])
        return record, [f"ERROR  {label}", f"         рендер: {exc}"]

    base = safe_name(f"{sid}__{cid}")
    if out_dir:
        (out_dir / f"{base}.prompt.md").write_text(prompt)

    if args.provider == "dry-run":
        record["status"] = "RENDERED"
        return record, [f"OK     {label}  (промпт {len(prompt)} символов)"]

    try:
        output, finish = call_llm(args.provider, args.model, prompt, args.max_tokens, args.timeout)
    except Exception as exc:  # noqa: BLE001
        record.update(status="ERROR", failures=[f"вызов модели: {exc}"])
        return record, [f"ERROR  {label}", f"         вызов модели: {exc}"]

    if out_dir:
        (out_dir / f"{base}.output.md").write_text(output)

    failures = check_expected(output, case.get("expected") or {})
    if not output.strip():
        failures.insert(0, "пустой ответ (токены могли уйти на reasoning)")
    elif finish in TRUNCATED:
        failures.insert(0, "ответ обрезан по лимиту токенов")
    record["finish_reason"] = finish

    verdicts = {}
    if getattr(args, "judge", False) and record["quality"] and output.strip():
        verdicts = judge_case(args, case, output, record["quality"], out_dir, base)
        record["quality_verdicts"] = verdicts
        if getattr(args, "judge_strict", False):
            failures += [f"quality: {flag} — {v['reason']}" for flag, v in verdicts.items() if v["verdict"] == "fail"]

    record["failures"] = failures
    record["status"] = "FAIL" if failures else "PASS"
    lines = [f"{record['status']:<6} {label}"] + [f"         - {f}" for f in failures]
    if verdicts:
        lines += [f"         quality {v['verdict']:<7} {flag}" for flag, v in verdicts.items()]
    elif record["quality"]:
        lines.append(f"         ручная проверка: {', '.join(record['quality'].keys())}")
    return record, lines


def run_cases(selected: list, args, out_dir: Path | None) -> list[dict]:
    """Run cases with args.jobs workers; print each case as it finishes, return records in input order."""
    results: list[dict | None] = [None] * len(selected)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_case, sid, case, args, out_dir): i for i, (sid, _, case) in enumerate(selected)}
        for future in as_completed(futures):
            record, lines = future.result()
            results[futures[future]] = record
            print("\n".join(lines), flush=True)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill", help="домен (db-sql) или id скилла (db-sql.write-migration)")
    ap.add_argument("--case", help="id одного кейса")
    ap.add_argument("--provider", choices=["anthropic", "openai", "ollama", "dry-run"], default="dry-run")
    ap.add_argument("--model", default=os.environ.get("AI_SKILLS_MODEL"), help="имя модели или env AI_SKILLS_MODEL")
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--jobs", type=int, default=1, help="сколько кейсов гонять параллельно (по умолчанию 1)")
    ap.add_argument("--judge", action="store_true", help="оценить флаги quality моделью-судьёй")
    ap.add_argument("--judge-model", help="модель-судья (по умолчанию --model), тот же провайдер")
    ap.add_argument("--judge-strict", action="store_true", help="вердикт fail судьи делает кейс FAIL")
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

    if args.jobs < 1:
        print("--jobs должен быть ≥ 1.", file=sys.stderr)
        return 2
    if args.judge_strict:
        args.judge = True
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

    print(f"Провайдер: {args.provider}  Модель: {args.model or '-'}  Кейсов: {len(selected)}  Потоков: {args.jobs}\n")
    results = run_cases(selected, args, None if args.no_save else out_dir)
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errored = sum(1 for r in results if r["status"] == "ERROR")

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"\nИтого: {total} кейсов" + (f", {passed} PASS, {failed} FAIL, {errored} ERROR" if live else f", ERROR: {errored}"))
    verdicts = [v["verdict"] for r in results for v in r.get("quality_verdicts", {}).values()]
    if verdicts:
        counts = ", ".join(f"{verdicts.count(k)} {k}" for k in JUDGE_VERDICTS)
        print(f"Quality (судья {args.judge_model or args.model}): {len(verdicts)} флагов — {counts}")

    if not args.no_save:
        summary = {
            "provider": args.provider,
            "model": args.model,
            "judge_model": (args.judge_model or args.model) if args.judge else None,
            "timestamp": stamp,
            "results": results,
        }
        (out_dir / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"Результаты: {out_dir.relative_to(ROOT)}")

    return 1 if (failed or errored) else 0


if __name__ == "__main__":
    sys.exit(main())
