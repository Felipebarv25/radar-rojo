# Manual de operación — Radar Rojo

Todo lo que necesitas para operar el sistema solo, día a día, durante la fase de
acumulación de datos.

> Recordatorio honesto: esto es una herramienta de asistencia para **revisar
> mercados a mano**, no una máquina de dinero (por más que el bot se llame así).
> Que los datos hablen antes de ponerle plata a nada. Sin garantías.

---

Todo se corre desde la carpeta del proyecto. Abre PowerShell ahí:

```powershell
cd "C:\Users\USER\OneDrive\Documentos\10. Radar Rojo"
```

## Modo recomendado: Radar Global (no te pierdes ninguna roja)

Vigila **todos** los partidos del mundo en vivo a la vez, con 1 request por ciclo.
Lo enciendes y lo dejas:

```powershell
python run_radar.py
```

- Escanea cada ~15 min. Cuando cae una roja en **cualquier** liga, te llega la
  alerta 🟥 con Alert Score, se guarda, y te hace **seguimiento cada ~15 min**
  hasta el final (avisando si el equipo con ventaja marcó tras la roja).
- **Trade-off:** cobertura total a cambio de latencia. Te enteras hasta ~15 min
  después, no al instante. Es el precio de cubrir todo gratis.
- Para cortarlo: **Ctrl+C**.

## Modo alterno: vigilar UN partido de cerca (baja latencia)

Si quieres seguir un partido concreto con detección rápida (~75s):

```powershell
python find_live_matches.py      # elige un fixture_id
python run_monitor.py 1234567    # vígilalo de cerca
```

## Si cortaste algo antes del final del partido

```powershell
python close_pending.py
```

**Revisar progreso cuando quieras** (no gasta cupo):

```powershell
python backtest.py
```

---

## Reglas de operación que importan

- **El Radar Global gasta ~1 request cada 15 min** (≈96/día si corre 24h). El
  guardián (`request_budget.py`) te frena si llegas al tope de 95. Cuando cae una
  roja gasta 1 request extra para traer las stats de ese partido.
- **La latencia es ~15 min.** No es inmediato. Si quieres menos, baja
  `GLOBAL_POLL_INTERVAL_SECONDS` en `.env`, pero gastarás más cupo (y a menos de
  ~15 min, 24h no cabe en el plan Free).
- **Las estadísticas solo llegan en ligas grandes** (Premier, LaLiga, Serie A...).
  Ahí el Alert Score sale "con stats" y el `momentum` se llena. Copa Colombia y
  ligas menores salen "sin stats" — es límite del plan Free, no un error.
- **Tu PC debe estar encendido** mientras el radar corre (aún no hay servidor
  24/7). Si apagas el equipo, se corta. Ese es el siguiente paso natural: subirlo
  a un servidor gratis 24/7 (Oracle).
- **El cupo se reinicia a las 7:00 PM hora Colombia** (00:00 UTC).
- **No esperes rojas todos los días.** Son raras. Habrá días con 0 registros. Es
  normal y esperado.

---

## Cuándo volver a retomar el proyecto

Cuando tengas ~**15–20 rojas acumuladas** (míralo con `python backtest.py`, que te
dice cuántos registros cerrados llevas):

- Corremos el backtest en serio y leemos si el Alert Score se asocia con algo.
- Decidimos si:
  - **afinar los pesos** del score,
  - montar el **despliegue 24/7 en Oracle Always Free** (para que no dependa de tu
    PC), o
  - explorar la **Ruta B** (scraping) para cobertura amplia — solo se tocaría la
    capa de datos, gracias al diseño desacoplado.

---

## Recordatorio de qué NO hace este sistema

- No apuesta ni se conecta a ninguna casa (nada de BetPlay).
- No promete ganancias ni calcula valor de apuesta.
- Solo detecta la roja, la puntúa por contexto, te avisa, y guarda el dato.
