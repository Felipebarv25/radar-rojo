# Radar Rojo — Alertas de tarjeta roja a Telegram
## Entrega 1: Investigación, decisiones y roadmap (sin código)

*Fecha: 2026-09-09 · Voz: primera persona, directo, sin garantías · Salida única: Telegram*

---

## 1. Qué es este sistema

Un sistema que vigila partidos de fútbol en vivo y me dispara una alerta a **Telegram** en cuanto cae una **tarjeta roja**.

- **La roja es el ÚNICO gatillo.** Las estadísticas nunca disparan solas.
- Cuando cae la roja, se activa una **segunda capa** que analiza todas las stats disponibles y calcula un **Alert Score de 0 a 100** que mide **fuerza relativa del contexto, NO probabilidad** de nada.
- El sistema queda **preparado para backtesting**.
- **Cero apuestas automáticas. Cero credenciales de BetPlay.** La única frase que emite es "revisar mercados manualmente".

**Sin garantías:** no prometo latencia "inmediata" ni ganarle a la casa de apuestas. Ver sección 5.

---

## 2. Decisiones cerradas (Fase 0)

| Decisión | Elección | Motivo |
|---|---|---|
| **Fuente de datos** | **Ruta A**: free de API-Football, 1 partido a la vez | Único camino gratis y estable para validar TODO el sistema con datos reales. Capa de datos desacoplada para ampliar después. |
| **Servidor 24/7** | **Oracle Cloud Always Free (micro-VM AMD)** | VM real, encendida siempre, gratis indefinido. AMD evita el *out of capacity* del ARM. Pide tarjeta solo para verificar (no cobra). |
| **Salida** | **Telegram, única** | Bot vía @BotFather. |
| **Apuestas** | **Ninguna automatización** | Solo mención de "revisar mercados manualmente". |

---

## 3. La verdad cruda sobre "gratis + todas las ligas"

**No se puede tener a la vez.** El cuello de botella son los DATOS, no el servidor.

| Fuente | Plan gratis | ¿Rojas en vivo? | ¿Cobertura amplia? | Veredicto |
|---|---|---|---|---|
| API-Football | 100 req/**día** | Sí (eventos) | Sí | El cupo mata el vivo: 1 partido a 30s = 180 req. **~1 partido/día** a 60s. |
| football-data.org | 10 llamadas/**minuto** | **NO** (gratis sin tarjetas ni datos de jugador; vivo desde €12/mes) | Solo 12 comps | Le falta justo la roja. |
| SportMonks | Free existe | Sí | **Solo 1–2 ligas** | Cobertura ridícula. |

**Conclusión:** ningún plan oficialmente gratis da rojas en vivo de todas las ligas.
- **Ruta A (elegida):** gratis, estable, cobertura mínima (1 partido). Banco de pruebas real.
- **Ruta B (futura, opcional):** scraping de fuente no oficial = único camino gratis y amplio, pero **frágil** (se rompe con cambios de la web, posible violación de ToS, bloqueo por IP, fiabilidad fuera de mi control).
- **Ruta C (descartada):** ~$12–19/mes = cobertura amplia y estable oficial. Anotada solo por honestidad.

---

## 4. Diseño del Alert Score (0–100, fuerza relativa)

Se calcula **solo tras la roja**, combinando de forma **ponderada y trazable** (cada alerta guarda sus sub-scores para poder afinarlos con backtesting):

| Componente | Qué mide |
|---|---|
| **Quién recibió la roja** | Titular clave vs suplente; posición (central/portero pesa más que extremo). |
| **Minuto** | Roja al 20' ≠ al 88'; cuánto partido queda para que importe. |
| **Marcador** | ¿El expulsado iba ganando, empatando o perdiendo? |
| **Momentum previo** | Posesión, remates, remates a puerta, córners, xG (si está): cómo venía el partido. |
| **Desequilibrio resultante** | Fuerza que la roja *crea* respecto a cómo venía el juego. |

**Es fuerza relativa del contexto. NO es probabilidad de gol/victoria ni valor de apuesta. No lleva EV ni garantías.**

---

## 5. La verdad sobre la latencia

```
Árbitro saca roja
   → el proveedor lo registra        (~10–30 s, a veces más)
   → mi poller detecta el cambio      (0–60 s según intervalo)
   → calculo Alert Score y formateo   (<1 s)
   → Telegram entrega                 (~1 s)
```

**Realista: ~15–60 segundos** desde la jugada. La casa de apuestas suele ir por delante (paga feeds premium). Esto es una **herramienta de asistencia para revisar mercados manualmente**, no arbitraje de milisegundos.

---

## 6. Términos y legalidad

- **Uso personal / análisis interno:** zona permitida. No redistribuyo el feed.
- **Ruta B (scraping):** puede violar ToS de la fuente; decisión de riesgo a tomar con ojos abiertos.
- **BetPlay / casas:** el sistema NUNCA toca credenciales ni ejecuta órdenes. Decisión de arquitectura.
- **Tarea pendiente Fase 1:** leer el ToS de API-Football antes de operar de forma continua.

---

## 7. Telegram (salida)

- Bot creado con **@BotFather** → token. Consigo mi **chat_id** (o id de canal). El bot postea con `sendMessage`.
- **Rate limits** (30 msg/s global, 1 msg/s por chat, 20/min por grupo): holgadísimos para alertas de roja.
- Previsto: cola de salida con **backoff exponencial** ante error 429 (respetar `retry_after`).

---

## 8. Roadmap por fases

- **Fase 0 — Decisiones y contratos** ✅ (esta entrega). Proveedor, servidor, bot Telegram, leer ToS.
- **Fase 1 — Núcleo del gatillo (MVP).** Poller de partido en vivo + detector de "nueva roja" (anti-duplicados) → mensaje simple a Telegram: equipo, jugador, minuto, marcador. Objetivo: **que la roja llegue.**
- **Fase 2 — Segunda capa: Alert Score.** Al detectar roja, recolecto stats y calculo el score 0–100 con pesos configurables. El mensaje incluye desglose + "revisar mercados manualmente".
- **Fase 3 — Persistencia / preparación de backtesting.** Guardo cada roja con su snapshot de stats y su score, en formato re-procesable.
- **Fase 4 — Backtesting.** Motor sobre el histórico para afinar pesos y validar si el score alto correlaciona con algo útil. **Aquí se mide si sirve.**
- **Fase 5 — Robustez y operación.** Caídas del proveedor, reconexión, dedupe robusto, logs, despliegue 24/7 en Oracle.

**Principio de diseño transversal:** la **capa de datos va desacoplada** desde el día uno, para poder cambiar de Ruta A a Ruta B tocando solo la fuente, no el sistema entero.

---

## 9. Riesgos abiertos

- **Cupo del free (100/día):** limita a ~1 partido/día. Es la restricción dura de la Ruta A.
- **Latencia del proveedor** por encima de lo tolerable.
- **Rojas revertidas por VAR:** necesito lógica de "evento revertido".
- **Sin xG** en el tier gratis: el score de Fase 2 arranca sin xG.
- **Ruta B frágil** si algún día ampliamos cobertura.

---

## 10. Próximo paso

Con la Fase 0 cerrada, el siguiente paso (cuando digas "adelante") es la **Fase 1**: montar el gatillo mínimo y probar que una roja real llega a Telegram. Ahí sí empiezo a escribir código.
