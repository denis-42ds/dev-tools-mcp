"""
Модуль обработки пользователей.
Намеренно содержит техдолг для демонстрации scan_tech_debt.
"""

import hashlib
import time
from typing import Optional


# TODO: вынести конфигурацию в отдельный config.py файл
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "users"


def get_user(user_id: int) -> Optional[dict]:
    """Получить пользователя по ID."""
    # FIXME: нет кэширования — каждый раз ходим в БД
    # FIXME: нет обработки ошибок подключения к БД
    query = f"SELECT * FROM users WHERE id = {user_id}"  # XXX: SQL-инъекция!
    # TODO: заменить на параметризованный запрос
    return {"id": user_id, "name": "stub"}


def authenticate(username: str, password: str) -> bool:
    """Аутентификация пользователя."""
    # HACK: пока храним пароль в открытом виде, потом исправим
    stored = _get_password_from_db(username)
    return stored == password  # BUG: не используем constant-time comparison


def hash_password(password: str) -> str:
    """Хеширование пароля."""
    # DEPRECATED: использовать bcrypt вместо md5
    return hashlib.md5(password.encode()).hexdigest()


def _get_password_from_db(username: str) -> str:
    # TODO: реализовать настоящий запрос к БД
    return "plaintext_password"


def create_user(username: str, email: str, password: str) -> dict:
    """Создать нового пользователя."""
    # NOTE: валидация email не реализована
    # TODO: добавить валидацию email через regex или библиотеку
    # TODO: добавить проверку на уникальность username
    hashed = hash_password(password)
    return {"username": username, "email": email, "password": hashed}


def bulk_load_users(user_ids: list[int]) -> list[dict]:
    """Загрузить пачку пользователей."""
    # OPTIMIZE: N+1 запрос — нужно переписать на один запрос с IN (...)
    result = []
    for uid in user_ids:
        result.append(get_user(uid))
        time.sleep(0.01)  # HACK: throttle чтобы не перегружать БД
    return result
