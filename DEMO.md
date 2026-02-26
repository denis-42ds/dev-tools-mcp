# 🎬 DEMO — Dev Tools MCP Server

Воспроизводимый сценарий тестирования всех трёх инструментов.  
**Время:** ~10–15 минут. Не требует внешних сервисов или API-ключей.

---

## Подготовка: запуск сервера

### Через Docker (рекомендуется)

```bash
# Сборка
docker build -t dev-tools-mcp .

# Запуск сервера
docker run -p 8000:8000 dev-tools-mcp serve
```

В другом терминале убедитесь, что сервер поднялся:

```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"dev-tools-mcp","version":"1.0.0","tools":[...]}
```

### Smoke-тест (быстрая проверка без запуска сервера)

```bash
docker run dev-tools-mcp smoke
```

Ожидаемый вывод:
```
╔══════════════════════════════════════════════╗
║   dev-tools-mcp  —  Smoke Test               ║
╚══════════════════════════════════════════════╝

🔍  Tool 1: scan_tech_debt
  ✅ Full scan (demo_project)
       → Всего: 28, High: 12 ✅
  ✅ Filter priority=high
  ✅ Filter extensions=.py
  ✅ Nonexistent path

📝  Tool 2: generate_release_notes
  ✅ v0.1.0..v1.0.0
  ✅ Auto range
  ...

🐳  Tool 3: audit_dockerfile
  ✅ Dockerfile.bad
  ✅ Dockerfile.good (strict)
  ...

════════════════════════════════════════════════
✅  ALL TESTS PASSED  (12/12)
════════════════════════════════════════════════
```

Код завершения: `echo $?` → `0`

---

### Запуск MCP Inspector (для ручного тестирования)

```bash
# Через HTTP (сервер должен быть запущен)
npx @modelcontextprotocol/inspector --url http://localhost:8000/mcp

# Или через stdio (локально)
npx @modelcontextprotocol/inspector python src/server.py
```

Откройте [http://localhost:5173](http://localhost:5173) → вкладка **Tools** → три инструмента.

---

## Сценарий 1 — Сканирование технического долга

Все примеры используют `/workspace` — это `demo_project/`, смонтированная в контейнер  
(или абсолютный путь на хосте при локальном запуске).

В Inspector вызовите `scan_tech_debt`:

### 1.1 Полное сканирование

```json
{
  "path": "/workspace"
}
```

**Ожидаемый результат:**
```
# 🔍 Отчёт по техдолгу
Путь: /workspace | Файлов: 6 | Найдено: 28

🔴 High: 12   🟡 Medium: 12   🔵 Low: 4

## 🔴 HIGH PRIORITY

💀 XXX — `src/users.py:13`
> SQL-инъекция!

🐛 BUG — `src/users.py:21`
> не используем constant-time comparison

⚠️ HACK — `src/users.py:24`
> пока храним пароль в открытом виде, потом исправим
...
```

---

### 1.2 Только критичные проблемы

```json
{
  "path": "/workspace",
  "priority_filter": "high"
}
```

**Ожидаемый результат:** только маркеры FIXME / BUG / HACK / XXX.

---

### 1.3 Только Python-файлы

```json
{
  "path": "/workspace",
  "extensions": ".py"
}
```

---

## Сценарий 2 — Генерация Release Notes

### 2.1 Между тегами v0.1.0 и v1.0.0

```json
{
  "repo_path": "/workspace",
  "from_ref": "v0.1.0",
  "to_ref": "v1.0.0",
  "version": "1.0.0"
}
```

**Ожидаемый результат:**
```markdown
# 🚀 Release Notes — 1.0.0
Дата: 2025-xx-xx | Диапазон: v0.1.0..v1.0.0 | Коммитов: 10

## 💥 BREAKING CHANGES
- **api**: change authentication endpoint from /auth to /api/v2/auth (b778b994)

## ✨ Новые возможности
- **users**: add user authentication module (c807938f)
- **core**: implement version tracking (be5cc76e)
- **cache**: add Redis cache manager (22ecb058)

## ⚡ Производительность
- **db**: optimize bulk user loading query (b8c645ad)

## 👷 CI/CD
- add GitHub Actions pipeline (a345016a)

## ♻️ Рефакторинг
- **users**: extract password hashing to separate module (f62f55fb)

## 👥 Авторы
- Demo User (10 коммитов)
```

---

### 2.2 Автоматическое определение диапазона

```json
{
  "repo_path": "/workspace"
}
```

Сервер сам найдёт два последних тега и возьмёт диапазон между ними.

---

### 2.3 Компактный вывод

```json
{
  "repo_path": "/workspace",
  "from_ref": "v0.1.0",
  "include_authors": false,
  "include_stats": false
}
```

---

## Сценарий 3 — Аудит Dockerfile

### 3.1 Проблемный Dockerfile

```json
{
  "path": "/workspace/infra/Dockerfile.bad"
}
```

**Ожидаемый результат:**
```
## 🐳 Dockerfile.bad
🔴 Critical: 3   🟡 Warning: 7   🔵 Info: 0

### 🔴 CRITICAL

[C001] Контейнер работает от root
  > 💡 Добавьте USER <non-root-user> перед CMD/ENTRYPOINT

[C002] Используется нефиксированный тег образа: `python:latest` (строка 2)
  > 💡 Укажите точный тег: python:3.11.9-slim

[C003] Возможная утечка секрета в ENV (строка 4)
  > 💡 Используйте Docker BuildKit secrets

### 🟡 WARNING
[W001] Отсутствует HEALTHCHECK
[W002] apt-get install без --no-install-recommends
[W003] apt-get update и install в разных слоях
...

Оценка: `████░░░░░░` 35/100
```

---

### 3.2 Эталонный Dockerfile

```json
{
  "path": "/workspace/infra/Dockerfile.good",
  "strict": true
}
```

**Ожидаемый результат:** 0 critical, оценка ≥ 90/100.

---

### 3.3 Вся директория infra/

```json
{
  "path": "/workspace/infra",
  "strict": true
}
```

Отчёт по обоим Dockerfile с итоговыми оценками.

---

## Сценарий 4 — Монтирование вашего проекта

Чтобы проанализировать свой реальный проект:

```bash
docker run -p 8000:8000 \
  -v /path/to/your/project:/workspace:ro \
  dev-tools-mcp serve
```

Затем в Inspector/Claude:

```json
{ "path": "/workspace" }                    // scan_tech_debt
{ "repo_path": "/workspace" }               // generate_release_notes  
{ "path": "/workspace" }                    // audit_dockerfile
```

---

## Ожидаемые результаты

| Инструмент | Сценарий | Ожидание |
|-----------|----------|---------|
| `scan_tech_debt` | demo_project | ≥ 20 маркеров, разбивка по приоритетам |
| `scan_tech_debt` | priority=high | Только FIXME/BUG/HACK/XXX |
| `scan_tech_debt` | несуществующий путь | Сообщение об ошибке, код не падает |
| `generate_release_notes` | v0.1.0..v1.0.0 | 10 коммитов, BREAKING CHANGE выделен |
| `generate_release_notes` | auto | Корректный автовыбор тегов |
| `generate_release_notes` | не git-репо | Понятное сообщение об ошибке |
| `audit_dockerfile` | Dockerfile.bad | ≥ 3 critical, score ≤ 40/100 |
| `audit_dockerfile` | Dockerfile.good | 0 critical, score ≥ 90/100 |
| `audit_dockerfile` | директория | Отчёт по нескольким файлам |

---

## Проверка через /health и /mcp напрямую

```bash
# Health check
curl http://localhost:8000/health

# Инициализация MCP-сессии
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

---

## Диагностика проблем

| Проблема | Решение |
|---------|---------|
| `connection refused :8000` | Убедитесь, что `serve` запущен; проверьте `docker ps` |
| `smoke` вернул ненулевой код | `docker run dev-tools-mcp smoke 2>&1` — читайте вывод |
| `git не найден` | Используйте Docker-образ (git уже включён) |
| `mcp not found` | `pip install -r requirements.txt` |
| Inspector не открывается | `npm install -g @modelcontextprotocol/inspector` |
