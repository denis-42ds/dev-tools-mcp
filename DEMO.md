# 🎬 DEMO — Dev Tools MCP Server

---

## Сценарий A — «Перед релизом: найти долг и написать changelog»

### Цель

Разработчик готовится к релизу v1.0.0. Нужно:
1. Понять, какой критичный техдолг накопился в кодовой базе — чтобы решить, что закрыть до релиза.
2. Сгенерировать Release Notes из git-лога — чтобы не писать changelog вручную.

Оба действия выполняются за 2 минуты через MCP-инструменты без ручного grep и git log.

---

### Предусловия

**1. Собрать и запустить контейнер:**

```bash
docker build -t dev-tools-mcp .
docker run -p 8000:8000 dev-tools-mcp serve
```

**2. Проверить готовность:**
```bash
curl http://localhost:8000/health
# {"status":"ok","service":"dev-tools-mcp","version":"1.0.0","tools":[...]}
```

**3. Открыть MCP Inspector** (в отдельном терминале):

```bash
# Требуется Node.js ≥ 22. Проверить: node --version
# Если версия старше — обновить через nvm или с nodejs.org

npx @modelcontextprotocol/inspector
```

В открывшемся браузере (`http://localhost:6274`):
- Поле **Transport**: выбрать `Streamable HTTP`
- Поле **URL**: ввести `http://localhost:8000/mcp`
- Нажать **Connect**
- Перейти на вкладку **Tools** — должны появиться 3 инструмента

> **Альтернатива без Inspector** — вызывать инструменты через curl (см. раздел ниже)

---

### Шаг 1 — Найти критичный техдолг

**Tool:** `scan_tech_debt`

**Аргументы:**
```json
{
  "path": "/app/demo_project",
  "priority_filter": "high"
}
```

**Ожидаемый результат:**

```
## 🔴 HIGH PRIORITY

💀 XXX — `src/users.py:13`
> SQL-инъекция!

🐛 BUG — `src/users.py:21`
> не используем constant-time comparison

⚠️ HACK — `src/users.py:24`
> пока храним пароль в открытом виде, потом исправим
...
```

**Признак успеха:** найдено ≥ 10 высокоприоритетных маркеров с файлом и номером строки.

---

### Шаг 2 — Сгенерировать Release Notes

**Tool:** `generate_release_notes`

**Аргументы:**
```json
{
  "repo_path": "/app/demo_project",
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
- **api**: change authentication endpoint from /auth to /api/v2/auth

## ✨ Новые возможности
- **users**: add user authentication module
- **core**: implement version tracking
- **cache**: add Redis cache manager

## ⚡ Производительность
- **db**: optimize bulk user loading query

## 👥 Авторы
- Demo User (10 коммитов)
```

**Признак успеха:** структурированный Markdown, выделен BREAKING CHANGE, указаны авторы.

---

### Итог сценария A

За два вызова получены:
- Список критичного техдолга → можно сразу создавать задачи в трекере
- Готовые Release Notes → вставить в GitHub Releases без редактирования

---

## Сценарий B — «Аудит Dockerfile перед деплоем»

### Шаг 1 — Проблемный Dockerfile

**Tool:** `audit_dockerfile`

```json
{
  "path": "/app/demo_project/infra/Dockerfile.bad"
}
```

**Ожидаемый результат:**
```
🔴 Critical: 3   🟡 Warning: 7

[C001] Контейнер работает от root
[C002] Используется нефиксированный тег: `python:latest`
[C003] Возможная утечка секрета в ENV

Оценка: `████░░░░░░` 35/100
```

### Шаг 2 — Эталонный Dockerfile

```json
{
  "path": "/app/demo_project/infra/Dockerfile.good",
  "strict": true
}
```

**Признак успеха:** 0 critical, оценка ≥ 90/100.

---

## Альтернатива: вызов через curl (без Inspector)

Если Inspector не запускается — инструменты можно вызвать напрямую через HTTP:

```bash
# 1. Инициализировать MCP-сессию
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "curl-test", "version": "1.0"}
    }
  }'

# 2. Вызвать scan_tech_debt
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "scan_tech_debt",
      "arguments": {"path": "/app/demo_project", "priority_filter": "high"}
    }
  }'
```

---

## Smoke-тест (автоматическая проверка)

```bash
docker run dev-tools-mcp smoke
```

Ожидаемый вывод:
```
✅  ALL TESTS PASSED  (12/12)
```

Код завершения `0` = все инструменты работают корректно.

---

## Использование со своим проектом

```bash
docker run -p 8000:8000 \
  -v /path/to/your/project:/workspace:ro \
  dev-tools-mcp serve
```

В Inspector/curl передавайте `/workspace` как путь.

---

## Диагностика

| Симптом | Что сделать |
|---------|-------------|
| `connection refused :8000` | Проверить `docker ps`, убедиться что `serve` запущен |
| `smoke` возвращает ненулевой код | `docker run dev-tools-mcp smoke` — читать вывод построчно |
| Inspector: `spawn --url ENOENT` | Запустить `npx @modelcontextprotocol/inspector` **без аргументов**, URL вводить в UI |
| Inspector: `Not Found` на `/mcp` | Убедиться что выбран транспорт **Streamable HTTP** (не SSE, не stdio) |
| Node.js слишком старый | Inspector требует Node ≥ 22: `node --version`, обновить через [nvm](https://github.com/nvm-sh/nvm) |
| `not a git repository` | Пересобрать образ: `docker build --no-cache -t dev-tools-mcp .` |
