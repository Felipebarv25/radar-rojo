"""Cierra registros de roja que quedaron 'abiertos' (sin desenlace).

Pasa cuando el monitor se apagó antes del pitido final (cupo agotado, Ctrl+C,
reinicio). Este script busca los registros sin outcome, consulta el resultado
final de cada partido (1 request por fixture) y los cierra.

Uso:
    python close_pending.py
"""
import glob
import json
import os

import config
import request_budget
from src.apifootball_source import APIFootballSource, BudgetExhausted
from src import persistence


def main():
    config.setup_console()
    config.validate()

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "red_cards")
    fixtures_pendientes = set()
    for path in glob.glob(os.path.join(data_dir, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        if rec.get("outcome") is None:
            fixtures_pendientes.add(str(rec["fixture"]["id"]))

    if not fixtures_pendientes:
        print("No hay registros pendientes de cerrar.")
        return

    print(f"Fixtures con registros abiertos: {len(fixtures_pendientes)} "
          f"(costará ~{len(fixtures_pendientes)} requests). "
          f"Cupo restante: {request_budget.remaining(config.MAX_REQUESTS_PER_DAY)}")

    source = APIFootballSource()
    total = 0
    for fid in fixtures_pendientes:
        try:
            snap = source.get_snapshot(fid)
        except BudgetExhausted as e:
            print(f"Sin cupo, me detengo: {e}")
            break
        except Exception as e:
            print(f"[WARN] fixture {fid}: {e}")
            continue
        if not snap.is_finished:
            print(f"Fixture {fid} aún no termina [{snap.status_short}]. Lo dejo pendiente.")
            continue
        n = persistence.close_match(snap)
        print(f"Fixture {fid}: {snap.scoreline} -> {n} registro(s) cerrados.")
        total += n

    print(f"\nListo. Registros cerrados en esta corrida: {total}")


if __name__ == "__main__":
    main()
