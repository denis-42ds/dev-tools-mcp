#!/usr/bin/env sh
# init_demo_git.sh — воссоздаёт git-историю demo_project/ во время docker build.
# GitHub не сохраняет вложенные .git, поэтому история создаётся здесь.
set -e

DEMO="/app/demo_project"
cd "$DEMO"

git init
git config user.email "demo@example.com"
git config user.name "Demo User"
git config init.defaultBranch master

# Все файлы уже скопированы через COPY — временно убираем лишние,
# чтобы воссоздать историю коммит за коммитом.
mkdir -p /tmp/demo_stash

# Файлы, которые появятся в более поздних коммитах
mv src/version.py   /tmp/demo_stash/ 2>/dev/null || true
mv src/cache.py     /tmp/demo_stash/ 2>/dev/null || true
mv docs             /tmp/demo_stash/ 2>/dev/null || true
mv tests            /tmp/demo_stash/ 2>/dev/null || true
mv .github-ci.yml   /tmp/demo_stash/ 2>/dev/null || true

# ── Коммит 1: initial setup ──────────────────────────────────────────────────
git add .
git commit -m "chore: initial project setup"
git tag v0.1.0

# ── Коммит 2: feat users ─────────────────────────────────────────────────────
echo "" >> README.md
git add README.md
git commit -m "feat(users): add user authentication module"

# ── Коммит 3: feat core ──────────────────────────────────────────────────────
cp /tmp/demo_stash/version.py src/version.py
git add src/version.py
git commit -m "feat(core): implement version tracking"

# ── Коммит 4: test ───────────────────────────────────────────────────────────
cp -r /tmp/demo_stash/tests .
git add tests/
git commit -m "test: add test infrastructure"

# ── Коммит 5: docs ───────────────────────────────────────────────────────────
cp -r /tmp/demo_stash/docs .
git add docs/
git commit -m "docs: add API documentation"

# ── Коммит 6: feat cache ─────────────────────────────────────────────────────
cp /tmp/demo_stash/cache.py src/cache.py
git add src/cache.py
git commit -m "feat(cache): add Redis cache manager"

# ── Коммит 7: perf ───────────────────────────────────────────────────────────
git commit --allow-empty -m "perf(db): optimize bulk user loading query"

# ── Коммит 8: ci ─────────────────────────────────────────────────────────────
cp /tmp/demo_stash/.github-ci.yml .
git add .github-ci.yml
git commit -m "ci: add GitHub Actions pipeline"

# ── Коммит 9: breaking change ────────────────────────────────────────────────
git commit --allow-empty -m "feat(api)!: change authentication endpoint from /auth to /api/v2/auth

BREAKING CHANGE: clients must update endpoint URL"

# ── Коммит 10: refactor ──────────────────────────────────────────────────────
git commit --allow-empty -m "refactor(users): extract password hashing to separate module"

# ── Коммит 11: chore + tag v1.0.0 ────────────────────────────────────────────
git commit --allow-empty -m "chore(deps): bump flask from 2.3.0 to 3.0.2"
git tag v1.0.0

echo "[init_demo_git] Done: $(git log --oneline | wc -l | tr -d ' ') commits, tags: $(git tag | tr '\n' ' ')"
