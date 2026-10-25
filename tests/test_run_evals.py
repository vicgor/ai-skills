import argparse
import time

import httpx
import pytest

import run_evals
from run_evals import (
    build_judge_prompt,
    call_llm,
    check_expected,
    parse_judge,
    resolve_placeholder,
    run_case,
    run_cases,
    safe_name,
)


class TestCheckExpected:
    def test_empty_expected_passes(self):
        assert check_expected("anything", {}) == []

    def test_must_contain_is_case_insensitive(self):
        assert check_expected("Use SHOW PROCESSLIST here", {"must_contain": ["show processlist"]}) == []

    def test_must_contain_missing_substring_fails(self):
        failures = check_expected("nothing relevant", {"must_contain": ["KILL"]})
        assert failures == ["нет обязательной подстроки: 'KILL'"]

    def test_must_contain_any_of_passes_on_one_option(self):
        assert check_expected("Если только нужно", {"must_contain": [["Unless", "если только"]]}) == []

    def test_must_contain_any_of_fails_when_no_option_found(self):
        failures = check_expected("ничего", {"must_contain": [["Unless", "если только"]]})
        assert len(failures) == 1
        assert "Unless" in failures[0]

    def test_should_not_contain_found_fails(self):
        failures = check_expected("сначала web_search, затем fetch", {"should_not_contain": ["Сначала web_search"]})
        assert failures == ["найдена запрещённая подстрока: 'Сначала web_search'"]

    def test_failures_from_all_checks_are_collected(self):
        expected = {"must_contain": ["a", "b"], "should_not_contain": ["c"]}
        assert len(check_expected("c", expected)) == 3


CONFLICT_MARKER = r"^\s*(<<<<<<<|>>>>>>>)( |$)"


class TestShouldNotMatch:
    @pytest.mark.parametrize(
        "output",
        [
            "<<<<<<< HEAD\nimport yaml",
            "code\n<<<<<<< feature/json-output\n",
            "  >>>>>>> feature/x",
            "x = 1\n>>>>>>>\n",
        ],
    )
    def test_unresolved_marker_at_line_start_fails(self, output):
        assert check_expected(output, {"should_not_match": [CONFLICT_MARKER]}) != []

    @pytest.mark.parametrize(
        "output",
        [
            "Проверь, что не осталось `<<<<<<<` и `>>>>>>>`.",
            "git grep -n -E '^(<<<<<<<|=======|>>>>>>>)' -- file.py",
            "<<<<<<<< not a marker",
            "import yaml\nimport json\n",
        ],
    )
    def test_quoted_or_absent_markers_pass(self, output):
        assert check_expected(output, {"should_not_match": [CONFLICT_MARKER]}) == []

    def test_pattern_is_case_sensitive(self):
        assert check_expected("kill 42", {"should_not_match": [r"^KILL"]}) == []


class TestResolvePlaceholder:
    def test_plain_value_unchanged(self):
        assert resolve_placeholder("def main(): ...") == "def main(): ..."

    def test_missing_file_keeps_placeholder(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_evals, "ROOT", tmp_path)
        assert resolve_placeholder("<см. examples/nope.md>") == "<см. examples/nope.md>"

    def test_returns_first_code_block(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_evals, "ROOT", tmp_path)
        (tmp_path / "ex.md").write_text("# Пример\n\n```python\nprint(1)\n```\n\n```bash\nls\n```\n")
        assert resolve_placeholder("  <см. ex.md>  ") == "print(1)"

    def test_returns_whole_file_without_code_blocks(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_evals, "ROOT", tmp_path)
        (tmp_path / "ex.md").write_text("просто текст")
        assert resolve_placeholder("<см. ex.md>") == "просто текст"


def test_safe_name_replaces_unsafe_chars():
    assert safe_name("db-sql.write-migration__drop col/1") == "db-sql.write-migration__drop_col_1"


# --- call_llm ----------------------------------------------------------------

OPENAI_OK = {"choices": [{"message": {"content": "ответ"}, "finish_reason": "stop"}]}


def fake_post(responses):
    """httpx.post, отдающий по очереди элементы responses: исключение или (status, json)."""
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        item = responses[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        status, body = item
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))

    post.calls = calls
    return post


@pytest.fixture
def no_sleep(monkeypatch):
    delays = []
    monkeypatch.setattr(run_evals, "sleep", delays.append)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    return delays


def test_call_llm_openai_returns_text_and_finish_reason(monkeypatch, no_sleep):
    monkeypatch.setattr(httpx, "post", fake_post([(200, OPENAI_OK)]))
    assert call_llm("openai", "m", "p", 100, 1) == ("ответ", "stop")
    assert no_sleep == []


def test_call_llm_anthropic_joins_text_blocks(monkeypatch, no_sleep):
    body = {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}], "stop_reason": "max_tokens"}
    monkeypatch.setattr(httpx, "post", fake_post([(200, body)]))
    assert call_llm("anthropic", "m", "p", 100, 1) == ("ab", "max_tokens")


def test_call_llm_ollama_passes_token_limit(monkeypatch, no_sleep):
    post = fake_post([(200, {"message": {"content": "x"}, "done_reason": "length"})])
    monkeypatch.setattr(httpx, "post", post)
    assert call_llm("ollama", "m", "p", 123, 1) == ("x", "length")
    assert post.calls[0]["options"] == {"num_predict": 123}


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("refused"),
        httpx.RemoteProtocolError("server disconnected"),
        httpx.ReadTimeout("slow"),
        (529, {}),
        (429, {}),
    ],
)
def test_call_llm_retries_transient_errors(monkeypatch, no_sleep, error):
    post = fake_post([error, (200, OPENAI_OK)])
    monkeypatch.setattr(httpx, "post", post)
    assert call_llm("openai", "m", "p", 100, 1) == ("ответ", "stop")
    assert len(post.calls) == 2
    assert no_sleep == [2]


def test_call_llm_gives_up_after_all_attempts(monkeypatch, no_sleep):
    post = fake_post([httpx.ConnectError("refused")] * run_evals.RETRY_ATTEMPTS)
    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(RuntimeError, match="retries exhausted.*ConnectError"):
        call_llm("openai", "m", "p", 100, 1)
    assert len(post.calls) == run_evals.RETRY_ATTEMPTS
    assert no_sleep == [2, 4, 8]


def test_call_llm_does_not_retry_client_error(monkeypatch, no_sleep):
    post = fake_post([(400, {"error": "bad request"})])
    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(httpx.HTTPStatusError):
        call_llm("openai", "m", "p", 100, 1)
    assert len(post.calls) == 1


# --- run_case / run_cases ----------------------------------------------------


def make_args(provider="openai", jobs=1):
    return argparse.Namespace(provider=provider, model="m", max_tokens=100, timeout=1, jobs=jobs)


CASE = {"id": "c", "input": {}, "expected": {"must_contain": ["yes"], "quality": {"has_x": True}}}


@pytest.fixture
def fake_llm(monkeypatch):
    """Подменяет build_prompt и call_llm; ответы задаются словарём prompt -> (text, finish)."""
    answers = {}
    monkeypatch.setattr(run_evals, "build_prompt", lambda sid, case: f"prompt:{case['id']}")
    monkeypatch.setattr(run_evals, "call_llm", lambda provider, model, prompt, *a: answers[prompt])
    return answers


@pytest.mark.parametrize(
    "answer, status, first_failure",
    [
        (("yes", "stop"), "PASS", None),
        (("no", "stop"), "FAIL", "нет обязательной подстроки: 'yes'"),
        (("yes", "length"), "FAIL", "ответ обрезан по лимиту токенов"),
        (("yes", "max_tokens"), "FAIL", "ответ обрезан по лимиту токенов"),
        (("  ", "stop"), "FAIL", "пустой ответ (токены могли уйти на reasoning)"),
    ],
)
def test_run_case_statuses(fake_llm, answer, status, first_failure):
    fake_llm["prompt:c"] = answer
    record, lines = run_case("s.k", CASE, make_args(), None)
    assert record["status"] == status
    assert record["finish_reason"] == answer[1]
    assert (record["failures"][0] if record["failures"] else None) == first_failure
    assert lines[0].startswith(status)
    assert lines[-1] == "         ручная проверка: has_x"


def test_run_case_llm_error(monkeypatch, fake_llm):
    def boom(*a):
        raise RuntimeError("retries exhausted (timeout)")

    monkeypatch.setattr(run_evals, "call_llm", boom)
    record, _ = run_case("s.k", CASE, make_args(), None)
    assert record["status"] == "ERROR"
    assert "retries exhausted" in record["failures"][0]


def test_run_case_dry_run_saves_prompt_only(fake_llm, tmp_path):
    record, _ = run_case("s.k", CASE, make_args("dry-run"), tmp_path)
    assert record["status"] == "RENDERED"
    assert [p.name for p in tmp_path.iterdir()] == ["s.k__c.prompt.md"]


def test_run_case_saves_prompt_and_output(fake_llm, tmp_path):
    fake_llm["prompt:c"] = ("yes", "stop")
    run_case("s.k", CASE, make_args(), tmp_path)
    assert (tmp_path / "s.k__c.output.md").read_text() == "yes"


def test_run_cases_parallel_keeps_input_order(monkeypatch, fake_llm, capsys):
    cases = [dict(CASE, id=f"c{i}") for i in range(6)]
    for i in range(6):
        fake_llm[f"prompt:c{i}"] = ("yes", "stop")
    # первые кейсы отвечают медленнее, чтобы порядок завершения был обратным
    real = run_evals.call_llm
    monkeypatch.setattr(run_evals, "call_llm", lambda p, m, prompt, *a: (time.sleep(0.05 * (6 - int(prompt[-1]))), real(p, m, prompt, *a))[1])

    records = run_cases([("s.k", "s", c) for c in cases], make_args(jobs=6), None)
    assert [r["case"] for r in records] == [f"c{i}" for i in range(6)]
    assert all(r["status"] == "PASS" for r in records)
    printed = [line.split()[-1] for line in capsys.readouterr().out.splitlines() if line.startswith("PASS")]
    assert printed[0] == "c5"  # печатаются по мере готовности


# --- judge -------------------------------------------------------------------


class TestParseJudge:
    def test_valid_json(self):
        text = '{"has_x": {"verdict": "pass", "reason": "есть"}, "has_y": {"verdict": "FAIL", "reason": "нет"}}'
        assert parse_judge(text, ["has_x", "has_y"]) == {
            "has_x": {"verdict": "pass", "reason": "есть"},
            "has_y": {"verdict": "fail", "reason": "нет"},
        }

    def test_json_wrapped_in_text_and_code_fence(self):
        text = 'Вот оценка:\n```json\n{"has_x": {"verdict": "unknown", "reason": "неясно"}}\n```'
        assert parse_judge(text, ["has_x"])["has_x"]["verdict"] == "unknown"

    @pytest.mark.parametrize(
        "text",
        ["не JSON вовсе", "{broken", '{"has_x": "pass"}', '{"has_x": {"verdict": "maybe"}}', "[1, 2]", "{}"],
    )
    def test_malformed_or_missing_is_unknown(self, text):
        assert parse_judge(text, ["has_x"]) == {
            "has_x": {"verdict": "unknown", "reason": "судья не вернул корректный вердикт"}
        }

    def test_extra_keys_are_ignored(self):
        text = '{"has_x": {"verdict": "pass", "reason": ""}, "other": {"verdict": "fail"}}'
        assert list(parse_judge(text, ["has_x"])) == ["has_x"]


def test_build_judge_prompt_lists_criteria_and_keys():
    prompt = build_judge_prompt(
        {"id": "c", "description": "Ответ без кода"}, "ОТВЕТ", {"asks_for_missing_input": True, "max_code_blocks": 0}
    )
    assert "Ответ без кода" in prompt
    assert "<answer>\nОТВЕТ\n</answer>" in prompt
    assert "- `asks_for_missing_input`\n" in prompt
    assert "- `max_code_blocks` (ожидаемое значение: 0)" in prompt
    assert '"max_code_blocks": {"verdict": "pass|fail|unknown"' in prompt


def make_judge_args(**kw):
    args = make_args()
    args.judge, args.judge_model, args.judge_strict = True, "judge-m", False
    for k, v in kw.items():
        setattr(args, k, v)
    return args


@pytest.fixture
def fake_llm_with_judge(monkeypatch):
    """Ответ модели — 'yes'; судья (judge-m) отвечает judge_answer[0]. Запоминает модели вызовов."""
    judge_answer = ['{"has_x": {"verdict": "fail", "reason": "нет X"}}']
    models = []
    monkeypatch.setattr(run_evals, "build_prompt", lambda sid, case: "prompt")

    def llm(provider, model, prompt, *a):
        models.append(model)
        return (judge_answer[0], "stop") if model == "judge-m" else ("yes", "stop")

    monkeypatch.setattr(run_evals, "call_llm", llm)
    return judge_answer, models


def test_run_case_judge_reports_without_failing(fake_llm_with_judge, tmp_path):
    _, models = fake_llm_with_judge
    record, lines = run_case("s.k", CASE, make_judge_args(), tmp_path)
    assert models == ["m", "judge-m"]
    assert record["status"] == "PASS"
    assert record["quality_verdicts"] == {"has_x": {"verdict": "fail", "reason": "нет X"}}
    assert lines[-1] == "         quality fail    has_x"
    assert (tmp_path / "s.k__c.judge.md").exists()


def test_run_case_judge_strict_turns_fail_verdict_into_failure(fake_llm_with_judge):
    record, _ = run_case("s.k", CASE, make_judge_args(judge_strict=True), None)
    assert record["status"] == "FAIL"
    assert record["failures"] == ["quality: has_x — нет X"]


def test_run_case_judge_strict_ignores_unknown(fake_llm_with_judge):
    fake_llm_with_judge[0][0] = '{"has_x": {"verdict": "unknown", "reason": "?"}}'
    record, _ = run_case("s.k", CASE, make_judge_args(judge_strict=True), None)
    assert record["status"] == "PASS"


def test_run_case_judge_error_gives_unknown(monkeypatch, fake_llm_with_judge):
    def llm(provider, model, prompt, *a):
        if model == "judge-m":
            raise RuntimeError("retries exhausted (timeout)")
        return "yes", "stop"

    monkeypatch.setattr(run_evals, "call_llm", llm)
    record, _ = run_case("s.k", CASE, make_judge_args(judge_strict=True), None)
    assert record["status"] == "PASS"
    assert record["quality_verdicts"]["has_x"]["verdict"] == "unknown"
    assert "ошибка вызова судьи" in record["quality_verdicts"]["has_x"]["reason"]


def test_run_case_judge_defaults_to_main_model(fake_llm_with_judge):
    _, models = fake_llm_with_judge
    run_case("s.k", CASE, make_judge_args(judge_model=None), None)
    assert models == ["m", "m"]


def test_run_case_without_judge_flag_does_not_call_judge(fake_llm_with_judge):
    _, models = fake_llm_with_judge
    record, lines = run_case("s.k", CASE, make_args(), None)
    assert models == ["m"]
    assert "quality_verdicts" not in record
    assert lines[-1] == "         ручная проверка: has_x"
