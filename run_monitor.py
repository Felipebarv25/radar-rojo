"""Monitor de un partido: vigila y alerta tarjetas rojas a Telegram.

Fase 1: gatillo mínimo. Un solo partido. Detecta rojas nuevas y las envía.
El Alert Score (segunda capa) llega en Fase 2.

Uso:
    python run_monitor.py <fixture_id>
    python run_monitor.py <fixture_id> --no-startup   (no manda el aviso de arranque)

Consíguete el fixture_id con:  python find_live_matches.py
"""
import argparse
import sys
import time

import config
import request_budget
from src import persistence
from src.alert_score import compute_alert_score
from src.apifootball_source import APIFootballSource, BudgetExhausted
from src.formatter import format_red_card, format_startup
from src.red_card_detector import RedCardDetector
from src.telegram_notifier import TelegramNotifier


def parse_args():
    parser = argparse.ArgumentParser(description="Radar Rojo — monitor de un partido")
    parser.add_argument("fixture_id", help="ID del partido (de find_live_matches.py)")
    parser.add_argument("--no-startup", action="store_true",
                        help="No enviar el mensaje de arranque a Telegram")
    return parser.parse_args()


def main():
    args = parse_args()
    config.setup_console()
    config.validate()

    source = APIFootballSource()
    notifier = TelegramNotifier()
    detector = RedCardDetector()

    interval = config.POLL_INTERVAL_SECONDS
    print(f"Radar Rojo — fixture {args.fixture_id} · intervalo {interval}s · "
          f"cupo restante hoy: {request_budget.remaining(config.MAX_REQUESTS_PER_DAY)}")

    primer_ciclo = True
    while True:
        try:
            snap = source.get_snapshot(args.fixture_id)
        except BudgetExhausted as e:
            print(f"\n[STOP] {e}")
            break
        except Exception as e:  # red/API caída: no matamos el monitor, reintentamos
            print(f"[WARN] fallo al consultar: {e}. Reintento en {interval}s.", file=sys.stderr)
            time.sleep(interval)
            continue

        if primer_ciclo:
            primer_ciclo = False
            previas = detector.prime(snap)
            print(f"Arranque: {snap.scoreline} [{snap.status_short}]. "
                  f"Rojas previas ignoradas: {len(previas)}.")
            for ev in previas:
                print(f"  (previa) {ev.player} {ev.team} min {ev.minute} — {ev.detail}")
            if not args.no_startup:
                notifier.send(format_startup(snap))
        else:
            for ev in detector.new_red_cards(snap):
                alert = compute_alert_score(ev, snap)
                print(f"[ROJA] {ev.player} ({ev.team}) min {ev.minute} - {ev.detail} "
                      f"| Alert Score {alert.score}/100 "
                      f"({'con' if alert.stats_available else 'sin'} stats)")
                for linea in alert.breakdown_lines():
                    print(f"     {linea}")
                ruta = persistence.save_red_card(snap, ev, alert)
                print(f"   -> guardado: {ruta}")
                enviado = notifier.send(format_red_card(ev, snap, alert))
                print("   -> Telegram:", "OK" if enviado else "FALLÓ")

        if snap.is_finished:
            cerrados = persistence.close_match(snap)
            print(f"Partido finalizado [{snap.status_short}]. "
                  f"Registros de roja cerrados con desenlace: {cerrados}. Fin del monitoreo.")
            if not args.no_startup:
                notifier.send(f"🏁 Partido finalizado: {snap.scoreline}. Radar Rojo apagado.")
            break

        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
