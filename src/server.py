"""
Dev Tools MCP Server
Инструменты для ежедневной работы разработчика:
  - scan_tech_debt          : поиск TODO/FIXME/HACK и приоритизация техдолга
  - generate_release_notes  : release notes из git-лога
  - audit_dockerfile        : аудит Dockerfile на best practices

Транспорты:
  stdio          — для Claude Desktop / MCP Inspector (python src/server.py)
  streamable-http — HTTP на порту 8000, /mcp + /health  (python src/server.py serve)
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="dev-tools-mcp",
    version="1.0.0",
    description="Developer productivity tools: tech debt scanner, release notes generator, Dockerfile auditor",
)

# ---------------------------------------------------------------------------
# TOOL 1 — Tech Debt Scanner
# ---------------------------------------------------------------------------

MARKERS = {
    "FIXME":      {"priority": "high",   "emoji": "🔴"},
    "BUG":        {"priority": "high",   "emoji": "🐛"},
    "HACK":       {"priority": "high",   "emoji": "⚠️"},
    "XXX":        {"priority": "high",   "emoji": "💀"},
    "TODO":       {"priority": "medium", "emoji": "🟡"},
    "DEPRECATED": {"priority": "medium", "emoji": "⚠️"},
    "NOTE":       {"priority": "low",    "emoji": "🔵"},
    "OPTIMIZE":   {"priority": "low",    "emoji": "⚡"},
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".mypy_cache", ".pytest_cache", "coverage",
}

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".swift", ".kt",
    ".scala", ".sh", ".bash", ".yml", ".yaml", ".tf", ".sql",
}


@mcp.tool()
def scan_tech_debt(
    path: str,
    priority_filter: Optional[str] = None,
    extensions: Optional[str] = None,
    max_results: int = 200,
) -> str:
    """
    Сканирует директорию на маркеры техдолга: TODO, FIXME, HACK, BUG, XXX, DEPRECATED и др.
    Возвращает приоритизированный список с файлом, строкой и контекстом.

    Args:
        path: Путь к директории или файлу для сканирования
        priority_filter: Фильтр по приоритету: "high", "medium", "low" (по умолчанию — все)
        extensions: Через запятую расширения файлов для сканирования, например ".py,.js"
                    (по умолчанию — все поддерживаемые)
        max_results: Максимальное количество результатов (по умолчанию 200)
    """
    root = Path(path).resolve()
    if not root.exists():
        return f"❌ Путь не найден: {path}"

    allowed_ext = set(
        e.strip() if e.strip().startswith(".") else f".{e.strip()}"
        for e in extensions.split(",")
    ) if extensions else SUPPORTED_EXTENSIONS

    pattern = re.compile(
        r"(?P<marker>" + "|".join(MARKERS.keys()) + r")\s*[:\-]?\s*(?P<text>.*)",
        re.IGNORECASE,
    )

    results = []

    files_to_scan = []
    if root.is_file():
        files_to_scan = [root]
    else:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                fpath = Path(dirpath) / fname
                if fpath.suffix in allowed_ext:
                    files_to_scan.append(fpath)

    stats = {"high": 0, "medium": 0, "low": 0, "files_scanned": len(files_to_scan)}

    for fpath in files_to_scan:
        try:
            lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        for lineno, line in enumerate(lines, start=1):
            m = pattern.search(line)
            if not m:
                continue

            marker_raw = m.group("marker").upper()
            # normalise: DEPRECATED -> DEPRECATED, etc.
            marker = next((k for k in MARKERS if k == marker_raw), marker_raw)
            info = MARKERS.get(marker, {"priority": "low", "emoji": "❓"})
            priority = info["priority"]

            if priority_filter and priority != priority_filter:
                continue

            stats[priority] += 1
            results.append(
                {
                    "file": str(fpath.relative_to(root)) if not root.is_file() else str(fpath),
                    "line": lineno,
                    "marker": marker,
                    "priority": priority,
                    "emoji": info["emoji"],
                    "text": m.group("text").strip()[:200],
                    "context": line.strip()[:300],
                }
            )

            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break

    # Sort: high → medium → low, then by file
    priority_order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda r: (priority_order[r["priority"]], r["file"], r["line"]))

    if not results:
        return (
            f"✅ Техдолг не обнаружен!\n"
            f"Просканировано файлов: {stats['files_scanned']}"
        )

    lines_out = [
        f"# 🔍 Отчёт по техдолгу",
        f"**Путь:** `{path}`  |  "
        f"**Файлов:** {stats['files_scanned']}  |  "
        f"**Найдено:** {len(results)}"
        + (" *(обрезано)*" if len(results) >= max_results else ""),
        "",
        f"🔴 High: {stats['high']}   "
        f"🟡 Medium: {stats['medium']}   "
        f"🔵 Low: {stats['low']}",
        "",
        "---",
        "",
    ]

    current_priority = None
    for r in results:
        if r["priority"] != current_priority:
            current_priority = r["priority"]
            label = {"high": "🔴 HIGH PRIORITY", "medium": "🟡 MEDIUM PRIORITY", "low": "🔵 LOW PRIORITY"}[current_priority]
            lines_out.append(f"## {label}\n")

        lines_out.append(
            f"{r['emoji']} **{r['marker']}** — `{r['file']}:{r['line']}`\n"
            f"> {r['text'] or r['context']}\n"
        )

    lines_out += [
        "---",
        "",
        "### 📊 Рекомендации",
        f"- Приоритет 1: разобрать **{stats['high']} критичных** маркеров (FIXME/BUG/HACK/XXX)",
        f"- Приоритет 2: запланировать **{stats['medium']} задач** среднего приоритета в следующий спринт",
        f"- Приоритет 3: при рефакторинге обработать **{stats['low']} low-priority** заметок",
    ]

    return "\n".join(lines_out)


# ---------------------------------------------------------------------------
# TOOL 2 — Release Notes Generator
# ---------------------------------------------------------------------------

COMMIT_CATEGORIES = {
    "feat":     ("✨ Новые возможности",      0),
    "fix":      ("🐛 Исправления багов",      1),
    "perf":     ("⚡ Производительность",     2),
    "refactor": ("♻️  Рефакторинг",           3),
    "docs":     ("📝 Документация",           4),
    "test":     ("🧪 Тесты",                  5),
    "build":    ("🏗️  Сборка и зависимости",  6),
    "ci":       ("👷 CI/CD",                  7),
    "chore":    ("🔧 Прочее",                 8),
    "style":    ("💄 Стиль кода",             9),
    "revert":   ("⏪ Откаты",                10),
    "other":    ("📦 Другие изменения",      11),
}


def _run_git(args: list[str], cwd: str) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", "git не найден в PATH"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


@mcp.tool()
def generate_release_notes(
    repo_path: str,
    from_ref: str = "",
    to_ref: str = "HEAD",
    version: str = "",
    include_authors: bool = True,
    include_stats: bool = True,
) -> str:
    """
    Генерирует release notes из git-лога в формате Markdown.
    Автоматически категоризирует коммиты по Conventional Commits.

    Args:
        repo_path: Путь к git-репозиторию
        from_ref:  Начальный ref (тег, ветка, хеш). Если пусто — берёт предпоследний тег
        to_ref:    Конечный ref (по умолчанию HEAD)
        version:   Версия для заголовка (если пусто — используется to_ref)
        include_authors: Добавить блок с авторами (default: True)
        include_stats:   Добавить статистику файлов (default: True)
    """
    repo = Path(repo_path).resolve()
    if not repo.exists():
        return f"❌ Репозиторий не найден: {repo_path}"

    code, _, err = _run_git(["rev-parse", "--git-dir"], str(repo))
    if code != 0:
        return f"❌ Не git-репозиторий: {err}"

    # Resolve from_ref
    if not from_ref:
        code, tags_out, _ = _run_git(
            ["tag", "--sort=-creatordate"], str(repo)
        )
        tags = [t.strip() for t in tags_out.splitlines() if t.strip()]
        if len(tags) >= 2:
            from_ref = tags[1]
        elif len(tags) == 1:
            from_ref = tags[0]
        else:
            # Fall back to first commit
            code2, first, _ = _run_git(
                ["rev-list", "--max-parents=0", "HEAD"], str(repo)
            )
            from_ref = first.strip() if code2 == 0 else ""

    range_spec = f"{from_ref}..{to_ref}" if from_ref else to_ref

    # Get commits: hash|author|date|subject|body
    sep = "|||"
    fmt = f"%H{sep}%an{sep}%ae{sep}%ad{sep}%s{sep}%b{sep}---END---"
    code, log_out, err = _run_git(
        ["log", range_spec, f"--pretty=format:{fmt}", "--date=short"],
        str(repo),
    )
    if code != 0:
        return f"❌ Ошибка git log: {err}"

    if not log_out.strip():
        return f"ℹ️  Нет коммитов в диапазоне `{range_spec}`"

    commits = []
    for entry in log_out.split("---END---"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(sep)
        if len(parts) < 6:
            continue
        sha, author, email, date, subject, body = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        commits.append(
            {"sha": sha[:8], "author": author, "email": email, "date": date,
             "subject": subject.strip(), "body": body.strip()}
        )

    if not commits:
        return "ℹ️  Коммиты не найдены"

    # Categorise
    categorised: dict[str, list[dict]] = {k: [] for k in COMMIT_CATEGORIES}
    breaking = []

    cc_re = re.compile(r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?\s*:\s*(?P<desc>.+)$")

    for c in commits:
        m = cc_re.match(c["subject"])
        if m:
            ctype = m.group("type").lower()
            scope = m.group("scope") or ""
            desc = m.group("desc")
            is_breaking = bool(m.group("breaking")) or "BREAKING CHANGE" in c["body"]
            entry = {**c, "scope": scope, "desc": desc, "is_breaking": is_breaking}
            if is_breaking:
                breaking.append(entry)
            cat = ctype if ctype in categorised else "other"
            categorised[cat].append(entry)
        else:
            categorised["other"].append({**c, "scope": "", "desc": c["subject"], "is_breaking": False})

    # Build output
    ver_label = version or to_ref
    date_now = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# 🚀 Release Notes — {ver_label}",
        f"**Дата:** {date_now}  |  "
        f"**Диапазон:** `{range_spec}`  |  "
        f"**Коммитов:** {len(commits)}",
        "",
    ]

    if breaking:
        lines += ["## 💥 BREAKING CHANGES\n"]
        for c in breaking:
            scope = f"**{c['scope']}**: " if c.get("scope") else ""
            lines.append(f"- {scope}{c['desc']} ({c['sha']})")
        lines.append("")

    for ctype, (label, _) in sorted(COMMIT_CATEGORIES.items(), key=lambda x: x[1][1]):
        items = categorised.get(ctype, [])
        if not items:
            continue
        lines += [f"## {label}\n"]
        for c in items:
            scope = f"**{c.get('scope')}**: " if c.get("scope") else ""
            lines.append(f"- {scope}{c.get('desc', c['subject'])} ({c['sha']})")
        lines.append("")

    if include_authors:
        authors: dict[str, int] = {}
        for c in commits:
            authors[c["author"]] = authors.get(c["author"], 0) + 1
        lines += ["## 👥 Авторы\n"]
        for author, count in sorted(authors.items(), key=lambda x: -x[1]):
            lines.append(f"- {author} ({count} коммит{'ов' if count > 4 else 'а' if count > 1 else ''})")
        lines.append("")

    if include_stats:
        code, stat_out, _ = _run_git(
            ["diff", "--shortstat", range_spec] if from_ref else
            ["diff", "--shortstat", f"{to_ref}~{min(len(commits), 50)}..{to_ref}"],
            str(repo),
        )
        if code == 0 and stat_out:
            lines += ["## 📊 Статистика изменений\n", f"```\n{stat_out}\n```\n"]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# TOOL 3 — Dockerfile Auditor
# ---------------------------------------------------------------------------

@mcp.tool()
def audit_dockerfile(
    path: str,
    strict: bool = False,
) -> str:
    """
    Анализирует Dockerfile (и опционально docker-compose.yml) на типичные проблемы:
    безопасность, размер образа, кэширование слоёв, best practices.

    Args:
        path: Путь к Dockerfile или директории (поиск Dockerfile/docker-compose.yml)
        strict: Показать предупреждения низкого приоритета (по умолчанию False)
    """
    root = Path(path).resolve()
    dockerfiles = []

    if root.is_file():
        dockerfiles = [root]
    else:
        for pattern in ["Dockerfile", "Dockerfile.*", "*.dockerfile"]:
            dockerfiles.extend(root.rglob(pattern))
        dockerfiles = [f for f in dockerfiles
                       if not any(p in f.parts for p in SKIP_DIRS)]

    if not dockerfiles:
        return f"❌ Dockerfile не найден в `{path}`"

    all_output = []

    for df_path in dockerfiles:
        try:
            content = df_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            all_output.append(f"❌ Не удалось прочитать {df_path}: {e}")
            continue

        issues = _audit_single_dockerfile(content, df_path, strict)
        rel = str(df_path.relative_to(root)) if not root.is_file() else df_path.name

        counts = {"critical": 0, "warning": 0, "info": 0}
        for iss in issues:
            counts[iss["level"]] += 1

        block = [
            f"## 🐳 {rel}",
            f"🔴 Critical: {counts['critical']}   "
            f"🟡 Warning: {counts['warning']}   "
            f"🔵 Info: {counts['info']}",
            "",
        ]

        if not issues:
            block.append("✅ Проблем не обнаружено!\n")
        else:
            for level in ("critical", "warning", "info"):
                lvl_issues = [i for i in issues if i["level"] == level]
                if not lvl_issues:
                    continue
                emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}[level]
                block.append(f"### {emoji} {level.upper()}\n")
                for iss in lvl_issues:
                    loc = f" *(строка {iss['line']})*" if iss.get("line") else ""
                    block.append(f"**[{iss['code']}]** {iss['message']}{loc}")
                    if iss.get("detail"):
                        block.append(f"  > 💡 {iss['detail']}")
                    block.append("")

        # Score
        score = max(0, 100 - counts["critical"] * 20 - counts["warning"] * 5 - counts["info"] * 1)
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        block.append(f"**Оценка:** `{bar}` {score}/100\n")
        all_output.extend(block)

    header = [
        "# 🔍 Аудит Dockerfile",
        f"**Путь:** `{path}`  |  **Найдено Dockerfile:** {len(dockerfiles)}",
        "",
        "---",
        "",
    ]
    return "\n".join(header + all_output)


def _audit_single_dockerfile(content: str, path: Path, strict: bool) -> list[dict]:
    lines = content.splitlines()
    issues = []

    def add(level, code, message, detail="", line=None):
        if level == "info" and not strict:
            return
        issues.append({"level": level, "code": code, "message": message, "detail": detail, "line": line})

    # Parse instructions
    instructions = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            parts = stripped.split(None, 1)
            instructions.append((i, parts[0].upper(), parts[1] if len(parts) > 1 else ""))

    instr_names = [i[1] for i in instructions]

    # --- CRITICAL ---

    # C001: root user
    user_set = False
    for lineno, instr, args in instructions:
        if instr == "USER":
            u = args.strip().split(":")[0]
            if u not in ("root", "0"):
                user_set = True
    if not user_set:
        add("critical", "C001",
            "Контейнер работает от root",
            "Добавьте USER <non-root-user> перед CMD/ENTRYPOINT для снижения привилегий")

    # C002: latest tag
    for lineno, instr, args in instructions:
        if instr in ("FROM",):
            img = args.split()[0]
            if img.endswith(":latest") or (":" not in img and "@" not in img and img != "scratch"):
                add("critical", "C002",
                    f"Используется нефиксированный тег образа: `{img}`",
                    "Укажите точный тег или digest: python:3.11.9-slim",
                    line=lineno)

    # C003: secrets in ENV/ARG
    secret_re = re.compile(r"(?i)(password|secret|token|api_key|private_key|passwd)\s*=\s*\S+")
    for lineno, instr, args in instructions:
        if instr in ("ENV", "ARG") and secret_re.search(args):
            add("critical", "C003",
                f"Возможная утечка секрета в {instr}",
                "Используйте Docker BuildKit secrets или передавайте переменные в runtime",
                line=lineno)

    # C004: ADD вместо COPY
    for lineno, instr, args in instructions:
        if instr == "ADD" and not re.search(r"https?://", args) and not args.endswith(".tar.gz") \
                and not args.endswith(".tar.bz2"):
            add("warning", "C004",
                f"ADD используется без необходимости (строка {lineno})",
                "Используйте COPY для локальных файлов; ADD нужен только для URL и tar-архивов",
                line=lineno)

    # --- WARNINGS ---

    # W001: нет HEALTHCHECK
    if "HEALTHCHECK" not in instr_names:
        add("warning", "W001",
            "Отсутствует HEALTHCHECK",
            "HEALTHCHECK позволяет оркестратору определять состояние контейнера")

    # W002: apt-get без --no-install-recommends
    for lineno, instr, args in instructions:
        if instr == "RUN" and "apt-get install" in args and "--no-install-recommends" not in args:
            add("warning", "W002",
                "apt-get install без --no-install-recommends",
                "Добавьте флаг для уменьшения размера образа",
                line=lineno)

    # W003: apt-get update и install в разных RUN
    update_lines = [lineno for lineno, instr, args in instructions
                    if instr == "RUN" and "apt-get update" in args and "apt-get install" not in args]
    if update_lines:
        add("warning", "W003",
            "apt-get update и apt-get install в разных слоях",
            "Объедините в один RUN: `RUN apt-get update && apt-get install -y ...`",
            line=update_lines[0])

    # W004: кэш apt не очищается
    for lineno, instr, args in instructions:
        if instr == "RUN" and "apt-get install" in args and "rm -rf /var/lib/apt/lists" not in args:
            add("warning", "W004",
                "Кэш apt-get не очищается",
                "Добавьте `&& rm -rf /var/lib/apt/lists/*` в конец RUN с apt-get",
                line=lineno)
            break

    # W005: pip без --no-cache-dir
    for lineno, instr, args in instructions:
        if instr == "RUN" and "pip install" in args and "--no-cache-dir" not in args:
            add("warning", "W005",
                "pip install без --no-cache-dir",
                "Добавьте --no-cache-dir для уменьшения размера образа",
                line=lineno)

    # W006: нет .dockerignore (эвристика)
    dockerignore = path.parent / ".dockerignore"
    if not dockerignore.exists():
        add("warning", "W006",
            "Файл .dockerignore не найден рядом с Dockerfile",
            "Создайте .dockerignore чтобы исключить node_modules, .git, __pycache__ и т.д.")

    # W007: COPY . . без .dockerignore
    has_copy_all = any(
        re.match(r"\.?\s+\.?", args.strip())
        for _, instr, args in instructions if instr == "COPY"
    )
    if has_copy_all and not dockerignore.exists():
        add("warning", "W007",
            "COPY . . без .dockerignore может включить чувствительные файлы",
            "Создайте .dockerignore и исключите .git, .env, secrets и т.п.")

    # W008: много RUN-команд (не multi-stage)
    run_count = instr_names.count("RUN")
    from_count = instr_names.count("FROM")
    if run_count > 7 and from_count < 2:
        add("warning", "W008",
            f"Много отдельных RUN-инструкций ({run_count})",
            "Объедините связанные команды через && для уменьшения числа слоёв")

    # --- INFO ---

    # I001: нет LABEL
    if "LABEL" not in instr_names:
        add("info", "I001",
            "Нет LABEL-метаданных",
            "Добавьте LABEL maintainer, version, description для документирования образа")

    # I002: нет явного WORKDIR
    if "WORKDIR" not in instr_names:
        add("info", "I002",
            "WORKDIR не задан",
            "Установите явный WORKDIR вместо работы в /")

    # I003: рекомендация multi-stage
    if from_count == 1:
        for _, instr, args in instructions:
            if instr == "RUN" and any(tool in args for tool in
                                      ("go build", "cargo build", "mvn", "gradle", "npm run build", "gcc", "g++")):
                add("info", "I003",
                    "Обнаружена сборка — рекомендуется multi-stage build",
                    "Используйте FROM builder AS build + FROM base для уменьшения итогового образа")
                break

    return issues


# ---------------------------------------------------------------------------
# HTTP server — /health + /mcp (Streamable HTTP)
# ---------------------------------------------------------------------------

def _create_http_app():
    """Создаёт составное ASGI-приложение: /health + /mcp."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route, Mount

    async def health(request):
        return JSONResponse(
            {
                "status": "ok",
                "service": "dev-tools-mcp",
                "version": "1.0.0",
                "tools": ["scan_tech_debt", "generate_release_notes", "audit_dockerfile"],
            }
        )

    mcp_asgi = mcp.streamable_http_app()

    return Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Mount("/mcp", app=mcp_asgi),
        ]
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if command == "serve":
        import uvicorn

        port = int(os.environ.get("PORT", 8000))
        print(f"[dev-tools-mcp] Starting HTTP server on 0.0.0.0:{port}", flush=True)
        print(f"[dev-tools-mcp]   /health — health check", flush=True)
        print(f"[dev-tools-mcp]   /mcp    — MCP Streamable HTTP endpoint", flush=True)
        app = _create_http_app()
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    else:
        # Default: stdio transport for Claude Desktop / MCP Inspector
        mcp.run(transport="stdio")
