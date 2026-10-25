# Changelog: devops skills

## 2026-10-25

Правки по замеру стабильности (`--repeat 5 --judge`, прогон 20261025-121537: 325/330 PASS, 61/66 кейсов стабильны). После правок затронутые скиллы — 70/70 PASS, 165/165 флагов pass.

### devops.server-hardening-checklist — v1.0.3
- Пункты на стыке тем — только в части фокуса (при фокусе SSH firewall — только правило для порта SSH).

Правки по вердиктам судьи (`run_evals.py --judge`): прогон до правок 20261025-102711 (65/66, quality 145 pass / 7 fail / 2 unknown), после — 20261025-105406 (66/66, quality 152 pass / 0 fail / 2 unknown).

### devops.server-hardening-checklist — v1.0.2
- Правило фокуса: при focus ≠ «всё» только относящиеся к нему разделы; мониторинг — только при focus «всё»/monitoring (раньше добавлялся всегда).
- Нумерованный чек-лист с приоритетом в каждом пункте: «1. [Критично] …».
- fail2ban обязателен, только если фокус «всё» или включает SSH.

### devops.write-dockerfile — v1.0.2
- Для существующего Dockerfile — раздел «Что изменено и почему»: каждое изменение (ENV, USER, --chown, .dockerignore…) строкой «было → стало → зачем»; перед ответом сверить построчно, что объяснена каждая новая инструкция и флаг.

### devops.github-actions-workflow — v1.0.1
- Раздел «Оптимизации» в тексте ответа: что закэшировано, ключ инвалидации, за счёт чего быстрее.
- Для существующего workflow — раздел «Что изменено и почему».

## 2026-10-12

### devops.server-hardening-checklist — v1.0.1
- Обязательная защита SSH от перебора: fail2ban (jail sshd), команда проверки и предупреждение не забанить свой IP.

### devops.write-dockerfile — v1.0.1
- Alpine + нативные расширения (numpy, psycopg2, lxml …): предупреждение про musl, основной Dockerfile на python-slim, Alpine — только как опция.
- known_failures: добавлена запись про python:alpine.

## 2026-06-05

### Все скиллы — v1.0.0 (initial release)
- debug-deployment: диагностика упавших деплоев (docker, systemd, ansible).
- write-dockerfile: production-ready Dockerfile для Python (multi-stage, uv, non-root).
- github-actions-workflow: CI/CD для Python-проектов с кэшированием и матрицей.
- server-hardening-checklist: hardening Ubuntu VPS (SSH, UFW, fail2ban, мониторинг).
- Добавлены eval-кейсы для debug-deployment.
