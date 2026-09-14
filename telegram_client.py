from __future__ import annotations

import html
import os
import time
from datetime import date, datetime
from typing import Iterable

import requests

from config import REQUEST_TIMEOUT
from models import Opportunity


def _e(value: str | None) -> str:
    return html.escape(value or "")


def _days_until(deadline: str | None) -> int | None:
    if not deadline:
        return None
    try:
        return (date.fromisoformat(deadline) - date.today()).days
    except ValueError:
        return None


def _deadline_label(deadline: str | None) -> str:
    if not deadline:
        return "não identificado automaticamente"
    try:
        d = date.fromisoformat(deadline)
    except ValueError:
        return deadline
    days = (d - date.today()).days
    formatted = d.strftime("%d/%m/%Y")
    if days < 0:
        return f"{formatted} (encerrado há {-days} dia(s))"
    if days == 0:
        return f"{formatted} (encerra HOJE)"
    if days == 1:
        return f"{formatted} (encerra amanhã)"
    return f"{formatted} ({days} dias)"


def opportunity_message(op: Opportunity, kind: str = "new") -> str:
    heading = "🧬 <b>NOVA OPORTUNIDADE</b>" if kind == "new" else "🔄 <b>ATUALIZAÇÃO DE OPORTUNIDADE</b>"
    lines = [heading, f"<b>{_e(op.title)}</b>"]
    if op.state:
        lines.append(f"📍 UF: <b>{_e(op.state)}</b>")
    lines.append(f"🎯 Compatibilidade: <b>{_e(op.fit_label)}</b> (score {op.score})")
    lines.append(f"🔬 Motivo: {_e(op.why)}")
    if op.vacancies_text:
        lines.append(f"👥 Vagas: {_e(op.vacancies_text)}")
    if op.salary_text:
        lines.append(f"💰 Remuneração citada: {_e(op.salary_text)}")
    if op.registration_text:
        lines.append(f"📝 Inscrições: {_e(op.registration_text)}")
    lines.append(f"⏳ Prazo final: <b>{_e(_deadline_label(op.deadline))}</b>")
    if op.exam_text:
        lines.append(f"📚 Prova/etapa: {_e(op.exam_text)}")
    lines.append(f"📰 Fonte: {_e(op.source)}")
    lines.append(f'🔗 <a href="{_e(op.url)}">Abrir matéria</a>')
    if op.official_url:
        lines.append(f'🏛 <a href="{_e(op.official_url)}">Possível link oficial/banca</a>')
    lines.append("\n<i>Confira sempre o edital oficial antes de se inscrever.</i>")
    return "\n".join(lines)


def digest_message(items: list[dict]) -> str:
    today = date.today()
    lines = [f"📅 <b>RESUMO DE PRAZOS — {today.strftime('%d/%m/%Y')}</b>"]
    if not items:
        lines.append("Nenhuma oportunidade ativa com prazo identificado nos próximos dias.")
        return "\n".join(lines)

    lines.append("Oportunidades ordenadas pela data de encerramento:")
    for i, item in enumerate(items, 1):
        deadline = item.get("deadline")
        days = _days_until(deadline)
        icon = "🔴" if days is not None and days <= 3 else "🟠" if days is not None and days <= 7 else "🟢"
        state = f" [{_e(item.get('state'))}]" if item.get("state") else ""
        label = _deadline_label(deadline)
        title = _e(item.get("title", "Oportunidade"))
        url = _e(item.get("url", ""))
        lines.append(f'{i}. {icon} <a href="{url}">{title}</a>{state}\n   ⏳ <b>{_e(label)}</b>')
    return "\n".join(lines)


class TelegramClient:
    def __init__(self) -> None:
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not self.token or not self.chat_id:
            raise RuntimeError("Defina TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.")
        self.endpoint = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send(self, text: str) -> None:
        # Bot API limita sendMessage a 4096 caracteres; quebramos por blocos seguros.
        chunks = []
        while len(text) > 3900:
            cut = text.rfind("\n", 0, 3900)
            if cut < 1000:
                cut = 3900
            chunks.append(text[:cut])
            text = text[cut:].lstrip()
        chunks.append(text)

        for chunk in chunks:
            response = requests.post(
                self.endpoint,
                data={
                    "chat_id": self.chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok"):
                raise RuntimeError(f"Telegram retornou erro: {payload}")
            time.sleep(0.4)
