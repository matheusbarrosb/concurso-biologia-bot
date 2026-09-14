from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Optional


@dataclass
class Opportunity:
    source: str
    title: str
    url: str
    text: str
    published_at: Optional[str] = None
    official_url: Optional[str] = None
    state: Optional[str] = None
    score: int = 0
    fit_label: str = "Possível"
    why: str = ""
    registration_text: Optional[str] = None
    deadline: Optional[str] = None  # ISO yyyy-mm-dd
    exam_text: Optional[str] = None
    salary_text: Optional[str] = None
    vacancies_text: Optional[str] = None

    @property
    def uid(self) -> str:
        normalized = self.url.strip().rstrip("/").lower()
        return sha256(normalized.encode("utf-8")).hexdigest()[:24]

    @property
    def signature(self) -> str:
        important = "|".join(
            [
                self.title or "",
                self.deadline or "",
                self.registration_text or "",
                self.exam_text or "",
                self.salary_text or "",
                self.vacancies_text or "",
                str(self.score),
            ]
        )
        return sha256(important.encode("utf-8")).hexdigest()[:20]

    def to_record(self) -> dict:
        d = asdict(self)
        d.pop("text", None)
        d["uid"] = self.uid
        d["signature"] = self.signature
        return d
