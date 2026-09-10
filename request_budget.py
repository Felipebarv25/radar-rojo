"""Guardián del cupo de requests del plan Free (100/día).

Cuenta cuántas requests hemos hecho en el día UTC actual y lo persiste en
request_budget.json, para que un reinicio del monitor no pierda la cuenta.
El límite real del plan Free es 100/día; dejamos margen con MAX_REQUESTS_PER_DAY.
"""
import json
import os
from datetime import datetime, timezone

_BUDGET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "request_budget.json")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> dict:
    try:
        with open(_BUDGET_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    # Si cambió el día UTC, la cuenta se reinicia sola.
    if data.get("date") != _today():
        data = {"date": _today(), "count": 0}
    return data


def _save(data: dict) -> None:
    with open(_BUDGET_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def used_today() -> int:
    return _load().get("count", 0)


def remaining(max_per_day: int) -> int:
    return max(0, max_per_day - used_today())


def can_spend(max_per_day: int) -> bool:
    return used_today() < max_per_day


def record_request() -> int:
    """Suma 1 a la cuenta del día y devuelve el total usado."""
    data = _load()
    data["count"] = data.get("count", 0) + 1
    _save(data)
    return data["count"]
