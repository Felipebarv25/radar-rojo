"""Carga y valida la configuración desde el archivo .env local.

Ninguna clave va escrita en el código. Todo vive en .env (que está en .gitignore).
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
API_FOOTBALL_BASE_URL = os.getenv(
    "API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io"
).strip().rstrip("/")

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "75"))
# Radar Global: escanea TODOS los partidos en vivo con 1 request por ciclo.
# 15 min (900s) -> ~96 requests/día si corre 24h; el guardián de cupo protege.
GLOBAL_POLL_INTERVAL_SECONDS = int(os.getenv("GLOBAL_POLL_INTERVAL_SECONDS", "900"))
MAX_REQUESTS_PER_DAY = int(os.getenv("MAX_REQUESTS_PER_DAY", "95"))


def setup_console() -> None:
    """Evita que un emoji o una tilde crashee la consola de Windows (cp1252).

    Pone stdout/stderr en UTF-8. Si la consola no lo soporta, reemplaza el
    carácter en vez de reventar.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

_PLACEHOLDERS = {
    "pega_aqui_el_token_de_BotFather",
    "pega_aqui_tu_api_key",
    "",
}


def validate(require_api: bool = True) -> None:
    """Corta con un mensaje claro si falta alguna clave.

    require_api=False permite validar solo lo de Telegram (para la prueba de humo).
    """
    faltan = []
    if TELEGRAM_BOT_TOKEN in _PLACEHOLDERS:
        faltan.append("TELEGRAM_BOT_TOKEN")
    if TELEGRAM_CHAT_ID in _PLACEHOLDERS:
        faltan.append("TELEGRAM_CHAT_ID")
    if require_api and API_FOOTBALL_KEY in _PLACEHOLDERS:
        faltan.append("API_FOOTBALL_KEY")

    if faltan:
        print(
            "ERROR: faltan claves en tu archivo .env: " + ", ".join(faltan) + "\n"
            "Copia .env.example a .env y rellena tus valores reales.",
            file=sys.stderr,
        )
        raise SystemExit(1)
