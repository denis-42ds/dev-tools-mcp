"""Утилиты общего назначения."""

import os
import json
import logging

logger = logging.getLogger(__name__)


# TODO: вынести в константы
MAX_RETRIES = 3
TIMEOUT = 30


def read_config(path: str) -> dict:
    """Читает конфиг из JSON-файла."""
    # FIXME: не обрабатывается ситуация когда файл не существует
    # FIXME: нет валидации схемы конфига
    with open(path) as f:
        return json.load(f)


def send_notification(user_id: int, message: str) -> bool:
    """Отправить уведомление пользователю."""
    # TODO: реализовать интеграцию с email-сервисом (SendGrid/SES)
    # TODO: реализовать интеграцию с push-уведомлениями
    # HACK: пока просто логируем
    logger.info(f"NOTIFICATION to {user_id}: {message}")
    return True


def generate_report(data: list) -> str:
    """Генерация отчёта."""
    # XXX: Очень медленная реализация, переписать
    result = ""
    for item in data:
        result += str(item) + "\n"  # OPTIMIZE: использовать join вместо конкатенации
    return result


def cleanup_temp_files():
    """Удалить временные файлы."""
    # BUG: не удаляет файлы в поддиректориях
    # NOTE: вызывать только в конце рабочего дня
    temp_dir = "/tmp/app_temp"
    if os.path.exists(temp_dir):
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))


class CacheManager:
    """Менеджер кэша."""

    # DEPRECATED: использовать Redis вместо in-memory кэша
    def __init__(self):
        self._cache = {}

    def get(self, key: str):
        # TODO: добавить TTL для записей
        return self._cache.get(key)

    def set(self, key: str, value):
        # FIXME: нет ограничения размера кэша — возможна утечка памяти
        self._cache[key] = value
