from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

CSV_COLUMNS = [
    "status",
    "prazo",
    "dias_restantes",
    "compatibilidade",
    "score",
    "uf",
    "titulo",
    "salario",
    "vagas",
    "inscricoes",
    "provas_etapas",
    "motivo_relevancia",
    "fonte",
    "link_oficial",
    "link_fonte",
    "primeira_deteccao",
    "ultima_alteracao",
    "notificado_em",
]


def deadline_info(deadline: str | None, today: date | None = None) -> tuple[str, str]:
    """Retorna (status, dias_restantes) para uma data ISO de encerramento."""
    today = today or date.today()
    if not deadline:
        return "SEM PRAZO", ""

    try:
        due = date.fromisoformat(deadline)
    except (TypeError, ValueError):
        return "PRAZO INVÁLIDO", ""

    days = (due - today).days
    if days < 0:
        return "ENCERRADO", str(days)
    if days == 0:
        return "ENCERRA HOJE", "0"
    if days <= 3:
        return "ENCERRA EM ATÉ 3 DIAS", str(days)
    if days <= 7:
        return "ENCERRA EM ATÉ 7 DIAS", str(days)
    if days <= 30:
        return "ABERTO - ATÉ 30 DIAS", str(days)
    return "ABERTO", str(days)


def _row(item: Mapping, today: date) -> dict[str, str | int]:
    status, days_left = deadline_info(item.get("deadline"), today=today)
    return {
        "status": status,
        "prazo": item.get("deadline") or "",
        "dias_restantes": days_left,
        "compatibilidade": item.get("fit_label") or "",
        "score": item.get("score", ""),
        "uf": item.get("state") or "",
        "titulo": item.get("title") or "",
        "salario": item.get("salary_text") or "",
        "vagas": item.get("vacancies_text") or "",
        "inscricoes": item.get("registration_text") or "",
        "provas_etapas": item.get("exam_text") or "",
        "motivo_relevancia": item.get("why") or "",
        "fonte": item.get("source") or "",
        "link_oficial": item.get("official_url") or "",
        "link_fonte": item.get("url") or "",
        "primeira_deteccao": item.get("first_seen") or "",
        "ultima_alteracao": item.get("last_seen") or "",
        "notificado_em": item.get("notified_at") or "",
    }


def export_history_csv(
    items: Iterable[Mapping],
    path: str = "data/concursos.csv",
    today: date | None = None,
) -> Path:
    """Gera um CSV legível a partir dos registros do histórico.

    O arquivo é determinístico: se o histórico não mudar, o conteúdo do CSV também
    não muda. Isso evita commits desnecessários do GitHub Actions.
    """
    today = today or date.today()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    rows = [_row(item, today=today) for item in items]

    # Oportunidades abertas primeiro, ordenadas por prazo; encerradas vão ao fim.
    status_rank = {
        "ENCERRA HOJE": 0,
        "ENCERRA EM ATÉ 3 DIAS": 1,
        "ENCERRA EM ATÉ 7 DIAS": 2,
        "ABERTO - ATÉ 30 DIAS": 3,
        "ABERTO": 4,
        "SEM PRAZO": 5,
        "PRAZO INVÁLIDO": 6,
        "ENCERRADO": 7,
    }
    rows.sort(
        key=lambda r: (
            status_rank.get(str(r["status"]), 99),
            str(r["prazo"]) or "9999-12-31",
            -int(r["score"] or 0),
            str(r["titulo"]).lower(),
        )
    )

    # utf-8-sig deixa acentos abrirem corretamente no Excel sem configuração extra.
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return output
