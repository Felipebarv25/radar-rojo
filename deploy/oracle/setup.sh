#!/usr/bin/env bash
# Instala y arranca Radar Rojo como servicio 24/7 en un servidor Ubuntu.
# Funciona en Oracle (usuario ubuntu) y Google Cloud (tu usuario de Google):
# genera el servicio systemd con el usuario y la ruta reales.
# Correr DENTRO del servidor, desde la carpeta del proyecto:
#   bash deploy/oracle/setup.sh
set -e

echo "==> Instalando Python y dependencias del sistema..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip git

cd "$(dirname "$0")/../.."   # ir a la raíz del proyecto
PROJ="$(pwd)"
RUN_USER="$(whoami)"
PY="$PROJ/.venv/bin/python"
echo "==> Proyecto: $PROJ  ·  usuario: $RUN_USER"

if [ ! -f .env ]; then
  echo "ERROR: falta el archivo .env con tus claves."
  echo "Créalo con:  cp .env.example .env  &&  nano .env"
  exit 1
fi

echo "==> Entorno virtual e instalación de librerías..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements.txt

echo "==> Creando el servicio systemd (24/7, se reinicia solo)..."
sudo tee /etc/systemd/system/radar-rojo.service >/dev/null <<EOF
[Unit]
Description=Radar Rojo - Radar Global 24/7
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJ
ExecStart=$PY run_radar.py --no-startup
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable radar-rojo
sudo systemctl restart radar-rojo

sleep 3
echo "==> Estado del servicio:"
sudo systemctl status radar-rojo --no-pager || true
echo ""
echo "Listo. Ver logs en vivo:  journalctl -u radar-rojo -f"
