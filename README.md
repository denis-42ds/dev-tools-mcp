# 🛠️ Dev Tools MCP Server

MCP-сервер с тремя практичными инструментами для ежедневной работы разработчика.  
Полностью локальный — без внешних API и платных ключей.

## Инструменты

| Tool | Что делает |
|------|-----------|
| `scan_tech_debt` | Ищет TODO/FIXME/HACK/BUG/XXX в кодовой базе, приоритизирует, группирует |
| `generate_release_notes` | Генерирует Release Notes из git-лога по Conventional Commits |
| `audit_dockerfile` | Аудирует Dockerfile: безопасность, размер образа, best practices |

---

## Быстрый старт

### Требования

- Docker 20.10+ (рекомендуемый способ)
- **или** Python 3.11+, git (для локального запуска)

### Вариант 1 — Docker (рекомендуется)

```bash
# 1. Клонировать репозиторий
git clone https://github.com/denis-42ds/dev-tools-mcp.git
cd dev-tools-mcp

# 2. Собрать образ
docker build -t dev-tools-mcp .

# 3. Запустить сервер (HTTP, порт 8000)
docker run -p 8000:8000 dev-tools-mcp serve

# 4. Проверить здоровье
curl http://localhost:8000/health

# 5. Smoke-тест
docker run dev-tools-mcp smoke
```

### Вариант 2 — Docker Compose

```bash
# Запуск сервера
docker compose up --build

# Smoke-тест
docker compose --profile smoke run smoke
```

### Вариант 3 — Локально

```bash
pip install -r requirements.txt

# Запустить HTTP-сервер
python src/server.py serve

# Smoke-тест
python smoke_test.py

# MCP Inspector (stdio)
npx @modelcontextprotocol/inspector python src/server.py
```

---

## Сетевой контракт

При запуске `serve` сервер слушает порт **8000**:

| Endpoint | Назначение |
|----------|-----------|
| `GET /health` | Проверка готовности сервиса (быстрый ответ) |
| `POST /mcp` | MCP Streamable HTTP endpoint |

```bash
# Проверить здоровье
curl http://localhost:8000/health
# {"status":"ok","service":"dev-tools-mcp","version":"1.0.0","tools":[...]}

# MCP Inspector через HTTP
npx @modelcontextprotocol/inspector --url http://localhost:8000/mcp
```

---

## Команды Docker

```bash
# Запустить MCP-сервер
docker run -p 8000:8000 dev-tools-mcp serve

# Smoke-тест (завершается 0 = OK, 1 = ошибка)
docker run dev-tools-mcp smoke

# Анализировать свой проект (монтирование)
docker run -p 8000:8000 \
  -v /path/to/your/project:/workspace:ro \
  dev-tools-mcp serve
```

---

## Подключение к Claude Desktop

Добавьте в конфиг Claude Desktop:

**Через HTTP (рекомендуется для Docker):**

Запустите сервер: `docker run -p 8000:8000 dev-tools-mcp serve`

Затем в `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "dev-tools-mcp": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

**Через stdio (локальный Python):**
```json
{
  "mcpServers": {
    "dev-tools-mcp": {
      "command": "python",
      "args": ["/absolute/path/to/dev-tools-mcp/src/server.py"]
    }
  }
}
```

---

## Описание инструментов

### `scan_tech_debt`

Рекурсивно сканирует директорию на маркеры технического долга.

**Параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|---------|
| `path` | string | **обязательный** | Путь к директории или файлу |
| `priority_filter` | string | все | `"high"`, `"medium"` или `"low"` |
| `extensions` | string | все поддерживаемые | Расширения: `".py,.js,.ts"` |
| `max_results` | int | `200` | Максимум результатов |

**Маркеры и приоритеты:**

| Маркер | Приоритет |
|--------|-----------|
| FIXME, BUG, HACK, XXX | 🔴 High |
| TODO, DEPRECATED | 🟡 Medium |
| NOTE, OPTIMIZE | 🔵 Low |

---

### `generate_release_notes`

Генерирует Release Notes из git-лога в формате Markdown.

**Параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|---------|
| `repo_path` | string | **обязательный** | Путь к git-репозиторию |
| `from_ref` | string | предпоследний тег | Начальный ref |
| `to_ref` | string | `HEAD` | Конечный ref |
| `version` | string | значение `to_ref` | Версия для заголовка |
| `include_authors` | bool | `true` | Блок авторов |
| `include_stats` | bool | `true` | Статистика файлов |

---

### `audit_dockerfile`

Анализирует Dockerfile на типичные проблемы. Находит все Dockerfile в директории.

**Параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|---------|
| `path` | string | **обязательный** | Путь к Dockerfile или директории |
| `strict` | bool | `false` | Включить info-уровень предупреждений |

**Проверяемые правила:**

| Код | Уровень | Описание |
|-----|---------|---------|
| C001 | 🔴 Critical | Запуск от root |
| C002 | 🔴 Critical | Нефиксированный тег (`:latest` или без тега) |
| C003 | 🔴 Critical | Секреты в ENV/ARG |
| C004 | 🟡 Warning | ADD вместо COPY |
| W001 | 🟡 Warning | Нет HEALTHCHECK |
| W002 | 🟡 Warning | apt-get без `--no-install-recommends` |
| W003 | 🟡 Warning | apt-get update и install в разных слоях |
| W004 | 🟡 Warning | Кэш apt не очищается |
| W005 | 🟡 Warning | pip без `--no-cache-dir` |
| W006 | 🟡 Warning | Нет .dockerignore |
| W007 | 🟡 Warning | COPY . . без .dockerignore |
| W008 | 🟡 Warning | Много отдельных RUN-инструкций |
| I001 | 🔵 Info | Нет LABEL-метаданных |
| I002 | 🔵 Info | WORKDIR не задан |
| I003 | 🔵 Info | Рекомендуется multi-stage build |

---

## Структура проекта

```
dev-tools-mcp/
├── src/
│   └── server.py               # MCP-сервер: все три инструмента + HTTP-транспорт
├── demo_project/               # Тестовые данные для demo-сценария
│   ├── src/
│   │   ├── users.py            # Намеренный техдолг (~15 маркеров)
│   │   ├── utils.py            # Намеренный техдолг (~10 маркеров)
│   │   └── cache.py
│   ├── infra/
│   │   ├── Dockerfile.bad      # Dockerfile с проблемами (для аудита)
│   │   └── Dockerfile.good     # Эталонный Dockerfile
│   └── .git/                   # git-репозиторий с тегами v0.1.0 / v1.0.0
├── Dockerfile                  # Образ MCP-сервера
├── docker-compose.yml
├── entrypoint.sh               # serve | smoke
├── smoke_test.py               # Автоматическая проверка инструментов
├── requirements.txt
├── .env.example
├── README.md
├── DEMO.md
└── AGENTS.md
```

---

## Ограничения по ресурсам

Сервер работает в рамках:
- **CPU:** 2.0 cores
- **RAM:** 2048 MB

Docker Compose автоматически выставляет эти лимиты (см. `docker-compose.yml`).

---

## Переменные окружения

Скопируйте `.env.example` в `.env` при необходимости. Базовый сценарий не требует настройки.

| Переменная | По умолчанию | Описание |
|-----------|-------------|---------|
| `PORT` | `8000` | Порт HTTP-сервера |
| `SCAN_PATH` | `./demo_project` | Путь к проекту для монтирования |

---

## Диагностика

```bash
# Сервер не отвечает — проверьте статус
docker ps | grep dev-tools-mcp
curl -v http://localhost:8000/health

# Smoke упал — посмотрите детали
docker run dev-tools-mcp smoke 2>&1

# Логи работающего сервера
docker logs dev-tools-mcp
```

---

## Требования

- Python 3.11+ (или Docker)
- `mcp[cli]>=1.3.0`, `uvicorn>=0.29.0`, `starlette>=0.37.0`
- `git` (для `generate_release_notes`)
- Docker 20.10+ (для контейнерного запуска)
