.PHONY: install inspect build serve smoke test lint clean

## Установить зависимости локально
install:
	pip install -r requirements.txt

## Запустить MCP Inspector (stdio, локально)
inspect:
	npx @modelcontextprotocol/inspector python src/server.py

## Запустить HTTP-сервер локально
serve:
	python src/server.py serve

## Собрать Docker-образ
build:
	docker build -t dev-tools-mcp .

## docker run IMAGE serve
docker-serve: build
	docker run -p 8000:8000 \
		-v $(CURDIR)/demo_project:/workspace:ro \
		dev-tools-mcp serve

## docker run IMAGE smoke
docker-smoke: build
	docker run dev-tools-mcp smoke

## Локальный smoke-тест
smoke:
	python smoke_test.py

## Проверить синтаксис
lint:
	python -m py_compile src/server.py && echo "Syntax OK"

## Запустить Inspector через HTTP (сервер должен быть запущен)
inspect-http:
	npx @modelcontextprotocol/inspector --url http://localhost:8000/mcp

clean:
	docker rmi dev-tools-mcp 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
