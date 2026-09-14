from __future__ import annotations

import logging
import os
from datetime import date

from csv_export import export_history_csv
from config import (
    DIGEST_DAYS_AHEAD,
    DIGEST_MAX_ITEMS,
    MAX_INITIAL_ALERTS,
    MAX_NEW_ALERTS_PER_RUN,
    MIN_RELEVANCE_SCORE,
)
from history import History
from parser import enrich
from sources import collect_all
from telegram_client import TelegramClient, digest_message, opportunity_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("concurso-bio")


def sort_key(op):
    deadline = op.deadline or "9999-12-31"
    return (deadline, -op.score, op.title.lower())


def main() -> None:
    history = History()
    first_run = history.is_empty
    telegram = TelegramClient()

    raw = collect_all()
    relevant = []
    seen_urls = set()
    for op in raw:
        op = enrich(op)
        if op.url in seen_urls or op.score < MIN_RELEVANCE_SCORE:
            continue
        seen_urls.add(op.url)
        relevant.append(op)

    relevant.sort(key=sort_key)
    log.info("%d oportunidades relevantes de %d artigos", len(relevant), len(raw))

    changes = []
    for op in relevant:
        status = history.status(op)
        history.upsert(op)
        if status in {"new", "updated"}:
            changes.append((op, status))

    # IMPORTANTE: seleciona alertas apenas entre oportunidades ainda ativas.
    # Antes, concursos expirados vinham primeiro na ordenação por data e podiam
    # ocupar todo o limite inicial, fazendo o bot não enviar nenhuma vaga atual.
    today_iso = date.today().isoformat()
    actionable_changes = [
        (op, status)
        for op, status in changes
        if not op.deadline or op.deadline >= today_iso
    ]

    if first_run and actionable_changes:
        telegram.send(
            "🧬 <b>Monitor de concursos para Biologia ativado</b>\n"
            f"Encontrei {len(relevant)} oportunidades relevantes no primeiro rastreio, "
            f"das quais {len(actionable_changes)} são novas/alteradas e não estão claramente expiradas. "
            f"Para evitar uma enxurrada de mensagens, vou mostrar agora até {MAX_INITIAL_ALERTS} "
            "das mais urgentes/relevantes e guardar todas no histórico."
        )
        selected = actionable_changes[:MAX_INITIAL_ALERTS]
    else:
        selected = actionable_changes[:MAX_NEW_ALERTS_PER_RUN]

    for op, status in selected:
        telegram.send(opportunity_message(op, status))
        history.mark_notified(op)

    if len(actionable_changes) > len(selected):
        telegram.send(
            f"ℹ️ Houve {len(actionable_changes)} novidades/alterações ativas; "
            f"enviei {len(selected)} nesta rodada para evitar excesso de mensagens. "
            "Todas ficaram registradas no histórico."
        )

    send_digest = os.environ.get("SEND_DAILY_DIGEST", "true").strip().lower() in {"1", "true", "yes", "sim"}
    if send_digest:
        digest = []
        for item in history.data["items"].values():
            deadline = item.get("deadline")
            if not deadline:
                continue
            try:
                days = (date.fromisoformat(deadline) - date.today()).days
            except ValueError:
                continue
            if 0 <= days <= DIGEST_DAYS_AHEAD:
                digest.append(item)
        digest.sort(key=lambda x: (x.get("deadline", "9999-12-31"), -int(x.get("score", 0))))
        telegram.send(digest_message(digest[:DIGEST_MAX_ITEMS]))

    history.save()
    csv_path = export_history_csv(history.data["items"].values())
    log.info("Histórico salvo em data/history.json")
    log.info("CSV atualizado em %s", csv_path)


if __name__ == "__main__":
    main()
