# Changelog: devops skills

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
