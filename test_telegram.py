"""Prueba de humo: manda un mensaje de prueba a tu Telegram.

Sirve para confirmar que el token y el chat_id funcionan ANTES de esperar una roja
real. No toca la API de fútbol, así que no gasta cupo.

Uso:
    python test_telegram.py
"""
import config
from src.telegram_notifier import TelegramNotifier


def main():
    config.setup_console()
    config.validate(require_api=False)  # solo necesitamos Telegram aquí
    notifier = TelegramNotifier()
    ok = notifier.send(
        "✅ <b>Prueba de Radar Rojo</b>\n"
        "Si ves esto, el bot y el chat_id están bien configurados.\n"
        "<i>Siguiente paso: elegir un partido en vivo y monitorear.</i>"
    )
    if ok:
        print("OK: mensaje enviado. Revisa tu Telegram.")
    else:
        print("FALLO: no se pudo enviar. Revisa TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env,")
        print("y que le hayas dado /start a tu bot desde tu cuenta.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
