"""Alert Score (Fase 2): mide la FUERZA RELATIVA del contexto tras una roja.

NO es probabilidad de gol/victoria ni valor de apuesta. Es un 0–100 que resume
qué tan desequilibrante es la situación creada por la expulsión, dado el contexto.

Se calcula SOLO cuando cae una roja. Cada componente queda trazado (valor, peso,
aporte) para poder afinarlo con backtesting en la Fase 4.

Componentes:
  - time_left    : cuánto partido queda (más minutos = más impacto).
  - scoreline    : qué tan "vivo y volteable" está el marcador.
  - position     : peso del puesto del expulsado (portero/defensa > delantero).
  - momentum     : dominio previo del equipo que queda con ventaja numérica
                   (posesión/remates/córners/xG). Solo si hay stats.

Si faltan stats, se omite 'momentum' y se renormalizan los pesos restantes:
el score sigue siendo 0–100, pero el mensaje avisa "sin stats".
"""
from dataclasses import dataclass, field
from typing import Optional

from src.data_source import MatchEvent, MatchSnapshot

# Pesos base (cuando TODOS los componentes están disponibles). Suman 1.0.
WEIGHTS = {
    "time_left": 0.30,
    "scoreline": 0.25,
    "position": 0.15,
    "momentum": 0.30,
}

# Métricas de dominio y su peso relativo dentro de 'momentum'.
MOMENTUM_METRICS = {
    "possession": 1.0,
    "shots_total": 1.0,
    "shots_on": 1.2,
    "corners": 0.6,
    "xg": 1.4,
}


@dataclass
class AlertScore:
    score: int
    stats_available: bool
    components: dict = field(default_factory=dict)  # nombre -> {value, weight, contribution}
    notes: list = field(default_factory=list)

    def breakdown_lines(self) -> list:
        orden = ["time_left", "scoreline", "position", "momentum"]
        out = []
        for name in orden:
            c = self.components.get(name)
            if not c:
                continue
            out.append(f"{name}: {c['value']:.2f} × {c['weight']:.2f} = {c['contribution']:.1f}")
        return out


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _sub_time_left(snap: MatchSnapshot) -> float:
    minute = snap.elapsed if snap.elapsed is not None else 45
    return _clamp((90 - minute) / 90.0)


def _sub_scoreline(diff: Optional[int]) -> float:
    """diff = goles del equipo EXPULSADO menos rival. Más 'vivo' el juego -> más alto."""
    if diff is None:
        return 0.6
    d = abs(diff)
    if d == 0:
        return 1.0          # empate: la balanza se inclina
    if d == 1:
        return 0.9 if diff > 0 else 0.8
    if d == 2:
        return 0.6 if diff > 0 else 0.5
    return 0.25             # 3+: partido liquidado


def _sub_position(pos: Optional[str]) -> float:
    return {"G": 1.0, "D": 1.0, "M": 0.6, "F": 0.4}.get(pos, 0.6)


def _sub_momentum(snap: MatchSnapshot, advantaged_team: str) -> Optional[float]:
    """Share de dominio del equipo con ventaja numérica. None si no hay stats."""
    adv = snap.team_stats.get(advantaged_team, {})
    opp = snap.team_stats.get(snap.opponent_of(advantaged_team), {})
    shares, pesos = [], []
    for metric, w in MOMENTUM_METRICS.items():
        a, o = adv.get(metric), opp.get(metric)
        if a is None or o is None:
            continue
        total = a + o
        if total <= 0:
            continue
        shares.append((a / total) * w)
        pesos.append(w)
    if not pesos:
        return None
    return _clamp(sum(shares) / sum(pesos))


def compute_alert_score(red: MatchEvent, snap: MatchSnapshot,
                        weights: dict = None) -> AlertScore:
    weights = dict(weights or WEIGHTS)
    sent_off_team = red.team
    advantaged_team = snap.opponent_of(sent_off_team)
    diff = None
    g_sent = snap.goals_of(sent_off_team)
    g_opp = snap.goals_of(advantaged_team)
    if g_sent is not None and g_opp is not None:
        diff = g_sent - g_opp

    notes = []
    subs = {
        "time_left": _sub_time_left(snap),
        "scoreline": _sub_scoreline(diff),
        "position": _sub_position(snap.player_positions.get(red.player_id)),
    }
    if red.player_id not in snap.player_positions:
        notes.append("posición del expulsado desconocida (peso neutro)")

    momentum = _sub_momentum(snap, advantaged_team)
    stats_available = momentum is not None
    if stats_available:
        subs["momentum"] = momentum
    else:
        notes.append("sin estadísticas de juego: score calculado sin 'momentum'")
        weights.pop("momentum", None)

    # Renormalizar los pesos de los componentes presentes para que sumen 1.
    total_w = sum(weights[k] for k in subs if k in weights)
    components = {}
    score_0_1 = 0.0
    for name, value in subs.items():
        w = weights.get(name, 0.0) / total_w if total_w else 0.0
        contribution = value * w * 100
        components[name] = {"value": value, "weight": w, "contribution": contribution}
        score_0_1 += value * w

    return AlertScore(
        score=int(round(score_0_1 * 100)),
        stats_available=stats_available,
        components=components,
        notes=notes,
    )
