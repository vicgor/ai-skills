# Changelog: git skills

## 2026-10-25

Правки по замеру стабильности (`--repeat 5 --judge`, прогон 20261025-121537: 325/330 PASS, 61/66 кейсов стабильны). После правок затронутые скиллы — 70/70 PASS, 165/165 флагов pass.

### git.pr-description — v1.0.2
- Блок «## ⚠️ BREAKING CHANGES» сразу после заголовка обязателен, если поле breaking_changes не пустое или изменение ломает совместимость; упоминание в Summary его не заменяет. Модель игнорировала явно переданный breaking_changes (1 из 5 прогонов).

## 2026-10-12

### git.pr-description — v1.0.1
- Если указан Issue, в конце описания — `Closes #N` / `Refs #N` дословно.

### git.resolve-merge-conflict (только eval-кейсы)
- Неразрешённые маркеры проверяются regex `should_not_match` (маркер в начале строки), а не подстрокой: цитаты маркеров в тексте и командах `git grep` больше не дают ложных FAIL, а маркеры любых веток (`<<<<<<< feature`) снова ловятся.

## 2026-06-06

### Все скиллы — v1.0.0 (initial release)
- write-commit-message: conventional commit message по diff или описанию.
- pr-description: структурированное описание PR с testing instructions.
- resolve-merge-conflict: анализ конфликта, стратегия, resolved версия.
- Добавлены eval-кейсы для write-commit-message.
- Добавлен пример commit-message-example.md.
