# TG — dados aeroportuários auditáveis (SBSJ)

Trabalho de graduação: uma arquitetura baseada em *event sourcing* para tornar dados de infraestrutura aeroportuária **geolocalizados e auditáveis**, com a pista do SBSJ (São José dos Campos) como estudo de caso.

**Comece pelo [GUIA.md](GUIA.md).**

| Pasta | O que é |
|---|---|
| [`artefato/`](artefato/README.md) | a biblioteca Python `aeroledger` — o artefato do TG |
| [`experimento/`](experimento/) | o notebook com os cinco experimentos, que usa a biblioteca passo a passo |
| [`protocolo/`](protocolo/) | o que se previu antes de rodar (v0.4 congelada; v0.5 em rascunho) |
| [`resultados/`](resultados/) | o registro de todas as execuções |

## Rodar

```sh
git clone https://github.com/heyfalheiro1537/tg-sbsj && cd tg-sbsj
pip install -r requirements.txt
scripts/pg_local.sh                           # PostgreSQL local (ou: docker compose up -d)

cd artefato && python3 -m pytest -q && cd ..  # testes da biblioteca
scripts/rodar_experimentos.sh --ensaio        # experimentos com dados fictícios
scripts/rodar_experimentos.sh                 # experimentos oficiais (protocolo v0.5 congelado)
```

## Ressalva

Dados do AIP Brasil (DECEA) usados para pesquisa. Nada aqui substitui a publicação oficial.
