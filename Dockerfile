FROM python:3.12-slim

LABEL maintainer="dev-tools-mcp"
LABEL description="MCP server: tech debt scanner, release notes generator, Dockerfile auditor"
LABEL version="1.0.0"

# git нужен для generate_release_notes и для init_demo_git.sh
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Минимальный git-конфиг для сборки
RUN git config --global user.email "build@dev-tools-mcp" \
    && git config --global user.name "Build"

WORKDIR /app

# Зависимости — отдельным слоем для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходный код и вспомогательные скрипты
COPY src/           ./src/
COPY smoke_test.py  ./
COPY entrypoint.sh  ./
COPY scripts/       ./scripts/
RUN chmod +x ./entrypoint.sh ./scripts/init_demo_git.sh

# demo_project — тестовые данные (без .git, он создаётся ниже)
COPY demo_project/  ./demo_project/

# Воссоздаём git-историю demo_project/ прямо в образе
RUN ./scripts/init_demo_git.sh

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
