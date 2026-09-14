from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Iterable, Optional

from config import PUBLIC_SELECTION_TERMS, RELATED_TERMS, STRONG_TERMS
from models import Opportunity

MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

STATE_RE = re.compile(r"(?:\s|-|\()([A-Z]{2})(?:\)|\s|:|$)")
MONEY_RE = re.compile(r"R\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})?")
VACANCY_RE = re.compile(
    r"\b(?:\d{1,5}\s+(?:vagas?|oportunidades?)|cadastro\s+(?:de\s+)?reserva|CR)\b",
    flags=re.I,
)
DATE_NUMERIC_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
DATE_WORD_RE = re.compile(
    r"\b(\d{1,2})\s+de\s+"
    r"(janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
    r"(?:\s+de\s+(\d{4}))?\b",
    flags=re.I,
)


def normalize(text: str) -> str:
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def clean_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    # Preserva quebras de linha do HTML extraído. Antes elas eram removidas por
    # clean_space(), o que podia juntar o conteúdo principal com menus/rodapés e
    # gerar trechos enormes em inscrições/salário.
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [clean_space(part) for part in parts if clean_space(part)]


def extract_dates(text: str, default_year: Optional[int] = None) -> list[date]:
    dates: list[date] = []
    for d, m, y in DATE_NUMERIC_RE.findall(text):
        try:
            dates.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass

    word_matches = list(DATE_WORD_RE.finditer(text))
    explicit_years = [int(m.group(3)) for m in word_matches if m.group(3)]
    fallback_year = default_year or (explicit_years[-1] if explicit_years else date.today().year)
    for m in word_matches:
        day = int(m.group(1))
        month = MONTHS[m.group(2).lower()]
        year = int(m.group(3)) if m.group(3) else fallback_year
        try:
            dates.append(date(year, month, day))
        except ValueError:
            pass
    return dates


def sentence_for(text: str, needles: Iterable[str], max_chars: int = 360) -> Optional[str]:
    normalized_needles = [normalize(n) for n in needles]
    for sentence in split_sentences(text):
        ns = normalize(sentence)
        if any(n in ns for n in normalized_needles):
            return clean_space(sentence)[:max_chars]
    return None


def registration_info(text: str) -> tuple[Optional[str], Optional[str]]:
    sentences = split_sentences(text)
    candidates = []
    for s in sentences:
        ns = normalize(s)
        if "inscri" in ns and any(k in ns for k in ["ate", "periodo", "realiz", "abert", "encerr", "prazo"]):
            candidates.append(s)

    if not candidates:
        candidates = [s for s in sentences if "inscri" in normalize(s)]

    for sentence in candidates[:5]:
        dates = extract_dates(sentence)
        if dates:
            # Em frases de período de inscrição, a última data costuma ser o encerramento.
            deadline = max(dates)
            return clean_space(sentence)[:420], deadline.isoformat()

    return (clean_space(candidates[0])[:420], None) if candidates else (None, None)


def exam_info(text: str) -> Optional[str]:
    for sentence in split_sentences(text):
        ns = normalize(sentence)
        if "prova" in ns and (extract_dates(sentence) or "previst" in ns or "aplic" in ns):
            return clean_space(sentence)[:360]
    return None


def salary_info(text: str) -> Optional[str]:
    # Prefere linhas que realmente falam de remuneração; procurar no documento
    # inteiro pode capturar salários de cards de "veja também" da página.
    salary_needles = (
        "remunera", "salário", "salario", "vencimento", "subsídio", "subsidio",
        "valor mensal", "bolsa",
    )
    contextual = []
    for sentence in split_sentences(text):
        ns = normalize(sentence)
        if any(normalize(k) in ns for k in salary_needles) and MONEY_RE.search(sentence):
            contextual.append(sentence)

    # A primeira linha contextual costuma ser o trecho do próprio edital.
    # Evitar concatenar várias linhas impede misturar salários de cards laterais.
    search_text = contextual[0] if contextual else text[:5000]
    values = MONEY_RE.findall(search_text)
    if not values:
        return None

    unique = []
    for v in values:
        if v not in unique:
            unique.append(v)
    if len(unique) == 1:
        return unique[0]
    return f"{unique[0]} a {unique[-1]}"


def vacancy_info(text: str) -> Optional[str]:
    matches = VACANCY_RE.findall(text)
    if not matches:
        return None
    unique = []
    for m in matches:
        m = clean_space(m)
        if m.lower() not in [x.lower() for x in unique]:
            unique.append(m)
    return ", ".join(unique[:3])


def infer_state(title: str, text: str) -> Optional[str]:
    for source in [title, text[:800]]:
        found = STATE_RE.search(source)
        if found:
            return found.group(1)
    return None


def score_relevance(title: str, text: str) -> tuple[int, str, str]:
    full = clean_space(f"{title}. {text}")
    nfull = normalize(full)
    score = 0
    reasons = []

    # Evita pontuar duas vezes variantes que ficam idênticas após remover acentos.
    strong_normalized: dict[str, tuple[str, int]] = {}
    for term, points in STRONG_TERMS.items():
        key = normalize(term)
        current = strong_normalized.get(key)
        if current is None or points > current[1]:
            strong_normalized[key] = (term, points)

    for key, (term, points) in strong_normalized.items():
        if key in nfull:
            score += points
            reasons.append(term)

    related_hits = []
    related_normalized: dict[str, tuple[str, int]] = {}
    for term, points in RELATED_TERMS.items():
        key = normalize(term)
        current = related_normalized.get(key)
        if current is None or points > current[1]:
            related_normalized[key] = (term, points)

    for key, (term, points) in related_normalized.items():
        if key in nfull:
            score += points
            related_hits.append(term)

    selection = any(normalize(term) in nfull for term in PUBLIC_SELECTION_TERMS)
    if selection:
        score += 2
    else:
        score -= 3

    # Termos ambientais amplos sozinhos não bastam; eles devem vir com evidência
    # de Biologia/formação compatível ou múltiplos indícios ambientais.
    has_strong = bool(reasons)
    if not has_strong and len(related_hits) < 2:
        score = min(score, 4)

    # Dá prioridade a menções no título.
    ntitle = normalize(title)
    if any(normalize(t) in ntitle for t in ["biólogo", "biologo", "biologia", "ciências biológicas", "ciencias biologicas"]):
        score += 4

    if score >= 12:
        label = "Alta"
    elif score >= 8:
        label = "Boa"
    else:
        label = "Possível"

    matched = reasons + related_hits
    matched = list(dict.fromkeys(matched))
    why = ", ".join(matched[:5]) if matched else "termos ambientais relacionados"
    return score, label, why


def enrich(op: Opportunity) -> Opportunity:
    score, fit, why = score_relevance(op.title, op.text)
    op.score = score
    op.fit_label = fit
    op.why = why
    op.registration_text, op.deadline = registration_info(op.text)
    op.exam_text = exam_info(op.text)
    op.salary_text = salary_info(op.text)
    op.vacancies_text = vacancy_info(op.text)
    op.state = op.state or infer_state(op.title, op.text)
    return op
