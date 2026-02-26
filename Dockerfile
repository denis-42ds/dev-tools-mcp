FROM python:3.12-slim

LABEL maintainer="dev-tools-mcp"
LABEL description="MCP server: tech debt scanner, release notes generator, Dockerfile auditor"
LABEL version="1.0.0"

# git нужен для generate_release_notes
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Зависимости — отдельным слоем для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходный код и вспомогательные скрипты
COPY src/          ./src/
COPY smoke_test.py ./
COPY entrypoint.sh ./

# demo_project — тестовые данные для команды smoke
COPY demo_project/ ./demo_project/

# Непривилегированный пользователь
RUN useradd -m -u 1000 mcpuser \
    && chown -R mcpuser:mcpuser /app

USER mcpuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

ENTRYPOINT ["./entrypoint.sh"]
CMD ["serve"]
