"""Detector de tarjetas rojas con anti-duplicados.

La roja es el ÚNICO gatillo. Este módulo decide qué cuenta como roja y evita
avisar dos veces del mismo evento.
"""
from src.data_source import MatchEvent, MatchSnapshot


def is_red_card(ev: MatchEvent) -> bool:
    """True si el evento es una roja (directa o doble amarilla).

    API-Football usa type="Card" con detail "Red Card" (directa) o
    "Second Yellow card" (doble amarilla -> expulsión).
    """
    if (ev.type or "").lower() != "card":
        return False
    detail = (ev.detail or "").lower()
    return "red" in detail or "second yellow" in detail


def _event_key(ev: MatchEvent):
    """Identidad estable de un evento para no repetir avisos."""
    who = ev.player_id if ev.player_id is not None else ev.player
    return (ev.minute, ev.extra, who, ev.detail)


class RedCardDetector:
    def __init__(self):
        self._seen = set()

    def prime(self, snapshot: MatchSnapshot) -> list:
        """Marca como 'ya vistas' las rojas que existían al empezar a monitorear.

        Devuelve esas rojas previas (para informarlas, no para alertar en caliente).
        Así, si arrancamos a mitad de partido, no disparamos alertas de rojas viejas.
        """
        previas = []
        for ev in snapshot.events:
            if is_red_card(ev):
                self._seen.add(_event_key(ev))
                previas.append(ev)
        return previas

    def new_red_cards(self, snapshot: MatchSnapshot) -> list:
        """Devuelve solo las rojas nuevas (no vistas antes)."""
        nuevas = []
        for ev in snapshot.events:
            if not is_red_card(ev):
                continue
            key = _event_key(ev)
            if key in self._seen:
                continue
            self._seen.add(key)
            nuevas.append(ev)
        return nuevas
