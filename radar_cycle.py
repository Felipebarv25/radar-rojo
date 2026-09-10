"""Radar Global (modo NUBE): UNA corrida. Pensado para GitHub Actions cada 15 min.

Carga el estado desde radar_state.json, hace un escaneo (run_one_cycle) y vuelve a
guardar el estado. GitHub Actions versiona radar_state.json, request_budget.json y
data/ entre corridas, así el sistema "recuerda" qué rojas ya avisó y cuáles sigue.

La PRIMERA corrida (sin estado previo) entra en modo prime: marca las rojas que ya
existían como vistas SIN avisar, para no spamear rojas viejas al arrancar.

Uso (local o en Actions):
    python radar_cycle.py
"""
import json
import os
import sys

import config
import request_budget
from src import radar_core
from src.apifootball_source import APIFootballSource, BudgetExhausted
from src.telegram_notifier import TelegramNotifier

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "radar_state.json")


def load_state():
    """Devuelve (state, es_primera_vez)."""
    if not os.path.exists(STATE_FILE):
        return {"seen_reds": {}, "following": {}}, True
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh), False
    except (json.JSONDecodeError, OSError):
        # Estado corrupto: tratamos como primera vez (prime) para no spamear.
        return {"seen_reds": {}, "following": {}}, True


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def main():
    config.setup_console()
    config.validate()

    source = APIFootballSource()
    notifier = TelegramNotifier()
    state, primera_vez = load_state()

    try:
        summary = radar_core.run_one_cycle(source, notifier, state, prime_only=primera_vez)
    except BudgetExhausted as e:
        print(f"[SKIP] {e}")
        save_state(state)  # guarda por si el cupo se liberó a media corrida
        return
    except Exception as e:
        # No reventamos el workflow: la próxima corrida (en 15 min) reintenta.
        print(f"[WARN] fallo en el escaneo: {e}", file=sys.stderr)
        return

    save_state(state)
    modo = "PRIME (sin avisos)" if primera_vez else "normal"
    print(f"[{modo}] en vivo: {summary['live']} · rojas nuevas: {summary['alerts']} · "
          f"siguiendo: {summary['following']} · cupo: {request_budget.used_today()}/"
          f"{config.MAX_REQUESTS_PER_DAY}")


if __name__ == "__main__":
    main()
