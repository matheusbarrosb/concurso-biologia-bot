import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from csv_export import deadline_info, export_history_csv


class CsvExportTests(unittest.TestCase):
    def test_deadline_statuses(self):
        today = date(2026, 9, 13)
        self.assertEqual(deadline_info("2026-09-13", today), ("ENCERRA HOJE", "0"))
        self.assertEqual(deadline_info("2026-09-15", today), ("ENCERRA EM ATÉ 3 DIAS", "2"))
        self.assertEqual(deadline_info("2026-09-20", today), ("ENCERRA EM ATÉ 7 DIAS", "7"))
        self.assertEqual(deadline_info("2026-10-01", today), ("ABERTO - ATÉ 30 DIAS", "18"))
        self.assertEqual(deadline_info("2026-09-01", today), ("ENCERRADO", "-12"))
        self.assertEqual(deadline_info(None, today), ("SEM PRAZO", ""))

    def test_export_contains_all_rows_and_orders_active_first(self):
        items = [
            {
                "deadline": "2026-08-01",
                "fit_label": "Boa",
                "score": 10,
                "state": "SP",
                "title": "Concurso antigo",
                "url": "https://example.com/antigo",
            },
            {
                "deadline": "2026-09-15",
                "fit_label": "Alta",
                "score": 12,
                "state": "RJ",
                "title": "Biólogo",
                "salary_text": "R$ 7.000,00",
                "url": "https://example.com/biologo",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "concursos.csv"
            export_history_csv(items, str(path), today=date(2026, 9, 13))
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["titulo"], "Biólogo")
        self.assertEqual(rows[0]["status"], "ENCERRA EM ATÉ 3 DIAS")
        self.assertEqual(rows[0]["dias_restantes"], "2")
        self.assertEqual(rows[1]["status"], "ENCERRADO")


if __name__ == "__main__":
    unittest.main()
