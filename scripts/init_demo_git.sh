#!/usr/bin/env sh
# init_demo_git.sh — создаёт git-историю в demo_project/ во время сборки образа.
# Вызывается из Dockerfile один раз: RUN ./scripts/init_demo_git.sh
# GitHub не хранит вложенные .git-папки, поэтому история воссоздаётся здесь.

set -e

DEMO="/app/demo_project"
cd "$DEMO"

git init
git config user.email "demo@example.com"
git config user.name "Demo User"

# ── Коммит 1: initial setup (tag v0.1.0) ────────────────────────────────────
git add .
git commit -m "chore: initial project setup"
git tag v0.1.0

# ── Коммит 2-3: features ─────────────────────────────────────────────────────
echo "# App" >> README.md
git add README.md
git commit -m "feat(users): add user authentication module"

echo "version = '1.0.0'" > src/version.py
git add src/version.py
git commit -m "feat(core): implement version tracking"

# ── Коммит 4: tests ──────────────────────────────────────────────────────────
mkdir -p tests
touch tests/__init__.py
git add tests/
git commit -m "test: add test infrastructure"

# ── Коммит 5: docs ───────────────────────────────────────────────────────────
mkdir -p docs
echo "# API docs" > docs/api.md
git add docs/
git commit -m "docs: add API documentation"

# ── Коммит 6: cache feature ──────────────────────────────────────────────────
cat > src/cache.py << 'EOF'
"""Redis cache integration."""
# TODO: подключить настоящий Redis
class RedisCache:
    pass
EOF
git add src/cache.py
git commit -m "feat(cache): add Redis cache manager"

# ── Коммит 7-9: perf, ci, breaking change ────────────────────────────────────
git commit --allow-empty -m "perf(db): optimize bulk user loading query"

cat > .github-ci.yml << 'EOF'
# CI placeholder
stages: [test, build, deploy]
EOF
git add .github-ci.yml
git commit -m "ci: add GitHub Actions pipeline"

git commit --allow-empty -m "feat(api)!: change authentication endpoint from /auth to /api/v2/auth

BREAKING CHANGE: clients must update endpoint URL"

# ── Коммит 10-11: refactor, chore (tag v1.0.0) ───────────────────────────────
git commit --allow-empty -m "refactor(users): extract password hashing to separate module"
git commit --allow-empty -m "chore(deps): bump flask from 2.3.0 to 3.0.2"
git tag v1.0.0

echo "[init_demo_git] Done: $(git log --oneline | wc -l) commits, tags: $(git tag | tr '\n' ' ')"
