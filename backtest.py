"""Backtester (Fase 4, acotado).

Lee los registros de roja guardados (data/red_cards/), toma los que ya tienen
desenlace y mide si el Alert Score se ASOCIA con lo que pasó después de la roja.

IMPORTANTE / HONESTIDAD:
- Esto mide ASOCIACIÓN, no poder predictivo ni valor de apuesta. No calcula EV.
- El Alert Score es fuerza relativa del contexto, NO probabilidad.
- Con pocas rojas los números NO son significativos. El reporte lo avisa fuerte.

Señal de desenlace que se cruza con el score:
- net_after   = goles del equipo con ventaja - goles del expulsado, TRAS la roja.
- adv_scored  = ¿el equipo con ventaja marcó al menos 1 tras la roja? (sí/no).

Uso:
    python backtest.py                 # reporte sobre data/red_cards/
    python backtest.py --list          # además, lista registro por registro
    python backtest.py --csv datos.csv # exporta los registros cerrados a CSV
    python backtest.py --dir otra/ruta # usa otra carpeta de registros
"""
import argparse
import csv
import glob
import json
import os
from statistics import mean

DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "red_cards")

BUCKETS = [(0, 25), (25, 50), (50, 75), (75, 101)]
MIN_SIGNIFICANT = 20  # bajo esto, avisamos que no hay nada concluyente


def load_records(data_dir):
    closed, pending = [], []
    for path in sorted(glob.glob(os.path.join(data_dir, "*.json"))):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        (closed if rec.get("outcome") else pending).append(rec)
    return closed, pending


def _row(rec):
    """Aplana un registro cerrado a los campos que analizamos/exportamos."""
    out = rec["outcome"]
    gar = out.get("goals_after_red", {}) or {}
    adv = gar.get("advantaged_team", 0) or 0
    sent = gar.get("sent_off_team", 0) or 0
    return {
        "record_id": rec.get("record_id"),
        "country": rec["fixture"].get("country", ""),
        "league": rec["fixture"].get("league", ""),
        "home_team": rec["fixture"].get("home_team", ""),
        "away_team": rec["fixture"].get("away_team", ""),
        "minute": rec["red_card"].get("minute"),
        "sent_off_team": rec["state_at_red"].get("sent_off_team", ""),
        "advantaged_team": rec["state_at_red"].get("advantaged_team", ""),
        "position": rec["red_card"].get("position") or "",
        "score": rec["alert_score"].get("score"),
        "stats_available": rec["alert_score"].get("stats_available", False),
        "goals_after_adv": adv,
        "goals_after_sent": sent,
        "net_after": adv - sent,
        "adv_scored": int(adv > 0),
        "result_sent_off": out.get("result_for_sent_off_team", ""),
        "final": f"{out.get('final_home_goals')}-{out.get('final_away_goals')}",
    }


def _pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _pct(part, total):
    return f"{100 * part / total:.0f}%" if total else "—"


def report(rows, show_list=False):
    print("=" * 64)
    print("  RADAR ROJO — BACKTEST (acotado)")
    print("=" * 64)

    n = len(rows)
    if n == 0:
        print("\nNo hay registros CERRADOS todavía. La mecánica funciona; solo")
        print("faltan datos. Corre el monitor en partidos y vuelve luego.")
        return

    con = [r for r in rows if r["stats_available"]]
    sin = n - len(con)
    print(f"\nRegistros cerrados: {n}   (con stats: {len(con)} · sin stats: {sin})")

    if n < MIN_SIGNIFICANT:
        print(f"\n⚠️  MUESTRA MUY PEQUEÑA (n={n} < {MIN_SIGNIFICANT}).")
        print("    Lo de abajo es descriptivo, NO concluyente. No decide nada.")

    # --- Tabla por rango de score ---
    print("\nPor rango de Alert Score:")
    print(f"  {'rango':>8} {'n':>3} {'adv marcó':>10} {'net medio':>10} {'expuls. perdió':>15}")
    print("  " + "-" * 52)
    for lo, hi in BUCKETS:
        b = [r for r in rows if r["score"] is not None and lo <= r["score"] < hi]
        if not b:
            print(f"  {f'{lo}-{hi-1}':>8} {0:>3} {'—':>10} {'—':>10} {'—':>15}")
            continue
        adv_hit = sum(r["adv_scored"] for r in b)
        net = mean(r["net_after"] for r in b)
        lost = sum(1 for r in b if r["result_sent_off"] == "loss")
        print(f"  {f'{lo}-{hi-1}':>8} {len(b):>3} {_pct(adv_hit, len(b)):>10} "
              f"{net:>+10.2f} {_pct(lost, len(b)):>15}")

    # --- Correlación score vs net_after ---
    scored = [(r["score"], r["net_after"]) for r in rows if r["score"] is not None]
    r = _pearson([s for s, _ in scored], [nt for _, nt in scored])
    print("\nCorrelación score ↔ goles netos tras la roja (Pearson):")
    if r is None:
        print("  n/d (hacen falta más datos con variación).")
    else:
        print(f"  r = {r:+.2f}   (n={len(scored)})  "
              f"{'— ignórala, muestra chica' if len(scored) < MIN_SIGNIFICANT else ''}")

    print("\nRecordatorio: esto es asociación, no probabilidad ni valor de apuesta.")

    if show_list:
        print("\nDetalle:")
        for r in rows:
            print(f"  [{r['score']:>3}] {r['sent_off_team']} exp min {r['minute']} "
                  f"→ final {r['final']}, net {r['net_after']:+d} "
                  f"({'con' if r['stats_available'] else 'sin'} stats) · {r['league']}")


def export_csv(rows, path):
    if not rows:
        print("No hay registros cerrados para exportar.")
        return
    campos = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(rows)
    print(f"Exportado {len(rows)} registro(s) a {path}")


def main():
    parser = argparse.ArgumentParser(description="Backtester de Radar Rojo")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="Carpeta de registros JSON")
    parser.add_argument("--list", action="store_true", help="Listar registro por registro")
    parser.add_argument("--csv", metavar="RUTA", help="Exportar registros cerrados a CSV")
    args = parser.parse_args()

    try:
        sys_stdout_utf8()
    except Exception:
        pass

    closed, pending = load_records(args.dir)
    rows = [_row(r) for r in closed]
    report(rows, show_list=args.list)
    if pending:
        print(f"\nℹ️  {len(pending)} registro(s) SIN cerrar (usa close_pending.py).")
    if args.csv:
        export_csv(rows, args.csv)


def sys_stdout_utf8():
    import sys
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    main()
