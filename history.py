from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models import Opportunity


class History:
    def __init__(self, path: str = "data/history.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {"meta": {"last_digest_date": None}, "items": {}}
        else:
            self.data = {"meta": {"last_digest_date": None}, "items": {}}
        self.data.setdefault("meta", {}).setdefault("last_digest_date", None)
        self.data.setdefault("items", {})

    @property
    def is_empty(self) -> bool:
        return not bool(self.data["items"])

    def status(self, op: Opportunity) -> str:
        old = self.data["items"].get(op.uid)
        if not old:
            return "new"
        if old.get("signature") != op.signature:
            return "updated"
        return "seen"

    def upsert(self, op: Opportunity) -> None:
        now = datetime.now(timezone.utc).isoformat()
        old = self.data["items"].get(op.uid, {})
        record = op.to_record()
        record["first_seen"] = old.get("first_seen", now)
        # Mantém last_seen estável quando nada mudou, evitando commit a cada checagem.
        record["last_seen"] = now if not old or old.get("signature") != op.signature else old.get("last_seen", now)
        record["notified_at"] = old.get("notified_at")
        self.data["items"][op.uid] = record

    def mark_notified(self, op: Opportunity) -> None:
        if op.uid in self.data["items"]:
            self.data["items"][op.uid]["notified_at"] = datetime.now(timezone.utc).isoformat()

    def set_digest_date(self, iso_date: str) -> None:
        self.data["meta"]["last_digest_date"] = iso_date

    def last_digest_date(self) -> str | None:
        return self.data["meta"].get("last_digest_date")

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.path)
