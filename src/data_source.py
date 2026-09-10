"""Capa de datos DESACOPLADA.

Este es el contrato que cualquier fuente de datos debe cumplir. Hoy lo implementa
API-Football (Ruta A). Mañana, si migramos a otra fuente (Ruta B / scraping), solo
escribimos otra clase que herede de MatchDataSource: el resto del sistema (detector,
Telegram, score) no cambia.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MatchEvent:
    """Un evento del partido, normalizado (independiente del proveedor)."""
    minute: Optional[int]
    extra: Optional[int]
    team: str
    player: str
    player_id: Optional[Any]
    type: str          # p. ej. "Card", "Goal", "subst"
    detail: str        # p. ej. "Red Card", "Yellow Card", "Second Yellow card"
    comments: Optional[str]
    raw: dict = field(default_factory=dict, repr=False)


@dataclass
class MatchSnapshot:
    """Foto del partido en un instante: marcador, minuto y lista de eventos."""
    fixture_id: Any
    status_short: str          # "1H", "HT", "2H", "FT", "LIVE", "NS"...
    elapsed: Optional[int]
    home_team: str
    away_team: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    league: str = ""
    country: str = ""
    events: list = field(default_factory=list)
    # Fase 2: contexto para el Alert Score (puede venir vacío en ligas menores).
    # team_stats: {nombre_equipo: {"possession": 55.0, "shots_total": 8, ...}}
    team_stats: dict = field(default_factory=dict)
    # player_positions: {player_id: "G"|"D"|"M"|"F"}
    player_positions: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict, repr=False)

    FINISHED_STATUSES = {"FT", "AET", "PEN", "PST", "CANC", "ABD", "AWD", "WO"}

    @property
    def is_finished(self) -> bool:
        return self.status_short in self.FINISHED_STATUSES

    @property
    def scoreline(self) -> str:
        h = self.home_goals if self.home_goals is not None else "-"
        a = self.away_goals if self.away_goals is not None else "-"
        return f"{self.home_team} {h}–{a} {self.away_team}"

    @property
    def has_stats(self) -> bool:
        """True si hay estadísticas útiles (posesión/remates/etc.)."""
        return any(bool(v) for v in self.team_stats.values())

    def opponent_of(self, team: str) -> str:
        """Devuelve el rival del equipo dado."""
        return self.away_team if team == self.home_team else self.home_team

    def goals_of(self, team: str) -> Optional[int]:
        if team == self.home_team:
            return self.home_goals
        if team == self.away_team:
            return self.away_goals
        return None


class MatchDataSource(ABC):
    """Contrato de una fuente de datos de partidos en vivo."""

    @abstractmethod
    def get_live_matches(self) -> list:
        """Devuelve una lista de partidos en vivo (para elegir cuál monitorear)."""

    @abstractmethod
    def get_snapshot(self, fixture_id) -> MatchSnapshot:
        """Devuelve la foto actual de un partido concreto."""
