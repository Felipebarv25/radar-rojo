"""Implementación de la capa de datos con API-Football (Ruta A, plan Free).

Cada llamada a la API se contabiliza contra el cupo de 100/día mediante request_budget.
Para un partido concreto usamos GET /fixtures?id=<id>, que en una sola request
devuelve marcador, minuto y la lista de eventos (incluidas las tarjetas).
"""
import sys

import requests

import request_budget
from config import (
    API_FOOTBALL_BASE_URL,
    API_FOOTBALL_KEY,
    MAX_REQUESTS_PER_DAY,
)
from src.data_source import MatchDataSource, MatchEvent, MatchSnapshot


class BudgetExhausted(RuntimeError):
    """Se alcanzó el tope diario de requests configurado."""


class APIFootballSource(MatchDataSource):
    def __init__(self, api_key: str = API_FOOTBALL_KEY, base_url: str = API_FOOTBALL_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": api_key})

    # ---- infraestructura ----
    def _get(self, path: str, params: dict) -> dict:
        if not request_budget.can_spend(MAX_REQUESTS_PER_DAY):
            raise BudgetExhausted(
                f"Cupo diario alcanzado ({request_budget.used_today()}/"
                f"{MAX_REQUESTS_PER_DAY}). Se reinicia a las 00:00 UTC."
            )
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=20)
        used = request_budget.record_request()
        print(f"[API] {path} params={params} -> {resp.status_code} "
              f"(usadas hoy: {used}/{MAX_REQUESTS_PER_DAY})", file=sys.stderr)

        if resp.status_code != 200:
            raise RuntimeError(f"API-Football devolvió {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        # API-Football mete los errores dentro del cuerpo con status 200.
        errors = data.get("errors")
        if errors:
            raise RuntimeError(f"API-Football error: {errors}")
        return data

    # ---- contrato MatchDataSource ----
    def get_live_matches(self) -> list:
        """Lista de partidos en vivo (1 request). Para elegir fixture_id."""
        data = self._get("/fixtures", {"live": "all"})
        partidos = []
        for item in data.get("response", []):
            partidos.append({
                "fixture_id": item["fixture"]["id"],
                "league": item["league"]["name"],
                "country": item["league"]["country"],
                "home": item["teams"]["home"]["name"],
                "away": item["teams"]["away"]["name"],
                "elapsed": item["fixture"]["status"].get("elapsed"),
                "status": item["fixture"]["status"].get("short"),
                "home_goals": item["goals"].get("home"),
                "away_goals": item["goals"].get("away"),
            })
        return partidos

    def _parse_item(self, item: dict) -> MatchSnapshot:
        """Convierte un item de la API (de /fixtures?id o ?live=all) en snapshot.

        En live=all NO vienen statistics ni lineups: quedan vacíos y el Alert Score
        degrada a 'sin stats' (o se enriquece con get_snapshot cuando cae una roja).
        """
        events = []
        for ev in item.get("events", []) or []:
            time = ev.get("time", {}) or {}
            team = ev.get("team", {}) or {}
            player = ev.get("player", {}) or {}
            events.append(MatchEvent(
                minute=time.get("elapsed"),
                extra=time.get("extra"),
                team=team.get("name", "¿?"),
                player=player.get("name", "¿?"),
                player_id=player.get("id"),
                type=ev.get("type", ""),
                detail=ev.get("detail", ""),
                comments=ev.get("comments"),
                raw=ev,
            ))
        status = item["fixture"]["status"]
        return MatchSnapshot(
            fixture_id=item["fixture"]["id"],
            status_short=status.get("short", "?"),
            elapsed=status.get("elapsed"),
            home_team=item["teams"]["home"]["name"],
            away_team=item["teams"]["away"]["name"],
            home_goals=item["goals"].get("home"),
            away_goals=item["goals"].get("away"),
            league=item.get("league", {}).get("name", ""),
            country=item.get("league", {}).get("country", ""),
            events=events,
            team_stats=self._parse_stats(item.get("statistics")),
            player_positions=self._parse_positions(item.get("lineups")),
            raw=item,
        )

    def get_snapshot(self, fixture_id) -> MatchSnapshot:
        """Foto de UN partido (1 request). Incluye eventos + statistics + lineups."""
        data = self._get("/fixtures", {"id": fixture_id})
        response = data.get("response", [])
        if not response:
            raise RuntimeError(f"No hay datos para el fixture {fixture_id}.")
        return self._parse_item(response[0])

    def get_all_live_snapshots(self) -> list:
        """Foto de TODOS los partidos en vivo (1 request). Trae eventos, NO stats.

        Es el corazón del Radar Global: una sola request para escanear rojas en
        todos los partidos del mundo a la vez.
        """
        data = self._get("/fixtures", {"live": "all"})
        return [self._parse_item(item) for item in data.get("response", [])]

    # ---- parsers de contexto (Fase 2) ----
    # Mapa de los nombres de API-Football a nuestras claves normalizadas.
    _STAT_MAP = {
        "Ball Possession": "possession",
        "Total Shots": "shots_total",
        "Shots on Goal": "shots_on",
        "Corner Kicks": "corners",
        "expected_goals": "xg",
    }

    @staticmethod
    def _num(value):
        """Convierte '55%', '1.8', 3, None -> float o None."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip().replace("%", "")
        try:
            return float(s)
        except ValueError:
            return None

    def _parse_stats(self, statistics) -> dict:
        """statistics -> {nombre_equipo: {clave_normalizada: numero}}."""
        out = {}
        for block in statistics or []:
            team = block.get("team", {}).get("name")
            if not team:
                continue
            valores = {}
            for s in block.get("statistics", []) or []:
                clave = self._STAT_MAP.get(s.get("type"))
                if clave is None:
                    continue
                num = self._num(s.get("value"))
                if num is not None:
                    valores[clave] = num
            if valores:
                out[team] = valores
        return out

    def _parse_positions(self, lineups) -> dict:
        """lineups -> {player_id: 'G'|'D'|'M'|'F'}."""
        out = {}
        for block in lineups or []:
            for grupo in ("startXI", "substitutes"):
                for entry in block.get(grupo, []) or []:
                    p = (entry or {}).get("player", {}) or {}
                    pid, pos = p.get("id"), p.get("pos")
                    if pid is not None and pos:
                        out[pid] = pos
        return out
