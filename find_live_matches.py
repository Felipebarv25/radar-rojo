"""Lista los partidos en vivo AHORA para que elijas cuál monitorear.

Gasta 1 request del cupo diario. Copia el fixture_id del partido que quieras y
úsalo con run_monitor.py.

Uso:
    python find_live_matches.py
"""
import config
from src.apifootball_source import APIFootballSource, BudgetExhausted


def main():
    config.setup_console()
    config.validate()
    source = APIFootballSource()
    try:
        partidos = source.get_live_matches()
    except BudgetExhausted as e:
        print(f"Sin cupo: {e}")
        raise SystemExit(1)

    if not partidos:
        print("No hay partidos en vivo en este momento.")
        return

    print(f"\n{len(partidos)} partido(s) en vivo:\n")
    print(f"{'fixture_id':>10}  {'min':>3}  marcador / liga")
    print("-" * 70)
    for p in partidos:
        marcador = f"{p['home']} {p['home_goals']}-{p['away_goals']} {p['away']}"
        elapsed = p["elapsed"] if p["elapsed"] is not None else "?"
        print(f"{p['fixture_id']:>10}  {elapsed:>3}  {marcador}")
        print(f"{'':>10}       {p['country']} · {p['league']}  [{p['status']}]")
    print("\nElige un fixture_id y corre:  python run_monitor.py <fixture_id>")


if __name__ == "__main__":
    main()
