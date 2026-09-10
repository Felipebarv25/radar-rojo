"""Radar Global (modo LOCAL): bucle infinito en tu PC.

Escanea TODOS los partidos en vivo cada GLOBAL_POLL_INTERVAL_SECONDS y avisa las
rojas nuevas con Alert Score, con seguimiento hasta el final del partido.

Para el modo 24/7 sin PC encendido, ver radar_cycle.py + GitHub Actions.

Uso:
    python run_radar.py
    python run_radar.py --no-startup
"""
import argparse
import sys
import time

import config
import request_budget
from src import radar_core
from src.apifootball_source import APIFootballSource, BudgetExhausted
from src.telegram_notifier import TelegramNotifier


def main():
    parser = argparse.ArgumentParser(description="Radar Rojo — Radar Global (local)")
    parser.add_argument("--no-startup", action="store_true")
    args = parser.parse_args()

    config.setup_console()
    config.validate()

    source = APIFootballSource()
    notifier = TelegramNotifier()
    state = {}  # en memoria; en la nube se persiste (ver radar_cycle.py)

    activo = config.GLOBAL_POLL_INTERVAL_SECONDS
    idle = config.IDLE_POLL_INTERVAL_SECONDS
    print(f"Radar Global adaptativo — activo ~{activo // 60} min / idle ~{idle // 60} min · "
          f"cupo restante hoy: {request_budget.remaining(config.MAX_REQUESTS_PER_DAY)}")

    primero = True
    while True:
        try:
            summary = radar_core.run_one_cycle(source, notifier, state, prime_only=primero)
        except BudgetExhausted as e:
            # Sin cupo hoy: dormimos hasta que se reinicie (00:00 UTC), sin morir.
            print(f"[STOP hoy] {e} Duermo {idle}s.", file=sys.stderr)
            time.sleep(idle)
            continue
        except Exception as e:
            print(f"[WARN] fallo al escanear: {e}. Reintento en {activo}s.", file=sys.stderr)
            time.sleep(activo)
            continue

        if primero:
            primero = False
            print(f"Arranque: {summary['live']} en vivo. Rojas previas ignoradas.")
            if not args.no_startup:
                notifier.send(f"🟢 <b>Radar Global activo (24/7)</b>\nVigilando "
                              f"{summary['live']} partido(s) en vivo.")
        else:
            print(f"[ciclo] {summary['live']} en vivo · {summary['alerts']} roja(s) nueva(s) · "
                  f"siguiendo {summary['following']} · cupo {request_budget.used_today()}/"
                  f"{config.MAX_REQUESTS_PER_DAY}", file=sys.stderr)

        # Adaptativo: rápido si hay fútbol, lento si no hay nada que mirar.
        time.sleep(activo if summary["live"] > 0 else idle)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
