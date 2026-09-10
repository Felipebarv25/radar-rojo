"""Salida a Telegram (única salida del sistema).

Envía mensajes con sendMessage. Maneja el error 429 (rate limit) respetando
retry_after con un par de reintentos. Para alertas de roja esto sobra de holgado.
"""
import time

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramNotifier:
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    def send(self, text: str, max_retries: int = 3) -> bool:
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        for intento in range(1, max_retries + 1):
            resp = requests.post(self.api_url, json=payload, timeout=15)
            if resp.status_code == 200:
                return True
            if resp.status_code == 429:
                retry_after = resp.json().get("parameters", {}).get("retry_after", 2)
                espera = retry_after + intento  # backoff con algo de margen
                print(f"[Telegram] 429 rate limit, reintento en {espera}s...")
                time.sleep(espera)
                continue
            # Otros errores: no reintentar a ciegas, mostrar el motivo.
            print(f"[Telegram] Error {resp.status_code}: {resp.text[:300]}")
            return False
        print("[Telegram] Agotados los reintentos por rate limit.")
        return False
