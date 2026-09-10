# Despliegue 24/7 en GitHub Actions

Esta guía deja el **Radar Global corriendo solo en la nube de GitHub**, gratis, sin
tu PC encendido y sin tarjeta. Un escaneo cada ~15 min.

> **Cómo funciona:** GitHub ejecuta `radar_cycle.py` cada 15 min. El estado (qué
> rojas ya avisó, cuáles sigue, el cupo del día, y el histórico de rojas) se guarda
> en el propio repositorio entre corridas. Tus 3 claves viven en "GitHub Secrets",
> **nunca** en el código.

> **Honestidad sobre la latencia:** el cron de GitHub es *best-effort*. Bajo carga
> puede retrasarse varios minutos o saltarse un ciclo. La latencia real puede pasar
> de 15 min. Es el precio de que sea gratis y sin servidor.

---

## Parte A — Crear cuenta de GitHub (si no tienes)

1. Entra a **github.com** y regístrate (correo + contraseña). Verifica el correo.
   *(Esto lo haces tú: yo no puedo crear cuentas ni poner contraseñas.)*

---

## Parte B — Subir el proyecto a un repositorio

La forma más fácil sin pelear con comandos es **GitHub Desktop**:

1. Descarga e instala **GitHub Desktop** (desktop.github.com) e inicia sesión con
   tu cuenta.
2. Menú **File → Add local repository** → elige la carpeta
   `C:\Users\USER\OneDrive\Documentos\10. Radar Rojo`.
3. Si te dice que no es un repositorio git, pulsa **"create a repository"** (crear
   uno aquí). Deja el nombre `radar-rojo`.
4. **IMPORTANTE:** en la lista de archivos a subir, confirma que **NO aparece
   `.env`**. No debe aparecer (está protegido por `.gitignore`). Si lo ves, **para
   y avísame** — ese archivo tiene tus claves y no puede subir.
5. Escribe un resumen (ej. "primer commit") y pulsa **Commit to main**.
6. Pulsa **Publish repository** (arriba a la derecha).
   - **Recomendado: repositorio PÚBLICO.** Razón honesta: los repos privados solo
     dan ~2000 minutos de Actions al mes, y a 15 min el radar se queda corto a fin
     de mes. En público, los minutos son **ilimitados**. En el repo no hay secretos
     (van aparte), solo el código y los datos de rojas — nada sensible.
   - Si prefieres **privado**, funciona, pero abre el archivo
     `.github/workflows/radar.yml` y cambia `cron: "*/15 * * * *"` por
     `cron: "*/30 * * * *"` (cada 30 min) para no pasarte del límite mensual.

*(Alternativa por consola, si prefieres git: `git init`, `git add -A`,
`git commit -m "primer commit"`, `git branch -M main`, `git remote add origin <URL>`,
`git push -u origin main`. Necesitarás un Personal Access Token para el push.)*

---

## Parte C — Cargar tus 3 claves como Secrets

En la página de tu repo en github.com:

1. **Settings** (del repo) → menú izquierdo **Secrets and variables → Actions**.
2. Botón **New repository secret**. Crea estos tres, uno por uno (nombre EXACTO):

   | Name | Secret (valor) |
   |------|----------------|
   | `TELEGRAM_BOT_TOKEN` | tu token de BotFather |
   | `TELEGRAM_CHAT_ID` | `6806509153` |
   | `API_FOOTBALL_KEY` | tu API key de api-sports.io |

   Pega cada valor y **Add secret**. No se vuelven a ver: quedan guardados y ocultos.

---

## Parte D — Encender y probar

1. En tu repo, pestaña **Actions**. Si te pide habilitar los workflows, acepta
   (**"I understand my workflows, go ahead and enable them"**).
2. En la lista de la izquierda, entra a **"Radar Rojo (Radar Global)"**.
3. Botón **Run workflow** (derecha) → **Run workflow**. Esto lo ejecuta a mano ya
   mismo, sin esperar los 15 min.
4. A los ~30–60 seg aparece la corrida. Ábrela y mira el paso **"Escanear"**:
   - La **primera** corrida dice `[PRIME (sin avisos)]` — normal, no manda alertas
     (solo memoriza las rojas que ya existían para no spamearte).
   - A partir de la segunda, dice `[normal]` y ya avisa rojas nuevas.
5. Verás que aparece un commit automático "state: ..." — es el radar guardando su
   memoria. Eso confirma que todo enlazó.

De ahí en adelante **corre solo cada 15 min**, día y noche, sin que hagas nada.

---

## Cómo vigilarlo y controlarlo

- **Ver que sigue vivo:** pestaña **Actions** → ves la lista de corridas cada 15 min
  (✓ verde = ok).
- **Pausarlo:** Actions → "Radar Rojo" → botón **···** → **Disable workflow**.
  Reactívalo con **Enable workflow**.
- **Revisar los datos de rojas / backtest:** los registros se guardan en la carpeta
  `data/red_cards/` del repo. Puedes descargar el repo actualizado (en GitHub
  Desktop: **Fetch/Pull**) y correr `python backtest.py` en tu PC como siempre.

---

## Recordatorios honestos

- **Latencia real ~15 min o más** (el cron de GitHub no es exacto). No es inmediato.
- **Stats solo en ligas grandes** — en Copa Colombia y menores el score sale "sin
  stats". Límite del plan Free, no un error.
- **Sigue sin ser una máquina de dinero.** Es asistencia para revisar mercados a
  mano. Sin garantías.
