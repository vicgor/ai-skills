# Changelog: db-sql skills

## 2026-10-12

### db-sql.diagnose-performance — v1.0.1
- Инструменты строго под указанный engine: для postgresql — pg_stat_activity, pg_locks, pg_stat_statements; никаких SHOW PROCESSLIST.
- Ожидания блокировок: найти блокирующую сессию и предложить `KILL` / `KILL QUERY` с предупреждением об откате транзакции.
- Default environment: «production» вместо «production MariaDB»; движок выводится отдельной строкой.
- Eval-кейсы: processlist принимает эквиваленты (information_schema.PROCESSLIST, performance_schema.threads).

### db-sql.write-migration — v1.0.1
- Для DROP COLUMN / DROP TABLE / удаления данных обязателен шаг резервного копирования и проверки копии.

## 2026-06-05

### Все скиллы — v1.0.0 (initial release)
- query-optimize: анализ и оптимизация SQL-запросов, EXPLAIN, индексы.
- schema-review: ревью DDL-схемы, типы данных, нормализация.
- write-migration: безопасные up/down миграции с оценкой рисков блокировок.
- diagnose-performance: диагностика проблем производительности БД по симптомам.
- Добавлены eval-кейсы для query-optimize.
