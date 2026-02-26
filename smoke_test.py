#!/usr/bin/env python3
"""
smoke_test.py — быстрая проверка работоспособности инструментов MCP-сервера.

Запуск:
  python smoke_test.py          # локально
  docker run IMAGE smoke        # в контейнере

Проверяет три инструмента напрямую (без HTTP), используя demo_project/ как тестовые данные.
Завершается с кодом 0 при успехе, 1 при любой ошибке.
"""

import os
import sys
import re
import traceback

# ── Путь к src ──────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))

# ── Если пакет mcp не установлен — используем заглушку ─────────────────────
try:
    import mcp  # noqa: F401
except ModuleNotFoundError:
    import types
    _mcp = types.ModuleType("mcp")
    _srv = types.ModuleType("mcp.server")
    _fst = types.ModuleType("mcp.server.fastmcp")

    class _FakeMCP:
        def __init__(self, **kw): pass
        def tool(self):
            def dec(fn): return fn
            return dec
        def run(self, **kw): pass
        def streamable_http_app(self): return None

    _fst.FastMCP = _FakeMCP
    _mcp.server = _srv
    _srv.fastmcp = _fst
    sys.modules["mcp"] = _mcp
    sys.modules["mcp.server"] = _srv
    sys.modules["mcp.server.fastmcp"] = _fst

from server import scan_tech_debt, generate_release_notes, audit_dockerfile

# ── Пути ────────────────────────────────────────────────────────────────────
DEMO  = os.path.join(ROOT, "demo_project")
INFRA = os.path.join(DEMO, "infra")
RESULTS = []


def check(name, fn, *args, expect_error=False, **kwargs):
    try:
        out = fn(*args, **kwargs)
        if expect_error:
            ok = isinstance(out, str) and any(x in out for x in ("❌", "не найден", "Не git", "ошибка"))
        else:
            ok = isinstance(out, str) and len(out) > 10 and not out.startswith("❌")
        print(f"  {'✅' if ok else '❌'} {name}")
        if not ok:
            print(f"       → {(out or '')[:300].replace(chr(10), ' ')}")
        RESULTS.append(ok)
        return out
    except Exception as exc:
        print(f"  ❌ {name}")
        print(f"       → EXCEPTION: {exc}")
        traceback.print_exc(file=sys.stdout)
        RESULTS.append(False)
        return None


# ═══════════════════════════════════════════════════════════════════════════
print()
print("╔══════════════════════════════════════════════╗")
print("║   dev-tools-mcp  —  Smoke Test               ║")
print("╚══════════════════════════════════════════════╝")
print()

# ── Tool 1: scan_tech_debt ──────────────────────────────────────────────────
print("🔍  Tool 1: scan_tech_debt")

r = check("Full scan (demo_project)", scan_tech_debt, DEMO)
if r:
    total_m = re.search(r"\*\*Найдено:\*\* (\d+)", r)
    high_m  = re.search(r"High: (\d+)", r)
    total   = int(total_m.group(1)) if total_m else 0
    high    = int(high_m.group(1))  if high_m  else 0
    ok_cnt  = total >= 15
    print(f"       → Всего: {total}, High: {high} {'✅' if ok_cnt else '⚠️ (ожидалось ≥15)'}")
    if not ok_cnt:
        RESULTS[-1] = False

check("Filter priority=high",  scan_tech_debt, DEMO, priority_filter="high")
check("Filter extensions=.py", scan_tech_debt, DEMO, extensions=".py")
check("Nonexistent path",      scan_tech_debt, "/nonexistent/path_xyz", expect_error=True)
print()

# ── Tool 2: generate_release_notes ─────────────────────────────────────────
print("📝  Tool 2: generate_release_notes")

r = check("v0.1.0..v1.0.0", generate_release_notes,
          DEMO, from_ref="v0.1.0", to_ref="v1.0.0", version="1.0.0")
if r:
    has_breaking = "BREAKING" in r
    has_feat     = "Новые возможности" in r
    cnt_m        = re.search(r"Коммитов:\*\* (\d+)", r)
    cnt          = int(cnt_m.group(1)) if cnt_m else 0
    print(f"       → Коммитов: {cnt}, BREAKING: {'да' if has_breaking else 'нет'}, Новые фичи: {'да' if has_feat else 'нет'}")

check("Auto range",            generate_release_notes, DEMO)
check("No authors/stats",      generate_release_notes, DEMO,
      from_ref="v0.1.0", include_authors=False, include_stats=False)
check("Non-git dir",           generate_release_notes, "/tmp", expect_error=True)
print()

# ── Tool 3: audit_dockerfile ────────────────────────────────────────────────
print("🐳  Tool 3: audit_dockerfile")

r = check("Dockerfile.bad", audit_dockerfile, os.path.join(INFRA, "Dockerfile.bad"))
if r:
    crits = len(re.findall(r"\[C0\d+\]", r))
    score_m = re.search(r"(\d+)/100", r)
    score   = int(score_m.group(1)) if score_m else 999
    ok = crits >= 2 and score < 60
    print(f"       → Critical: {crits}, Score: {score}/100 {'✅' if ok else '⚠️ (ожидалось ≥2 critical, score<60)'}")
    if not ok:
        RESULTS[-1] = False

r = check("Dockerfile.good (strict)", audit_dockerfile,
          os.path.join(INFRA, "Dockerfile.good"), strict=True)
if r:
    crits   = len(re.findall(r"\[C0\d+\]", r))
    score_m = re.search(r"(\d+)/100", r)
    score   = int(score_m.group(1)) if score_m else 0
    ok      = crits == 0 and score >= 70
    print(f"       → Critical: {crits}, Score: {score}/100 {'✅' if ok else '⚠️ (ожидалось 0 critical, score≥70)'}")
    if not ok:
        RESULTS[-1] = False

check("Directory scan",     audit_dockerfile, INFRA, strict=True)
check("No Dockerfile path", audit_dockerfile, "/tmp", expect_error=True)

# ═══════════════════════════════════════════════════════════════════════════
print()
passed  = sum(RESULTS)
total   = len(RESULTS)
all_ok  = passed == total
label   = "ALL TESTS PASSED" if all_ok else f"{total - passed} TEST(S) FAILED"
icon    = "✅" if all_ok else "❌"

print("═" * 48)
print(f"{icon}  {label}  ({passed}/{total})")
print("═" * 48)
print()
sys.exit(0 if all_ok else 1)
