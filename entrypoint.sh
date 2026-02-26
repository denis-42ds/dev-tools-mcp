#!/usr/bin/env sh
# entrypoint.sh — точка входа контейнера
# Использование:
#   docker run IMAGE serve   — запустить MCP HTTP-сервер на порту 8000
#   docker run IMAGE smoke   — быстрая проверка работоспособности

set -e

COMMAND="${1:-serve}"

case "$COMMAND" in
  serve)
    echo "[entrypoint] Starting MCP server (HTTP, port 8000)..."
    exec python src/server.py serve
    ;;
  smoke)
    echo "[entrypoint] Running smoke tests..."
    exec python smoke_test.py
    ;;
  *)
    echo "[entrypoint] Unknown command: $COMMAND"
    echo "Usage: docker run IMAGE [serve|smoke]"
    exit 1
    ;;
esac
