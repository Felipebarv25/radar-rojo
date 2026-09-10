"""Núcleo compartido del Radar Global: UN ciclo de escaneo.

Lo usan dos "motores":
  - run_radar.py     : bucle infinito local (llama run_one_cycle en loop).
  - radar_cycle.py   : una sola corrida (GitHub Actions cada 15 min).

El estado (rojas ya vistas, rojas en seguimiento) vive en un dict JSON-serializable,
para que en la nube se pueda guardar entre corridas. Todo se recalcula desde
/fixtures?live=all, que trae el estado completo de cada partido en cada escaneo.
"""
import sys

import config
import request_budget
from src import persistence
from src.alert_score import compute_alert_score
from src.formatter import format_followup, format_red_card
from src.red_card_detector import is_red_card

ENRICH_MIN_REMAINING = 15  # solo pedir stats de la roja si quedan más de N requests


def red_key(ev) -> str:
    """Identidad estable de una roja (para no avisar dos veces)."""
    who = ev.player_id if ev.player_id is not None else ev.player
    return f"{ev.minute}|{ev.extra or 0}|{who}|{ev.detail}"


def _goals_of(snap, team, home_g, away_g):
    if team == snap.home_team:
        return home_g if home_g is not None else 0
    return away_g if away_g is not None else 0


def _handle_followup(source, notifier, fid, st, live_by_id) -> bool:
    """Manda la actualización periódica de una roja seguida.

    Devuelve True si el partido terminó (dejar de seguirlo).
    """
    snap = live_by_id.get(fid)
    finished = snap is None
    if finished:
        if not request_budget.can_spend(config.MAX_REQUESTS_PER_DAY):
            return True  # sin cupo: lo deja; close_pending.py lo cierra luego
        try:
            snap = source.get_snapshot(fid)
        except Exception as e:
            print(f"[WARN] no pude cerrar seguimiento de {fid}: {e}", file=sys.stderr)
            return True

    adv_now = _goals_of(snap, st["advantaged"], snap.home_goals, snap.away_goals)
    sent_now = _goals_of(snap, st["sent_off"], snap.home_goals, snap.away_goals)
    adv_at = _goals_of(snap, st["advantaged"], st["home_goals_at_red"], st["away_goals_at_red"])
    sent_at = _goals_of(snap, st["sent_off"], st["home_goals_at_red"], st["away_goals_at_red"])
    goals_adv_after = max(0, adv_now - adv_at)
    goals_sent_after = max(0, sent_now - sent_at)

    if finished or snap.is_finished:
        persistence.close_match(snap)
        finished = True

    notifier.send(format_followup(
        snap, st["red_min"], st["sent_off"], st["advantaged"],
        goals_adv_after, goals_sent_after, finished,
    ))
    return finished


def run_one_cycle(source, notifier, state, prime_only=False) -> dict:
    """Un escaneo de TODOS los partidos. Muta `state` (seen_reds, following).

    prime_only=True: marca las rojas actuales como vistas SIN avisar (para el
    primer arranque, y así no spamear rojas viejas).
    """
    snapshots = source.get_all_live_snapshots()
    live_by_id = {str(s.fixture_id): s for s in snapshots}
    seen = state.setdefault("seen_reds", {})
    following = state.setdefault("following", {})
    alerts = 0

    # 1) Seguimiento de rojas ya detectadas (antes de agregar nuevas).
    for fid in list(following.keys()):
        if _handle_followup(source, notifier, fid, following[fid], live_by_id):
            del following[fid]

    # 2) Detección de rojas NUEVAS en todos los partidos.
    for snap in snapshots:
        fkey = str(snap.fixture_id)
        known = set(seen.get(fkey, []))
        current_reds = [ev for ev in snap.events if is_red_card(ev)]
        nuevas = [ev for ev in current_reds if red_key(ev) not in known]
        seen[fkey] = [red_key(ev) for ev in current_reds]  # marca todas como vistas
        if prime_only:
            continue
        for ev in nuevas:
            snap_score = snap
            if request_budget.remaining(config.MAX_REQUESTS_PER_DAY) > ENRICH_MIN_REMAINING:
                try:
                    snap_score = source.get_snapshot(fkey)  # enriquece con stats
                except Exception as e:
                    print(f"[WARN] no pude enriquecer {fkey}: {e}", file=sys.stderr)
            alert = compute_alert_score(ev, snap_score)
            print(f"[ROJA] {snap.home_team} vs {snap.away_team} | {ev.player} "
                  f"({ev.team}) min {ev.minute} | Score {alert.score}/100 "
                  f"({'con' if alert.stats_available else 'sin'} stats)")
            persistence.save_red_card(snap_score, ev, alert)
            notifier.send(format_red_card(ev, snap_score, alert))
            following[fkey] = {
                "red_min": ev.minute,
                "sent_off": ev.team,
                "advantaged": snap.opponent_of(ev.team),
                "home_goals_at_red": snap.home_goals or 0,
                "away_goals_at_red": snap.away_goals or 0,
            }
            alerts += 1

    # 3) Limpieza: soltar rojas-vistas de partidos que ya terminaron.
    for fid in list(seen.keys()):
        if fid not in live_by_id and fid not in following:
            del seen[fid]

    return {"live": len(snapshots), "alerts": alerts, "following": len(following)}
