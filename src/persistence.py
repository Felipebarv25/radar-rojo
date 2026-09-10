"""Persistencia para backtesting (Fase 3).

Cada tarjeta roja se guarda como UN archivo JSON en data/red_cards/. El registro
nace "abierto" (outcome=null) con todo el contexto y el Alert Score, y se CIERRA
con el desenlace del partido (resultado final y goles tras la roja) cuando termina.

Formato re-procesable: la Fase 4 (backtester) solo tiene que leer estos JSON y
correlacionar alert_score.score con outcome.

Un archivo por evento facilita: inspeccionarlos a mano, actualizarlos (cerrar el
desenlace) y sobrevivir reinicios sin corromper nada.
"""
import glob
import json
import os
import re
from datetime import datetime, timezone

from src.alert_score import AlertScore
from src.data_source import MatchEvent, MatchSnapshot

SCHEMA_VERSION = 1
_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "red_cards"
)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", str(text))


def record_id(fixture_id, ev: MatchEvent) -> str:
    who = ev.player_id if ev.player_id is not None else _slug(ev.player)
    return f"{_slug(fixture_id)}_{ev.minute}_{ev.extra or 0}_{_slug(who)}"


def _path(rid: str) -> str:
    return os.path.join(_DATA_DIR, f"{rid}.json")


def _effective_minute(minute, extra) -> float:
    """Minuto comparable que respeta el tiempo de descuento."""
    return (minute if minute is not None else 0) + (extra or 0) / 100.0


def _goals_after(snapshot: MatchSnapshot, red_min, red_extra) -> dict:
    """Cuenta goles ANOTADOS después de la roja, por equipo (maneja autogol)."""
    limite = _effective_minute(red_min, red_extra)
    conteo = {snapshot.home_team: 0, snapshot.away_team: 0}
    for ev in snapshot.events:
        if (ev.type or "").lower() != "goal":
            continue
        if _effective_minute(ev.minute, ev.extra) <= limite:
            continue
        # Autogol: el gol cuenta para el RIVAL del que lo marcó.
        if "own" in (ev.detail or "").lower():
            beneficiado = snapshot.opponent_of(ev.team)
        else:
            beneficiado = ev.team
        if beneficiado in conteo:
            conteo[beneficiado] += 1
    return conteo


def save_red_card(snapshot: MatchSnapshot, ev: MatchEvent, alert: AlertScore) -> str:
    """Crea el registro 'abierto' de una roja. Devuelve la ruta del archivo."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    rid = record_id(snapshot.fixture_id, ev)
    sent_off = ev.team
    advantaged = snapshot.opponent_of(sent_off)

    record = {
        "schema_version": SCHEMA_VERSION,
        "record_id": rid,
        "detected_at_utc": _now_utc(),
        "fixture": {
            "id": snapshot.fixture_id,
            "league": snapshot.league,
            "country": snapshot.country,
            "home_team": snapshot.home_team,
            "away_team": snapshot.away_team,
        },
        "red_card": {
            "minute": ev.minute,
            "extra": ev.extra,
            "team": sent_off,
            "player": ev.player,
            "player_id": ev.player_id,
            "detail": ev.detail,
            "position": snapshot.player_positions.get(ev.player_id),
        },
        "state_at_red": {
            "home_goals": snapshot.home_goals,
            "away_goals": snapshot.away_goals,
            "sent_off_team": sent_off,
            "advantaged_team": advantaged,
            "stats_available": snapshot.has_stats,
            "team_stats": snapshot.team_stats,
        },
        "alert_score": {
            "score": alert.score,
            "stats_available": alert.stats_available,
            "components": alert.components,
            "notes": alert.notes,
        },
        "outcome": None,  # se completa al cerrar el partido
    }
    with open(_path(rid), "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2)
    return _path(rid)


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def open_records_for_fixture(fixture_id) -> list:
    """Rutas de registros de esta fixture que aún no tienen desenlace."""
    pendientes = []
    for path in glob.glob(os.path.join(_DATA_DIR, "*.json")):
        try:
            rec = _load(path)
        except (json.JSONDecodeError, OSError):
            continue
        if str(rec.get("fixture", {}).get("id")) != str(fixture_id):
            continue
        if rec.get("outcome") is None:
            pendientes.append(path)
    return pendientes


def close_match(final_snapshot: MatchSnapshot) -> int:
    """Cierra los registros abiertos de esta fixture con el desenlace final.

    Devuelve cuántos registros cerró.
    """
    cerrados = 0
    for path in open_records_for_fixture(final_snapshot.fixture_id):
        rec = _load(path)
        rc = rec["red_card"]
        after = _goals_after(final_snapshot, rc["minute"], rc["extra"])
        sent_off = rec["state_at_red"]["sent_off_team"]
        advantaged = rec["state_at_red"]["advantaged_team"]

        fh_goals = final_snapshot.home_goals
        fa_goals = final_snapshot.away_goals
        g_sent = final_snapshot.goals_of(sent_off)
        g_adv = final_snapshot.goals_of(advantaged)
        if g_sent is None or g_adv is None:
            resultado = None
        elif g_sent > g_adv:
            resultado = "win"
        elif g_sent < g_adv:
            resultado = "loss"
        else:
            resultado = "draw"

        rec["outcome"] = {
            "closed_at_utc": _now_utc(),
            "final_status": final_snapshot.status_short,
            "final_home_goals": fh_goals,
            "final_away_goals": fa_goals,
            "goals_after_red": {
                "sent_off_team": after.get(sent_off, 0),
                "advantaged_team": after.get(advantaged, 0),
            },
            "result_for_sent_off_team": resultado,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
        cerrados += 1
    return cerrados
