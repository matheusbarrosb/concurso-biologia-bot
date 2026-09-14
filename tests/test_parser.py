import unittest

from models import Opportunity
from parser import enrich, registration_info, salary_info, score_relevance, split_sentences


class ParserTests(unittest.TestCase):
    def test_registration_deadline_words(self):
        text = "As inscrições vão das 10h de 12 de agosto às 23h59 de 21 de setembro de 2026."
        registration, deadline = registration_info(text)
        self.assertIn("inscrições", registration.lower())
        self.assertEqual(deadline, "2026-09-21")

    def test_registration_deadline_numeric(self):
        text = "Inscrições serão realizadas de 03/09/2026 até 28/09/2026 pela internet."
        _, deadline = registration_info(text)
        self.assertEqual(deadline, "2026-09-28")

    def test_strong_relevance(self):
        score, label, why = score_relevance(
            "Prefeitura abre concurso",
            "Edital com vaga para Biólogo, exigindo Ciências Biológicas e registro no CRBio.",
        )
        self.assertGreaterEqual(score, 12)
        self.assertEqual(label, "Alta")
        self.assertTrue("biólogo" in why.lower() or "ciências biológicas" in why.lower())

    def test_weak_environmental_term_is_not_enough(self):
        score, _, _ = score_relevance(
            "Prefeitura anuncia programa",
            "Projeto sobre meio ambiente para estudantes, sem concurso ou edital.",
        )
        self.assertLess(score, 6)


    def test_line_breaks_are_preserved_for_extraction(self):
        text = (
            "As inscrições serão realizadas até 30 de setembro de 2026.\n"
            "Veja também: outro concurso com inscrições até 15 de outubro de 2026.\n"
        )
        registration, deadline = registration_info(text)
        self.assertIn("30 de setembro", registration.lower())
        self.assertEqual(deadline, "2026-09-30")

    def test_salary_prefers_remuneration_context(self):
        text = (
            "A remuneração para o cargo é de R$ 7.500,00.\n"
            "Veja também: outro concurso com salários de até R$ 20.000,00.\n"
        )
        self.assertEqual(salary_info(text), "R$ 7.500,00")

    def test_enrich(self):
        op = Opportunity(
            source="teste",
            title="Concurso para Biólogo - SP",
            url="https://example.com/1",
            text=(
                "Foi publicado edital de concurso público para Biólogo. "
                "A remuneração é de R$ 7.500,00. "
                "As inscrições ficam abertas até 30 de setembro de 2026. "
                "A prova será aplicada em 18 de outubro de 2026."
            ),
        )
        op = enrich(op)
        self.assertEqual(op.deadline, "2026-09-30")
        self.assertEqual(op.state, "SP")
        self.assertTrue(op.salary_text)
        self.assertTrue(op.exam_text)


if __name__ == "__main__":
    unittest.main()
