# 🧬 Bot de concursos para Biologia no Telegram

Monitor nacional de concursos públicos e processos seletivos potencialmente adequados a profissionais de Biologia. Ele busca oportunidades, calcula relevância, extrai prazos, evita alertas repetidos, mantém histórico e envia um resumo diário de datas no Telegram.

## O que esta versão faz

- cobre o Brasil inteiro, sem filtro por estado;
- procura **Biólogo, Biologia, Ciências Biológicas** e áreas relacionadas;
- inclui oportunidades como **Analista Ambiental, Especialista/Fiscal Ambiental, Biodiversidade, Ecologia, Licenciamento, Professor de Biologia/Ciências, Pesquisador e Perícia** quando o texto traz evidências suficientes;
- usa **PCI Concursos** como fonte de busca por cargo/termo e **Concursos no Brasil** como segunda fonte de notícias recentes;
- guarda `data/history.json`, evitando reenviar a mesma matéria sem mudança;
- detecta alterações importantes (prazo, inscrição, prova, salário etc.) e envia como atualização;
- resume inscrições, data-limite, provas/etapas, salário e vagas quando esses dados aparecem no texto;
- envia pela manhã um **resumo de prazos**, ordenado por data de encerramento;
- roda automaticamente pelo GitHub Actions às **08:30 e 18:30 de Brasília**.

> O parser é deliberadamente conservador: se uma página usa uma redação incomum, algum campo pode ficar como “não identificado automaticamente”. O link da fonte continua sendo enviado para conferência. Sempre valide no edital oficial.

---

## 1. Criar o bot no Telegram

1. No Telegram, abra `@BotFather`.
2. Envie `/newbot`.
3. Escolha nome e username.
4. O BotFather fornecerá um token parecido com `123456:ABC...`.
5. **Não coloque esse token no código nem no histórico.**
6. Abra o bot recém-criado e envie `/start`.

## 2. Descobrir seu `chat_id`

No seu computador, dentro desta pasta:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN='COLE_O_TOKEN_AQUI'
python get_chat_id.py
```

O script mostrará algo como:

```text
TELEGRAM_CHAT_ID=123456789
```

No Windows PowerShell, em vez de `export`, use:

```powershell
$env:TELEGRAM_BOT_TOKEN="COLE_O_TOKEN_AQUI"
```

## 3. Testar localmente

```bash
export TELEGRAM_BOT_TOKEN='...'
export TELEGRAM_CHAT_ID='123456789'
python bot.py
```

Na primeira execução ele guarda tudo que encontrou, mas limita a quantidade de mensagens iniciais para não inundar o Telegram.

## 4. Colocar no GitHub e deixar gratuito

1. Crie um repositório no GitHub (público é suficiente; privado também funciona enquanto houver cota de Actions disponível na sua conta).
2. Envie todos estes arquivos para o repositório, inclusive `.github/workflows/concursos.yml` e `data/history.json`.
3. No GitHub, abra **Settings → Secrets and variables → Actions**.
4. Crie dois *Repository secrets*:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Abra **Actions → Monitorar concursos de Biologia → Run workflow** para testar manualmente.
6. Depois disso, o agendamento executará automaticamente duas vezes ao dia.

O workflow tem `permissions: contents: write` porque o próprio robô faz commit de `data/history.json` quando há mudança relevante, preservando o histórico entre execuções. O token do Telegram e o `chat_id` permanecem em Secrets e não são commitados.

## Estrutura

```text
.
├── .github/workflows/concursos.yml
├── bot.py
├── config.py
├── get_chat_id.py
├── history.py
├── models.py
├── parser.py
├── sources.py
├── telegram_client.py
├── requirements.txt
├── data/history.json
└── tests/test_parser.py
```

## Ajustar sensibilidade

Em `config.py`:

- `DISCOVERY_TERMS`: termos pesquisados;
- `STRONG_TERMS`: evidências fortes de compatibilidade com Biologia;
- `RELATED_TERMS`: áreas correlatas;
- `MIN_RELEVANCE_SCORE`: aumente para receber menos alertas e diminuir falsos positivos; reduza para ser mais abrangente;
- `DIGEST_DAYS_AHEAD`: quantos dias futuros entram no resumo de prazos.

## Horários

GitHub Actions usa cron em UTC. O arquivo atual usa:

- `30 11 * * *` → 08:30 em Brasília;
- `30 21 * * *` → 18:30 em Brasília.

O horário oficial de Brasília é UTC-3 e não usa horário de verão atualmente.

## Limitações e melhorias recomendadas

1. Sites podem mudar HTML; por isso cada fonte fica isolada em `sources.py` e uma falha não impede as outras.
2. Nem toda notícia exibe no texto a formação aceita; vagas ambientais amplas podem exigir conferência do edital.
3. A detecção de prazo é heurística. Retificações e prorrogações são tratadas como atualização quando alteram os campos extraídos.
4. A próxima melhoria mais valiosa é adicionar adaptadores de fontes oficiais/diários oficiais e uma lista de bancas, mantendo as duas fontes agregadoras para descoberta rápida.

## Segurança

- nunca comite `TELEGRAM_BOT_TOKEN`;
- mantenha o token apenas nos GitHub Actions Secrets;
- se o token vazar, revogue-o no BotFather e gere outro;
- o histórico contém apenas informações públicas dos concursos encontrados.

## CSV legível do histórico

A cada execução, o bot também gera `data/concursos.csv` com todas as oportunidades do histórico. O arquivo inclui status do prazo, dias restantes, compatibilidade, score, UF, título, salário, vagas, inscrições, etapas/provas e links. O GitHub Actions versiona esse CSV junto com `data/history.json`, então ele pode ser aberto ou baixado diretamente pelo repositório.
