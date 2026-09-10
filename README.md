# Radar Rojo 🟥

Sistema que vigila un partido de fútbol en vivo y te avisa a **Telegram** cuando cae una **tarjeta roja**. La roja es el único gatillo.

> **Fase 1 ✅:** gatillo mínimo. Un partido a la vez. Detecta rojas nuevas y las envía a Telegram.
> **Fase 2 ✅:** Alert Score 0–100 (fuerza relativa del contexto, no probabilidad).
> **Fase 3 ✅:** persistencia — cada roja se guarda con su contexto, score y desenlace, lista para backtesting.
> **Fase 4 ✅ (acotada):** backtester que cruza Alert Score vs desenlace. Mide asociación, NO valor de apuesta. Necesita acumular datos para significar algo.
>
> Sin apuestas automáticas. Sin credenciales de casas. Solo "revisar mercados manualmente". Sin garantías.

## Requisitos

- Python 3.9 o superior.
- Tus tres claves: token del bot de Telegram, tu chat_id, y la API key de API-Football (plan Free).

## Instalación (Windows PowerShell)

Desde la carpeta del proyecto:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuración

1. Copia el archivo de ejemplo a `.env`:

```bash
copy .env.example .env
```

2. Abre `.env` y rellena tus valores reales:
   - `TELEGRAM_BOT_TOKEN` — el token de BotFather.
   - `TELEGRAM_CHAT_ID` — ya está puesto tu id (`6806509153`), verifícalo.
   - `API_FOOTBALL_KEY` — tu key de api-sports.io.

   El archivo `.env` **nunca** se comparte ni se sube a ningún lado (está en `.gitignore`).

## Uso

**1) Prueba de humo** (confirma que Telegram funciona; no gasta cupo de la API):

```bash
python test_telegram.py
```

Deberías recibir un mensaje en tu Telegram. Si no llega, revisa que le hayas dado **/start** a tu bot.

**2) Ver partidos en vivo** (gasta 1 request) y copiar el `fixture_id`:

```bash
python find_live_matches.py
```

**3a) Radar Global — no te pierdes ninguna roja (recomendado):**

```bash
python run_radar.py
```

Un proceso vigila **todos** los partidos en vivo a la vez (1 request por ciclo, ~15 min). Cuando cae una roja en cualquier liga, te llega la alerta con Alert Score y te hace **seguimiento cada ~15 min** hasta el final. Trade-off: cobertura total a cambio de latencia (~15 min, no instantáneo).

**3b) Monitorear UN partido de cerca (baja latencia):**

```bash
python run_monitor.py 1234567
```

(reemplaza `1234567` por el `fixture_id` real). Cada ~75s consulta ese partido; útil para seguir uno concreto rápido, pero solo cubre ese.

## Datos para backtesting (Fase 3)

Cada roja detectada se guarda como un JSON en `data/red_cards/`:

- Nace **abierto** (`outcome: null`) con el contexto completo (marcador, stats si hay, posición del expulsado) y el **Alert Score** con su desglose por componente.
- Al terminar el partido se **cierra** con el desenlace: resultado final y **goles anotados después de la roja** por cada equipo. Eso es lo que el backtester (Fase 4) correlacionará con el score.

Si el monitor se apagó antes del pitido final, cierra los pendientes con:

```bash
python close_pending.py
```

(consulta el resultado final de cada partido pendiente; cuesta ~1 request por partido).

La carpeta `data/` es local y está en `.gitignore` (no se versiona).

## Backtesting (Fase 4, acotada)

Cuando tengas registros cerrados:

```bash
python backtest.py                 # reporte: score por rangos vs desenlace
python backtest.py --list          # además, registro por registro
python backtest.py --csv datos.csv # exporta a CSV (para Excel / Power BI)
```

El reporte cruza el Alert Score con lo que pasó tras la roja (si el equipo con ventaja marcó, goles netos, si el expulsado perdió) y calcula una correlación simple.

**Honestidad:** mide **asociación, no poder predictivo ni valor de apuesta**; no calcula EV. Con menos de ~20 rojas los números **no son concluyentes** y el reporte lo avisa. Y aun con 20+, es un piso mínimo, no una garantía estadística.

## Despliegue 24/7 (sin tu PC encendido)

Para que el Radar Global corra solo en la nube, gratis, sin servidor ni tarjeta,
ver **[deploy/DESPLIEGUE-GITHUB.md](deploy/DESPLIEGUE-GITHUB.md)** (GitHub Actions,
un escaneo cada ~15 min). El estado (rojas vistas/seguidas, cupo, histórico) se
guarda en el propio repo entre corridas; las claves van en GitHub Secrets.

## Cupo del plan Free (importante)

- Límite real: **100 requests/día** (se reinicia a las 00:00 UTC).
- Un partido completo a 75s de intervalo gasta **~84 requests**. Por eso: **un partido a la vez**.
- El guardián (`request_budget.py`) cuenta las requests del día y **detiene el monitor** si llegas al tope (`MAX_REQUESTS_PER_DAY`, por defecto 95). No hay forma de gastar de más sin querer.

## Estructura

```
config.py               Carga y valida el .env
request_budget.py       Guardián del cupo 100/día
src/
  data_source.py        Contrato de la capa de datos (DESACOPLADA)
  apifootball_source.py Implementación Ruta A (API-Football)
  red_card_detector.py  Detección de rojas + anti-duplicados
  alert_score.py        Alert Score 0-100 (Fase 2)
  persistence.py        Guardado/cierre de registros para backtesting (Fase 3)
  telegram_notifier.py  Salida a Telegram
  formatter.py          Texto de las alertas
src/
  radar_core.py         Núcleo de UN ciclo de escaneo (compartido)
find_live_matches.py    Lista partidos en vivo (elegir fixture_id)
run_radar.py            RADAR GLOBAL local: bucle en tu PC (cobertura total)
radar_cycle.py          RADAR GLOBAL nube: una corrida (para GitHub Actions 24/7)
run_monitor.py          Monitor de UN partido (baja latencia ~75s)
close_pending.py        Cierra registros de roja sin desenlace
backtest.py             Backtester acotado (Fase 4) + export CSV
test_telegram.py        Prueba de humo de Telegram
.github/workflows/      Workflow de GitHub Actions (cron 24/7)
deploy/                 Guía de despliegue 24/7
data/red_cards/         Registros JSON de rojas
```

La capa de datos está desacoplada a propósito: para cambiar de fuente en el futuro solo se escribe otra clase que herede de `MatchDataSource`; el resto no cambia.
