"""Configuração do monitor de concursos para profissionais de Biologia."""

# Termos usados para descobrir editais/notícias. A filtragem final é feita por score,
# então termos amplos não são enviados automaticamente só por terem aparecido na busca.
DISCOVERY_TERMS = [
    "biólogo",
    "biologo",
    "biologia",
    "ciências biológicas",
    "ciencias biologicas",
    "analista ambiental",
    "especialista ambiental",
    "fiscal ambiental",
    "meio ambiente",
    "biodiversidade",
    "ecologia",
    "licenciamento ambiental",
    "professor biologia",
    "professor ciências",
    "pesquisador biologia",
    "perito biologia",
]

# Evidências muito fortes de que uma vaga é adequada para alguém formado em Biologia.
STRONG_TERMS = {
    "biólogo": 8,
    "biologo": 8,
    "ciências biológicas": 8,
    "ciencias biologicas": 8,
    "graduação em biologia": 9,
    "graduacao em biologia": 9,
    "formação em biologia": 9,
    "formacao em biologia": 9,
    "registro no crbio": 9,
    "crbio": 7,
}

# Áreas que podem aceitar biólogos, mas exigem evidência adicional para reduzir ruído.
RELATED_TERMS = {
    "analista ambiental": 3,
    "especialista ambiental": 3,
    "fiscal ambiental": 3,
    "analista de meio ambiente": 3,
    "licenciamento ambiental": 2,
    "biodiversidade": 2,
    "ecologia": 2,
    "zoologia": 2,
    "botânica": 2,
    "botanica": 2,
    "microbiologia": 2,
    "biotecnologia": 2,
    "genética": 2,
    "genetica": 2,
    "conservação": 2,
    "conservacao": 2,
    "gestão ambiental": 1,
    "gestao ambiental": 1,
    "meio ambiente": 1,
    "recursos naturais": 1,
    "fauna": 1,
    "flora": 1,
    "perito criminal": 1,
    "pesquisador": 1,
    "professor de biologia": 4,
    "professor de ciências": 3,
    "professor de ciencias": 3,
}

# Palavras que confirmam que se trata de seleção pública/oportunidade real.
PUBLIC_SELECTION_TERMS = [
    "concurso público",
    "concurso publico",
    "processo seletivo",
    "seleção pública",
    "selecao publica",
    "edital",
    "cadastro reserva",
    "cadastro de reserva",
]

MIN_RELEVANCE_SCORE = 6
REQUEST_TIMEOUT = 25
REQUEST_DELAY_SECONDS = 0.8
MAX_ARTICLES_PER_DISCOVERY_TERM = 8
MAX_RECENT_ARTICLES_SECONDARY_SOURCE = 45
MAX_INITIAL_ALERTS = 12
MAX_NEW_ALERTS_PER_RUN = 20
DIGEST_DAYS_AHEAD = 30
DIGEST_MAX_ITEMS = 18

USER_AGENT = (
    "Mozilla/5.0 (compatible; ConcursoBiologiaBot/1.0; "
    "+https://github.com/matheusbarrosb/concurso-biologia-bot)"
)
