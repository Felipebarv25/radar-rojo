# Despliegue 24/7 en Oracle Cloud (Always Free)

Deja el Radar Global corriendo **fiable, 24/7, sin tu PC**, en un servidor Linux
gratis de Oracle. A diferencia de GitHub Actions, aquí es un proceso propio que
**no se salta turnos**.

> **Gratis de verdad ($0)** si nos quedamos en Always Free — usamos 1 VM micro, que
> es Always Free. Oracle pide **tarjeta para verificar identidad** (retención
> temporal ~$1 que se devuelve; no cobran mientras estés en Always Free).

---

## Parte A — Crear la cuenta y la máquina (lo haces tú)

1. Entra a **oracle.com/cloud/free**, pulsa **Start for free** y regístrate.
   - Verifica correo y teléfono. Pon la **tarjeta** (solo verificación, no cobro).
   - Elige una región cercana (ej. **US East (Ashburn)** o **Brazil/São Paulo**).

2. Ya dentro de la consola de Oracle: menú **☰ → Compute → Instances → Create instance**.
   - **Name:** `radar-rojo`
   - **Image:** deja **Canonical Ubuntu** (22.04 o 24.04).
   - **Shape:** pulsa **Change shape → Ampere** puede dar "out of capacity"; para
     evitarlo elige **Specialty and previous generation → VM.Standard.E2.1.Micro**
     (AMD, **Always Free**, siempre disponible).
   - **SSH keys:** deja **Generate a key pair for me** y **descarga la clave
     privada** (un archivo `.key` o `.pem`). Guárdala bien; sin ella no entras.
   - **Create.** Espera a que la instancia quede **Running** y anota su
     **Public IP address**.

3. **Abrir el firewall** (para que el server pueda salir a internet ya está; no
   necesitas abrir puertos de entrada porque el radar solo hace salidas). No hay
   que tocar nada más de red.

---

## Parte B — Conectarte por SSH (desde tu PC)

Windows 10/11 ya trae `ssh`. Abre PowerShell donde guardaste la clave y corre
(reemplaza la ruta de la clave y la IP):

```powershell
ssh -i "C:\ruta\a\tu-clave.key" ubuntu@LA_IP_PUBLICA
```

La primera vez pregunta si confías en el host → escribe `yes`. Si se queja de
permisos de la clave, en Linux/Mac sería `chmod 600`; en Windows suele entrar igual.

Ya dentro verás algo como `ubuntu@radar-rojo:~$`.

---

## Parte C — Instalar el radar en el servidor

Dentro del servidor (por SSH), corre esto **línea por línea**:

```bash
# 1) Traer el código (repo público)
git clone https://github.com/Felipebarv25/radar-rojo.git
cd radar-rojo

# 2) Crear el .env con tus claves (NO está en el repo, por seguridad)
cp .env.example .env
nano .env
```

En `nano`: pega tu **TELEGRAM_BOT_TOKEN** y tu **API_FOOTBALL_KEY** (el chat_id ya
está puesto). Guarda con **Ctrl+O, Enter** y sal con **Ctrl+X**.

```bash
# 3) Instalar y arrancar como servicio 24/7
bash deploy/oracle/setup.sh
```

Al final debe decir `active (running)`. ✅ Ya está corriendo solo.

---

## Parte D — Apagar el GitHub Actions (para no duplicar)

Como ahora manda Oracle, hay que **apagar** el radar de GitHub (si no, correrían
dos a la vez, con alertas dobles y cupo peleado):

- En **github.com/Felipebarv25/radar-rojo → Actions → "Radar Rojo"** → botón **···**
  → **Disable workflow**.

---

## Cómo controlarlo (comandos en el servidor)

```bash
sudo systemctl status radar-rojo     # ¿está corriendo?
journalctl -u radar-rojo -f          # ver logs en vivo (Ctrl+C para salir)
sudo systemctl restart radar-rojo    # reiniciar
sudo systemctl stop radar-rojo       # pausar
```

El servicio arranca solo con la máquina y **se reinicia solo si falla**. Aunque
Oracle reinicie el servidor, el radar vuelve.

---

## Recordatorios honestos

- **Adaptativo:** escanea seguido (~10 min) cuando hay partidos en vivo a cualquier
  hora, y descansa cuando no hay. Respeta el cupo de 100/día.
- Sigue **sin ser <10s** ni ganarle a la casa. Es cobertura fiable, no tiempo real.
- Mantén la cuenta dentro de **Always Free** para que siga en $0.
