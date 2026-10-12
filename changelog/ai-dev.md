# Changelog: ai-dev skills

## 2026-10-12

### ai-dev.design-prompt — v2.0.1
- Противоречивые требования (например, «кратко» и «подробно»): промпт обязан назвать главное правило и исключение («Unless ...» / «если только ...») с конкретным лимитом.
- mode=improve: в каждом пункте диагноза цитировать проблемный фрагмент current_prompt.
- mode=write: отсутствие «Текущего промпта» не ошибка; при расплывчатом goal — 2–3 уточняющих вопроса.
- Eval-кейсы: проверки принимают эквивалентные формулировки.

### ai-dev.write-eval — v2.0.1
- Для agent_type=research обязательны измерения groundedness, coverage и source quality.
- Eval-кейсы: в no_rigid_tool_order возвращена проверка coverage; в insufficient_failures_no_hallucination убраны слишком общие слова («нужно», «мало», «вопросы»).

## 2026-10-10

### ai-dev.write-eval — v2.0.0
- Новый скилл: проектирование eval-сьюта для LLM-фичи или агента (graders, rubric, метрики pass@k / pass^k).
- Добавлены eval-кейсы: evals/ai-dev/write-eval.cases.yaml.

### ai-dev.design-prompt — v2.0.0
- Приведён к актуальной схеме скиллов: inputs[].name вместо id, добавлены prompt_template, output_contract.format и must_include.
- Добавлены owner, tags, use_when, avoid_when, quality_checks, examples.
- Новый необязательный вход failure_examples для режима improve.
- Режим improve без current_prompt: скилл просит прислать промпт и не выдумывает его.
- Добавлен пример examples/ai-dev/design-prompt-example.md.

## 2026-08-30

### ai-dev.design-prompt — v1.0.0 (initial release)
- Написание системного промпта с нуля или улучшение существующего: роль, ограничения, формат вывода, uncertainty handling.
