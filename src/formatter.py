"""Formatea el mensaje de la alerta de roja para Telegram.

Fase 1: mensaje simple (equipo, jugador, minuto, marcador). El Alert Score llega
en Fase 2. Se incluye ya el recordatorio de 'revisar mercados manualmente'.
"""
import html

from src.data_source import MatchEvent, MatchSnapshot


def _min_str(ev: MatchEvent) -> str:
    base = ev.minute if ev.minute is not None else "?"
    if ev.extra:
        return f"{base}+{ev.extra}'"
    return f"{base}'"


def _score_bar(score: int) -> str:
    """Barra visual de 10 bloques según el score 0-100."""
    llenos = round(score / 10)
    return "█" * llenos + "░" * (10 - llenos)


def format_red_card(ev: MatchEvent, snap: MatchSnapshot, alert=None) -> str:
    tipo = "Doble amarilla" if "second yellow" in (ev.detail or "").lower() else "Roja directa"
    jugador = html.escape(str(ev.player))
    equipo = html.escape(str(ev.team))
    marcador = html.escape(snap.scoreline)
    minuto = _min_str(ev)

    msg = (
        "🟥 <b>TARJETA ROJA</b>\n"
        f"<b>{jugador}</b> ({equipo})\n"
        f"Minuto {minuto} · {tipo}\n"
        f"Marcador: {marcador}\n"
    )

    if alert is not None:
        etiqueta = "sin stats" if not alert.stats_available else "con stats"
        msg += (
            "\n"
            f"<b>Alert Score: {alert.score}/100</b>  ({etiqueta})\n"
            f"<code>{_score_bar(alert.score)}</code>\n"
            "<i>Fuerza relativa del contexto, NO probabilidad.</i>\n"
        )
        if alert.notes:
            msg += "· " + "\n· ".join(html.escape(n) for n in alert.notes) + "\n"

    msg += (
        "\n"
        "<i>Solo asistencia. Revisa los mercados manualmente. "
        "Sin garantías ni recomendaciones de apuesta.</i>"
    )
    return msg


def format_followup(snap: MatchSnapshot, red_min, sent_off_team: str,
                    advantaged_team: str, goals_adv_after: int, goals_sent_after: int,
                    finished: bool) -> str:
    """Actualización periódica tras una roja (cada ~15 min hasta el final)."""
    cab = "🏁 <b>Cierre tras la roja</b>" if finished else "🔎 <b>Seguimiento tras la roja</b>"
    estado = "Final" if finished else (f"min {snap.elapsed}" if snap.elapsed is not None else snap.status_short)
    msg = (
        f"{cab}\n"
        f"{html.escape(snap.scoreline)}  ·  {estado}\n"
        f"(roja al {red_min}' a {html.escape(sent_off_team)})\n"
    )
    if goals_adv_after > 0:
        msg += (f"⚽ El equipo con ventaja ({html.escape(advantaged_team)}) marcó "
                f"{goals_adv_after} tras la roja.\n")
    if goals_sent_after > 0:
        msg += (f"↩️ Aun con 10, {html.escape(sent_off_team)} marcó "
                f"{goals_sent_after} tras la roja.\n")
    if goals_adv_after == 0 and goals_sent_after == 0:
        msg += "Sin goles desde la roja.\n"
    return msg


def format_startup(snap: MatchSnapshot) -> str:
    return (
        "🟢 <b>Radar Rojo activo</b>\n"
        f"Vigilando: {html.escape(snap.scoreline)}\n"
        f"Estado: {snap.status_short}"
        + (f" · min {snap.elapsed}" if snap.elapsed is not None else "")
    )
