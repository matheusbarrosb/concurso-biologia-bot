"""Descobre o TELEGRAM_CHAT_ID depois que o usuário envia /start ao bot."""
from __future__ import annotations

import json
import os
import sys

import requests


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Defina TELEGRAM_BOT_TOKEN antes de executar.", file=sys.stderr)
        raise SystemExit(2)
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    data = requests.get(url, timeout=25).json()
    if not data.get("ok"):
        print(json.dumps(data, indent=2, ensure_ascii=False))
        raise SystemExit(1)

    found = set()
    for update in data.get("result", []):
        msg = update.get("message") or update.get("channel_post") or {}
        chat = msg.get("chat") or {}
        if "id" in chat:
            found.add((chat["id"], chat.get("type"), chat.get("title") or chat.get("username") or chat.get("first_name")))

    if not found:
        print("Nenhum chat encontrado. Abra o bot no Telegram, envie /start e rode de novo.")
        return
    print("Chats encontrados:")
    for chat_id, kind, name in sorted(found, key=lambda x: str(x[0])):
        print(f"  TELEGRAM_CHAT_ID={chat_id}   tipo={kind}   nome={name}")


if __name__ == "__main__":
    main()
