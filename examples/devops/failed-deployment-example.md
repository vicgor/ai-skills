# Пример: упавший деплой systemd-сервиса

Используй как входные данные для `devops.debug-deployment`.

## Входные данные

```yaml
skill_id: devops.debug-deployment
inputs:
  deployment_type: systemd
  environment: "Ubuntu 22.04 LTS, Python 3.12, uv 0.4"
  what_changed: "обновили зависимости через uv sync после добавления pydantic-settings"
  error_logs: |
    Jun 05 23:44:01 prod-01 systemd[1]: Starting My API Service...
    Jun 05 23:44:01 prod-01 myapi[12483]: Traceback (most recent call last):
    Jun 05 23:44:01 prod-01 myapi[12483]:   File "/opt/myapi/.venv/bin/myapi", line 8, in <module>
    Jun 05 23:44:01 prod-01 myapi[12483]:     from myapi.config import Settings
    Jun 05 23:44:01 prod-01 myapi[12483]:   File "/opt/myapi/.venv/lib/python3.12/site-packages/myapi/config.py", line 3, in <module>
    Jun 05 23:44:01 prod-01 myapi[12483]:     from pydantic_settings import BaseSettings
    Jun 05 23:44:01 prod-01 myapi[12483]: ModuleNotFoundError: No module named 'pydantic_settings'
    Jun 05 23:44:01 prod-01 systemd[1]: myapi.service: Main process exited, code=exited, status=1/FAILURE
    Jun 05 23:44:01 prod-01 systemd[1]: Failed to start My API Service.
  current_config: |
    [Unit]
    Description=My API Service
    After=network.target mariadb.service

    [Service]
    User=appuser
    WorkingDirectory=/opt/myapi
    ExecStart=/opt/myapi/.venv/bin/myapi serve
    Restart=on-failure
    RestartSec=5
    EnvironmentFile=/opt/myapi/.env

    [Install]
    WantedBy=multi-user.target
```

## Ожидаемый результат

- Root cause: `pydantic-settings` не установлен в `.venv` на сервере
- Гипотезы: забыли запустить `uv sync` на сервере, или `pyproject.toml` не содержит зависимость
- Команды: `sudo -u appuser /opt/myapi/.venv/bin/pip list | grep pydantic`, `uv sync`
- Verification: `systemctl start myapi && systemctl status myapi`
